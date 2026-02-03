"""
Open-Monitor Fortinet Services
Serviços especializados para dispositivos Fortinet.
"""
from app.services.fortinet.fortinet_presets import (
    FortinetProduct,
    FortinetProductType,
    FORTINET_PRODUCTS,
    FORTIOS_VERSIONS,
    SUPPORTED_FORTIOS_BRANCHES,
    EOL_FORTIOS_BRANCHES,
    CRITICAL_FORTINET_CVES,
    get_product,
    get_all_firewall_products,
    get_all_cpe_prefixes,
    is_version_supported,
    is_version_eol,
    parse_fortios_version,
    compare_versions,
    is_version_affected,
    generate_vendor_product_seeds
)

from app.services.fortinet.fortinet_matching import (
    FortinetMatchingService,
    MatchResult,
    get_fortinet_matching_service
)

__all__ = [
    'FortinetProduct',
    'FortinetProductType',
    'FORTINET_PRODUCTS',
    'FORTIOS_VERSIONS',
    'SUPPORTED_FORTIOS_BRANCHES',
    'EOL_FORTIOS_BRANCHES',
    'CRITICAL_FORTINET_CVES',
    'get_product',
    'get_all_firewall_products',
    'get_all_cpe_prefixes',
    'is_version_supported',
    'is_version_eol',
    'parse_fortios_version',
    'compare_versions',
    'is_version_affected',
    'generate_vendor_product_seeds',
    'FortinetMatchingService',
    'MatchResult',
    'get_fortinet_matching_service',
]
