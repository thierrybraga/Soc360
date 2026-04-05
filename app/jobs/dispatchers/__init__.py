"""
Open-Monitor Dispatchers Package
Alert and notification dispatchers.
"""

from .monitoring_dispatcher import MonitoringDispatcher, EmailService

__all__ = [
    'MonitoringDispatcher',
    'EmailService'
]