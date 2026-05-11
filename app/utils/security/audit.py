"""
SOC360 Audit Logging Service
Comprehensive audit trail for security events and user actions.
"""
import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, request, g, has_request_context
from flask_login import current_user
from sqlalchemy import event


class AuditAction(str, Enum):
    """Audit action types."""
    # Authentication
    LOGIN_SUCCESS = 'auth.login.success'
    LOGIN_FAILED = 'auth.login.failed'
    LOGOUT = 'auth.logout'
    PASSWORD_CHANGE = 'auth.password.change'
    PASSWORD_RESET_REQUEST = 'auth.password.reset_request'
    PASSWORD_RESET_COMPLETE = 'auth.password.reset_complete'
    MFA_ENABLED = 'auth.mfa.enabled'
    MFA_DISABLED = 'auth.mfa.disabled'
    MFA_FAILED = 'auth.mfa.failed'
    SESSION_EXPIRED = 'auth.session.expired'
    ACCOUNT_LOCKED = 'auth.account.locked'
    ACCOUNT_UNLOCKED = 'auth.account.unlocked'
    
    # User Management
    USER_CREATED = 'user.created'
    USER_UPDATED = 'user.updated'
    USER_DELETED = 'user.deleted'
    USER_ACTIVATED = 'user.activated'
    USER_DEACTIVATED = 'user.deactivated'
    ROLE_ASSIGNED = 'user.role.assigned'
    ROLE_REMOVED = 'user.role.removed'
    
    # API Keys
    API_KEY_CREATED = 'api_key.created'
    API_KEY_REVOKED = 'api_key.revoked'
    API_KEY_USED = 'api_key.used'
    
    # Assets
    ASSET_CREATED = 'asset.created'
    ASSET_UPDATED = 'asset.updated'
    ASSET_DELETED = 'asset.deleted'
    ASSET_SCANNED = 'asset.scanned'
    
    # Vulnerabilities
    CVE_VIEWED = 'cve.viewed'
    CVE_EXPORTED = 'cve.exported'
    CVE_SEARCH = 'cve.search'
    
    # NVD Sync
    NVD_SYNC_STARTED = 'nvd.sync.started'
    NVD_SYNC_COMPLETED = 'nvd.sync.completed'
    NVD_SYNC_FAILED = 'nvd.sync.failed'
    
    # Monitoring Rules
    RULE_CREATED = 'rule.created'
    RULE_UPDATED = 'rule.updated'
    RULE_DELETED = 'rule.deleted'
    RULE_ENABLED = 'rule.enabled'
    RULE_DISABLED = 'rule.disabled'
    ALERT_TRIGGERED = 'alert.triggered'
    ALERT_ACKNOWLEDGED = 'alert.acknowledged'
    
    # Reports
    REPORT_GENERATED = 'report.generated'
    REPORT_DOWNLOADED = 'report.downloaded'
    REPORT_DELETED = 'report.deleted'
    
    # System
    SETTINGS_CHANGED = 'system.settings.changed'
    BACKUP_CREATED = 'system.backup.created'
    BACKUP_RESTORED = 'system.backup.restored'
    
    # Security Events
    RATE_LIMIT_EXCEEDED = 'security.rate_limit.exceeded'
    SUSPICIOUS_ACTIVITY = 'security.suspicious_activity'
    ACCESS_DENIED = 'security.access_denied'
    INVALID_INPUT = 'security.invalid_input'


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


