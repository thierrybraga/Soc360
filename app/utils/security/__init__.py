"""
Open-Monitor Security Utils Package
Security utilities: headers, encryption, audit logging, rate limiting, validation.
"""

from app.utils.security.security import (
    validate_password_strength,
    rate_limit,
    admin_required,
    role_required,
    owner_or_admin_required,
    api_key_required,
    sanitize_input,
    sanitize_html,
)

from app.utils.security.headers import (
    SecurityHeadersService,
    security_headers,
    get_csp_config,
    CSP_DEVELOPMENT,
    CSP_PRODUCTION,
)

from app.utils.security.encryption import (
    EncryptionService,
    encryption_service,
    EncryptedField,
    generate_encryption_key,
    generate_aes_key,
)

from app.utils.security.audit import (
    AuditLogger,
    AuditAction,
    AuditSeverity,
    audit_logger,
    audit_action,
    SQLAlchemyAuditMixin,
)

__all__ = [
    # Password validation
    'validate_password_strength',
    
    # Rate limiting
    'rate_limit',
    
    # Authorization decorators
    'admin_required',
    'role_required',
    'owner_or_admin_required',
    'api_key_required',
    
    # Input sanitization
    'sanitize_input',
    'sanitize_html',
    
    # Security headers
    'SecurityHeadersService',
    'security_headers',
    'get_csp_config',
    'CSP_DEVELOPMENT',
    'CSP_PRODUCTION',
    
    # Encryption
    'EncryptionService',
    'encryption_service',
    'EncryptedField',
    'generate_encryption_key',
    'generate_aes_key',
    
    # Audit logging
    'AuditLogger',
    'AuditAction',
    'AuditSeverity',
    'audit_logger',
    'audit_action',
    'SQLAlchemyAuditMixin',
]
