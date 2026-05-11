
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    celery = Celery()
    CELERY_AVAILABLE = True
except ImportError:
    logger.warning("Celery not installed. Task queue features will be disabled.")
    celery = None
    CELERY_AVAILABLE = False

from flask import Flask


def init_celery(app: Flask) -> None:
    """Initialize Celery with Flask app config."""
    if not CELERY_AVAILABLE or celery is None:
        logger.warning("Celery not available, skipping initialization.")
        return

    # Celery 5+ uses lowercase keys — map explicitly from Flask's CELERY_* convention
    celery.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND'),
        task_serializer=app.config.get('CELERY_TASK_SERIALIZER', 'json'),
        result_serializer=app.config.get('CELERY_RESULT_SERIALIZER', 'json'),
        accept_content=app.config.get('CELERY_ACCEPT_CONTENT', ['json']),
        timezone=app.config.get('CELERY_TIMEZONE', 'UTC'),
        beat_schedule=app.config.get('CELERY_BEAT_SCHEDULE', {}),
        broker_connection_retry_on_startup=True,
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    app.extensions['celery'] = celery
