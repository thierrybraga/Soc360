"""
Open-Monitor NVD Controller
Rotas para visualização e gerenciamento de vulnerabilidades.
"""
import logging
from datetime import datetime, timedelta
from statistics import mean

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models.nvd import Vulnerability, CvssMetric, Weakness, Reference, Mitigation, Credit, AffectedProduct
from app.services.nvd import NVDSyncService
from app.models.inventory.category import AssetCategory
from app.utils.security import role_required


logger = logging.getLogger(__name__)


nvd_bp = Blueprint('nvd', __name__)


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def _serialize_dt(dt):
    """Convert datetime to ISO string, return None if None."""
    return dt.isoformat() if dt else None


def _build_mitigation_history(cve_id: str, limit: int = 100):
    from app.models.inventory import Asset, AssetVulnerability

    mitigation_entries = []
    mitigations = Mitigation.query.filter_by(cve_id=cve_id).order_by(Mitigation.created_at.desc()).limit(limit).all()
    for m in mitigations:
        mitigation_entries.append({
            'timestamp': _serialize_dt(m.created_at),
            'kind': 'mitigation_record',
            'title': m.type or 'Mitigation',
            'description': m.description,
            'source': m.source,
            'effectiveness': m.effectiveness,
            'user_id': None,
            'asset_vulnerability_id': None
        })

    workflow_entries = []
    associations = AssetVulnerability.query.options(
        joinedload(AssetVulnerability.asset),
        joinedload(AssetVulnerability.assignee)
    ).outerjoin(
        Asset, Asset.id == AssetVulnerability.asset_id
    ).filter(
        func.upper(AssetVulnerability.cve_id) == cve_id
    ).order_by(AssetVulnerability.updated_at.desc()).limit(limit).all()

    for av in associations:
        asset_label = av.asset.name if av.asset else f'Asset #{av.asset_id}'
        ts = av.updated_at or av.created_at
        workflow_entries.append({
            'timestamp': _serialize_dt(ts),
            'kind': 'workflow_event',
            'title': f'Status {av.status} for {asset_label}',
            'description': av.remediation_notes or av.notes or '',
            'source': 'asset_workflow',
            'effectiveness': None,
            'user_id': av.assignee_id,
            'username': av.assignee.username if av.assignee else None,
            'status': av.status,
            'asset_vulnerability_id': av.id,
            'due_date': av.due_date.isoformat() if av.due_date else None
        })
        if av.acknowledged_at:
            workflow_entries.append({
                'timestamp': _serialize_dt(av.acknowledged_at),
                'kind': 'workflow_event',
                'title': f'Acknowledged for {asset_label}',
                'description': '',
                'source': 'asset_workflow',
                'effectiveness': None,
                'user_id': av.assignee_id,
                'username': av.assignee.username if av.assignee else None,
                'status': 'IN_PROGRESS',
                'asset_vulnerability_id': av.id,
                'due_date': None
            })
        if av.resolved_at:
            workflow_entries.append({
                'timestamp': _serialize_dt(av.resolved_at),
                'kind': 'workflow_event',
                'title': f'Resolved for {asset_label}',
                'description': '',
                'source': 'asset_workflow',
                'effectiveness': None,
                'user_id': av.assignee_id,
                'username': av.assignee.username if av.assignee else None,
                'status': av.status,
                'asset_vulnerability_id': av.id,
                'due_date': None
            })

    combined = mitigation_entries + workflow_entries
    combined.sort(key=lambda x: x['timestamp'] or '', reverse=True)
    return combined[:limit]


@nvd_bp.route('/')
@login_required
def index():
    """Lista de vulnerabilidades."""
    return render_template('nvd/index.html')




