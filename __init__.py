from flask import Flask, request, redirect
import os
from werkzeug.middleware.proxy_fix import ProxyFix

# Importações do seu projeto
from app.routes import main_blueprint
from app.models import create_table
from app.utils import schedule_update
from app.llmconnectorOLD import get_risk_analysis

def create_app():
    """
    Inicializa a aplicação Flask com diretórios corretos para templates e arquivos estáticos.
    Aplica redirecionamento de HTTP para HTTPS em ambiente de produção.
    """
    project_root = os.path.abspath(os.path.dirname(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, 'static/templates'),
        static_folder=os.path.join(project_root, 'static')
    )

    # Registrar rotas
    app.register_blueprint(main_blueprint)

    # Inicializar tabelas e agendamento de tarefas
    create_table()
    schedule_update()

    # Forçar HTTPS apenas em produção
    if os.getenv("FLASK_CONFIG", "development") == "production":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)

        @app.before_request
        def redirect_to_https():
            if not request.is_secure:
                url = request.url.replace("http://", "https://", 1)
                return redirect(url, code=301)

    return app
