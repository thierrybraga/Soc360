"""
SOC360 CVE Vendor Model
Association table: Vulnerability <-> Vendor (Many-to-Many).
Note: No FK to vendors table as it's in a different database bind.
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, PrimaryKeyConstraint
from app.extensions.db import db


class CVEVendor(db.Model):
    """
    Association model for Vulnerability-Vendor relationship.
    Uses logical references (no cross-database FK constraints).
    """
    __tablename__ = 'cve_vendors'
    __bind_key__ = 'public'

    cve_id = Column(
        String(20),
        ForeignKey('vulnerabilities.cve_id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    vendor_id = Column(
        Integer,
        nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint('cve_id', 'vendor_id', name='pk_cve_vendor'),
    )

    def __repr__(self):
        return f"<CVEVendor cve_id={self.cve_id} vendor_id={self.vendor_id}>"
