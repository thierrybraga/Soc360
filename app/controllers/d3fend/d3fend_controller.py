"""
SOC360 D3FEND Controller
Endpoints para integração com MITRE D3FEND
"""
import logging
import threading
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from app.utils.security.security import role_required
from app.services.d3fend.d3fend_service import D3FENDService
from app.models.d3fend import D3fendTechnique, CveD3fendCorrelation

logger = logging.getLogger(__name__)

d3fend_bp = Blueprint('d3fend', __name__, url_prefix='/api/d3fend')


def _run_in_context(app, func, *args, **kwargs):
    """Executa função em thread com app context."""
    def runner():
        with app.app_context():
            try:
                func(*args, **kwargs)
            except Exception as e:
                logger.exception('D3FEND background task failed: %s', e)
    t = threading.Thread(target=runner, daemon=True)
    t.start()
    return t


@d3fend_bp.route('/sync/status', methods=['GET'])
@login_required
def sync_status():
    """API: Status da sincronização D3FEND."""
    service = D3FENDService()
    return jsonify(service.get_progress())


@d3fend_bp.route('/sync', methods=['POST'])
@login_required
@role_required('ADMIN')
def start_sync():
    """API: Iniciar sincronização D3FEND."""
    service = D3FENDService()
    
    # Verificar se já está rodando
    progress = service.get_progress()
    if progress.get('status') == 'running':
        return jsonify({
            'message': 'D3FEND sync already running',
            'status': 'running'
        }), 200
    
    # Iniciar em background
    app = current_app._get_current_object()
    _run_in_context(app, service.sync_all)
    
    logger.info(f'D3FEND sync started by {current_user.username}')
    return jsonify({
        'message': 'D3FEND sync started',
        'status': 'running'
    }), 202


@d3fend_bp.route('/sync/correlate', methods=['POST'])
@login_required
@role_required('ADMIN')
def correlate_cves():
    """API: Correlacionar CVEs com D3FEND."""
    data = request.get_json() or {}
    limit = data.get('limit', 1000)
    
    service = D3FENDService()
    
    # Verificar se já está rodando
    progress = service.get_progress()
    if progress.get('status') == 'running':
        return jsonify({
            'message': 'Correlation already running',
            'status': 'running'
        }), 200
    
    # Iniciar em background
    app = current_app._get_current_object()
    _run_in_context(app, service.correlate_cves, limit)
    
    logger.info(f'CVE-D3FEND correlation started by {current_user.username}')
    return jsonify({
        'message': 'CVE-D3FEND correlation started',
        'status': 'running'
    }), 202


@d3fend_bp.route('/techniques', methods=['GET'])
@login_required
def list_techniques():
    """API: Listar técnicas D3FEND."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    query = D3fendTechnique.query.paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'techniques': [t.to_dict() for t in query.items],
        'total': query.total,
        'pages': query.pages,
        'current_page': page
    })


@d3fend_bp.route('/techniques/<technique_id>', methods=['GET'])
@login_required
def get_technique(technique_id):
    """API: Detalhes de uma técnica D3FEND."""
    technique = D3fendTechnique.query.get_or_404(technique_id)
    return jsonify(technique.to_dict())


@d3fend_bp.route('/correlate/<cve_id>', methods=['GET'])
@login_required
def get_cve_correlations(cve_id):
    """API: Correlações D3FEND para uma CVE."""
    service = D3FENDService()
    correlations = service.get_d3fend_for_cve(cve_id)
    return jsonify({
        'cve_id': cve_id,
        'correlations': correlations,
        'count': len(correlations)
    })