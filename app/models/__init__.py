"""
Open-Monitor Models
Exportação centralizada de todos os models.
"""
# System Models
from app.models.system import (
    BaseModel,
    CoreModel,
    PublicModel,
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
    SyncMetadata
)

# Auth Models
from app.models.auth import User, Role, UserRole

# NVD Models
from app.models.nvd import (
    Vulnerability,
    CvssMetric,
    Weakness,
    Reference,
    Mitigation
)

# Inventory Models
from app.models.inventory import (
    Asset,
    AssetVulnerability,
    Vendor,
    Product
)

# Monitoring Models
from app.models.monitoring import (
    MonitoringRule,
    Alert,
    Report,
    RiskAssessment,
    ApiCallLog
)


__all__ = [
    # System
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
    
    # Auth
    'User',
    'Role',
    'UserRole',
    
    # NVD
    'Vulnerability',
    'CvssMetric',
    'Weakness',
    'Reference',
    'Mitigation',
    
    # Inventory
    'Asset',
    'AssetVulnerability',
    'Vendor',
    'Product',
    
    # Monitoring
    'MonitoringRule',
    'Alert',
    'Report',
    'RiskAssessment',
    'ApiCallLog'
]