@nvd_bp.route('/api/list')
@login_required
def list_vulnerabilities():
    """API: Listar vulnerabilidades com filtros e paginação."""
    # Paginação
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)

    # Filtros
    severity = request.args.get('severity')
    vendor = request.args.get('vendor')
    product = request.args.get('product')
    search = request.args.get('search')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    cisa_kev = request.args.get('cisa_kev')

    # Aceita ambos os nomes de parâmetros de ordenação
    sort_by = request.args.get('sort_by') or request.args.get('sort', 'published_date')
    sort_order = request.args.get('sort_order') or request.args.get('order', 'desc')

    # Mapear nomes JS -> campos do model
    sort_field_map = {
        'published': 'published_date',
        'published_date': 'published_date',
        'cve_id': 'cve_id',
        'cvss_score': 'cvss_score',
        'severity': 'base_severity',
        'base_severity': 'base_severity',
        'last_modified': 'last_modified_date',
    }
    sort_field = sort_field_map.get(sort_by, 'published_date')

    # Query base
    query = Vulnerability.query

    # Aplicar filtros
    if severity:
        query = query.filter(Vulnerability.base_severity == severity.upper())

    if vendor:
        # PostgreSQL JSONB containment
        query = query.filter(
            db.cast(
                Vulnerability.nvd_vendors_data, db.Text
            ).ilike(f'%{vendor}%')
        )

    if product:
        query = query.filter(
            db.cast(
                Vulnerability.nvd_products_data, db.Text
            ).ilike(f'%{product}%')
        )

    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Vulnerability.cve_id.ilike(search_term),
                Vulnerability.description.ilike(search_term)
            )
        )

    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.filter(Vulnerability.published_date >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.filter(Vulnerability.published_date <= to_date)
        except ValueError:
            pass

    if cisa_kev == 'true':
        query = query.filter(Vulnerability.is_in_cisa_kev.is_(True))

    # Ordenação
    sort_column = getattr(
        Vulnerability, sort_field, Vulnerability.published_date
    )
    if sort_order == 'desc':
        query = query.order_by(sort_column.desc().nullslast())
    else:
        query = query.order_by(sort_column.asc().nullsfirst())

    # Paginação
    pagination = query.paginate(
        page=page, per_page=per_page, error_out=False
    )

    # Estatísticas de severidade (contagem global, não filtrada)
    severity_counts = db.session.query(
        Vulnerability.base_severity,
        db.func.count(Vulnerability.cve_id)
    ).group_by(Vulnerability.base_severity).all()

    severity_map = {}
    total_cves = 0
    for sev_name, count in severity_counts:
        key = (sev_name or 'NONE').upper()
        severity_map[key] = count
        total_cves += count

    return jsonify({
        'items': [v.to_list_dict() for v in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'stats': {
            'total': total_cves,
            'critical': severity_map.get('CRITICAL', 0),
            'high': severity_map.get('HIGH', 0),
            'medium': severity_map.get('MEDIUM', 0),
            'low': severity_map.get('LOW', 0),
        }
    })


@nvd_bp.route('/<cve_id>')
@login_required
def detail(cve_id):
    """Detalhes de uma vulnerabilidade."""
    vuln = Vulnerability.query.filter_by(cve_id=cve_id.upper()).first_or_404()

    # Carregar relacionamentos explicitamente
    cvss_metrics = CvssMetric.query.filter_by(cve_id=vuln.cve_id).all()
    weaknesses = Weakness.query.filter_by(cve_id=vuln.cve_id).all()
    references = Reference.query.filter_by(cve_id=vuln.cve_id).all()

    mitigations = Mitigation.query.filter_by(cve_id=vuln.cve_id).all()
    credits = Credit.query.filter_by(cve_id=vuln.cve_id).all()
    affected_products = AffectedProduct.query.filter_by(cve_id=vuln.cve_id).all()

    # Importar models de inventory (cross-db)
    from app.models.inventory import Asset, AssetVulnerability
    affected_assets_query = AssetVulnerability.query.options(
        joinedload(AssetVulnerability.asset),
        joinedload(AssetVulnerability.assignee)
    ).outerjoin(
        Asset, Asset.id == AssetVulnerability.asset_id
    ).filter(
        func.upper(AssetVulnerability.cve_id) == vuln.cve_id
    )

    affected_assets = affected_assets_query.order_by(
        Asset.name.asc().nullslast(),
        AssetVulnerability.discovered_at.desc()
    ).all()

    open_statuses = {'OPEN', 'IN_PROGRESS'}
    resolved_statuses = {'RESOLVED', 'MITIGATED'}
    open_assets_count = sum(1 for av in affected_assets if av.status in open_statuses)
    resolved_assets_count = sum(1 for av in affected_assets if av.status in resolved_statuses)
    overdue_assets_count = sum(1 for av in affected_assets if av.is_overdue)
    unassigned_assets_count = sum(1 for av in affected_assets if av.assignee_id is None)
    contextual_scores = [av.contextual_risk_score for av in affected_assets if av.contextual_risk_score is not None]
    avg_contextual_risk = round(mean(contextual_scores), 2) if contextual_scores else None
    max_contextual_risk = round(max(contextual_scores), 2) if contextual_scores else None

    asset_type_counts = {}
    asset_criticality_counts = {}
    for av in affected_assets:
        if av.asset and av.asset.asset_type:
            key = av.asset.asset_type.upper()
            asset_type_counts[key] = asset_type_counts.get(key, 0) + 1
        if av.asset and av.asset.criticality:
            key = av.asset.criticality.upper()
            asset_criticality_counts[key] = asset_criticality_counts.get(key, 0) + 1

    top_asset_types = sorted(
        asset_type_counts.items(),
        key=lambda item: item[1],
        reverse=True
    )[:3]

    primary_metric = cvss_metrics[0] if cvss_metrics else None
    threat_intel_score = 0
    if vuln.exploit_available:
        threat_intel_score += 4
    if vuln.is_in_cisa_kev:
        threat_intel_score += 4
    if not vuln.patch_available:
        threat_intel_score += 2
    threat_intel_score = min(threat_intel_score, 10)
    exposure_score = min(len(affected_assets) * 2, 10)
    open_risk_score = None
    if avg_contextual_risk is not None:
        open_scores = [av.contextual_risk_score for av in affected_assets if av.status in open_statuses and av.contextual_risk_score is not None]
        open_risk_score = round(mean(open_scores), 2) if open_scores else avg_contextual_risk

    radar_chart = None
    if (
        vuln.cvss_score is not None
        and primary_metric
        and primary_metric.exploitability_score is not None
        and primary_metric.impact_score is not None
        and open_risk_score is not None
        and len(affected_assets) > 0
    ):
        radar_chart = {
            'labels': [
                'CVSS Base',
                'Exploitability',
                'Impact',
                'Asset Exposure',
                'Open Risk',
                'Threat Intel'
            ],
            'values': [
                round(vuln.cvss_score, 2),
                round(primary_metric.exploitability_score, 2),
                round(primary_metric.impact_score, 2),
                round(exposure_score, 2),
                round(open_risk_score, 2),
                round(float(threat_intel_score), 2),
            ]
        }

    # Separar referências por tipo
    patch_refs = [r for r in references if r.is_patch]
    exploit_refs = [r for r in references if r.is_exploit]
    advisory_refs = [r for r in references if r.is_vendor_advisory]
    other_refs = [r for r in references if not r.is_patch and not r.is_exploit and not r.is_vendor_advisory]

    return render_template(
        'nvd/detail.html',
        vulnerability=vuln,
        cvss_metrics=cvss_metrics,
        weaknesses=weaknesses,
        references=references,
        patch_refs=patch_refs,
        exploit_refs=exploit_refs,
        advisory_refs=advisory_refs,
        other_refs=other_refs,
        mitigations=mitigations,
        credits=credits,
        affected_products=affected_products,
        affected_assets=affected_assets,
        open_assets_count=open_assets_count,
        resolved_assets_count=resolved_assets_count,
        overdue_assets_count=overdue_assets_count,
        unassigned_assets_count=unassigned_assets_count,
        avg_contextual_risk=avg_contextual_risk,
        max_contextual_risk=max_contextual_risk,
        top_asset_types=top_asset_types,
        asset_criticality_counts=asset_criticality_counts,
        radar_chart=radar_chart,
        mitigation_history=_build_mitigation_history(vuln.cve_id),
    )


@nvd_bp.route('/api/<cve_id>/mitigations/workflow', methods=['POST'])
@login_required
def mitigation_workflow(cve_id):
    cve_id_upper = cve_id.upper()
    payload = request.get_json(silent=True) or {}
    action = (payload.get('action') or '').strip().lower()
    if action not in {'start', 'update', 'resolve', 'mitigate', 'accept_risk', 'reopen', 'add_note'}:
        return jsonify({'error': 'Invalid action'}), 400

    from app.models.inventory import Asset, AssetVulnerability

    asset_vuln = None
    asset_vuln_id = payload.get('asset_vulnerability_id')
    if asset_vuln_id:
        asset_vuln = AssetVulnerability.query.options(
            joinedload(AssetVulnerability.asset),
            joinedload(AssetVulnerability.assignee)
        ).filter(
            AssetVulnerability.id == asset_vuln_id,
            func.upper(AssetVulnerability.cve_id) == cve_id_upper
        ).first()
        if not asset_vuln:
            return jsonify({'error': 'Asset vulnerability association not found'}), 404
        if not current_user.is_admin and (not asset_vuln.asset or asset_vuln.asset.owner_id != current_user.id):
            return jsonify({'error': 'Forbidden'}), 403
    elif not current_user.is_admin:
        return jsonify({'error': 'asset_vulnerability_id is required for non-admin users'}), 400

    notes = (payload.get('notes') or '').strip()
    effectiveness = (payload.get('effectiveness') or '').strip() or None
    source = (payload.get('source') or '').strip() or 'organization'
    mitigation_type = (payload.get('type') or '').strip() or 'Workaround'
    mitigation_description = (payload.get('mitigation_description') or '').strip()
    due_date = _parse_iso_datetime(payload.get('due_date'))
    assignee_id = payload.get('assignee_id')

    status_map = {
        'start': 'IN_PROGRESS',
        'update': None,
        'resolve': 'RESOLVED',
        'mitigate': 'MITIGATED',
        'accept_risk': 'ACCEPTED',
        'reopen': 'OPEN',
        'add_note': None
    }

    now = datetime.utcnow()
    changed_status = None
    try:
        if asset_vuln:
            next_status = status_map[action]
            if next_status:
                asset_vuln.status = next_status
                changed_status = next_status
            if action == 'start' and not asset_vuln.acknowledged_at:
                asset_vuln.acknowledged_at = now
            if action in {'resolve', 'mitigate'}:
                asset_vuln.resolved_at = now
            if action == 'reopen':
                asset_vuln.resolved_at = None
            if due_date:
                asset_vuln.due_date = due_date
            if assignee_id is not None and current_user.is_admin:
                asset_vuln.assignee_id = assignee_id
            if notes:
                previous = (asset_vuln.remediation_notes or '').strip()
                prefix = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}][{action.upper()}]"
                asset_vuln.remediation_notes = f"{previous}\n{prefix} {notes}".strip() if previous else f"{prefix} {notes}"
            if mitigation_description:
                extra = f" mitigation={mitigation_type} source={source}"
                if effectiveness:
                    extra = f"{extra} effectiveness={effectiveness}"
                description_line = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}][MITIGATION]{extra}: {mitigation_description}"
                asset_vuln.remediation_notes = f"{asset_vuln.remediation_notes}\n{description_line}".strip() if asset_vuln.remediation_notes else description_line

        db.session.commit()

        return jsonify({
            'success': True,
            'cve_id': cve_id_upper,
            'action': action,
            'asset_vulnerability': asset_vuln.to_dict() if asset_vuln else None,
            'created_mitigation': None,
            'history': _build_mitigation_history(cve_id_upper, limit=40)
        })
    except Exception as exc:
        db.session.rollback()
        logger.error(f'Error on mitigation workflow for {cve_id_upper}: {exc}')
        return jsonify({'error': 'Failed to update mitigation workflow'}), 500


