"""
SOC360 Login Extension
Configuração do Flask-Login para gerenciamento de sessões.
"""
from flask_login import LoginManager
from flask import redirect, url_for, flash, request


login_manager = LoginManager()


def init_login(app):
    """Inicializa o Flask-Login com a aplicação."""
    login_manager.init_app(app)
    
    # Configurações
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection = 'strong'
    login_manager.refresh_view = 'auth.login'
    login_manager.needs_refresh_message = 'Sua sessão expirou. Por favor, faça login novamente.'
    login_manager.needs_refresh_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Carrega o usuário pelo ID da sessão."""
        from app.models.auth.user import User
        return User.query.get(int(user_id))
    
    @login_manager.unauthorized_handler
    def unauthorized():
        """Handler para acessos não autorizados."""
        if request.is_json or request.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({
                'status': 'error',
                'message': 'Autenticação necessária',
                'code': 'UNAUTHORIZED'
            }), 401
        
        flash('Por favor, faça login para acessar esta página.', 'warning')
        return redirect(url_for('auth.login', next=request.url))
    
    return login_manager


def get_login_manager():
    """Retorna a instância do LoginManager."""
    return login_manager
