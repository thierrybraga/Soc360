"""
SOC360 CSRF Extension
Proteção contra Cross-Site Request Forgery.
"""
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask import jsonify, flash, redirect, url_for, request, render_template


csrf = CSRFProtect()


def init_csrf(app):
    """Inicializa a proteção CSRF na aplicação."""
    csrf.init_app(app)
    
    # Endpoints excluídos da proteção CSRF (webhooks, etc)
    # Nota: APIs devem usar tokens próprios, não CSRF
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        """Handler para erros de CSRF."""
        if hasattr(e, 'description'):
            message = e.description
        else:
            message = 'Token CSRF inválido ou expirado.'

        # Se for na página de login, redirecionar para recarregar o token
        if request.endpoint == 'auth.login':
            flash('Sessão expirada. Por favor, tente novamente.', 'warning')
            return redirect(url_for('auth.login'))

        # Detecta requisições AJAX/API (qualquer endpoint "/api/" dentro de um
        # blueprint, XHR, JSON ou Accept explícito). Inclui /reports/api/...,
        # /vulnerabilities/api/..., /monitoring/api/..., etc.
        is_api_like = (
            request.is_json
            or '/api/' in request.path
            or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in (request.headers.get('Accept') or '')
        )
        if is_api_like:
            return jsonify({
                'status': 'error',
                'error': message,
                'message': message,
                'code': 'CSRF_ERROR'
            }), 400

        # Renderizar página de erro para requisições normais
        return render_template('errors/error.html', error_code=400, error_title='CSRF Error', error_message=message), 400
    
    return csrf


def get_csrf():
    """Retorna a instância do CSRFProtect."""
    return csrf


def exempt_csrf(view_func):
    """Decorator para isentar views da proteção CSRF."""
    return csrf.exempt(view_func)
