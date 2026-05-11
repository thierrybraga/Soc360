"""
SOC360 Database Utilities
Funções para inicialização e manutenção do banco de dados.
"""
import os
import logging
from flask import Flask
from app.extensions import db
from app.models.auth import User, Role
from app.models.system import SyncMetadata
from sqlalchemy import inspect, text, create_engine


def _is_postgres_available(uri: str, timeout: int = 3) -> bool:
    """Verifica se o PostgreSQL está acessível na URI fornecida."""
    try:
        test_engine = create_engine(uri, pool_pre_ping=True, connect_args={'connect_timeout': timeout})
        with test_engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        return True
    except Exception:
        return False

logger = logging.getLogger(__name__)

def _sqlite_col_type(column) -> str:
    """Converte o tipo SQLAlchemy de uma coluna para um tipo SQLite válido."""
    type_str = str(column.type).upper()
    base = type_str.split('(')[0].strip()

    # Inteiros
    if base in ('INTEGER', 'INT', 'BIGINT', 'SMALLINT', 'TINYINT'):
        return 'INTEGER'
    # Booleano (SQLite armazena como INTEGER 0/1)
    if base in ('BOOLEAN', 'BOOL'):
        return 'INTEGER'
    # Ponto flutuante
    if base in ('FLOAT', 'REAL', 'DOUBLE', 'DOUBLE_PRECISION', 'NUMERIC', 'DECIMAL'):
        return 'REAL'
    # Data/hora
    if base in ('DATETIME', 'TIMESTAMP'):
        return 'DATETIME'
    if base == 'DATE':
        return 'DATE'
    # Strings de tamanho fixo
    if base in ('VARCHAR', 'CHAR', 'NVARCHAR', 'NCHAR'):
        return 'TEXT'
    # Tudo o mais (TEXT, JSON, JSONB, INET, ARRAY, BLOB, etc.) → TEXT
    return 'TEXT'


