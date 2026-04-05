"""
Open-Monitor Monitoring Controller
Rotas para gerenciamento de regras de monitoramento e alertas.
"""
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.monitoring import MonitoringRule, Alert
from app.models.system import MonitoringRuleType, AlertChannel, AlertStatus
from app.utils.security import role_required


logger = logging.getLogger(__name__)


monitoring_bp = Blueprint('monitoring', __name__)


def _serialize_rule(rule: MonitoringRule):
    data = rule.to_dict()
    data['owner_id'] = rule.user_id
    data['is_active'] = rule.enabled
    channels = rule.alert_channels or []
    normalized_channels = []
    for channel in channels:
        if isinstance(channel, dict):
            channel_type = channel.get('type')
            if channel_type:
                normalized_channels.append(channel_type)
        elif channel:
            normalized_channels.append(str(channel))
    data['notification_channels'] = normalized_channels
    return data


@monitoring_bp.route('/')
@login_required
def index():
    """Lista de regras de monitoramento."""
    return render_template('monitoring/index.html')


@monitoring_bp.route('/api/rules')
@login_required
def list_rules():
    """API: Listar regras de monitoramento."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 50, type=int), 100)
    
    # Query base - filtrar por owner se não admin
    query = MonitoringRule.query
    if not current_user.is_admin:
        query = query.filter(MonitoringRule.user_id == current_user.id)
    
    # Filtros
    rule_type = request.args.get('type')
    is_active = request.args.get('active')
    
    if rule_type:
        try:
            query = query.filter(MonitoringRule.rule_type == MonitoringRuleType(rule_type))
        except ValueError:
            pass
    
    if is_active is not None:
        query = query.filter(MonitoringRule.enabled == (is_active.lower() == 'true'))
    
    # Ordenação
    query = query.order_by(MonitoringRule.created_at.desc())
    
    # Paginação
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [_serialize_rule(r) for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })


@monitoring_bp.route('/rules/create')
@login_required
@role_required('ADMIN', 'ANALYST')
def create_rule_page():
    """Página de criação de regra."""
    return render_template('monitoring/rule_form.html', rule=None)


@monitoring_bp.route('/rules/<int:rule_id>/edit')
@login_required
@role_required('ADMIN', 'ANALYST')
def edit_rule_page(rule_id):
    """Página de edição de regra."""
    rule = MonitoringRule.query.get_or_404(rule_id)
    if not current_user.is_admin and rule.user_id != current_user.id:
        abort(403)
    return render_template('monitoring/rule_form.html', rule=rule)


@monitoring_bp.route('/alerts')
@login_required
def alerts_page():
    """Página de alertas."""
    return render_template('monitoring/alerts.html')


@monitoring_bp.route('/api/alerts')
@login_required
def list_alerts():
    """API: Listar alertas."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    
    query = Alert.query

    if not current_user.is_admin:
        query = query.outerjoin(MonitoringRule).filter(
            or_(
                Alert.rule_id.is_(None),
                MonitoringRule.user_id == current_user.id
            )
        )
    
    # Filtros
    status = request.args.get('status')
    severity = request.args.get('severity')
    rule_id = request.args.get('rule_id', type=int)
    
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if rule_id:
        query = query.filter(Alert.rule_id == rule_id)
        
    # Ordenação
    query = query.order_by(Alert.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page,
        'per_page': per_page,
        'has_prev': pagination.has_prev,
        'has_next': pagination.has_next,
        'prev_num': pagination.prev_num,
        'next_num': pagination.next_num
    })


@monitoring_bp.route('/api/alerts/<int:alert_id>/status', methods=['PUT'])
@login_required
@role_required('ADMIN', 'ANALYST')
def update_alert_status(alert_id):
    """API: Atualizar status do alerta."""
    alert = Alert.query.get_or_404(alert_id)
    data = request.get_json(silent=True) or {}
    
    new_status = data.get('status')
    if not new_status:
        return jsonify({'error': 'Status required'}), 400
        
    try:
        status_enum = AlertStatus(new_status)
    except ValueError:
        return jsonify({'error': 'Invalid status'}), 400
        
    if status_enum == AlertStatus.ACKNOWLEDGED:
        alert.mark_as_acknowledged(current_user.id)
    elif status_enum == AlertStatus.RESOLVED:
        alert.mark_as_resolved(current_user.id)
    elif status_enum == AlertStatus.DISMISSED:
        alert.mark_as_dismissed(current_user.id)
    else:
        alert.status = status_enum.value
        
    db.session.commit()
    return jsonify(alert.to_dict())


