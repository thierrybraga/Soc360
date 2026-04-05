"""
Open-Monitor CVE Product Model
Association table: Vulnerability <-> AffectedProduct (Many-to-Many).
"""
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, PrimaryKeyConstraint
from app.extensions.db import db


class CVEProduct(db.Model):
    """
    Association model for Vulnerability-AffectedProduct relationship.
    """
    __tablename__ = 'cve_products'
    __bind_key__ = 'public'

    cve_id = Column(
        String(20),
        ForeignKey('vulnerabilities.cve_id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    product_id = Column(
        Integer,
        ForeignKey('affected_products.id', ondelete='CASCADE'),
        nullable=False, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint('cve_id', 'product_id', name='pk_cve_product'),
    )

    def __repr__(self):
        return f"<CVEProduct cve_id={self.cve_id} product_id={self.product_id}>"
