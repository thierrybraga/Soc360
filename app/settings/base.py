"""
Open-Monitor Base Settings
Configurações compartilhadas entre todos os ambientes.
"""
import os
from datetime import timedelta


class BaseConfig:
    """Configurações base do Open-Monitor."""
    
    # Application
    APP_NAME = "Open-Monitor"
    APP_VERSION = "3.0.0"
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Session
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'True').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    
    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # Database URLs
    DB_CORE_HOST = os.environ.get('DB_CORE_HOST', 'postgres_core')
    DB_CORE_PORT = os.environ.get('DB_CORE_PORT', '5432')
    DB_CORE_NAME = os.environ.get('DB_CORE_NAME', 'open_monitor_core')
    DB_CORE_USER = os.environ.get('DB_CORE_USER', 'open_monitor')
    DB_CORE_PASSWORD = os.environ.get('DB_CORE_PASSWORD', 'change_me')
    
    DB_PUBLIC_HOST = os.environ.get('DB_PUBLIC_HOST', 'postgres_public')
    DB_PUBLIC_PORT = os.environ.get('DB_PUBLIC_PORT', '5432')
    DB_PUBLIC_NAME = os.environ.get('DB_PUBLIC_NAME', 'open_monitor_public')
    DB_PUBLIC_USER = os.environ.get('DB_PUBLIC_USER', 'open_monitor')
    DB_PUBLIC_PASSWORD = os.environ.get('DB_PUBLIC_PASSWORD', 'change_me')
    
    SQLALCHEMY_DATABASE_URI = f"postgresql://{DB_CORE_USER}:{DB_CORE_PASSWORD}@{DB_CORE_HOST}:{DB_CORE_PORT}/{DB_CORE_NAME}"
    
    SQLALCHEMY_BINDS = {
        'core': f"postgresql://{DB_CORE_USER}:{DB_CORE_PASSWORD}@{DB_CORE_HOST}:{DB_CORE_PORT}/{DB_CORE_NAME}",
        'public': f"postgresql://{DB_PUBLIC_USER}:{DB_PUBLIC_PASSWORD}@{DB_PUBLIC_HOST}:{DB_PUBLIC_PORT}/{DB_PUBLIC_NAME}"
    }
    
    # Redis
    REDIS_HOST = os.environ.get('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)
    REDIS_URL = os.environ.get('REDIS_URL', f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    CACHE_DEFAULT_TTL = 900  # 15 minutes
    
    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', f"redis://{REDIS_HOST}:{REDIS_PORT}/1")
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', f"redis://{REDIS_HOST}:{REDIS_PORT}/1")
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_TIMEZONE = 'UTC'
    
    from celery.schedules import crontab
    CELERY_BEAT_SCHEDULE = {
        'sync-nvd-incremental': {
            'task': 'nvd.sync',
            'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
            'args': ('incremental',)
        },
    }
    
    # NVD API
    NVD_API_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    NVD_API_KEY = os.environ.get('NVD_API_KEY', None)
    NVD_RATE_LIMIT_WITH_KEY = 50  # requests per 30 seconds
    NVD_RATE_LIMIT_WITHOUT_KEY = 5  # requests per 30 seconds
    NVD_SYNC_WINDOW_DAYS = 120  # NVD API limit
    NVD_INCREMENTAL_DAYS = 30
    NVD_RESULTS_PER_PAGE = 2000
    
    # OpenAI
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', None)
    OPENAI_MODEL = os.environ.get('OPENAI_MODEL', 'gpt-4')
    OPENAI_MAX_TOKENS = 4000
    
    # Email (SMTP)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', None)
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', None)
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@open-monitor.local')
    
    # Rate Limiting
    RATE_LIMIT_LOGIN_ATTEMPTS = 5
    RATE_LIMIT_LOGIN_WINDOW = 300  # 5 minutes
    RATE_LIMIT_API_REQUESTS = 100
    RATE_LIMIT_API_WINDOW = 60  # 1 minute
    
    # Password Policy
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_DIGIT = True
    PASSWORD_REQUIRE_SPECIAL = True
    PASSWORD_RESET_TOKEN_EXPIRY = 86400  # 24 hours
    
    # Bcrypt
    BCRYPT_LOG_ROUNDS = 12
    
    # Pagination
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 100
    
    # File Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Reports
    REPORTS_DIR = os.environ.get('REPORTS_DIR', '/app/reports')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = 'json'
    
    # Auto Root User
    AUTO_CREATE_ROOT = os.environ.get('AUTO_CREATE_ROOT', 'false').lower() == 'true'
    AUTO_ROOT_USERNAME = os.environ.get('AUTO_ROOT_USERNAME', 'admin')
    AUTO_ROOT_EMAIL = os.environ.get('AUTO_ROOT_EMAIL', 'admin@open-monitor.local')
    AUTO_ROOT_PASSWORD = os.environ.get('AUTO_ROOT_PASSWORD', None)
