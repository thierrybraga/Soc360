"""
Open-Monitor Enums
Enumerações utilizadas em todo o sistema.
"""
from enum import Enum


class Severity(str, Enum):
    """Níveis de severidade CVSS."""
    CRITICAL = 'CRITICAL'
    HIGH = 'HIGH'
    MEDIUM = 'MEDIUM'
    LOW = 'LOW'
    NONE = 'NONE'
    
    @classmethod
    def from_cvss_score(cls, score):
        """Determina severidade baseado no score CVSS v3.1."""
        if score is None:
            return cls.NONE
        if score >= 9.0:
            return cls.CRITICAL
        if score >= 7.0:
            return cls.HIGH
        if score >= 4.0:
            return cls.MEDIUM
        if score >= 0.1:
            return cls.LOW
        return cls.NONE
    
    @property
    def color(self):
        """Retorna a cor associada à severidade."""
        colors = {
            'CRITICAL': '#dc2626',
            'HIGH': '#ea580c',
            'MEDIUM': '#f59e0b',
            'LOW': '#10b981',
            'NONE': '#6b7280'
        }
        return colors.get(self.value, '#6b7280')
    
    @property
    def priority(self):
        """Retorna prioridade numérica para ordenação."""
        priorities = {
            'CRITICAL': 4,
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1,
            'NONE': 0
        }
        return priorities.get(self.value, 0)


class AssetType(str, Enum):
    """Tipos de ativos de TI."""
    SERVER = 'SERVER'
    WORKSTATION = 'WORKSTATION'
    NETWORK_DEVICE = 'NETWORK_DEVICE'
    FIREWALL = 'FIREWALL'
    DATABASE = 'DATABASE'
    APPLICATION = 'APPLICATION'
    CONTAINER = 'CONTAINER'
    CLOUD_SERVICE = 'CLOUD_SERVICE'
    IOT_DEVICE = 'IOT_DEVICE'
    MOBILE_DEVICE = 'MOBILE_DEVICE'
    ORGANIZATION = 'ORGANIZATION'
    OTHER = 'OTHER'


class AssetStatus(str, Enum):
    """Status do ativo."""
    ACTIVE = 'ACTIVE'
    INACTIVE = 'INACTIVE'
    MAINTENANCE = 'MAINTENANCE'
    DECOMMISSIONED = 'DECOMMISSIONED'


class VulnerabilityStatus(str, Enum):
    """Status de uma vulnerabilidade em um ativo."""
    OPEN = 'OPEN'
    IN_PROGRESS = 'IN_PROGRESS'
    MITIGATED = 'MITIGATED'
    RESOLVED = 'RESOLVED'
    ACCEPTED = 'ACCEPTED'
    FALSE_POSITIVE = 'FALSE_POSITIVE'


class ReportType(str, Enum):
    """Tipos de relatório."""
    EXECUTIVE = 'EXECUTIVE'
    TECHNICAL = 'TECHNICAL'
    COMPLIANCE = 'COMPLIANCE'
    INCIDENT = 'INCIDENT'
    TREND = 'TREND'
    RISK_ASSESSMENT = 'RISK_ASSESSMENT'


class ReportStatus(str, Enum):
    """Status do relatório."""
    PENDING = 'PENDING'
    GENERATING = 'GENERATING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class MonitoringRuleType(str, Enum):
    """Tipos de regra de monitoramento."""
    NEW_CVE = 'NEW_CVE'
    SEVERITY_THRESHOLD = 'SEVERITY_THRESHOLD'
    VENDOR_SPECIFIC = 'VENDOR_SPECIFIC'
    PRODUCT_SPECIFIC = 'PRODUCT_SPECIFIC'
    CISA_KEV = 'CISA_KEV'
    ASSET_EXPOSURE = 'ASSET_EXPOSURE'


class AlertChannel(str, Enum):
    """Canais de alerta."""
    EMAIL = 'EMAIL'
    WEBHOOK = 'WEBHOOK'
    SLACK = 'SLACK'
    TEAMS = 'TEAMS'


class AlertStatus(str, Enum):
    """Status do alerta."""
    NEW = 'NEW'
    ACKNOWLEDGED = 'ACKNOWLEDGED'
    RESOLVED = 'RESOLVED'
    DISMISSED = 'DISMISSED'


class SyncStatus(str, Enum):
    """Status do sync NVD."""
    IDLE = 'IDLE'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'
    PAUSED = 'PAUSED'


class RoleType(str, Enum):
    """Tipos de roles do sistema."""
    ADMIN = 'ADMIN'
    ANALYST = 'ANALYST'
    VIEWER = 'VIEWER'
    API_USER = 'API_USER'


class CvssVersion(str, Enum):
    """Versões do CVSS."""
    V2 = '2.0'
    V3 = '3.0'
    V31 = '3.1'
    V4 = '4.0'


class ReferenceType(str, Enum):
    """Tipos de referência de CVE."""
    ADVISORY = 'ADVISORY'
    PATCH = 'PATCH'
    VENDOR = 'VENDOR'
    ARTICLE = 'ARTICLE'
    EXPLOIT = 'EXPLOIT'
    TOOL = 'TOOL'
    THIRD_PARTY = 'THIRD_PARTY'
    OTHER = 'OTHER'
