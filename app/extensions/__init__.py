"""
Open-Monitor Extensions Module
Inicialização centralizada de todas as extensões Flask.
"""
from app.extensions.db import db, migrate, init_db, get_db
from app.extensions.login import login_manager, init_login, get_login_manager
from app.extensions.csrf import csrf, init_csrf, get_csrf, exempt_csrf
from app.extensions.middleware import (
    init_middleware,
    admin_required,
    role_required,
    owner_or_admin_required,
    api_key_required
)
from app.extensions.celery_extension import celery, init_celery
from app.utils.security.headers import security_headers


def init_extensions(app):
    """Inicializa todas as extensões Flask."""
    # Banco de dados
    init_db(app)
    
    # Autenticação
    init_login(app)
    
    # CSRF Protection
    init_csrf(app)
    
    # Celery
    init_celery(app)
    
    # Middlewares
    init_middleware(app)
    
    # Security Headers
    security_headers.init_app(app)


__all__ = [
    # Database
    'db',
    'migrate',
    'init_db',
    'get_db',
    
    # Login
    'login_manager',
    'init_login',
    'get_login_manager',
    
    # CSRF
    'csrf',
    'init_csrf',
    'get_csrf',
    'exempt_csrf',
    
    # Middleware
    'init_middleware',
    'admin_required',
    'role_required',
    'owner_or_admin_required',
    'api_key_required',
    
    # Init
    'init_extensions',

    # Celery
    'celery'
]
