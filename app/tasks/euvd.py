from app.extensions.celery_extension import celery, CELERY_AVAILABLE
from app.services.euvd.euvd_service import EUVDService


def _task(name):
    """Decorator that uses celery.task if available, otherwise a no-op."""
    def decorator(fn):
        if CELERY_AVAILABLE and celery is not None:
            return celery.task(name=name)(fn)
        return fn
    return decorator


@_task(name='euvd.sync_latest')
def sync_euvd_latest_task():
    """
    Tarefa Celery para sincronização das últimas vulnerabilidades EUVD.
    """
    service = EUVDService()
    service.sync_latest()


@_task(name='euvd.sync_by_date')
def sync_euvd_by_date_task(from_date: str, to_date: str):
    """
    Tarefa Celery para sincronização EUVD por intervalo de datas.
    
    Args:
        from_date: Data inicial (YYYY-MM-DD)
        to_date: Data final (YYYY-MM-DD)
    """
    service = EUVDService()
    service.sync_by_date(from_date, to_date)