@nvd_bp.route('/api/<cve_id>/mitigations/history')
@login_required
def mitigation_history(cve_id):
    vuln = Vulnerability.query.filter_by(cve_id=cve_id.upper()).first_or_404()
    return jsonify({
        'cve_id': vuln.cve_id,
        'items': _build_mitigation_history(vuln.cve_id, limit=200)
    })


@nvd_bp.route('/api/<cve_id>')
@login_required
def api_detail(cve_id):
    """API: Detalhes de uma vulnerabilidade."""
    vuln = Vulnerability.query.filter_by(cve_id=cve_id.upper()).first_or_404()
    
    # Carregar relacionamentos
    cvss_metrics = CvssMetric.query.filter_by(cve_id=cve_id.upper()).all()
    weaknesses = Weakness.query.filter_by(cve_id=cve_id.upper()).all()
    references = Reference.query.filter_by(cve_id=cve_id.upper()).all()
    
    return jsonify({
        'vulnerability': vuln.to_dict(),
        'cvss_metrics': [m.to_dict() for m in cvss_metrics],
        'weaknesses': [w.to_dict() for w in weaknesses],
        'references': [r.to_dict() for r in references]
    })


@nvd_bp.route('/api/stats')
@login_required
def stats():
    """API: Estatísticas de vulnerabilidades."""
    # Total por severidade
    severity_counts = db.session.query(
        Vulnerability.base_severity,
        db.func.count(Vulnerability.cve_id)
    ).group_by(Vulnerability.base_severity).all()
    
    # CVEs nas últimas 24h, 7 dias, 30 dias
    now = datetime.utcnow()
    
    last_24h = Vulnerability.query.filter(
        Vulnerability.published_date >= now - timedelta(hours=24)
    ).count()
    
    last_7d = Vulnerability.query.filter(
        Vulnerability.published_date >= now - timedelta(days=7)
    ).count()
    
    last_30d = Vulnerability.query.filter(
        Vulnerability.published_date >= now - timedelta(days=30)
    ).count()
    
    # Total CISA KEV
    cisa_kev_count = Vulnerability.query.filter(
        Vulnerability.is_in_cisa_kev.is_(True)
    ).count()

    # Top vendors
    # Usando raw SQL para JSONB array unnest (PostgreSQL)
    try:
        with db.engines['public'].connect() as conn:
            top_vendors_query = conn.execute(
                db.text("""
                    SELECT vendor, COUNT(*) as count
                    FROM vulnerabilities,
                         jsonb_array_elements_text(nvd_vendors_data) as vendor
                    GROUP BY vendor
                    ORDER BY count DESC
                    LIMIT 10
                """)
            ).fetchall()
        top_vendors = [{'vendor': row[0], 'count': row[1]} for row in top_vendors_query]
    except Exception:
        top_vendors = []

    return jsonify({
        'total': Vulnerability.query.count(),
        'by_severity': {
            (sev or 'NONE'): count for sev, count in severity_counts
        },
        'last_24h': last_24h,
        'last_7d': last_7d,
        'last_30d': last_30d,
        'cisa_kev': cisa_kev_count,
        'top_vendors': top_vendors
    })


