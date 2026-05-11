import logging
import threading

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required
from app.utils.security.security import role_required
from app.models.system import SyncMetadata
from app.services.euvd.euvd_service import EUVDService

logger = logging.getLogger(__name__)

euvd_bp = Blueprint('euvd', __name__)


def _euvd_is_running() -> bool:
    return (SyncMetadata.get('euvd_sync_progress_status') or '').lower() == 'running'


def _run_in_app_context(app, fn, *args, **kwargs):
    def _runner():
        with app.app_context():
            try:
                fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.exception('EUVD background task failed: %s', exc)
    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    return t


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
    """API: Disparar sincronização EUVD em background (retorna imediatamente)."""
    if _euvd_is_running():
        return jsonify({
            'message': 'EUVD sync already running',
            'status': 'running'
        }), 200

    app = current_app._get_current_object()
    service = EUVDService()
    _run_in_app_context(app, service.sync_latest)
    return jsonify({
        'message': 'EUVD sync started',
        'status': 'running'
    }), 202


@euvd_bp.route('/api/euvd/sync/range', methods=['POST'])
@login_required
@role_required('ADMIN')
def sync_range():
    """API: Sincronizar EUVD por intervalo de datas (background)."""
    data = request.get_json() or {}
    from_date = data.get('from_date')
    to_date = data.get('to_date')

    if not from_date or not to_date:
        return jsonify({'error': 'from_date and to_date required'}), 400

    if _euvd_is_running():
        return jsonify({
            'message': 'EUVD sync already running',
            'status': 'running'
        }), 200

    app = current_app._get_current_object()
    service = EUVDService()
    _run_in_app_context(app, service.sync_by_date, from_date, to_date)
    return jsonify({
        'message': 'EUVD range sync started',
        'status': 'running'
    }), 202
