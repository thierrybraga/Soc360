"""Wazuh SIEM integration services."""
from app.services.wazuh.wazuh_service import (
    WazuhConfig,
    WazuhService,
)

__all__ = ['WazuhConfig', 'WazuhService']