@nvd_bp.route('/api/vendors')
@login_required
def list_vendors():
    """API: Listar vendors com contagem."""
    search = request.args.get('search', '')
    limit = min(request.args.get('limit', 50, type=int), 200)

    # Query JSONB array com contagem (PostgreSQL)
    try:
        with db.engines['public'].connect() as conn:
            result = conn.execute(
                db.text("""
                    SELECT vendor, COUNT(*) as count
                    FROM vulnerabilities,
                         jsonb_array_elements_text(nvd_vendors_data) as vendor
                    WHERE vendor ILIKE :search
                    GROUP BY vendor
                    ORDER BY count DESC
                    LIMIT :limit
                """),
                {'search': f'%{search}%', 'limit': limit}
            ).fetchall()
        vendors = [{'name': row[0], 'count': row[1]} for row in result]
    except Exception:
        vendors = []

    return jsonify({
        'vendors': vendors
    })


@nvd_bp.route('/api/products')
@login_required
def list_products():
    """API: Listar produtos (opcionalmente filtrado por vendor)."""
    vendor = request.args.get('vendor')
    search = request.args.get('search', '')
    limit = min(request.args.get('limit', 50, type=int), 200)

    try:
        with db.engines['public'].connect() as conn:
            if vendor:
                # Produtos de um vendor específico
                result = conn.execute(
                    db.text("""
                        SELECT product, COUNT(*) as count
                        FROM vulnerabilities v,
                             jsonb_array_elements_text(v.nvd_vendors_data) as vendor,
                             jsonb_array_elements_text(v.nvd_products_data) as product
                        WHERE vendor = :vendor
                        AND product ILIKE :search
                        GROUP BY product
                        ORDER BY count DESC
                        LIMIT :limit
                    """),
                    {'vendor': vendor, 'search': f'%{search}%', 'limit': limit}
                ).fetchall()
            else:
                # Todos os produtos
                result = conn.execute(
                    db.text("""
                        SELECT product, COUNT(*) as count
                        FROM vulnerabilities,
                             jsonb_array_elements_text(nvd_products_data) as product
                        WHERE product ILIKE :search
                        GROUP BY product
                        ORDER BY count DESC
                        LIMIT :limit
                    """),
                    {'search': f'%{search}%', 'limit': limit}
                ).fetchall()
        products = [{'name': row[0], 'count': row[1]} for row in result]
    except Exception:
        products = []

    return jsonify({
        'products': products
    })


