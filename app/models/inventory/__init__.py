"""
Open-Monitor Inventory Models
Models de gestão de ativos.
"""
from app.models.inventory.asset import Asset
from app.models.inventory.asset_vulnerability import AssetVulnerability
from app.models.inventory.vendor import Vendor, Product
from app.models.inventory.category import AssetCategory


__all__ = [
    'Asset',
    'AssetVulnerability',
    'Vendor',
    'Product',
    'AssetCategory'
]