def ensure_schema_up_to_date(app: Flask):
    """
    Verifica se o schema do banco de dados está atualizado.
    Para SQLite, adiciona colunas faltantes automaticamente via ALTER TABLE.
    """
    with app.app_context():
        # 1. Criar tabelas que ainda não existem
        db.create_all()

        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        # Iterar sobre todos os mappers registrados no SQLAlchemy
        for mapper in db.Model.registry.mappers:
            model = mapper.class_
            if not hasattr(model, '__table__'):
                continue

            table_name = model.__tablename__
            if table_name not in table_names:
                continue

            # Obter colunas atuais do banco
            try:
                existing_columns = {c['name'] for c in inspector.get_columns(table_name)}
            except Exception:
                continue

            # Verificar cada coluna do model
            for column in model.__table__.columns:
                if column.name in existing_columns:
                    continue

                logger.info(f"Adicionando coluna faltante '{column.name}' na tabela '{table_name}'...")

                col_type = _sqlite_col_type(column)

                default_val = ""
                if column.default is not None and hasattr(column.default, 'arg'):
                    arg = column.default.arg
                    if isinstance(arg, bool):
                        default_val = f" DEFAULT {1 if arg else 0}"
                    elif isinstance(arg, (int, float)):
                        default_val = f" DEFAULT {arg}"
                    elif isinstance(arg, str):
                        # Escapar aspas simples para evitar SQL injection via valores defaults
                        safe = arg.replace("'", "''")
                        default_val = f" DEFAULT '{safe}'"

                try:
                    db.session.execute(
                        text(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{default_val}")
                    )
                    db.session.commit()
                    logger.info(f"Coluna '{column.name}' adicionada com sucesso.")
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Erro ao adicionar coluna '{column.name}' em '{table_name}': {e}")

def initialize_database(app: Flask):
    """
    Inicializa o banco de dados, cria tabelas e dados iniciais.
    
    1. Cria todas as tabelas se não existirem.
    2. Cria as roles padrão (ADMIN, ANALYST, VIEWER, API_USER).
    3. Cria o usuário administrador padrão (admin/admin).
    4. Marca o sistema como inicializado.
    5. Dispara gatilhos de sincronização inicial.
    """
    with app.app_context():
        # 1. Criar tabelas
        logger.info("Criando tabelas no banco de dados...")
        db.create_all()
        
        # 2. Criar roles padrão
        logger.info("Inicializando roles padrão...")
        roles_created = Role.create_default_roles()
        if roles_created:
            logger.info(f"Roles criadas: {', '.join(roles_created)}")
        else:
            logger.info("Roles já existem.")
            
        # 3. Criar usuário admin padrão
        create_default_admin()
        
        # 4. Marcar sistema como inicializado
        SyncMetadata.set_value('system_initialized', 'true')
        logger.info("Sistema marcado como inicializado.")
        
        # 5. Aviso de Sincronização
        logger.warning(
            "As sincronizações base (NVD, EUVD, MITRE) não são mais disparadas automaticamente no start da aplicação "
            "para evitar problemas de Threads inseguras no servidor WSGI (Gunicorn/uWSGI). "
            "Por favor, proceda com o Sync manualmente através da Interface UI (Assistente admin) ou via DAGs do Airflow."
        )

def create_default_admin():
    """Cria o usuário administrador padrão (admin/admin)."""
    admin_username = 'admin'
    admin_email = 'admin@soc360.local'
    admin_password = 'admin' # Senha solicitada pelo usuário
    
    admin_user = User.query.filter_by(username=admin_username).first()
    if not admin_user:
        logger.info(f"Criando usuário administrador: {admin_username}")
        # Criar admin usando o novo construtor que lida com is_admin
        admin_user = User(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            is_admin=True,
            is_active=True,
            email_confirmed=True,
            force_password_reset=True
        )
        db.session.add(admin_user)
        db.session.commit()
        logger.info("Usuário administrador criado com sucesso.")
    else:
        logger.info("Usuário administrador já existe.")
        # Garantir que tenha a role ADMIN
        admin_role = Role.query.filter_by(name='ADMIN').first()
        if admin_role and admin_role not in admin_user.roles:
            admin_user.roles.append(admin_role)
            db.session.commit()
            logger.info("Role ADMIN associada ao usuário administrador existente.")



def check_and_init_db(app: Flask):
    """Verifica se o banco precisa ser inicializado e o faz se necessário."""
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    db_path = os.path.join(basedir, 'instance', 'app.db')

    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')

    # Se estiver em modo PostgreSQL e não acessível, faz fallback para SQLite
    if db_uri.startswith('postgresql://'):
        if not _is_postgres_available(db_uri):
            app.logger.warning('Postgres não acessível (%s). Fallback para SQLite em %s', db_uri, db_path)
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
            app.config['SQLALCHEMY_BINDS'] = {
                'core': 'sqlite:///' + db_path,
                'public': 'sqlite:///' + db_path
            }
            # StaticPool compartilha uma única conexão entre threads de forma segura,
            # evitando "SQLite objects created in a thread can only be used in that same thread".
            from sqlalchemy.pool import StaticPool
            app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'connect_args': {'check_same_thread': False},
                'poolclass': StaticPool,
            }
            app.config['REDIS_URL'] = None
            app.config['REDIS_HOST'] = 'localhost'
            app.config['DB_CORE_HOST'] = 'localhost'
            app.config['DB_PUBLIC_HOST'] = 'localhost'
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']

            # Rebind SQLAlchemy (o init_extensions pode já estar aplicado com a URI antiga)
            try:
                logger.info('Reconectando SQLAlchemy com SQLite após fallback.')
                from app.extensions import db as app_db
                app_db.session.remove()
                app_db.engine.dispose()
                app_db.init_app(app)
            except Exception as e:
                logger.error('Erro ao reconfigurar SQLAlchemy após fallback: %s', e, exc_info=True)

    if db_uri.startswith('sqlite:///'):
        if not os.path.exists(db_path):
            logger.info(f"Banco de dados SQLite não encontrado em {db_path}. Iniciando inicialização...")
            initialize_database(app)
        else:
            # Mesmo se o arquivo existe, garante que o schema está atualizado
            ensure_schema_up_to_date(app)

            # Verifica se o sistema foi marcado como inicializado
            with app.app_context():
                try:
                    if not SyncMetadata.get('system_initialized'):
                        logger.info("Banco existe mas sistema não está inicializado. Rodando inicialização...")
                        initialize_database(app)
                except Exception:
                    # Se der erro (ex: tabela SyncMetadata não existe), inicializa
                    logger.info("Erro ao verificar status. Rodando inicialização completa...")
                    initialize_database(app)
    else:
        # Em modo não SQlite assumimos banco principal já existe (Postgres disponível)
        logger.info('Usando mecanismo de banco de dados existente: %s', db_uri)
