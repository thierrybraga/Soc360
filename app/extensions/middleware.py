"""
Open-Monitor Middleware
Middlewares para logging e processamento de requests.
"""
from flask import request, g, current_app
import time
import uuid


def init_middleware(app):
    """Registra todos os middlewares na aplicação."""

    @app.before_request
    def before_request():
        """Executa antes de cada request."""
        # Request ID para rastreamento
        g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        g.request_start_time = time.time()

        # Log do request
        if current_app.config.get('DEBUG'):
            current_app.logger.debug(
                f"Request: {request.method} {request.path}",
                extra={
                    'request_id': g.request_id,
                    'remote_addr': request.remote_addr,
                    'user_id': (current_user.id
                               if current_user.is_authenticated
                               else None)
                }
            )

    @app.after_request
    def after_request(response):
        """Executa após cada request."""
        # Tempo de resposta
        if hasattr(g, 'request_start_time'):
            elapsed = time.time() - g.request_start_time
            response.headers['X-Response-Time'] = f"{elapsed:.3f}s"

        # Request ID no response
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id

        # Cache control para APIs
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'

        return response

    @app.teardown_request
    def teardown_request(exception=None):
        """Executa no final de cada request, mesmo com erro."""
        if exception:
            current_app.logger.error(
                f"Request error: {exception}",
                extra={
                    'request_id': getattr(g, 'request_id', 'unknown'),
                    'path': request.path
                }
            )
