"""
Wazuh SIEM integration blueprint.

Provides a SOC-focused dashboard at ``/integrations/wazuh`` plus a JSON API
for alerts, treatment workflow, AI analysis, stats, sync control, and
report export. Config management is admin-only and reuses the
``SyncMetadata`` key/value store (see :mod:`app.services.wazuh`).
"""
from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime, timezone, timedelta

from flask import (
    Blueprint, render_template, request, jsonify, Response,
    current_app, abort,
)
from flask_login import login_required, current_user
from sqlalchemy import func, and_, or_, desc

from app.extensions.db import db
from app.models.auth import User
from app.models.wazuh import WazuhAlert, WazuhTreatmentNote
from app.models.wazuh.wazuh_alert import (
    WAZUH_ALERT_STATUSES, WAZUH_SEVERITIES, severity_from_level,
)
from app.forms.wazuh_forms import WazuhConfigForm
from app.services.wazuh import WazuhService, WazuhConfig
from app.utils.security import role_required, admin_required

logger = logging.getLogger(__name__)


wazuh_bp = Blueprint(
    'wazuh',
    __name__,
    url_prefix='/integrations/wazuh',
)


# =============================================================================
# HELPERS
# =============================================================================

STATUS_OPEN = ('NEW', 'TRIAGED', 'IN_PROGRESS', 'ESCALATED')
STATUS_CLOSED = ('RESOLVED', 'FALSE_POSITIVE', 'DISMISSED')


def _parse_date(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except Exception:  # noqa: BLE001
        return None


def _base_alert_query():
    """Alerts visible to the caller. Analysts see everything for now — SOC
    queues are typically shared. Refine here if you introduce tenancy."""
    return WazuhAlert.query


def _apply_filters(query, args):
    severity = args.get('severity')
    status = args.get('status')
    bucket = args.get('bucket')  # 'open' or 'closed' shortcut
    agent = args.get('agent')
    rule_id = args.get('rule_id')
    min_level = args.get('min_level', type=int)
    q = (args.get('q') or '').strip()
    ts_from = _parse_date(args.get('from'))
    ts_to = _parse_date(args.get('to'))
    assigned_to = args.get('assigned_to', type=int)

    if severity and severity in WAZUH_SEVERITIES:
        query = query.filter(WazuhAlert.severity == severity)
    if status and status in WAZUH_ALERT_STATUSES:
        query = query.filter(WazuhAlert.status == status)
    elif bucket == 'open':
        query = query.filter(WazuhAlert.status.in_(STATUS_OPEN))
    elif bucket == 'closed':
        query = query.filter(WazuhAlert.status.in_(STATUS_CLOSED))
    if agent:
        query = query.filter(WazuhAlert.agent_name == agent)
    if rule_id:
        query = query.filter(WazuhAlert.rule_id == rule_id)
    if min_level is not None:
        query = query.filter(WazuhAlert.rule_level >= min_level)
    if ts_from:
        query = query.filter(WazuhAlert.timestamp >= ts_from)
    if ts_to:
        query = query.filter(WazuhAlert.timestamp <= ts_to)
    if assigned_to:
        query = query.filter(WazuhAlert.assigned_to_id == assigned_to)
    if q:
        like = f'%{q}%'
        query = query.filter(or_(
            WazuhAlert.rule_description.ilike(like),
            WazuhAlert.agent_name.ilike(like),
            WazuhAlert.full_log.ilike(like),
            WazuhAlert.src_ip.ilike(like),
            WazuhAlert.location.ilike(like),
        ))
    return query


def _append_note(alert: WazuhAlert, *, action: str, note: str = '', extra: dict | None = None):
    entry = WazuhTreatmentNote(
        alert_id=alert.id,
        user_id=getattr(current_user, 'id', None),
        action=action,
        note=note or None,
        extra=extra or None,
    )
    db.session.add(entry)
    return entry


# =============================================================================
# PAGES
# =============================================================================

@wazuh_bp.route('/')
@login_required
def dashboard():
    """SOC dashboard with charts, filters and alert list."""
    return render_template('wazuh/dashboard.html')


@wazuh_bp.route('/alerts/<int:alert_id>')
@login_required
def alert_detail_page(alert_id):
    """Dedicated detail page (the dashboard opens the same content inline)."""
    alert = WazuhAlert.query.get_or_404(alert_id)
    return render_template('wazuh/alert_detail.html', alert_id=alert.id)


@wazuh_bp.route('/config', methods=['GET', 'POST'])
@login_required
@admin_required
def config_page():
    """Admin-only configuration form."""
    cfg = WazuhConfig.load()
    form = WazuhConfigForm(
        enabled=cfg.enabled,
        url=cfg.url,
        username=cfg.username,
        verify_tls=cfg.verify_tls,
        index_pattern=cfg.index_pattern,
        min_rule_level=cfg.min_rule_level,
        poll_interval_seconds=cfg.poll_interval_seconds,
    )
    feedback = {'type': None, 'message': None}

    if request.method == 'POST':
        form = WazuhConfigForm()
        if form.validate_on_submit():
            try:
                new_cfg = WazuhConfig(
                    enabled=bool(form.enabled.data),
                    url=(form.url.data or '').strip(),
                    username=(form.username.data or '').strip(),
                    password=form.password.data or '',
                    verify_tls=bool(form.verify_tls.data),
                    index_pattern=(form.index_pattern.data or 'wazuh-alerts-*').strip(),
                    min_rule_level=int(form.min_rule_level.data or 0),
                    poll_interval_seconds=int(form.poll_interval_seconds.data or 60),
                )
                new_cfg.save()

                if form.submit_test.data:
                    result = WazuhService.test_connection()
                    feedback['type'] = 'success' if result['ok'] else 'warning'
                    feedback['message'] = f"Teste: {result['message']}"
                elif form.submit_sync.data:
                    result = WazuhService.sync_alerts()
                    feedback['type'] = 'success' if result['ok'] else 'danger'
                    feedback['message'] = f"Sync: {result['message']}"
                else:
                    feedback = {'type': 'success', 'message': 'Configuração salva.'}
            except ValueError as ve:
                feedback = {'type': 'danger', 'message': f'Configuração inválida: {ve}'}
            except Exception as exc:  # noqa: BLE001
                logger.exception('Wazuh config save/test failed')
                feedback = {'type': 'danger', 'message': f'Erro: {exc}'}

    return render_template(
        'wazuh/config.html',
        form=form,
        config=WazuhConfig.load(),
        last_sync=WazuhService.last_sync_status(),
        feedback=feedback,
    )


# =============================================================================
# API — ALERTS
# =============================================================================

@wazuh_bp.route('/api/alerts')
@login_required
def list_alerts():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 25, type=int), 200)

    query = _apply_filters(_base_alert_query(), request.args)
    query = query.order_by(desc(WazuhAlert.timestamp), desc(WazuhAlert.id))

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'items': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': pagination.prev_num,
        'next_num': pagination.next_num,
    })


