"""
Open-Monitor Schemas Package
Marshmallow schemas and service classes.
"""

# Auth schemas
from .auth_schema import (
    AuthRegisterSchema,
    AuthLoginSchema,
    AuthResponseSchema
)

# Monitoring schemas
from .monitoring_schema import MonitoringRuleSchema

# Sync schemas (shared between NVD and reports)
from .sync_schema import SyncMetadataSchema, ApiCallLogSchema

# User schemas
from .user_schema import UserSchema, UserCreateSchema, UserLoginSchema

# Vulnerability schemas
from .vulnerability_schema import VulnerabilitySchema


__all__ = [
    # Auth
    'AuthRegisterSchema',
    'AuthLoginSchema',
    'AuthResponseSchema',
    # Monitoring
    'MonitoringRuleSchema',
    # Sync
    'SyncMetadataSchema',
    'ApiCallLogSchema',
    # User
    'UserSchema',
    'UserCreateSchema',
    'UserLoginSchema',
    # Vulnerability
    'VulnerabilitySchema',
]
