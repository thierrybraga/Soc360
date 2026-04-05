
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

    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    app.extensions['celery'] = celery
