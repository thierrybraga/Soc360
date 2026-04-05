"""
Open-Monitor Database Extension
Configuração do SQLAlchemy com suporte a múltiplos bancos.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import MetaData

# Convenção de nomenclatura para constraints
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=naming_convention)

# Instância global do SQLAlchemy
db = SQLAlchemy(metadata=metadata)

# Instância global do Flask-Migrate
migrate = Migrate()


def init_db(app):
    """Inicializa o banco de dados com a aplicação Flask."""
    db.init_app(app)
    migrate.init_app(app, db)
    
    with app.app_context():
        # Importar models para registrar no metadata
        from app.models import (
            User, Role, UserRole,
            Vulnerability, CvssMetric, Weakness, Reference, Mitigation,
            Asset, AssetVulnerability, Vendor, Product,
            MonitoringRule, Alert, Report, RiskAssessment,
            SyncMetadata, ApiCallLog,
            Tactic, Technique, AttackMitigation
        )
    
    return db


def get_db():
    """Retorna a instância do banco de dados."""
    return db
