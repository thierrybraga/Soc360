"""Wazuh SIEM models."""
from app.models.wazuh.wazuh_alert import WazuhAlert
from app.models.wazuh.wazuh_treatment_note import WazuhTreatmentNote

__all__ = ['WazuhAlert', 'WazuhTreatmentNote']
