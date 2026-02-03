#!/usr/bin/env python3
"""
Open-Monitor Optimized Asset Matching
Script otimizado para matching de vulnerabilidades com assets.

Melhorias sobre versão original:
- Query otimizada com índices GIN
- Validação de versão precisa via CPE ranges
- Batch processing para performance
- Suporte especial para Fortinet
- Cache de resultados por vendor
- Progress tracking
"""
import sys
import os
import logging
import argparse
from datetime import datetime
from typing import List, Dict, Optional, Set

from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models.inventory import Asset, AssetVulnerability, Vendor, Product
from app.models.nvd import Vulnerability
from app.models.system.enums import VulnerabilityStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OptimizedMatcher:
    """
    Matcher otimizado para associar vulnerabilidades a assets.

    Features:
    - Batch processing para reduzir queries
    - Cache de vulnerabilidades por vendor
    - Validação de versão quando disponível
    - Estatísticas detalhadas
    """

    def __init__(self, app):
        self.app = app
        self.stats = {
            'assets_processed': 0,
            'assets_skipped': 0,
            'new_associations': 0,
            'existing_skipped': 0,
            'critical_found': 0,
            'high_found': 0,
            'cisa_kev_found': 0,
            'errors': 0
        }

        # Cache de vulnerabilidades por vendor
        self._vuln_cache: Dict[str, List[Vulnerability]] = {}

        # Set de associações existentes
        self._existing_associations: Set[tuple] = set()

    def _load_existing_associations(self):
        """Carrega associações existentes para evitar duplicatas."""
        logger.info("Loading existing associations...")

        associations = db.session.query(
            AssetVulnerability.asset_id,
            AssetVulnerability.cve_id
        ).all()

        self._existing_associations = set(associations)
        logger.info(f"Loaded {len(self._existing_associations)} existing associations")

    def _get_vulns_for_vendor(self, vendor_name: str) -> List[Vulnerability]:
        """Retorna vulnerabilidades para um vendor (com cache)."""
        vendor_lower = vendor_name.lower()

        if vendor_lower in self._vuln_cache:
            return self._vuln_cache[vendor_lower]

        logger.debug(f"Fetching vulnerabilities for vendor: {vendor_lower}")

        vulns = Vulnerability.query.filter(
            Vulnerability.nvd_vendors_data.contains([vendor_lower])
        ).order_by(
            Vulnerability.cvss_score.desc().nullslast()
        ).all()

        self._vuln_cache[vendor_lower] = vulns
        logger.info(f"Cached {len(vulns)} vulnerabilities for {vendor_lower}")

        return vulns

    def _extract_vendor_product_from_asset(self, asset: Asset) -> tuple:
        """Extrai vendor, produto e versão de um asset."""
        vendor_name = None
        product_name = None
        version = asset.version

        # Método 1: Via relacionamentos
        if asset.vendor:
            vendor_name = asset.vendor.normalized_name or asset.vendor.name.lower()

        if asset.product:
            product_name = asset.product.normalized_name or asset.product.name.lower()
            if not version:
                version = asset.product.version

        # Método 2: Via CPE do produto
        if asset.product and asset.product.cpe_string:
            parts = asset.product.cpe_string.split(':')
            if len(parts) >= 5:
                vendor_name = vendor_name or parts[3]
                product_name = product_name or parts[4]
                if len(parts) > 5 and parts[5] != '*':
                    version = version or parts[5]

        # Método 3: Via OS info (especial para Fortinet)
        if not vendor_name and asset.os_family:
            os_lower = asset.os_family.lower()
            if 'forti' in os_lower:
                vendor_name = 'fortinet'
                product_name = product_name or 'fortios'

        # Método 4: Via installed_software
        if not vendor_name and asset.installed_software:
            for software in asset.installed_software:
                if isinstance(software, dict):
                    v = software.get('vendor', '').lower()
                    p = software.get('product', '').lower()
                    if v and p:
                        vendor_name = v
                        product_name = p
                        version = version or software.get('version')
                        break

        return vendor_name, product_name, version or asset.os_version

    def _match_product(
        self,
        vuln: Vulnerability,
        vendor_name: str,
        product_name: str
    ) -> bool:
        """Verifica se vulnerabilidade afeta o produto."""
        if not vuln.nvd_products_data:
            return True

        products_map = vuln.nvd_products_data

        if isinstance(products_map, dict):
            vendor_products = products_map.get(vendor_name, [])

            if isinstance(vendor_products, list):
                return product_name in vendor_products
            else:
                return vendor_products == product_name

        elif isinstance(products_map, list):
            return product_name in products_map

        return False

    def _check_version_affected(
        self,
        vuln: Vulnerability,
        product_name: str,
        version: str
    ) -> bool:
        """Verifica se versão específica é afetada via CPE ranges."""
        if not version or not vuln.cpe_configurations:
            return True

        from app.services.fortinet.fortinet_presets import compare_versions
        def _cmp_safe(a: str, b: str, op: str) -> bool:
            try:
                c = compare_versions(a, b)
            except Exception:
                return True
            if op == '>=':
                return c >= 0
            if op == '>':
                return c > 0
            if op == '<=':
                return c <= 0
            if op == '<':
                return c < 0
            return True

        configs = vuln.cpe_configurations
        if not isinstance(configs, list):
            configs = [configs]

        for config in configs:
            if not isinstance(config, dict):
                continue

            for node in config.get('nodes', []):
                for match in node.get('cpeMatch', []):
                    if not match.get('vulnerable', False):
                        continue

                    criteria = match.get('criteria', '')

                    if f":{product_name}:" not in criteria.lower():
                        continue

                    v_start_incl = match.get('versionStartIncluding')
                    v_start_excl = match.get('versionStartExcluding')
                    v_end_incl = match.get('versionEndIncluding')
                    v_end_excl = match.get('versionEndExcluding')

                    if any([v_start_incl, v_start_excl, v_end_incl, v_end_excl]):
                        in_range = True

                        if v_start_incl:
                            in_range = in_range and _cmp_safe(version, v_start_incl, '>=')
                        if v_start_excl:
                            in_range = in_range and _cmp_safe(version, v_start_excl, '>')
                        if v_end_incl:
                            in_range = in_range and _cmp_safe(version, v_end_incl, '<=')
                        if v_end_excl:
                            in_range = in_range and _cmp_safe(version, v_end_excl, '<')

                        if in_range:
                            return True
                    else:
                        return True

        return False

    def match_asset(self, asset: Asset) -> List[Dict]:
        """Encontra vulnerabilidades para um asset."""
        vendor, product, version = self._extract_vendor_product_from_asset(asset)

        if not vendor:
            logger.debug(f"Asset {asset.id} ({asset.name}): No vendor info, skipping")
            return []

        logger.debug(f"Matching asset {asset.id}: vendor={vendor}, product={product}, version={version}")

        vulns = self._get_vulns_for_vendor(vendor)

        if not vulns:
            return []

        matches = []

        for vuln in vulns:
            # Filtro 1: Produto
            if product and not self._match_product(vuln, vendor, product):
                continue

            # Filtro 2: Versão
            if product and version:
                if not self._check_version_affected(vuln, product, version):
                    continue

            matches.append({
                'cve_id': vuln.cve_id,
                'cvss_score': vuln.cvss_score,
                'severity': vuln.base_severity,
                'is_cisa_kev': vuln.is_in_cisa_kev,
                'matched_vendor': vendor,
                'matched_product': product,
                'matched_version': version
            })

        return matches

    def process_assets(
        self,
        assets: List[Asset],
        create_associations: bool = True,
        batch_size: int = 50
    ) -> Dict:
        """Processa lista de assets."""
        self._load_existing_associations()

        total = len(assets)
        logger.info(f"Processing {total} assets...")

        pending_associations = []

        for i, asset in enumerate(assets, 1):
            try:
                matches = self.match_asset(asset)

                if not matches:
                    self.stats['assets_skipped'] += 1
                    continue

                self.stats['assets_processed'] += 1

                for match in matches:
                    key = (asset.id, match['cve_id'])
                    if key in self._existing_associations:
                        self.stats['existing_skipped'] += 1
                        continue

                    if match['severity'] == 'CRITICAL':
                        self.stats['critical_found'] += 1
                    elif match['severity'] == 'HIGH':
                        self.stats['high_found'] += 1

                    if match['is_cisa_kev']:
                        self.stats['cisa_kev_found'] += 1

                    if create_associations:
                        av = AssetVulnerability(
                            asset_id=asset.id,
                            cve_id=match['cve_id'],
                            status=VulnerabilityStatus.OPEN.value,
                            discovered_at=datetime.utcnow(),
                            detection_method='auto_scan',
                            detected_by='OptimizedMatcher',
                            notes=f"Matched: {match['matched_vendor']}/{match['matched_product']} v{match['matched_version']}"
                        )

                        if match['cvss_score']:
                            av.contextual_risk_score = asset.calculate_risk_score(match['cvss_score'])

                        pending_associations.append(av)
                        self._existing_associations.add(key)
                        self.stats['new_associations'] += 1

                # Commit em batches
                if len(pending_associations) >= batch_size:
                    db.session.add_all(pending_associations)
                    db.session.commit()
                    pending_associations = []
                    logger.info(f"Progress: {i}/{total} assets ({(i/total)*100:.1f}%)")

            except Exception as e:
                logger.error(f"Error processing asset {asset.id}: {e}")
                self.stats['errors'] += 1

        # Commit remaining
        if pending_associations:
            db.session.add_all(pending_associations)
            db.session.commit()

        return self.stats


