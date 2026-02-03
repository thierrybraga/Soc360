"""
Open-Monitor Development Settings
Configurações otimizadas para desenvolvimento local.
"""
import os
from app.settings.base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """Configurações de desenvolvimento."""
    
    DEBUG = True
    TESTING = False
    
    # Security - Relaxed for development
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = True
    
    # Development database - pode usar SQLite para testes rápidos
    DB_CORE_HOST = os.environ.get('DB_CORE_HOST', 'localhost')
    DB_PUBLIC_HOST = os.environ.get('DB_PUBLIC_HOST', 'localhost')
    
    # Re-definir URIs para usar os hosts locais (sobrescrevendo BaseConfig)
    SQLALCHEMY_DATABASE_URI = f"postgresql://{BaseConfig.DB_CORE_USER}:{BaseConfig.DB_CORE_PASSWORD}@{DB_CORE_HOST}:{BaseConfig.DB_CORE_PORT}/{BaseConfig.DB_CORE_NAME}"
    
    SQLALCHEMY_BINDS = {
        'core': SQLALCHEMY_DATABASE_URI,
        'public': f"postgresql://{BaseConfig.DB_PUBLIC_USER}:{BaseConfig.DB_PUBLIC_PASSWORD}@{DB_PUBLIC_HOST}:{os.environ.get('DB_PUBLIC_PORT', BaseConfig.DB_PUBLIC_PORT)}/{BaseConfig.DB_PUBLIC_NAME}"
    }

    # Redis - localhost
    REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    
    # Performance - Development friendly
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0
    
    # Database pool - smaller for development
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 5,
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'echo': False,  # Set True to see SQL queries
    }
    
    # SQLite fallback support
    if os.environ.get('USE_SQLITE'):
        print("DEBUG: Enabling SQLite Mode in DevelopmentConfig")
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        db_path = os.path.join(basedir, 'app.db')
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + db_path
        SQLALCHEMY_BINDS = {
            'core': 'sqlite:///' + db_path,
            'public': 'sqlite:///' + db_path
        }
        # Disable Redis if using SQLite mode
        REDIS_URL = None
        CELERY_BROKER_URL = 'memory://'
        CELERY_RESULT_BACKEND = 'db+sqlite:///' + os.path.join(basedir, 'celery.db')

    @classmethod
    def init_app(cls, app):
        """Inicialização específica de desenvolvimento."""
        pass


class TestingConfig(BaseConfig):
    """Configurações para testes automatizados."""
    
    DEBUG = True
    TESTING = True
    
    # Force localhost for testing if not set
    DB_CORE_HOST = os.environ.get('DB_CORE_HOST', 'localhost')
    DB_PUBLIC_HOST = os.environ.get('DB_PUBLIC_HOST', 'localhost')
    
    # Re-definir URIs para usar os hosts locais
    SQLALCHEMY_DATABASE_URI = f"postgresql://{BaseConfig.DB_CORE_USER}:{BaseConfig.DB_CORE_PASSWORD}@{DB_CORE_HOST}:{BaseConfig.DB_CORE_PORT}/{BaseConfig.DB_CORE_NAME}"
    
    SQLALCHEMY_BINDS = {
        'core': SQLALCHEMY_DATABASE_URI,
        'public': f"postgresql://{BaseConfig.DB_PUBLIC_USER}:{BaseConfig.DB_PUBLIC_PASSWORD}@{DB_PUBLIC_HOST}:{BaseConfig.DB_PUBLIC_PORT}/{BaseConfig.DB_PUBLIC_NAME}"
    }
    
    # Use SQLite in-memory for tests ONLY if explicitly requested or if no DB configured
    # Otherwise, respect BaseConfig (PostgreSQL)
    if os.environ.get('USE_SQLITE_TEST'):
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        SQLALCHEMY_BINDS = {
            'core': 'sqlite:///:memory:',
            'public': 'sqlite:///:memory:'
        }
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Disable rate limiting for tests
    RATE_LIMIT_LOGIN_ATTEMPTS = 1000
    RATE_LIMIT_API_REQUESTS = 10000
    
    # Use lower bcrypt rounds for faster tests
    BCRYPT_LOG_ROUNDS = 4
    
    # Disable Redis caching
    CACHE_DEFAULT_TTL = 0
    
    @classmethod
    def init_app(cls, app):
        """Inicialização específica de testes."""
        pass