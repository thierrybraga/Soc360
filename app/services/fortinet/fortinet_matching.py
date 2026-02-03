"""
Open-Monitor Fortinet Matching Service
Serviço de matching otimizado para CVEs de produtos Fortinet.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from sqlalchemy import or_, func
from app.extensions.db import db
from app.models.inventory import Asset, AssetVulnerability
from app.models.nvd import Vulnerability
from app.models.system.enums import VulnerabilityStatus
from app.services.fortinet.fortinet_presets import (
    FORTINET_PRODUCTS,
    CRITICAL_FORTINET_CVES,
    parse_fortios_version,
    compare_versions,
    is_version_supported,
    is_version_eol
)

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Resultado de um match de vulnerabilidade."""
    cve_id: str
    cvss_score: float
    severity: str
    is_version_match: bool
    is_cisa_kev: bool
    affected_product: str
    affected_versions: str
    confidence: str  # HIGH, MEDIUM, LOW
    match_reason: str


class FortinetMatchingService:
    """
    Serviço de matching de CVEs otimizado para Fortinet.

    Features:
    - Query otimizada usando índices GIN
    - Validação de versão precisa
    - Cache de resultados
    - Priorização CISA KEV
    - Suporte a múltiplos produtos Fortinet
    """

    # Cache simples em memória (usar Redis em produção)
    _cache: Dict[str, Tuple[datetime, List]] = {}
    CACHE_TTL = timedelta(hours=1)

    def __init__(self):
        self.vendor = 'fortinet'
        self._products_cache = None

    @property
    def products(self) -> List[str]:
        """Lista de produtos Fortinet para matching."""
        if self._products_cache is None:
            self._products_cache = list(FORTINET_PRODUCTS.keys())
        return self._products_cache

    def _get_from_cache(self, key: str) -> Optional[List]:
        """Recupera do cache se válido."""
        if key in self._cache:
            cached_time, data = self._cache[key]
            if datetime.utcnow() - cached_time < self.CACHE_TTL:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: List):
        """Armazena no cache."""
        self._cache[key] = (datetime.utcnow(), data)

    def get_all_fortinet_cves(
        self,
        severity_filter: List[str] = None,
        cisa_kev_only: bool = False,
        limit: int = 1000
    ) -> List[Vulnerability]:
        """
        Busca todas as CVEs Fortinet.

        Args:
            severity_filter: Lista de severidades (ex: ['CRITICAL', 'HIGH'])
            cisa_kev_only: Se True, retorna apenas CISA KEV
            limit: Limite de resultados

        Returns:
            Lista de vulnerabilidades
        """
        cache_key = f"fortinet_all_{severity_filter}_{cisa_kev_only}_{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        query = Vulnerability.query.filter(
            Vulnerability.nvd_vendors_data.contains([self.vendor])
        )

        if severity_filter:
            query = query.filter(Vulnerability.base_severity.in_(severity_filter))

        if cisa_kev_only:
            query = query.filter(Vulnerability.is_in_cisa_kev == True)  # noqa: E712

        query = query.order_by(
            Vulnerability.cvss_score.desc().nullslast(),
            Vulnerability.published_date.desc()
        )

        results = query.limit(limit).all()
        self._set_cache(cache_key, results)

        logger.info(f"Found {len(results)} Fortinet CVEs")
        return results

    def get_cves_by_product(
        self,
        product: str,
        version: str = None,
        severity_filter: List[str] = None,
        limit: int = 500
    ) -> List[Vulnerability]:
        """
        Busca CVEs para um produto Fortinet específico.

        Args:
            product: Nome do produto (ex: 'fortios', 'fortigate')
            version: Versão específica (ex: '7.4.3')
            severity_filter: Filtro de severidade
            limit: Limite de resultados

        Returns:
            Lista de vulnerabilidades
        """
        product_lower = product.lower()

        # FortiGate geralmente tem CVEs em FortiOS
        if product_lower == 'fortigate':
            products_to_check = ['fortigate', 'fortios']
        else:
            products_to_check = [product_lower]

        cache_key = f"fortinet_{product_lower}_{version}_{severity_filter}_{limit}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        product_conditions = []
        for prod in products_to_check:
            product_conditions.append(
                Vulnerability.nvd_products_data.contains({self.vendor: [prod]})
            )

        query = Vulnerability.query.filter(
            Vulnerability.nvd_vendors_data.contains([self.vendor]),
            or_(*product_conditions)
        )

        if severity_filter:
            query = query.filter(Vulnerability.base_severity.in_(severity_filter))

        query = query.order_by(
            Vulnerability.cvss_score.desc().nullslast(),
            Vulnerability.published_date.desc()
        )

        results = query.limit(limit).all()

        # Se versão especificada, filtrar por range de versão
        if version and results:
            results = self._filter_by_version(results, product_lower, version)

        self._set_cache(cache_key, results)

        logger.info(f"Found {len(results)} CVEs for {product} (version={version})")
        return results

    def _filter_by_version(
        self,
        vulnerabilities: List[Vulnerability],
        product: str,
        version: str
    ) -> List[Vulnerability]:
        """Filtra vulnerabilidades por versão afetada."""
        filtered = []
        parsed_version = parse_fortios_version(version)

        if not parsed_version:
            return vulnerabilities

        for vuln in vulnerabilities:
            if self._is_version_vulnerable(vuln, product, version, parsed_version):
                filtered.append(vuln)

        return filtered

    def _is_version_vulnerable(
        self,
        vuln: Vulnerability,
        product: str,
        version: str,
        parsed: dict
    ) -> bool:
        """Verifica se uma versão específica é vulnerável via CPE ranges."""
        if not vuln.cpe_configurations:
            return True

        configs = vuln.cpe_configurations
        if not isinstance(configs, list):
            configs = [configs]

        for config in configs:
            if not isinstance(config, dict):
                continue

            nodes = config.get('nodes', [])
            for node in nodes:
                cpe_matches = node.get('cpeMatch', [])
                for match in cpe_matches:
                    if not match.get('vulnerable', False):
                        continue

                    criteria = match.get('criteria', '')

                    if f":fortinet:{product}:" not in criteria.lower():
                        continue

                    cpe_parts = criteria.split(':')
                    if len(cpe_parts) < 6:
                        continue

                    cpe_version = cpe_parts[5]

                    version_start_incl = match.get('versionStartIncluding')
                    version_start_excl = match.get('versionStartExcluding')
                    version_end_incl = match.get('versionEndIncluding')
                    version_end_excl = match.get('versionEndExcluding')

                    if any([version_start_incl, version_start_excl, version_end_incl, version_end_excl]):
                        in_range = True

                        if version_start_incl:
                            in_range = in_range and compare_versions(version, version_start_incl) >= 0
                        if version_start_excl:
                            in_range = in_range and compare_versions(version, version_start_excl) > 0
                        if version_end_incl:
                            in_range = in_range and compare_versions(version, version_end_incl) <= 0
                        if version_end_excl:
                            in_range = in_range and compare_versions(version, version_end_excl) < 0

                        if in_range:
                            return True

                    elif cpe_version != '*':
                        if compare_versions(version, cpe_version) == 0:
                            return True

                    else:
                        return True

        return False

    def match_asset(
        self,
        asset: Asset,
        product_override: str = None,
        version_override: str = None
    ) -> List[MatchResult]:
        """Faz matching de vulnerabilidades para um asset Fortinet."""
        results = []

        product = product_override
        version = version_override

        if not product:
            if asset.product:
                product = asset.product.normalized_name
            elif asset.os_family and 'forti' in asset.os_family.lower():
                product = 'fortios'

        if not version:
            version = asset.version or asset.os_version

        if not product:
            logger.warning(f"Cannot determine product for asset {asset.id}")
            return results

        cves = self.get_cves_by_product(
            product=product,
            version=version,
            severity_filter=['CRITICAL', 'HIGH', 'MEDIUM']
        )

        for vuln in cves:
            confidence = 'HIGH' if version else 'MEDIUM'

            if version and not self._is_version_vulnerable(
                vuln, product, version, parse_fortios_version(version)
            ):
                continue

            match = MatchResult(
                cve_id=vuln.cve_id,
                cvss_score=vuln.cvss_score or 0,
                severity=vuln.base_severity or 'UNKNOWN',
                is_version_match=confidence == 'HIGH',
                is_cisa_kev=vuln.is_in_cisa_kev,
                affected_product=product,
                affected_versions=self._get_affected_versions_str(vuln, product),
                confidence=confidence,
                match_reason=f"Vendor: fortinet, Product: {product}"
            )
            results.append(match)

        results.sort(key=lambda x: (-x.is_cisa_kev, -x.cvss_score))

        return results

    def _get_affected_versions_str(self, vuln: Vulnerability, product: str) -> str:
        """Extrai string de versões afetadas da CVE."""
        if not vuln.cpe_configurations:
            return "Todas as versoes"

        versions = []
        configs = vuln.cpe_configurations
        if not isinstance(configs, list):
            configs = [configs]

        for config in configs:
            if not isinstance(config, dict):
                continue

            for node in config.get('nodes', []):
                for match in node.get('cpeMatch', []):
                    if not match.get('vulnerable'):
                        continue

                    criteria = match.get('criteria', '')
                    if f":fortinet:{product}:" not in criteria.lower():
                        continue

                    start = match.get('versionStartIncluding') or match.get('versionStartExcluding')
                    end = match.get('versionEndIncluding') or match.get('versionEndExcluding')

                    if start and end:
                        versions.append(f"{start} - {end}")
                    elif start:
                        versions.append(f">= {start}")
                    elif end:
                        versions.append(f"<= {end}")

        return ', '.join(versions) if versions else "Ver detalhes CVE"

    def scan_all_fortinet_assets(
        self,
        owner_id: int = None,
        create_associations: bool = True
    ) -> Dict:
        """Escaneia todos os assets Fortinet e associa vulnerabilidades."""
        stats = {
            'assets_scanned': 0,
            'total_matches': 0,
            'critical_matches': 0,
            'high_matches': 0,
            'cisa_kev_matches': 0,
            'new_associations': 0,
            'skipped_existing': 0,
            'errors': 0
        }

        query = Asset.query.filter(
            or_(
                Asset.vendor.has(normalized_name='fortinet'),
                Asset.os_family.ilike('%forti%'),
                Asset.asset_type == 'FIREWALL'
            )
        )

        if owner_id:
            query = query.filter_by(owner_id=owner_id)

        assets = query.all()
        stats['assets_scanned'] = len(assets)

        logger.info(f"Starting Fortinet scan for {len(assets)} assets")

        for asset in assets:
            try:
                matches = self.match_asset(asset)
                stats['total_matches'] += len(matches)

                for match in matches:
                    if match.severity == 'CRITICAL':
                        stats['critical_matches'] += 1
                    elif match.severity == 'HIGH':
                        stats['high_matches'] += 1

                    if match.is_cisa_kev:
                        stats['cisa_kev_matches'] += 1

                    if create_associations:
                        existing = AssetVulnerability.query.filter_by(
                            asset_id=asset.id,
                            cve_id=match.cve_id
                        ).first()

                        if existing:
                            stats['skipped_existing'] += 1
                            continue

                        av = AssetVulnerability(
                            asset_id=asset.id,
                            cve_id=match.cve_id,
                            status=VulnerabilityStatus.OPEN.value,
                            discovered_at=datetime.utcnow(),
                            detection_method='auto_scan',
                            detected_by='FortinetMatchingService',
                            notes=f"Confidence: {match.confidence}. {match.match_reason}"
                        )

                        av.contextual_risk_score = asset.calculate_risk_score(match.cvss_score)

                        db.session.add(av)
                        stats['new_associations'] += 1

            except Exception as e:
                logger.error(f"Error scanning asset {asset.id}: {e}")
                stats['errors'] += 1

        if create_associations:
            try:
                db.session.commit()
                logger.info(f"Committed {stats['new_associations']} new associations")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error committing associations: {e}")
                stats['errors'] += 1

        return stats

    def get_fortinet_dashboard_stats(self) -> Dict:
        """Retorna estatísticas para dashboard Fortinet."""
        stats = {}

        stats['total_cves'] = Vulnerability.query.filter(
            Vulnerability.nvd_vendors_data.contains([self.vendor])
        ).count()

        severity_query = db.session.query(
            Vulnerability.base_severity,
            func.count(Vulnerability.cve_id)
        ).filter(
            Vulnerability.nvd_vendors_data.contains([self.vendor])
        ).group_by(Vulnerability.base_severity).all()

        stats['by_severity'] = {s or 'UNKNOWN': c for s, c in severity_query}

        stats['cisa_kev_count'] = Vulnerability.query.filter(
            Vulnerability.nvd_vendors_data.contains([self.vendor]),
            Vulnerability.is_in_cisa_kev == True  # noqa: E712
        ).count()

        cutoff = datetime.utcnow() - timedelta(days=30)
        stats['recent_30_days'] = Vulnerability.query.filter(
            Vulnerability.nvd_vendors_data.contains([self.vendor]),
            Vulnerability.published_date >= cutoff
        ).count()

        top_products = []
        for product_key in ['fortios', 'fortigate', 'fortimanager', 'forticlient', 'fortiweb']:
            count = Vulnerability.query.filter(
                Vulnerability.nvd_vendors_data.contains([self.vendor]),
                Vulnerability.nvd_products_data.contains({self.vendor: [product_key]})
            ).count()
            top_products.append({'product': product_key, 'count': count})

        top_products.sort(key=lambda x: -x['count'])
        stats['top_products'] = top_products[:5]

        stats['known_critical_cves'] = list(CRITICAL_FORTINET_CVES.keys())

        return stats

    def check_version_status(self, version: str) -> Dict:
        """Verifica status de uma versão FortiOS."""
        result = {
            'version': version,
            'parsed': parse_fortios_version(version),
            'is_supported': is_version_supported(version),
            'is_eol': is_version_eol(version),
            'critical_cves': [],
            'total_cves': 0,
            'recommendations': []
        }

        if result['is_eol']:
            result['recommendations'].append(
                f"ATENCAO: FortiOS {version} esta em End of Life (EOL). "
                "Atualize para uma versao suportada imediatamente."
            )
        elif not result['is_supported']:
            result['recommendations'].append(
                f"FortiOS {version} pode nao receber mais atualizacoes de seguranca."
            )

        cves = self.get_cves_by_product('fortios', version, ['CRITICAL', 'HIGH'])
        result['total_cves'] = len(cves)

        for cve in cves:
            if cve.is_in_cisa_kev:
                result['critical_cves'].append({
                    'cve_id': cve.cve_id,
                    'cvss_score': cve.cvss_score,
                    'is_cisa_kev': True,
                    'description': cve.description[:200] if cve.description else None
                })
                result['recommendations'].append(
                    f"CRITICO: {cve.cve_id} esta no CISA KEV - requer acao imediata!"
                )

        if result['total_cves'] > 10:
            result['recommendations'].append(
                f"Esta versao tem {result['total_cves']} vulnerabilidades conhecidas. "
                "Considere atualizar para a versao mais recente do branch."
            )

        return result


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_service_instance = None


def get_fortinet_matching_service() -> FortinetMatchingService:
    """Retorna instância singleton do serviço."""
    global _service_instance
    if _service_instance is None:
        _service_instance = FortinetMatchingService()
    return _service_instance
