web: gunicorn app:create_app()
worker: celery -A scripts.workers.celery_worker.celery worker --loglevel=info
beat: celery -A scripts.workers.celery_worker.celery beat --loglevel=info
