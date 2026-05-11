"""
SOC360 System Models
Models de sistema e infraestrutura.
"""
from app.models.system.base_model import BaseModel, CoreModel, PublicModel
from app.models.system.enums import (
    Severity,
    AssetType,
    AssetStatus,
    VulnerabilityStatus,
    ReportType,
    ReportStatus,
    MonitoringRuleType,
    AlertChannel,
    AlertStatus,
    SyncStatus,
    RoleType,
    CvssVersion,
    ReferenceType,
)
from app.models.system.sync_metadata import SyncMetadata
from app.models.system.audit_log import AuditLog
from app.models.system.chat import ChatSession, ChatMessage
from app.models.system.chat_log import ChatLog
from app.models.system.newsletter_subscriber import NewsletterSubscription, NewsletterSubscriber


__all__ = [
    'BaseModel',
    'CoreModel',
    'PublicModel',
    'Severity',
    'AssetType',
    'AssetStatus',
    'VulnerabilityStatus',
    'ReportType',
    'ReportStatus',
    'MonitoringRuleType',
    'AlertChannel',
    'AlertStatus',
    'SyncStatus',
    'RoleType',
    'CvssVersion',
    'ReferenceType',
    'SyncMetadata',
    'AuditLog',
    'ChatSession',
    'ChatMessage',
    'ChatLog',
    'NewsletterSubscription',
    'NewsletterSubscriber',
]