@nvd_bp.route('/sync')
@login_required
@role_required('ADMIN', 'ANALYST')
def sync_page():
    """Página de gerenciamento de sincronização."""
    from app.models.system import SyncMetadata
    from datetime import datetime, timezone
    import os

    api_key = SyncMetadata.get_value('nvd_api_key') or os.environ.get('NVD_API_KEY')
    api_key_configured = bool(api_key)

    return render_template(
        'nvd/sync.html',
        api_key_configured=api_key_configured,
        now_utc=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    )


@nvd_bp.route('/api/vulnerabilities/<cve_id>/organizations', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def associate_organizations(cve_id):
    """API: Associar organizações a uma CVE."""
    vuln = Vulnerability.query.filter_by(cve_id=cve_id).first_or_404()
    data = request.get_json()
    
    if not data or 'organization_ids' not in data:
        return jsonify({'error': 'Missing organization_ids'}), 400
        
    org_ids = data['organization_ids']
    orgs = AssetCategory.query.filter(
        AssetCategory.id.in_(org_ids),
        AssetCategory.is_organization == True
    ).all()
    
    vuln.organizations = orgs
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'organizations': [o.to_dict() for o in vuln.organizations]
    })


@nvd_bp.route('/api/sync/status')
@login_required
def sync_status():
    """API: Status da sincronização."""
    service = NVDSyncService()
    return jsonify(service.get_progress())