class AuditLogger:
    """
    Audit logging service.
    
    Logs security events and user actions to database and/or external services.
    """
    
    def __init__(self, app: Optional[Flask] = None):
        self.app = app
        self._handlers: List[callable] = []
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize with Flask app."""
        self.app = app
        
        # Register as extension
        app.extensions['audit'] = self
        
        # Add default database handler
        if app.config.get('AUDIT_LOG_TO_DB', True):
            self.add_handler(self._db_handler)
        
        # Add file handler if configured
        log_file = app.config.get('AUDIT_LOG_FILE')
        if log_file:
            self.add_handler(self._file_handler)
        
        # Register request hooks
        app.before_request(self._before_request)
        app.after_request(self._after_request)
    
    def add_handler(self, handler: callable) -> None:
        """Add custom audit handler."""
        self._handlers.append(handler)
    
    def remove_handler(self, handler: callable) -> None:
        """Remove audit handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
    
    def _before_request(self) -> None:
        """Set up request context for auditing."""
        g.audit_request_id = str(uuid.uuid4())
        g.audit_request_start = datetime.now(timezone.utc)
    
    def _after_request(self, response):
        """Log request completion if needed."""
        # Could add automatic request logging here
        return response
    
    def log(
        self,
        action: Union[AuditAction, str],
        severity: Union[AuditSeverity, str] = AuditSeverity.INFO,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> None:
        """
        Log an audit event.
        
        Args:
            action: Action type (AuditAction enum or string)
            severity: Event severity level
            resource_type: Type of resource affected (e.g., 'user', 'asset')
            resource_id: ID of affected resource
            details: Additional event details
            user_id: User ID (auto-detected if not provided)
            success: Whether action succeeded
            error_message: Error message if action failed
        """
        # Build audit entry
        entry = self._build_entry(
            action=action,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            user_id=user_id,
            success=success,
            error_message=error_message
        )
        
        # Dispatch to all handlers
        for handler in self._handlers:
            try:
                handler(entry)
            except Exception as e:
                if self.app:
                    self.app.logger.error(f'Audit handler failed: {e}')
    
    def _build_entry(
        self,
        action: Union[AuditAction, str],
        severity: Union[AuditSeverity, str],
        resource_type: Optional[str],
        resource_id: Optional[str],
        details: Optional[Dict[str, Any]],
        user_id: Optional[int],
        success: bool,
        error_message: Optional[str]
    ) -> Dict[str, Any]:
        """Build audit log entry."""
        # Convert enums to strings
        action_str = action.value if isinstance(action, AuditAction) else action
        severity_str = severity.value if isinstance(severity, AuditSeverity) else severity
        
        # Get user info
        if user_id is None and has_request_context():
            try:
                if current_user and current_user.is_authenticated:
                    user_id = current_user.id
            except Exception:
                pass
        
        # Get request info
        request_info = self._get_request_info()
        
        # Build entry
        entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action_str,
            'severity': severity_str,
            'success': success,
            'user_id': user_id,
            'resource_type': resource_type,
            'resource_id': str(resource_id) if resource_id else None,
            'details': details or {},
            'error_message': error_message,
            'request': request_info
        }
        
        return entry
    
    def _get_request_info(self) -> Dict[str, Any]:
        """Extract request information for audit."""
        if not has_request_context():
            return {}
        
        return {
            'id': getattr(g, 'audit_request_id', None),
            'method': request.method,
            'path': request.path,
            'ip_address': self._get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:200],
            'referrer': request.headers.get('Referer', '')[:200],
        }
    
    def _get_client_ip(self) -> str:
        """Get client IP address."""
        if not has_request_context():
            return ''
        
        # Check for proxy headers
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or ''
    
    def _db_handler(self, entry: Dict[str, Any]) -> None:
        """Save audit entry to database."""
        try:
            from app.models.system import AuditLog
            from app.extensions import db
            
            audit_log = AuditLog(
                event_id=entry['id'],
                timestamp=datetime.fromisoformat(entry['timestamp']),
                action=entry['action'],
                severity=entry['severity'],
                success=entry['success'],
                user_id=entry['user_id'],
                resource_type=entry['resource_type'],
                resource_id=entry['resource_id'],
                details=entry['details'],
                error_message=entry['error_message'],
                request_id=entry['request'].get('id'),
                request_method=entry['request'].get('method'),
                request_path=entry['request'].get('path'),
                ip_address=entry['request'].get('ip_address'),
                user_agent=entry['request'].get('user_agent'),
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
        except Exception as e:
            if self.app:
                self.app.logger.error(f'Failed to save audit log to DB: {e}')
            # Don't raise - audit failures shouldn't break the app
    
    def _file_handler(self, entry: Dict[str, Any]) -> None:
        """Write audit entry to file."""
        try:
            log_file = self.app.config.get('AUDIT_LOG_FILE')
            if not log_file:
                return
            
            line = json.dumps(entry, default=str) + '\n'
            
            with open(log_file, 'a') as f:
                f.write(line)
                
        except Exception as e:
            if self.app:
                self.app.logger.error(f'Failed to write audit log to file: {e}')
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    def log_auth_success(
        self,
        user_id: int,
        method: str = 'password',
        details: Optional[Dict] = None
    ) -> None:
        """Log successful authentication."""
        self.log(
            action=AuditAction.LOGIN_SUCCESS,
            severity=AuditSeverity.INFO,
            resource_type='user',
            resource_id=user_id,
            user_id=user_id,
            details={'auth_method': method, **(details or {})}
        )
    
    def log_auth_failure(
        self,
        username: str,
        reason: str,
        details: Optional[Dict] = None
    ) -> None:
        """Log failed authentication."""
        self.log(
            action=AuditAction.LOGIN_FAILED,
            severity=AuditSeverity.WARNING,
            resource_type='user',
            details={'username': username, 'reason': reason, **(details or {})},
            success=False,
            error_message=reason
        )
    
    def log_access_denied(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        reason: str = 'Insufficient permissions'
    ) -> None:
        """Log access denied event."""
        self.log(
            action=AuditAction.ACCESS_DENIED,
            severity=AuditSeverity.WARNING,
            resource_type=resource_type,
            resource_id=resource_id,
            success=False,
            error_message=reason
        )
    
    def log_data_change(
        self,
        action: Union[AuditAction, str],
        resource_type: str,
        resource_id: str,
        changes: Optional[Dict] = None
    ) -> None:
        """Log data modification."""
        self.log(
            action=action,
            severity=AuditSeverity.INFO,
            resource_type=resource_type,
            resource_id=resource_id,
            details={'changes': changes} if changes else None
        )
    
    def log_security_event(
        self,
        event_type: str,
        severity: AuditSeverity = AuditSeverity.WARNING,
        details: Optional[Dict] = None
    ) -> None:
        """Log security-related event."""
        self.log(
            action=event_type,
            severity=severity,
            details=details
        )


def audit_action(
    action: Union[AuditAction, str],
    resource_type: Optional[str] = None,
    get_resource_id: Optional[callable] = None,
    include_args: bool = False,
    severity: AuditSeverity = AuditSeverity.INFO
):
    """
    Decorator to automatically audit function calls.
    
    Args:
        action: Audit action type
        resource_type: Type of resource being affected
        get_resource_id: Function to extract resource ID from kwargs
        include_args: Include function arguments in audit details
        severity: Event severity level
    
    Example:
        @audit_action(AuditAction.ASSET_CREATED, 'asset')
        def create_asset(name, ...):
            ...
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            audit = None
            
            # Get audit logger
            try:
                from flask import current_app
                audit = current_app.extensions.get('audit')
            except Exception:
                pass
            
            # Prepare details
            details = {}
            if include_args:
                details['args'] = [str(a)[:100] for a in args]
                details['kwargs'] = {
                    k: str(v)[:100] for k, v in kwargs.items()
                    if not k.lower().endswith(('password', 'secret', 'token', 'key'))
                }
            
            # Get resource ID
            resource_id = None
            if get_resource_id:
                try:
                    resource_id = get_resource_id(kwargs)
                except Exception:
                    pass
            
            try:
                result = f(*args, **kwargs)
                
                # Log success
                if audit:
                    # Try to get resource ID from result if not already set
                    if resource_id is None and hasattr(result, 'id'):
                        resource_id = result.id
                    
                    audit.log(
                        action=action,
                        severity=severity,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details if details else None,
                        success=True
                    )
                
                return result
                
            except Exception as e:
                # Log failure
                if audit:
                    audit.log(
                        action=action,
                        severity=AuditSeverity.ERROR,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        details=details if details else None,
                        success=False,
                        error_message=str(e)[:500]
                    )
                raise
        
        return wrapped
    return decorator


class SQLAlchemyAuditMixin:
    """
    Mixin to automatically audit SQLAlchemy model changes.
    
    Usage:
        class User(db.Model, SQLAlchemyAuditMixin):
            __audit_type__ = 'user'
            ...
    """
    
    __audit_type__: str = 'model'
    __audit_exclude_fields__: List[str] = ['password_hash', 'api_key']
    
    @classmethod
    def __declare_last__(cls):
        """Register SQLAlchemy event listeners."""
        event.listen(cls, 'after_insert', cls._audit_insert)
        event.listen(cls, 'after_update', cls._audit_update)
        event.listen(cls, 'after_delete', cls._audit_delete)
    
    @staticmethod
    def _audit_insert(mapper, connection, target):
        """Audit INSERT operations."""
        try:
            from flask import current_app
            audit = current_app.extensions.get('audit')
            if audit:
                audit.log(
                    action=f'{target.__audit_type__}.created',
                    resource_type=target.__audit_type__,
                    resource_id=getattr(target, 'id', None),
                    details={'new_values': target._get_audit_values()}
                )
        except Exception:
            pass
    
    @staticmethod
    def _audit_update(mapper, connection, target):
        """Audit UPDATE operations."""
        try:
            from flask import current_app
            from sqlalchemy.orm import object_session
            
            audit = current_app.extensions.get('audit')
            if audit:
                session = object_session(target)
                if session:
                    changes = {}
                    for attr in session.dirty:
                        if hasattr(attr, 'key'):
                            key = attr.key
                            if key not in target.__audit_exclude_fields__:
                                history = getattr(target, key).history
                                if history.has_changes():
                                    changes[key] = {
                                        'old': history.deleted[0] if history.deleted else None,
                                        'new': history.added[0] if history.added else None
                                    }
                    
                    if changes:
                        audit.log(
                            action=f'{target.__audit_type__}.updated',
                            resource_type=target.__audit_type__,
                            resource_id=getattr(target, 'id', None),
                            details={'changes': changes}
                        )
        except Exception:
            pass
    
    @staticmethod
    def _audit_delete(mapper, connection, target):
        """Audit DELETE operations."""
        try:
            from flask import current_app
            audit = current_app.extensions.get('audit')
            if audit:
                audit.log(
                    action=f'{target.__audit_type__}.deleted',
                    resource_type=target.__audit_type__,
                    resource_id=getattr(target, 'id', None),
                    severity=AuditSeverity.WARNING
                )
        except Exception:
            pass
    
    def _get_audit_values(self) -> Dict[str, Any]:
        """Get auditable field values."""
        values = {}
        
        for column in self.__table__.columns:
            if column.name not in self.__audit_exclude_fields__:
                value = getattr(self, column.name, None)
                if value is not None:
                    values[column.name] = str(value)[:200]
        
        return values


# Global instance
audit_logger = AuditLogger()
