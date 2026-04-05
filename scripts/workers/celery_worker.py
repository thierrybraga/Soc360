
import os
from app import create_app
from app.extensions.celery_extension import celery

flask_app = create_app(os.getenv('FLASK_ENV', 'development'))
flask_app.app_context().push()
