"""
Open-Monitor NVD Models
Models relacionados ao NVD (National Vulnerability Database).
"""
from app.models.nvd.vulnerability import Vulnerability
from app.models.nvd.cvss_metric import CvssMetric
from app.models.nvd.weakness import Weakness
from app.models.nvd.reference import Reference, Mitigation
from app.models.nvd.credit import Credit
from app.models.nvd.product import AffectedProduct
from app.models.nvd.cve_product import CVEProduct
from app.models.nvd.cve_vendor import CVEVendor
from app.models.nvd.reference_type import ReferenceTypeModel
from app.models.nvd.version_reference import VersionReference


__all__ = [
    'Vulnerability',
    'CvssMetric',
    'Weakness',
    'Reference',
    'Mitigation',
    'Credit',
    'AffectedProduct',
    'CVEProduct',
    'CVEVendor',
    'ReferenceTypeModel',
    'VersionReference',
]