@monitoring_bp.route('/api/rules', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def create_rule():
    """API: Criar regra de monitoramento."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['name', 'rule_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Validar tipo
    try:
        rule_type = MonitoringRuleType(data['rule_type'])
    except ValueError:
        return jsonify({'error': f'Invalid rule type: {data["rule_type"]}'}), 400
    
    # Validar canais
    channel_names = data.get('notification_channels', [])
    if not channel_names and data.get('alert_channels'):
        channel_names = data.get('alert_channels', [])

    channels = []
    for channel_name in channel_names:
        try:
            channels.append({
                'type': AlertChannel(channel_name).value,
                'config': {}
            })
        except ValueError:
            pass
    
    # Criar regra
    rule = MonitoringRule(
        name=data['name'],
        description=data.get('description'),
        rule_type=rule_type,
        parameters=data.get('parameters', {}),
        alert_channels=channels,
        cooldown_minutes=data.get('cooldown_minutes', 60),
        user_id=current_user.id,
        enabled=data.get('is_active', data.get('enabled', True))
    )
    
    db.session.add(rule)
    db.session.commit()
    
    logger.info(f'Monitoring rule created: {rule.name} by {current_user.username}')
    
    return jsonify({
        'message': 'Rule created successfully',
        'rule': _serialize_rule(rule)
    }), 201


@monitoring_bp.route('/api/rules/<int:rule_id>')
@login_required
def get_rule(rule_id):
    """API: Obter detalhes de uma regra."""
    rule = MonitoringRule.query.get_or_404(rule_id)
    
    if not current_user.is_admin and rule.user_id != current_user.id:
        abort(403)
    
    return jsonify(_serialize_rule(rule))


@monitoring_bp.route('/api/rules/<int:rule_id>', methods=['PUT'])
@login_required
@role_required('ADMIN', 'ANALYST')
def update_rule(rule_id):
    """API: Atualizar regra de monitoramento."""
    rule = MonitoringRule.query.get_or_404(rule_id)
    
    if not current_user.is_admin and rule.user_id != current_user.id:
        abort(403)
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    # Campos atualizáveis
    if 'name' in data:
        rule.name = data['name']
    if 'description' in data:
        rule.description = data['description']
    if 'parameters' in data:
        rule.parameters = data['parameters']
    if 'cooldown_minutes' in data:
        rule.cooldown_minutes = data['cooldown_minutes']
    if 'is_active' in data:
        rule.enabled = data['is_active']
    if 'enabled' in data:
        rule.enabled = data['enabled']
    
    if 'notification_channels' in data or 'alert_channels' in data:
        input_channels = data.get('notification_channels')
        if input_channels is None:
            input_channels = data.get('alert_channels', [])
        channels = []
        for channel_name in input_channels:
            try:
                channels.append({
                    'type': AlertChannel(channel_name).value,
                    'config': {}
                })
            except ValueError:
                pass
        rule.alert_channels = channels
    
    db.session.commit()
    
    logger.info(f'Monitoring rule updated: {rule.name} by {current_user.username}')
    
    return jsonify({
        'message': 'Rule updated successfully',
        'rule': _serialize_rule(rule)
    })


@monitoring_bp.route('/api/rules/<int:rule_id>', methods=['DELETE'])
@login_required
@role_required('ADMIN')
def delete_rule(rule_id):
    """API: Deletar regra de monitoramento."""
    rule = MonitoringRule.query.get_or_404(rule_id)
    
    db.session.delete(rule)
    db.session.commit()
    
    logger.info(f'Monitoring rule deleted: {rule.name} by {current_user.username}')
    
    return jsonify({'message': 'Rule deleted successfully'})


@monitoring_bp.route('/api/rules/<int:rule_id>/toggle', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def toggle_rule(rule_id):
    """API: Ativar/desativar regra."""
    rule = MonitoringRule.query.get_or_404(rule_id)
    
    if not current_user.is_admin and rule.user_id != current_user.id:
        abort(403)
    
    rule.enabled = not rule.enabled
    db.session.commit()
    
    status = 'activated' if rule.enabled else 'deactivated'
    logger.info(f'Monitoring rule {status}: {rule.name} by {current_user.username}')
    
    return jsonify({
        'message': f'Rule {status}',
        'is_active': rule.enabled
    })


@monitoring_bp.route('/api/rules/<int:rule_id>/test', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def test_rule(rule_id):
    """API: Testar regra de monitoramento."""
    rule = MonitoringRule.query.get_or_404(rule_id)
    
    if not current_user.is_admin and rule.user_id != current_user.id:
        abort(403)
    
    data = request.get_json() or {}
    test_cve_id = data.get('cve_id', 'CVE-2021-44228')
    
    # Buscar CVE de teste
    from app.models.nvd import Vulnerability
    vuln = Vulnerability.query.get(test_cve_id.upper())
    
    if not vuln:
        # Fallback: try to get any vulnerability for testing purposes
        vuln = Vulnerability.query.first()
        if vuln:
            test_cve_id = vuln.id
    
    if not vuln:
        return jsonify({
            'error': f'Test CVE not found: {test_cve_id} and no vulnerabilities available in database'
        }), 404
    
    # Testar match
    matches = rule.matches_vulnerability(vuln)
    
    return jsonify({
        'rule_id': rule.id,
        'rule_name': rule.name,
        'test_cve': test_cve_id,
        'matches': matches,
        'parameters': rule.parameters
    })


@monitoring_bp.route('/api/templates')
@login_required
def rule_templates():
    """API: Templates de regras pré-definidas."""
    templates = [
        {
            'name': 'Critical CVEs',
            'description': 'Alert on all CRITICAL severity CVEs',
            'rule_type': 'SEVERITY_THRESHOLD',
            'icon': 'exclamation-triangle',
            'parameters': {
                'min_severity': 'CRITICAL'
            }
        },
        {
            'name': 'High CVEs with CISA KEV',
            'description': 'Alert on HIGH+ CVEs in CISA KEV list',
            'rule_type': 'CISA_KEV',
            'icon': 'shield-virus',
            'parameters': {
                'min_severity': 'HIGH',
                'cisa_kev_only': True
            }
        },
        {
            'name': 'New CVEs Daily',
            'description': 'Daily summary of new CVEs',
            'rule_type': 'NEW_CVE',
            'icon': 'calendar-day',
            'parameters': {
                'frequency': 'daily'
            }
        },
        {
            'name': 'Vendor-Specific Alerts',
            'description': 'Alert on CVEs for specific vendors',
            'rule_type': 'VENDOR_SPECIFIC',
            'icon': 'building',
            'parameters': {
                'vendors': []
            }
        }
    ]
    
    return jsonify({'templates': templates})


@monitoring_bp.route('/api/stats')
@login_required
def stats():
    """API: Estatísticas de monitoramento."""
    # Query base
    query = MonitoringRule.query
    if not current_user.is_admin:
        query = query.filter(MonitoringRule.user_id == current_user.id)
    
    total = query.count()
    active = query.filter(MonitoringRule.enabled == True).count()
    
    # Por tipo
    type_counts = db.session.query(
        MonitoringRule.rule_type,
        db.func.count(MonitoringRule.id)
    )
    
    if not current_user.is_admin:
        type_counts = type_counts.filter(MonitoringRule.user_id == current_user.id)
    
    type_counts = type_counts.group_by(MonitoringRule.rule_type).all()
    
    # Últimas triggers
    recent_triggers = query.filter(
        MonitoringRule.last_triggered_at.isnot(None)
    ).order_by(MonitoringRule.last_triggered_at.desc()).limit(5).all()
    
    return jsonify({
        'total': total,
        'active': active,
        'inactive': total - active,
        'by_type': {str(row[0]): row[1] for row in type_counts},
        'recent_triggers': [
            {
                'rule_name': r.name,
                'triggered_at': r.last_triggered_at.isoformat() if r.last_triggered_at else None,
                'trigger_count': r.trigger_count
            }
            for r in recent_triggers
        ]
    })
