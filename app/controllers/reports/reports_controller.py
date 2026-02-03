"""
Open-Monitor Reports Controller
Rotas para geração e gerenciamento de relatórios.
"""
import logging
import os
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, abort, send_file, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.models.monitoring import Report, RiskAssessment
from app.models.system import ReportType, ReportStatus
from app.utils.security import role_required


logger = logging.getLogger(__name__)


reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/')
@login_required
def index():
    """Lista de relatórios."""
    return render_template('reports/index.html')


@reports_bp.route('/api/list')
@login_required
def list_reports():
    """API: Listar relatórios."""
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)
    
    # Query base
    query = Report.query
    if not current_user.is_admin:
        query = query.filter(Report.user_id == current_user.id)
    
    # Filtros
    report_type = request.args.get('type')
    status = request.args.get('status')
    search = request.args.get('search')

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Report.title.ilike(search_term)) |
            (Report.description.ilike(search_term))
        )
    
    if report_type:
        try:
            # Tenta converter string para Enum (ex: EXECUTIVE -> ReportType.EXECUTIVE)
            # Se vier da URL como string simples, precisamos garantir match com Enum
            r_type = ReportType[report_type] if report_type in ReportType.__members__ else ReportType(report_type)
            query = query.filter(Report.report_type == r_type.value)
        except (ValueError, KeyError):
            pass
    
    if status:
        try:
            r_status = ReportStatus[status] if status in ReportStatus.__members__ else ReportStatus(status)
            query = query.filter(Report.status == r_status.value)
        except (ValueError, KeyError):
            pass
    
    # Ordenação
    query = query.order_by(Report.created_at.desc())
    
    # Paginação
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'items': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'page': page
    })


