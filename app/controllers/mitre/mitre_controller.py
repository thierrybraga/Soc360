from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.utils.security.security import role_required
from app.services.mitre.mitre_service import MitreService

mitre_bp = Blueprint('mitre', __name__)

@mitre_bp.route('/api/mitre/sync/status', methods=['GET'])
@login_required
def sync_status():
    """API: Status da sincronização MITRE."""
    service = MitreService()
    return jsonify(service.get_status())

@mitre_bp.route('/api/mitre/sync/<cve_id>', methods=['POST'])
@login_required
@role_required('ADMIN')
def sync_cve(cve_id):
    """API: Sincronizar um CVE específico da MITRE."""
    service = MitreService()
    try:
        stats = service.sync_cve(cve_id)
        return jsonify({
            'message': f'MITRE sync for {cve_id} completed',
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@mitre_bp.route('/api/mitre/enrich', methods=['POST'])
@login_required
@role_required('ADMIN')
def enrich_vulnerabilities():
    """API: Enriquecer vulnerabilidades existentes com dados da MITRE."""
    limit = request.args.get('limit', 100, type=int)
    service = MitreService()
    
    if service.start_enrichment_task(limit=limit):
        return jsonify({
            'message': 'MITRE enrichment started',
            'status': 'running'
        }), 202
    else:
        return jsonify({
            'message': 'MITRE enrichment already in progress',
            'status': 'running'
        }), 200