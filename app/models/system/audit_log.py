"""
Open-Monitor Audit Log Model
Model for storing audit trail entries.
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import Index, text
from app.extensions.db_types import JSONB, USE_SQLITE

from app.extensions import db
from app.models.system.base_model import CoreModel


class AuditLog(CoreModel):
    """
    Audit log entry for tracking security events and user actions.
    
    Stored in CORE database for security isolation.
    """
    
    __tablename__ = 'audit_logs'
    
    # Event identification
    event_id = db.Column(db.String(36), unique=True, nullable=False, index=True)
    timestamp = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True
    )
    
    # Action details
    action = db.Column(db.String(100), nullable=False, index=True)
    severity = db.Column(db.String(20), nullable=False, default='info', index=True)
    success = db.Column(db.Boolean, nullable=False, default=True)
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Resource information
    resource_type = db.Column(db.String(50), nullable=True, index=True)
    resource_id = db.Column(db.String(100), nullable=True)
    
    # Event details (JSONB for flexible data)
    details = db.Column(JSONB, nullable=True, default=dict)
    
    # Error information
    error_message = db.Column(db.Text, nullable=True)
    
    # Request information
    request_id = db.Column(db.String(36), nullable=True)
    request_method = db.Column(db.String(10), nullable=True)
    request_path = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    user_agent = db.Column(db.String(500), nullable=True)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))
    
    # Indexes for common queries
    if not USE_SQLITE:
        __table_args__ = (
            # Composite index for action + timestamp queries
            Index('ix_audit_logs_action_timestamp', 'action', timestamp.desc()),
            
            # Composite index for user + timestamp queries
            Index('ix_audit_logs_user_timestamp', 'user_id', timestamp.desc()),
            
            # Composite index for resource queries
            Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
            
            # GIN index for JSONB details
            Index('ix_audit_logs_details_gin', 'details', postgresql_using='gin'),
            
            # Partial index for failed actions (common security query)
            Index(
                'ix_audit_logs_failed',
                'timestamp',
                postgresql_where=text('success = false')
            ),
            
            # Partial index for security events
            Index(
                'ix_audit_logs_security',
                'timestamp',
                postgresql_where=text("action LIKE 'security.%'")
            ),
        )
    else:
        __table_args__ = (
            Index('ix_audit_logs_action_timestamp', 'action', timestamp.desc()),
            Index('ix_audit_logs_user_timestamp', 'user_id', timestamp.desc()),
            Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
        )
    
    def __repr__(self) -> str:
        return f'<AuditLog {self.event_id}: {self.action}>'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'action': self.action,
            'severity': self.severity,
            'success': self.success,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'details': self.details,
            'error_message': self.error_message,
            'request': {
                'id': self.request_id,
                'method': self.request_method,
                'path': self.request_path,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
            }
        }
    
    @classmethod
    def query_by_action(
        cls,
        action: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List['AuditLog']:
        """
        Query audit logs by action type.
        
        Args:
            action: Action type or prefix (e.g., 'auth.' for all auth events)
            start_date: Filter from this date
            end_date: Filter until this date
            limit: Maximum results
            
        Returns:
            List of matching audit logs
        """
        query = cls.query
        
        if action.endswith('.'):
            # Prefix match
            query = query.filter(cls.action.like(f'{action}%'))
        else:
            query = query.filter(cls.action == action)
        
        if start_date:
            query = query.filter(cls.timestamp >= start_date)
        
        if end_date:
            query = query.filter(cls.timestamp <= end_date)
        
        return query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def query_by_user(
        cls,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List['AuditLog']:
        """
        Query audit logs by user.
        
        Args:
            user_id: User ID
            start_date: Filter from this date
            end_date: Filter until this date
            limit: Maximum results
            
        Returns:
            List of matching audit logs
        """
        query = cls.query.filter(cls.user_id == user_id)
        
        if start_date:
            query = query.filter(cls.timestamp >= start_date)
        
        if end_date:
            query = query.filter(cls.timestamp <= end_date)
        
        return query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def query_by_resource(
        cls,
        resource_type: str,
        resource_id: Optional[str] = None,
        limit: int = 100
    ) -> List['AuditLog']:
        """
        Query audit logs by resource.
        
        Args:
            resource_type: Resource type (e.g., 'user', 'asset')
            resource_id: Specific resource ID (optional)
            limit: Maximum results
            
        Returns:
            List of matching audit logs
        """
        query = cls.query.filter(cls.resource_type == resource_type)
        
        if resource_id:
            query = query.filter(cls.resource_id == resource_id)
        
        return query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def query_failures(
        cls,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List['AuditLog']:
        """
        Query failed actions.
        
        Args:
            start_date: Filter from this date
            end_date: Filter until this date
            limit: Maximum results
            
        Returns:
            List of failed action audit logs
        """
        query = cls.query.filter(cls.success == False)  # noqa: E712
        
        if start_date:
            query = query.filter(cls.timestamp >= start_date)
        
        if end_date:
            query = query.filter(cls.timestamp <= end_date)
        
        return query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def query_security_events(
        cls,
        severity: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List['AuditLog']:
        """
        Query security-related events.
        
        Args:
            severity: Filter by severity level
            start_date: Filter from this date
            end_date: Filter until this date
            limit: Maximum results
            
        Returns:
            List of security event audit logs
        """
        query = cls.query.filter(cls.action.like('security.%'))
        
        if severity:
            query = query.filter(cls.severity == severity)
        
        if start_date:
            query = query.filter(cls.timestamp >= start_date)
        
        if end_date:
            query = query.filter(cls.timestamp <= end_date)
        
        return query.order_by(cls.timestamp.desc()).limit(limit).all()
    
    @classmethod
    def get_action_summary(
        cls,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Get count summary of actions.
        
        Args:
            start_date: Filter from this date
            end_date: Filter until this date
            
        Returns:
            Dictionary of action -> count
        """
        from sqlalchemy import func
        
        query = db.session.query(
            cls.action,
            func.count(cls.id).label('count')
        )
        
        if start_date:
            query = query.filter(cls.timestamp >= start_date)
        
        if end_date:
            query = query.filter(cls.timestamp <= end_date)
        
        results = query.group_by(cls.action).all()
        
        return {action: count for action, count in results}
    
    @classmethod
    def cleanup_old_logs(cls, days: int = 90) -> int:
        """
        Delete audit logs older than specified days.
        
        Args:
            days: Delete logs older than this many days
            
        Returns:
            Number of deleted records
        """
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        deleted = cls.query.filter(cls.timestamp < cutoff).delete()
        db.session.commit()
        
        return deleted
