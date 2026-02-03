"""
Open-Monitor Middleware
Middlewares para segurança, logging e processamento de requests.
"""
from functools import wraps
from flask import request, g, current_app, jsonify
from flask_login import current_user
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


def admin_required(f):
    """
    Decorator que requer que o usuário seja administrador.
    Deve ser usado APÓS @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'status': 'error',
                'message': 'Autenticação necessária',
                'code': 'UNAUTHORIZED'
            }), 401
        
        if not current_user.is_admin:
            return jsonify({
                'status': 'error',
                'message': 'Acesso negado. Permissão de administrador necessária.',
                'code': 'FORBIDDEN'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def role_required(*roles):
    """
    Decorator que requer que o usuário tenha uma das roles especificadas.
    Uso: @role_required('analyst', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'status': 'error',
                    'message': 'Autenticação necessária',
                    'code': 'UNAUTHORIZED'
                }), 401
            
            # Admin sempre tem acesso
            if current_user.is_admin:
                return f(*args, **kwargs)
            
            # Verificar se usuário tem alguma das roles
            user_roles = [r.name for r in current_user.roles]
            if not any(role in user_roles for role in roles):
                return jsonify({
                    'status': 'error',
                    'message': f'Acesso negado. Roles permitidas: {", ".join(roles)}',
                    'code': 'FORBIDDEN'
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def owner_or_admin_required(get_owner_id_func):
    """
    Decorator que verifica se o usuário é dono do recurso ou admin.
    
    Args:
        get_owner_id_func: Função que recebe os kwargs da view e retorna o owner_id
    
    Uso:
        @owner_or_admin_required(lambda kwargs: Asset.query.get(kwargs['id']).owner_id)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    'status': 'error',
                    'message': 'Autenticação necessária',
                    'code': 'UNAUTHORIZED'
                }), 401
            
            # Admin sempre tem acesso
            if current_user.is_admin:
                return f(*args, **kwargs)
            
            # Verificar ownership
            try:
                owner_id = get_owner_id_func(kwargs)
                if owner_id != current_user.id:
                    return jsonify({
                        'status': 'error',
                        'message': 'Acesso negado. Você não é o proprietário deste recurso.',
                        'code': 'FORBIDDEN'
                    }), 403
            except Exception as e:
                current_app.logger.error(f"Error checking ownership: {e}")
                return jsonify({
                    'status': 'error',
                    'message': 'Erro ao verificar permissões',
                    'code': 'INTERNAL_ERROR'
                }), 500
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def api_key_required(f):
    """
    Decorator para endpoints que requerem API key.
    A key deve ser enviada no header X-API-Key.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'status': 'error',
                'message': 'API key não fornecida',
                'code': 'API_KEY_REQUIRED'
            }), 401
        
        # Validar API key
        from app.models.auth.user import User
        user = User.query.filter_by(api_key=api_key, is_active=True).first()
        
        if not user:
            return jsonify({
                'status': 'error',
                'message': 'API key inválida',
                'code': 'INVALID_API_KEY'
            }), 401
        
        # Adicionar usuário ao contexto
        g.api_user = user
        
        return f(*args, **kwargs)
    return decorated_function