from app.services.mitre.mitre_attack_service import MitreAttackService

@nvd_bp.route('/api/mitre-attack/status')
@login_required
def mitre_attack_status():
    """API: Status da sincronização do MITRE ATT&CK."""
    service = MitreAttackService()
    return jsonify(service.get_progress())

@nvd_bp.route('/api/mitre-attack/sync', methods=['POST'])
@login_required
@role_required('ADMIN')
def mitre_attack_sync():
    """API: Iniciar sincronização do MITRE ATT&CK."""
    from flask import current_app
    app = current_app._get_current_object()
    
    def run_sync(app_instance):
        with app_instance.app_context():
            service = MitreAttackService()
            service.sync_all_domains()
            
    import threading
    thread = threading.Thread(target=run_sync, args=(app,))
    thread.start()
    
    return jsonify({'message': 'Sincronização iniciada em segundo plano.'})

@nvd_bp.route('/api/mitre-attack/map', methods=['POST'])
@login_required
@role_required('ADMIN')
def mitre_attack_map():
    """API: Mapear CVEs para técnicas do ATT&CK."""
    from flask import current_app
    app = current_app._get_current_object()
    
    def run_map(app_instance):
        with app_instance.app_context():
            service = MitreAttackService()
            service.map_cves_to_techniques()
            
    import threading
    thread = threading.Thread(target=run_map, args=(app,))
    thread.start()
    
    return jsonify({'message': 'Mapeamento iniciado em segundo plano.'})