@wazuh_bp.route('/api/alerts/<int:alert_id>')
@login_required
def get_alert(alert_id):
    alert = WazuhAlert.query.get_or_404(alert_id)
    notes = (
        WazuhTreatmentNote.query
        .filter_by(alert_id=alert.id)
        .order_by(WazuhTreatmentNote.created_at.asc())
        .all()
    )
    return jsonify({
        'alert': alert.to_dict(include_raw=True),
        'notes': [n.to_dict() for n in notes],
    })


@wazuh_bp.route('/api/alerts/<int:alert_id>/status', methods=['PUT'])
@login_required
@role_required('ADMIN', 'ANALYST')
def update_status(alert_id):
    alert = WazuhAlert.query.get_or_404(alert_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get('status')
    note = data.get('note') or ''

    if new_status not in WAZUH_ALERT_STATUSES:
        return jsonify({'error': f'Invalid status. Allowed: {list(WAZUH_ALERT_STATUSES)}'}), 400

    prev = alert.status
    if new_status == prev:
        return jsonify({'error': 'Status unchanged'}), 400

    if new_status == 'TRIAGED':
        alert.mark_triaged(current_user.id)
    elif new_status in ('RESOLVED', 'FALSE_POSITIVE', 'DISMISSED'):
        alert.mark_resolved(current_user.id, resolution=note, status=new_status)
    else:
        alert.status = new_status
        if new_status == 'IN_PROGRESS' and not alert.triaged_at:
            alert.triaged_at = datetime.now(timezone.utc)
        if new_status == 'IN_PROGRESS' and not alert.assigned_to_id:
            alert.assigned_to_id = current_user.id

    _append_note(
        alert,
        action='STATUS_CHANGE',
        note=note,
        extra={'from': prev, 'to': new_status},
    )
    db.session.commit()
    return jsonify(alert.to_dict())


@wazuh_bp.route('/api/alerts/<int:alert_id>/assign', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def assign_alert(alert_id):
    alert = WazuhAlert.query.get_or_404(alert_id)
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if user_id in ('', None):
        # Unassign
        prev = alert.assigned_to_id
        alert.assigned_to_id = None
        _append_note(alert, action='ASSIGN', extra={'from': prev, 'to': None})
        db.session.commit()
        return jsonify(alert.to_dict())

    user = User.query.get(int(user_id))
    if not user:
        return jsonify({'error': 'User not found'}), 404

    prev = alert.assigned_to_id
    alert.assigned_to_id = user.id
    _append_note(
        alert,
        action='ASSIGN',
        extra={'from': prev, 'to': user.id, 'to_name': user.username},
    )
    db.session.commit()
    return jsonify(alert.to_dict())


@wazuh_bp.route('/api/alerts/<int:alert_id>/note', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def add_note(alert_id):
    alert = WazuhAlert.query.get_or_404(alert_id)
    data = request.get_json(silent=True) or {}
    note = (data.get('note') or '').strip()
    if not note:
        return jsonify({'error': 'Empty note'}), 400
    _append_note(alert, action='COMMENT', note=note)
    db.session.commit()
    return jsonify({'ok': True})


@wazuh_bp.route('/api/alerts/<int:alert_id>/ai-analyze', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def ai_analyze(alert_id):
    alert = WazuhAlert.query.get_or_404(alert_id)
    result = WazuhService.ai_analyze(alert)
    if not result.get('ok'):
        return jsonify(result), 502

    alert.ai_summary = result['summary']
    alert.ai_recommendations = result['recommendations']
    alert.ai_analysis_at = datetime.now(timezone.utc)
    _append_note(
        alert,
        action='AI_ANALYSIS',
        note=result['summary'][:500],
        extra={'recommendation_count': len(result['recommendations'])},
    )
    db.session.commit()

    return jsonify({
        'ok': True,
        'summary': alert.ai_summary,
        'recommendations': alert.ai_recommendations,
        'analysis_at': alert.ai_analysis_at.isoformat(),
    })


# =============================================================================
# API — STATS (feeds the dashboard charts)
# =============================================================================

@wazuh_bp.route('/api/stats')
@login_required
def stats():
    hours = request.args.get('hours', default=24, type=int)
    hours = max(1, min(hours, 24 * 30))  # clamp to [1h, 30d]
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    base = WazuhAlert.query.filter(WazuhAlert.timestamp >= since)

    # Severity distribution
    sev_rows = (
        base.with_entities(WazuhAlert.severity, func.count(WazuhAlert.id))
        .group_by(WazuhAlert.severity).all()
    )
    by_severity = {s: 0 for s in WAZUH_SEVERITIES}
    for sev, n in sev_rows:
        if sev in by_severity:
            by_severity[sev] = int(n)

    # Status distribution (against ALL, not windowed — open tickets persist)
    status_rows = (
        WazuhAlert.query.with_entities(WazuhAlert.status, func.count(WazuhAlert.id))
        .group_by(WazuhAlert.status).all()
    )
    by_status = {s: 0 for s in WAZUH_ALERT_STATUSES}
    for st, n in status_rows:
        if st in by_status:
            by_status[st] = int(n)

    # Top rules
    top_rules_rows = (
        base.with_entities(
            WazuhAlert.rule_id,
            WazuhAlert.rule_description,
            func.count(WazuhAlert.id).label('n'),
            func.max(WazuhAlert.rule_level).label('max_level'),
        )
        .filter(WazuhAlert.rule_id.isnot(None))
        .group_by(WazuhAlert.rule_id, WazuhAlert.rule_description)
        .order_by(desc('n')).limit(10).all()
    )

    # Top agents
    top_agents_rows = (
        base.with_entities(
            WazuhAlert.agent_name, func.count(WazuhAlert.id).label('n'),
        )
        .filter(WazuhAlert.agent_name.isnot(None))
        .group_by(WazuhAlert.agent_name)
        .order_by(desc('n')).limit(10).all()
    )

    # Timeline — coarse per-hour bucket (database-agnostic via Python)
    timeline_map: dict[str, dict[str, int]] = {}
    bucket_rows = base.with_entities(
        WazuhAlert.timestamp, WazuhAlert.severity,
    ).all()
    for ts, sev in bucket_rows:
        if not ts:
            continue
        bucket = ts.replace(minute=0, second=0, microsecond=0).isoformat()
        slot = timeline_map.setdefault(bucket, {s: 0 for s in WAZUH_SEVERITIES})
        if sev in slot:
            slot[sev] += 1
    timeline = [
        {'bucket': b, **timeline_map[b]}
        for b in sorted(timeline_map.keys())
    ]

    total = base.count()
    all_total = WazuhAlert.query.count()
    last_24h = (
        WazuhAlert.query.filter(
            WazuhAlert.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)
        ).count()
    )
    open_count = WazuhAlert.query.filter(WazuhAlert.status.in_(STATUS_OPEN)).count()
    assigned_to_me = (
        WazuhAlert.query
        .filter(WazuhAlert.assigned_to_id == current_user.id)
        .filter(WazuhAlert.status.in_(STATUS_OPEN))
        .count()
    )

    return jsonify({
        'window_hours': hours,
        'total_window': total,
        'total_all': all_total,
        'total_24h': last_24h,
        'open_count': open_count,
        'assigned_to_me_open': assigned_to_me,
        'by_severity': by_severity,
        'by_status': by_status,
        'top_rules': [
            {
                'rule_id': rid, 'description': desc_, 'count': int(n),
                'max_level': int(ml or 0),
                'severity': severity_from_level(ml or 0),
            }
            for rid, desc_, n, ml in top_rules_rows
        ],
        'top_agents': [
            {'agent_name': name, 'count': int(n)}
            for name, n in top_agents_rows
        ],
        'timeline': timeline,
    })


@wazuh_bp.route('/api/agents')
@login_required
def distinct_agents():
    rows = (
        db.session.query(WazuhAlert.agent_name)
        .filter(WazuhAlert.agent_name.isnot(None))
        .distinct().order_by(WazuhAlert.agent_name.asc()).limit(500).all()
    )
    return jsonify({'agents': [r[0] for r in rows]})


@wazuh_bp.route('/api/analysts')
@login_required
def analyst_list():
    """Users eligible to be assignees (admin or analyst role)."""
    from app.models.auth import Role
    users = (
        User.query
        .filter(User.is_active == True)  # noqa: E712
        .filter(or_(
            User.is_admin == True,  # noqa: E712
            User.roles.any(Role.name.in_(['ANALYST', 'ADMIN'])),
        ))
        .order_by(User.username.asc())
        .all()
    )
    return jsonify({
        'analysts': [
            {'id': u.id, 'username': u.username, 'email': u.email}
            for u in users
        ]
    })


# =============================================================================
# API — SYNC CONTROL
# =============================================================================

@wazuh_bp.route('/api/sync', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def trigger_sync():
    """Trigger an on-demand sync. Runs inline (bounded by max_pages)."""
    if not WazuhService.is_configured():
        return jsonify({'ok': False, 'message': 'Wazuh não configurado.'}), 400
    result = WazuhService.sync_alerts()
    code = 200 if result.get('ok') else 502
    return jsonify(result), code


@wazuh_bp.route('/api/sync/status')
@login_required
def sync_status():
    cfg = WazuhConfig.load()
    return jsonify({
        'enabled': cfg.enabled,
        'configured': WazuhService.is_configured(),
        'url': cfg.url,
        'index_pattern': cfg.index_pattern,
        'poll_interval_seconds': cfg.poll_interval_seconds,
        'last_sync': WazuhService.last_sync_status(),
    })


@wazuh_bp.route('/api/config/test', methods=['POST'])
@login_required
@admin_required
def config_test():
    return jsonify(WazuhService.test_connection())


# =============================================================================
# API — REPORTS (CSV + PDF)
# =============================================================================

@wazuh_bp.route('/api/report/csv')
@login_required
def report_csv():
    query = _apply_filters(_base_alert_query(), request.args)
    query = query.order_by(desc(WazuhAlert.timestamp)).limit(5000)
    alerts = query.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        'timestamp', 'severity', 'status', 'rule_id', 'rule_level',
        'rule_description', 'agent_name', 'agent_ip', 'src_ip', 'dst_ip',
        'assigned_to', 'resolution', 'mitre_ids',
    ])
    for a in alerts:
        writer.writerow([
            a.timestamp.isoformat() if a.timestamp else '',
            a.severity or '',
            a.status or '',
            a.rule_id or '',
            a.rule_level if a.rule_level is not None else '',
            a.rule_description or '',
            a.agent_name or '',
            a.agent_ip or '',
            a.src_ip or '',
            a.dst_ip or '',
            a.assigned_to.username if a.assigned_to else '',
            (a.resolution or '').replace('\n', ' '),
            ','.join(a.rule_mitre_ids or []),
        ])

    data = buf.getvalue()
    filename = f'wazuh-alerts-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}.csv'
    return Response(
        data,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@wazuh_bp.route('/api/report/pdf')
@login_required
def report_pdf():
    """Render a PDF summary of filtered alerts using WeasyPrint.

    Falls back to an HTML response (inline) when WeasyPrint is unavailable,
    so the endpoint is still useful in dev environments without the
    native deps installed.
    """
    query = _apply_filters(_base_alert_query(), request.args)
    query = query.order_by(desc(WazuhAlert.timestamp)).limit(500)
    alerts = query.all()
    stats_data = json.loads(stats().get_data(as_text=True))  # reuse stats

    html = render_template(
        'wazuh/report_pdf.html',
        alerts=alerts,
        stats=stats_data,
        generated_at=datetime.now(timezone.utc),
        filters=dict(request.args),
        user=current_user,
    )

    try:
        from weasyprint import HTML  # type: ignore
        pdf_bytes = HTML(string=html, base_url=request.url_root).write_pdf()
        filename = f'wazuh-report-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}.pdf'
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning('Falling back to HTML report: %s', exc)
        return Response(html, mimetype='text/html')
