
from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.utils.security.security import role_required
from app.services.euvd.euvd_service import EUVDService

euvd_bp = Blueprint('euvd', __name__)

@euvd_bp.route('/api/euvd/sync/status', methods=['GET'])
@login_required
def sync_status():
    """API: Status da sincronização EUVD."""
    service = EUVDService()
    return jsonify(service.get_status())

@euvd_bp.route('/api/euvd/sync/latest', methods=['POST'])
@login_required
@role_required('ADMIN')
def sync_latest():
    """API: Sincronizar últimas vulnerabilidades da EUVD."""
    service = EUVDService()
    try:
        stats = service.sync_latest()
        return jsonify({
            'message': 'EUVD sync completed',
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@euvd_bp.route('/api/euvd/sync/range', methods=['POST'])
@login_required
@role_required('ADMIN')
def sync_range():
    """API: Sincronizar EUVD por intervalo de datas."""
    data = request.get_json()
    from_date = data.get('from_date')
    to_date = data.get('to_date')
    
    if not from_date or not to_date:
        return jsonify({'error': 'from_date and to_date required'}), 400
        
    service = EUVDService()
    try:
        # TODO: Isso pode demorar, idealmente deveria ser async (Celery)
        # Por enquanto faremos síncrono para testar ou assumindo range pequeno
        service.sync_by_date(from_date, to_date)
        return jsonify({
            'message': 'EUVD range sync started/completed',
            'stats': service.stats
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