@nvd_bp.route('/api/sync/start', methods=['POST'])
@login_required
@role_required('ADMIN')
def start_sync():
    """API: Iniciar sincronização."""
    from app.services.nvd.nvd_sync_service import SyncMode
    
    data = request.get_json() or {}
    mode = data.get('mode', 'incremental')
    
    try:
        sync_mode = SyncMode(mode)
    except ValueError:
        return jsonify({'error': f'Invalid mode: {mode}'}), 400
    
    service = NVDSyncService()

    if service.start_sync(mode=sync_mode):
        logger.info(
            f'NVD sync started by {current_user.username}: mode={mode}'
        )
        return jsonify({
            'message': f'Sync started in {mode} mode',
            'status': 'running'
        })
    else:
        return jsonify({'error': 'Sync already running'}), 409


@nvd_bp.route('/api/sync/cancel', methods=['POST'])
@login_required
@role_required('ADMIN')
def cancel_sync():
    """API: Cancelar sincronização."""
    service = NVDSyncService()

    if service.cancel_sync():
        logger.info(f'NVD sync cancelled by {current_user.username}')
        return jsonify({'message': 'Sync cancellation requested'})
    else:
        return jsonify({'error': 'No sync running'}), 400


@nvd_bp.route('/api/search')
@login_required
def search_cves():
    """API: Busca avançada de CVEs."""
    query_text = request.args.get('q', '')

    if not query_text or len(query_text) < 3:
        return jsonify(
            {'error': 'Query must be at least 3 characters'}
        ), 400

    # Busca em CVE ID e descrição
    results = Vulnerability.query.filter(
        db.or_(
            Vulnerability.cve_id.ilike(f'%{query_text}%'),
            Vulnerability.description.ilike(f'%{query_text}%')
        )
    ).order_by(Vulnerability.cvss_score.desc()).limit(20).all()

    return jsonify({
        'results': [
            {
                'cve_id': v.cve_id,
                'description': (
                    v.description[:200] + '...'
                    if len(v.description) > 200 else v.description
                ),
                'cvss_score': v.cvss_score,
                'severity': v.base_severity
            }
            for v in results
        ]
    })


@nvd_bp.route('/api/timeline')
@login_required
def timeline():
    """API: Timeline de CVEs por data."""
    days = request.args.get('days', 30, type=int)
    severity = request.args.get('severity')
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.session.query(
        db.func.date(Vulnerability.published_date).label('date'),
        db.func.count(Vulnerability.cve_id).label('count')
    ).filter(
        Vulnerability.published_date >= start_date
    )
    
    if severity:
        query = query.filter(Vulnerability.base_severity == severity.upper())
    
    results = query.group_by(
        db.func.date(Vulnerability.published_date)
    ).order_by('date').all()
    
    return jsonify({
        'timeline': [
            {'date': str(row.date), 'count': row.count}
            for row in results
        ]
    })


@nvd_bp.route('/api/import/bulk', methods=['POST'])
@login_required
@role_required('ADMIN')
def bulk_import():
    """API: Importar CVEs em massa (JSON)."""
    from app.tasks.nvd import bulk_import_task
    
    data = request.get_json()
    file_path = data.get('file_path')
    
    if not file_path:
        return jsonify({'error': 'File path required'}), 400
        
    task = bulk_import_task.delay(file_path)
    
    return jsonify({
        'message': 'Bulk import started',
        'task_id': task.id
    }), 202