def main():
    """Funcao principal."""
    parser = argparse.ArgumentParser(description='Optimized Asset Vulnerability Matching')
    parser.add_argument('--dry-run', action='store_true', help='Nao cria associacoes, apenas mostra matches')
    parser.add_argument('--vendor', type=str, help='Filtrar por vendor especifico')
    parser.add_argument('--asset-type', type=str, help='Filtrar por tipo de asset')
    parser.add_argument('--owner', type=int, help='Filtrar por owner_id')
    parser.add_argument('--limit', type=int, default=0, help='Limitar numero de assets')
    parser.add_argument('--fortinet-only', action='store_true', help='Processar apenas assets Fortinet')

    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        logger.info("=" * 60)
        logger.info("OPTIMIZED ASSET MATCHING")
        logger.info("=" * 60)

        # Build query
        query = Asset.query

        if args.fortinet_only:
            query = query.filter(
                db.or_(
                    Asset.vendor.has(normalized_name='fortinet'),
                    Asset.os_family.ilike('%forti%'),
                    Asset.asset_type == 'FIREWALL'
                )
            )
            logger.info("Filter: Fortinet assets only")

        if args.vendor:
            query = query.filter(
                Asset.vendor.has(normalized_name=args.vendor.lower())
            )
            logger.info(f"Filter: Vendor = {args.vendor}")

        if args.asset_type:
            query = query.filter_by(asset_type=args.asset_type.upper())
            logger.info(f"Filter: Asset type = {args.asset_type}")

        if args.owner:
            query = query.filter_by(owner_id=args.owner)
            logger.info(f"Filter: Owner ID = {args.owner}")

        if args.limit > 0:
            query = query.limit(args.limit)
            logger.info(f"Limit: {args.limit} assets")

        assets = query.all()

        if not assets:
            logger.warning("No assets found matching criteria")
            return

        logger.info(f"Found {len(assets)} assets to process")

        # Process
        matcher = OptimizedMatcher(app)
        stats = matcher.process_assets(
            assets,
            create_associations=not args.dry_run
        )

        # Print results
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)
        print(f"Assets processed:      {stats['assets_processed']}")
        print(f"Assets skipped:        {stats['assets_skipped']}")
        print(f"New associations:      {stats['new_associations']}")
        print(f"Existing (skipped):    {stats['existing_skipped']}")
        print(f"Critical CVEs:         {stats['critical_found']}")
        print(f"High CVEs:             {stats['high_found']}")
        print(f"CISA KEV CVEs:         {stats['cisa_kev_found']}")
        print(f"Errors:                {stats['errors']}")
        print("=" * 60)

        if args.dry_run:
            print("\n[DRY RUN] No associations were created")


if __name__ == '__main__':
    main()