@reports_bp.route('/api/generate', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def generate_report():
    """API: Gerar novo relatório."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['title', 'report_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Validar tipo
    try:
        # Mapeia valores do form para Enum
        report_type_str = data['report_type']
        if report_type_str == 'EXECUTIVE_SUMMARY': report_type = ReportType.EXECUTIVE
        elif report_type_str == 'TECHNICAL_REPORT': report_type = ReportType.TECHNICAL
        elif report_type_str == 'RISK_ASSESSMENT': report_type = ReportType.RISK_ASSESSMENT  # Se não existir no Enum, dar erro? Enum tem EXECUTIVE, TECHNICAL, COMPLIANCE, INCIDENT, TREND
        elif report_type_str == 'COMPLIANCE_REPORT': report_type = ReportType.COMPLIANCE
        elif report_type_str == 'TREND_ANALYSIS': report_type = ReportType.TREND
        else:
            report_type = ReportType(report_type_str)
    except ValueError:
        return jsonify({'error': f'Invalid report type: {data["report_type"]}'}), 400
    
    # Criar relatório
    report = Report(
        title=data['title'],
        description=data.get('description'),
        report_type=report_type.value,
        filters=data.get('parameters', {}),
        user_id=current_user.id
    )
    
    db.session.add(report)
    db.session.commit()
    
    # Iniciar geração em background
    report.start_generation()
    db.session.commit()
    
    # TODO: Disparar task de geração em celery/thread
    # Por hora, geramos inline
    _generate_report_data(report)
    
    logger.info(f'Report generation started: {report.title} by {current_user.username}')
    
    return jsonify({
        'message': 'Report generation started',
        'report': report.to_dict()
    }), 202


@reports_bp.route('/api/<int:report_id>')
@login_required
def get_report(report_id):
    """API: Obter detalhes de um relatório."""
    report = Report.query.get_or_404(report_id)
    
    if not current_user.is_admin and report.user_id != current_user.id:
        abort(403)
    
    return jsonify(report.to_dict())


@reports_bp.route('/api/<int:report_id>/download')
@login_required
def download_report(report_id):
    """Download do relatório em PDF."""
    report = Report.query.get_or_404(report_id)
    
    if not current_user.is_admin and report.user_id != current_user.id:
        abort(403)
    
    if report.status != ReportStatus.COMPLETED.value:
        return jsonify({'error': 'Report not ready'}), 400
    
    if not report.file_path or not os.path.exists(report.file_path):
        return jsonify({'error': 'Report file not found'}), 404
    
    return send_file(
        report.file_path,
        as_attachment=True,
        download_name=f'{report.title.replace(" ", "_")}.pdf'
    )


@reports_bp.route('/api/<int:report_id>/share', methods=['POST'])
@login_required
@role_required('ADMIN', 'ANALYST')
def share_report(report_id):
    """API: Gerar link de compartilhamento."""
    report = Report.query.get_or_404(report_id)
    
    if not current_user.is_admin and report.user_id != current_user.id:
        abort(403)
    
    # data = request.get_json() or {}
    # expires_hours = data.get('expires_hours', 24)
    
    token = report.generate_share_token()
    # db.session.commit() # generate_share_token already commits
    
    share_url = f"{request.host_url}reports/shared/{token}"
    
    return jsonify({
        'share_url': share_url,
        'expires_at': None # report.share_expires_at.isoformat() if report.share_expires_at else None
    })


@reports_bp.route('/shared/<token>')
def view_shared_report(token):
    """Visualizar relatório compartilhado."""
    report = Report.query.filter_by(share_token=token).first_or_404()
    
    if report.share_expires_at and report.share_expires_at < datetime.utcnow():
        abort(410)  # Gone - link expirado
    
    return render_template('reports/shared.html', report=report)


@reports_bp.route('/api/<int:report_id>', methods=['DELETE'])
@login_required
@role_required('ADMIN')
def delete_report(report_id):
    """API: Deletar relatório."""
    report = Report.query.get_or_404(report_id)
    
    # Remover arquivo se existir
    if report.file_path and os.path.exists(report.file_path):
        try:
            os.remove(report.file_path)
        except Exception as e:
            logger.error(f'Error removing report file: {e}')
    
    db.session.delete(report)
    db.session.commit()
    
    logger.info(f'Report deleted: {report.title} by {current_user.username}')
    
    return jsonify({'message': 'Report deleted successfully'})


@reports_bp.route('/api/templates')
@login_required
def report_templates():
    """API: Templates de relatórios disponíveis."""
    templates = [
        {
            'name': 'Executive Summary',
            'report_type': 'EXECUTIVE_SUMMARY',
            'description': 'High-level overview of vulnerability landscape for executives',
            'parameters': {
                'include_charts': True,
                'time_range_days': 30
            }
        },
        {
            'name': 'Technical Report',
            'report_type': 'TECHNICAL_REPORT',
            'description': 'Detailed technical analysis of vulnerabilities',
            'parameters': {
                'include_cve_details': True,
                'include_mitigations': True
            }
        },
        {
            'name': 'Compliance Report',
            'report_type': 'COMPLIANCE_REPORT',
            'description': 'Compliance status against security frameworks',
            'parameters': {
                'framework': 'CIS',
                'include_remediation_status': True
            }
        },
        {
            'name': 'Risk Assessment',
            'report_type': 'RISK_ASSESSMENT',
            'description': 'Risk analysis with business impact assessment',
            'parameters': {
                'include_bia': True,
                'asset_groups': []
            }
        },
        {
            'name': 'Trend Analysis',
            'report_type': 'TREND_ANALYSIS',
            'description': 'Vulnerability trends over time',
            'parameters': {
                'time_range_days': 90,
                'group_by': 'severity'
            }
        }
    ]
    
    return jsonify({'templates': templates})


@reports_bp.route('/api/stats')
@login_required
def stats():
    """API: Estatísticas de relatórios."""
    query = Report.query
    if not current_user.is_admin:
        query = query.filter(Report.user_id == current_user.id)
    
    total = query.count()
    
    # Por status
    status_counts = db.session.query(
        Report.status,
        db.func.count(Report.id)
    )
    if not current_user.is_admin:
        status_counts = status_counts.filter(Report.user_id == current_user.id)
    status_counts = status_counts.group_by(Report.status).all()
    
    # Por tipo
    type_counts = db.session.query(
        Report.report_type,
        db.func.count(Report.id)
    )
    if not current_user.is_admin:
        type_counts = type_counts.filter(Report.user_id == current_user.id)
    type_counts = type_counts.group_by(Report.report_type).all()
    
    return jsonify({
        'total': total,
        'by_status': {str(row[0]): row[1] for row in status_counts},
        'by_type': {str(row[0]): row[1] for row in type_counts}
    })


@reports_bp.route('/<int:report_id>')
@login_required
def detail(report_id):
    """Detalhes de um relatório."""
    report = Report.query.get_or_404(report_id)
    
    if not current_user.is_admin and report.user_id != current_user.id:
        abort(403)
    
    return render_template('reports/detail.html', report=report)


def _generate_report_data(report: Report) -> None:
    """
    Gerar dados do relatório.
    
    Esta função seria chamada de forma assíncrona em produção.
    """
    from app.models.nvd import Vulnerability
    from app.models.inventory import Asset, AssetVulnerability
    from datetime import timedelta
    
    try:
        params = report.filters or {}
        time_range = params.get('time_range_days', 30)
        
        start_date = datetime.utcnow() - timedelta(days=time_range)
        
        # Coletar dados baseado no tipo
        data = {}
        
        if report.report_type == ReportType.EXECUTIVE.value:
            # Total de CVEs
            data['total_cves'] = Vulnerability.query.count()
            
            # CVEs recentes
            data['recent_cves'] = Vulnerability.query.filter(
                Vulnerability.published_date >= start_date
            ).count()
            
            # Por severidade
            severity_counts = db.session.query(
                Vulnerability.base_severity,
                db.func.count(Vulnerability.cve_id)
            ).group_by(Vulnerability.base_severity).all()
            data['by_severity'] = {row[0]: row[1] for row in severity_counts}
            
            # CISA KEV
            data['cisa_kev'] = Vulnerability.query.filter(
                Vulnerability.is_in_cisa_kev == True
            ).count()
        
        elif report.report_type == ReportType.RISK_ASSESSMENT.value:
            # Ativos do usuário
            assets = Asset.query.filter_by(owner_id=report.user_id).all()
            
            data['total_assets'] = len(assets)
            data['assets_with_vulns'] = 0
            data['high_risk_assets'] = []
            
            for asset in assets:
                vulns = AssetVulnerability.query.filter_by(asset_id=asset.id).count()
                if vulns > 0:
                    data['assets_with_vulns'] += 1
                    
                    risk_score = asset.calculate_risk_score()
                    if risk_score and risk_score > 7.0:
                        data['high_risk_assets'].append({
                            'name': asset.name,
                            'risk_score': risk_score,
                            'vulnerabilities': vulns
                        })
        
        # Salvar dados
        report.data = data
        report.complete_generation()
        db.session.commit()
        
        # TODO: Gerar PDF
        # _generate_pdf(report)
        
    except Exception as e:
        logger.error(f'Report generation failed: {e}')
        report.status = ReportStatus.FAILED
        report.data = {'error': str(e)}
        db.session.commit()
