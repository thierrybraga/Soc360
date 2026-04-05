"""
Open-Monitor Settings Module
Export configurations based on environment.
"""
import os
from app.settings.base import BaseConfig
from app.settings.production import ProductionConfig
from app.settings.development import DevelopmentConfig, TestingConfig


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env_name=None):
    """Return configuration based on environment name or FLASK_ENV."""
    if env_name is None:
        env_name = os.environ.get('FLASK_ENV', 'development')
    return config.get(env_name, config['default'])


__all__ = [
    'BaseConfig',
    'ProductionConfig', 
    'DevelopmentConfig',
    'TestingConfig',
    'config',
    'get_config'
]
