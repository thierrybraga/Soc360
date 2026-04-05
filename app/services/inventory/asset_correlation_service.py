import re
from datetime import datetime
from typing import Dict, List, Set

from app.extensions import db
from app.models.inventory import Asset, AssetVulnerability, Vendor, Product
from app.models.nvd import Vulnerability, Weakness
from app.models.system import VulnerabilityStatus


class AssetCorrelationService:
    def __init__(self):
        self.vendor_profiles = {
            'fortinet': {
                'label': 'Fortinet',
                'vendor_name': 'Fortinet',
                'vendor_aliases': ['fortinet', 'fortigate', 'forti'],
                'product_aliases': {
                    'fortigate': ['fortigate', 'fg'],
                    'fortios': ['fortios', 'forti os', 'fortigate os'],
                    'fortimanager': ['fortimanager', 'fmg'],
                    'fortianalyzer': ['fortianalyzer', 'faz'],
                    'forticlient': ['forticlient'],
                    'fortiswitch': ['fortiswitch', 'fsw'],
                    'fortiap': ['fortiap', 'fap'],
                    'fortimail': ['fortimail', 'fml'],
                    'fortiweb': ['fortiweb', 'fwb'],
                    'fortisandbox': ['fortisandbox', 'fsb']
                }
            },
            'cisco_meraki': {
                'label': 'Cisco (Meraki)',
                'vendor_name': 'Cisco',
                'vendor_aliases': ['cisco', 'meraki', 'cisco_meraki'],
                'product_aliases': {
                    'meraki_mx': ['mx', 'meraki mx', 'mx appliance'],
                    'meraki_mr': ['mr', 'meraki mr', 'mr access point'],
                    'meraki_ms': ['ms', 'meraki ms', 'ms switch'],
                    'meraki_mv': ['mv', 'meraki mv', 'mv camera'],
                    'meraki_dashboard': ['dashboard', 'meraki dashboard'],
                    'meraki_firmware': ['meraki firmware', 'meraki os']
                }
            },
            'sophos': {
                'label': 'Sophos',
                'vendor_name': 'Sophos',
                'vendor_aliases': ['sophos'],
                'product_aliases': {
                    'xg_firewall': ['xg', 'sfos', 'xg firewall'],
                    'sophos_central': ['central', 'sophos central'],
                    'intercept_x': ['intercept x', 'endpoint', 'hitmanpro'],
                    'sophos_os': ['sophos os', 'sfos']
                }
            },
            'wazuh': {
                'label': 'Wazuh',
                'vendor_name': 'Wazuh',
                'vendor_aliases': ['wazuh'],
                'product_aliases': {
                    'wazuh_manager': ['manager', 'wazuh manager'],
                    'wazuh_agent': ['agent', 'wazuh agent'],
                    'wazuh_dashboard': ['dashboard', 'wazuh dashboard']
                }
            },
            'umbrella': {
                'label': 'Cisco Umbrella',
                'vendor_name': 'Cisco',
                'vendor_aliases': ['cisco', 'umbrella', 'opendns'],
                'product_aliases': {
                    'umbrella_roaming_client': ['roaming client', 'umbrella client'],
                    'umbrella_va': ['virtual appliance', 'va'],
                    'umbrella_dashboard': ['umbrella dashboard']
                }
            },
            'zabbix': {
                'label': 'Zabbix',
                'vendor_name': 'Zabbix',
                'vendor_aliases': ['zabbix'],
                'product_aliases': {
                    'zabbix_server': ['server', 'zabbix server'],
                    'zabbix_agent': ['agent', 'zabbix agent'],
                    'zabbix_proxy': ['proxy', 'zabbix proxy']
                }
            }
        }

    def normalize(self, value: str) -> str:
        if not value:
            return ''
        normalized = re.sub(r'[^a-z0-9]+', '_', value.strip().lower())
        return normalized.strip('_')

    def parse_version(self, value: str) -> List[int]:
        if not value:
            return []
        numbers = re.findall(r'\d+', value)
        return [int(n) for n in numbers[:6]]

    def compare_versions(self, left: str, right: str) -> int:
        left_parts = self.parse_version(left)
        right_parts = self.parse_version(right)
        max_len = max(len(left_parts), len(right_parts))
        left_parts.extend([0] * (max_len - len(left_parts)))
        right_parts.extend([0] * (max_len - len(right_parts)))
        for idx in range(max_len):
            if left_parts[idx] > right_parts[idx]:
                return 1
            if left_parts[idx] < right_parts[idx]:
                return -1
        return 0

    def get_vendor_profile_payload(self) -> Dict:
        return {
            'profiles': [
                {
                    'key': key,
                    'label': profile['label'],
                    'vendor_name': profile['vendor_name'],
                    'products': [
                        {
                            'key': product_key,
                            'label': product_key.replace('_', ' ').title()
                        }
                        for product_key in profile['product_aliases'].keys()
                    ]
                }
                for key, profile in self.vendor_profiles.items()
            ]
        }

    def resolve_vendor_and_product(self, payload: Dict) -> Dict:
        profile_key = payload.get('vendor_profile')
        model = payload.get('model')
        vendor_name = payload.get('vendor_name')
        product_name = payload.get('product_name')
        if profile_key in self.vendor_profiles:
            profile = self.vendor_profiles[profile_key]
            vendor_name = profile['vendor_name']
            if not product_name:
                product_name = self.infer_product_from_model(model=model, profile_key=profile_key)
        return {
            'vendor_profile': profile_key,
            'vendor_name': vendor_name,
            'product_name': product_name,
            'model': model
        }

    def infer_product_from_model(self, model: str, profile_key: str) -> str:
        if not model or profile_key not in self.vendor_profiles:
            return ''
        value = self.normalize(model)
        aliases = self.vendor_profiles[profile_key]['product_aliases']
        for product_key, tokens in aliases.items():
            for token in tokens:
                token_norm = self.normalize(token)
                if token_norm and token_norm in value:
                    return product_key
        return ''

    def ensure_vendor_product(self, vendor_name: str, product_name: str) -> Dict:
        vendor = None
        product = None
        if vendor_name:
            vendor = Vendor.get_by_name(vendor_name)
            if not vendor:
                vendor = Vendor(name=vendor_name)
                db.session.add(vendor)
                db.session.flush()
        if product_name and vendor:
            product = Product.get_by_name(product_name, vendor_id=vendor.id)
            if not product:
                product = Product(name=product_name, vendor_id=vendor.id)
                db.session.add(product)
                db.session.flush()
        return {'vendor': vendor, 'product': product}

    def _extract_candidates(self, asset: Asset) -> Dict:
        vendors: Set[str] = set()
        products: Set[str] = set()
        versions: Set[str] = set()
        os_tokens: Set[str] = set()
        if asset.vendor:
            vendors.add(self.normalize(asset.vendor.name))
            if asset.vendor.normalized_name:
                vendors.add(self.normalize(asset.vendor.normalized_name))
        if asset.product:
            products.add(self.normalize(asset.product.name))
            if asset.product.normalized_name:
                products.add(self.normalize(asset.product.normalized_name))
        if asset.version:
            versions.add(asset.version)
        if asset.os_family:
            os_tokens.add(self.normalize(asset.os_family))
        if asset.os_name:
            os_tokens.add(self.normalize(asset.os_name))
            products.add(self.normalize(asset.os_name))
        if asset.os_version:
            versions.add(asset.os_version)
        custom_fields = asset.custom_fields or {}
        model = custom_fields.get('model')
        if model:
            products.add(self.normalize(model))
        for sw in asset.installed_software or []:
            if not isinstance(sw, dict):
                continue
            if sw.get('vendor'):
                vendors.add(self.normalize(sw.get('vendor')))
            if sw.get('product'):
                products.add(self.normalize(sw.get('product')))
            if sw.get('version'):
                versions.add(sw.get('version'))
        profile = custom_fields.get('vendor_profile')
        if profile in self.vendor_profiles:
            profile_data = self.vendor_profiles[profile]
            vendors.update(self.normalize(alias) for alias in profile_data['vendor_aliases'])
            inferred = self.infer_product_from_model(model=model, profile_key=profile)
            if inferred:
                products.add(self.normalize(inferred))
        if any('forti' in p for p in products):
            products.add('fortios')
            products.add('fortigate')
            vendors.add('fortinet')
        if any(p.startswith('meraki') or p in {'mx', 'mr', 'ms', 'mv'} for p in products):
            vendors.add('cisco')
            vendors.add('meraki')
            products.add('meraki_firmware')
        if any('sophos' in p for p in products) or any('sfos' in p for p in products):
            vendors.add('sophos')
            products.add('sfos')
        if any('wazuh' in p for p in products):
            vendors.add('wazuh')
        if any('umbrella' in p for p in products):
            vendors.add('cisco')
            vendors.add('umbrella')
        if any('zabbix' in p for p in products):
            vendors.add('zabbix')
        return {
            'vendors': {v for v in vendors if v},
            'products': {p for p in products if p},
            'versions': {v for v in versions if v},
            'os_tokens': {o for o in os_tokens if o}
        }

    def _vendor_match(self, vulnerability: Vulnerability, vendors: Set[str]) -> bool:
        if not vendors:
            return False
        vuln_vendors = {self.normalize(v) for v in vulnerability.vendors}
        if vuln_vendors.intersection(vendors):
            return True
        text_blob = self.normalize(str(vulnerability.nvd_vendors_data or ''))
        return any(v in text_blob for v in vendors)

    def _product_match(self, vulnerability: Vulnerability, products: Set[str], os_tokens: Set[str]) -> bool:
        if not products and not os_tokens:
            return False
        vuln_products = {self.normalize(p) for p in vulnerability.products}
        candidates = set(products).union(os_tokens)
        if vuln_products.intersection(candidates):
            return True
        blob = self.normalize(str(vulnerability.nvd_products_data or ''))
        return any(token in blob for token in candidates if token)

    def _version_match(self, vulnerability: Vulnerability, versions: Set[str]) -> bool:
        if not versions:
            return True
        if not vulnerability.cpe_configurations:
            return True
        configs = vulnerability.cpe_configurations
        if not isinstance(configs, list):
            configs = [configs]
        for version in versions:
            for config in configs:
                if not isinstance(config, dict):
                    continue
                for node in config.get('nodes', []):
                    for match in node.get('cpeMatch', []):
                        if not match.get('vulnerable'):
                            continue
                        start_incl = match.get('versionStartIncluding')
                        start_excl = match.get('versionStartExcluding')
                        end_incl = match.get('versionEndIncluding')
                        end_excl = match.get('versionEndExcluding')
                        cpe_version = (match.get('criteria') or '').split(':')[5] if len((match.get('criteria') or '').split(':')) > 5 else ''
                        valid = True
                        if start_incl:
                            valid = valid and self.compare_versions(version, start_incl) >= 0
                        if start_excl:
                            valid = valid and self.compare_versions(version, start_excl) > 0
                        if end_incl:
                            valid = valid and self.compare_versions(version, end_incl) <= 0
                        if end_excl:
                            valid = valid and self.compare_versions(version, end_excl) < 0
                        if any([start_incl, start_excl, end_incl, end_excl]):
                            if valid:
                                return True
                        elif cpe_version and cpe_version != '*':
                            if self.compare_versions(version, cpe_version) == 0:
                                return True
                        else:
                            return True
        return False

    def correlate_asset(self, asset: Asset, auto_associate: bool = True) -> Dict:
        candidates = self._extract_candidates(asset)
        if not candidates['vendors'] and not candidates['products']:
            return {'matches': [], 'new_associations': 0, 'existing_associations': 0}
        query = Vulnerability.query
        vendor_filters = [
            db.cast(Vulnerability.nvd_vendors_data, db.Text).ilike(f'%{vendor}%')
            for vendor in candidates['vendors']
        ]
        product_filters = [
            db.cast(Vulnerability.nvd_products_data, db.Text).ilike(f'%{product}%')
            for product in candidates['products']
        ]
        if vendor_filters and product_filters:
            query = query.filter(db.or_(*vendor_filters, *product_filters))
        elif vendor_filters:
            query = query.filter(db.or_(*vendor_filters))
        elif product_filters:
            query = query.filter(db.or_(*product_filters))
        potential = query.order_by(Vulnerability.cvss_score.desc().nullslast()).limit(1500).all()
        matches = []
        for vuln in potential:
            vendor_hit = self._vendor_match(vuln, candidates['vendors'])
            product_hit = self._product_match(vuln, candidates['products'], candidates['os_tokens'])
            version_hit = self._version_match(vuln, candidates['versions'])
            if not (vendor_hit and (product_hit or version_hit)):
                continue
            confidence = 'HIGH' if vendor_hit and product_hit and version_hit else 'MEDIUM' if vendor_hit and product_hit else 'LOW'
            matches.append({
                'cve_id': vuln.cve_id,
                'cvss_score': vuln.cvss_score,
                'severity': vuln.base_severity,
                'is_cisa_kev': vuln.is_in_cisa_kev,
                'confidence': confidence
            })
        cve_ids = [m['cve_id'] for m in matches]
        weakness_map = {}
        if cve_ids:
            weaknesses = Weakness.query.filter(Weakness.cve_id.in_(cve_ids)).all()
            for weakness in weaknesses:
                weakness_map.setdefault(weakness.cve_id, []).append(weakness.cwe_id)
        new_associations = 0
        existing_associations = 0
        if auto_associate:
            for match in matches:
                existing = AssetVulnerability.query.filter_by(asset_id=asset.id, cve_id=match['cve_id']).first()
                if existing:
                    existing_associations += 1
                    continue
                association = AssetVulnerability(
                    asset_id=asset.id,
                    cve_id=match['cve_id'],
                    status=VulnerabilityStatus.OPEN.value,
                    discovered_at=datetime.utcnow(),
                    detection_method='asset_correlation',
                    detected_by='AssetCorrelationService',
                    notes=f"Confidence={match['confidence']}"
                )
                association.contextual_risk_score = asset.calculate_risk_score(match['cvss_score'] or 0)
                db.session.add(association)
                new_associations += 1
        for match in matches:
            match['cwes'] = weakness_map.get(match['cve_id'], [])
        return {
            'matches': matches,
            'new_associations': new_associations,
            'existing_associations': existing_associations
        }


_service_instance = None


def get_asset_correlation_service() -> AssetCorrelationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = AssetCorrelationService()
    return _service_instance
