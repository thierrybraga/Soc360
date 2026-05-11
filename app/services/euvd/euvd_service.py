import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.dialects.postgresql import insert
from app.extensions import db
from app.models.nvd import Vulnerability, CvssMetric
from app.jobs.fetchers import EUVDFetcher
from app.models.system import SyncMetadata
from app.services.monitoring.alert_service import AlertService

logger = logging.getLogger(__name__)

from app.services.core.base_sync_service import BaseSyncService, SyncStatus

class EUVDService(BaseSyncService):
    """
    Serviço para sincronização e consolidação de dados da EUVD.
    """
    
    def __init__(self):
        super().__init__(prefix='euvd')
        self.fetcher = EUVDFetcher()

    def get_status(self) -> Dict:
        """Obter status atual da sincronização."""
        return self.get_progress()

    def sync_latest(self):
        """Sincronizar últimas vulnerabilidades de todos os endpoints especializados."""
        try:
            self.start_sync('Fetching latest vulnerabilities...')

            # Coletar de todos os endpoints especializados, deduplicando por ID
            seen_ids = set()
            all_items = []

            for label, fetch_fn in [
                ('latest', self.fetcher.fetch_latest),
                ('exploited', self.fetcher.fetch_exploited),
                ('eu_csirt', self.fetcher.fetch_eu_csirt),
                ('critical', self.fetcher.fetch_critical),
            ]:
                try:
                    items = fetch_fn()
                    if not isinstance(items, list):
                        items = items.get('items', []) if isinstance(items, dict) else []
                    added = 0
                    for item in items:
                        item_id = item.get('id')
                        if item_id and item_id not in seen_ids:
                            seen_ids.add(item_id)
                            all_items.append(item)
                            added += 1
                    logger.info(f'EUVD {label}: {len(items)} fetched, {added} new unique items')
                except Exception as e:
                    logger.warning(f'EUVD {label} fetch failed: {e}')

            self._update_progress(message=f'Processing {len(all_items)} items...', total=len(all_items))
            self._process_items(all_items)

            self.complete_sync()
            return self.stats
        except Exception as e:
            self.fail_sync(str(e))
            raise

    def sync_by_date(self, from_date: str, to_date: str):
        """Sincronizar por intervalo de datas."""
        try:
            self.start_sync(f'Fetching EUVD from {from_date} to {to_date}...')
            page = 0
            while True:
                response = self.fetcher.fetch_search(
                    page=page,
                    size=100,
                    from_date=from_date,
                    to_date=to_date
                )
                items = response.get('items', [])
                if not items:
                    break

                self._process_items(items)

                total = response.get('total', 0)
                self._update_progress(
                    message=f'Page {page + 1}: processed {self.stats["processed"]}/{total}',
                    **self.stats
                )

                if (page + 1) * 100 >= total:
                    break

                page += 1

            self.complete_sync()
        except Exception as e:
            self.fail_sync(str(e))
            raise

    def _process_items(self, items: List[Dict]):
        """Processar lista de itens da EUVD."""
        total = len(items)
        self.stats['total'] = total
        for i, item in enumerate(items):
            try:
                self._process_single_item(item)
                # Commit per-item so session never accumulates stale state
                db.session.commit()
                self.stats['processed'] += 1
            except Exception as e:
                logger.error(f"Error processing item {item.get('id')}: {e}")
                self.stats['errors'] += 1
                # Always reset session after any failure so subsequent items work
                try:
                    db.session.rollback()
                except Exception:
                    pass

            # Update status every 10 items — guard against session issues
            if (i + 1) % 10 == 0:
                try:
                    self._update_progress(
                        message=f'Processing item {i+1}/{total}...',
                        **self.stats
                    )
                except Exception as e:
                    logger.warning(f"Progress update failed (non-fatal): {e}")
                    try:
                        db.session.rollback()
                    except Exception:
                        pass

    def _process_single_item(self, item: Dict):
        """
        Processar um único item e consolidar com o banco.
        Prioridade: CVE ID > EUVD ID.
        """
        # Tentar extrair CVE ID dos aliases
        cve_id = self._extract_cve_id(item)
        primary_id = cve_id if cve_id else item.get('id')
        
        if not primary_id:
            logger.warning(f"Item without ID: {item}")
            return

        # Verificar se já existe
        existing = Vulnerability.query.filter_by(cve_id=primary_id).first()
        
        data = self._map_to_model(item, primary_id)
        
        if existing:
            # Update logic (Consolidação)
            updated = False
            
            # Atualizar campos básicos se vazios
            if not existing.description and data['description']:
                existing.description = data['description']
                updated = True
                
            if not existing.cvss_score and data['cvss_score']:
                existing.cvss_score = data['cvss_score']
                updated = True

            # Campos específicos EUVD (complementares à NIST)
            if data.get('euvd_id'):
                existing.euvd_id = data['euvd_id']
                updated = True
            
            if data.get('enisa_alternative_id'):
                existing.enisa_alternative_id = data['enisa_alternative_id']
                updated = True

            if data.get('enisa_exploitation_status'):
                existing.enisa_exploitation_status = data['enisa_exploitation_status']
                updated = True

            if data.get('enisa_source'):
                existing.enisa_source = data['enisa_source']
                updated = True

            if data.get('enisa_last_changed'):
                existing.enisa_last_changed = data['enisa_last_changed']
                updated = True

            is_coordinated = bool(data.get('is_eu_csirt_coordinated'))
            if existing.is_eu_csirt_coordinated != is_coordinated:
                existing.is_eu_csirt_coordinated = is_coordinated
                updated = True
            
            # Save EUVD specific CVSS Metric
            self._save_cvss_metric(primary_id, data)
            
            if updated:
                self.stats['updated'] += 1
        else:
            # Insert new
            new_vuln = Vulnerability(**data)
            db.session.add(new_vuln)
            db.session.flush() # Ensure ID exists for relationships
            self._save_cvss_metric(primary_id, data)
            self.stats['inserted'] += 1
            
            # Alert
            AlertService.process_new_vulnerability(new_vuln)

    def _save_cvss_metric(self, cve_id: str, data: Dict):
        """Salvar métrica CVSS específica da EUVD."""
        if not data.get('cvss_score'):
            return

        metric_data = {
            'cve_id': cve_id,
            'version': data.get('cvss_version') or '3.1', # Default assumption if missing
            'source': 'euvd',
            'type': 'Secondary', # Usually EUVD is secondary if NVD exists
            'base_score': data.get('cvss_score'),
            'vector_string': data.get('cvss_vector_string'),
            'updated_at': datetime.utcnow()
        }

        stmt = insert(CvssMetric).values(metric_data)
        stmt = stmt.on_conflict_do_update(
            index_elements=['cve_id', 'version', 'source'],
            set_={
                'base_score': stmt.excluded.base_score,
                'vector_string': stmt.excluded.vector_string,
                'updated_at': datetime.utcnow()
            }
        )
        db.session.execute(stmt)

    def _extract_cve_id(self, item: Dict) -> Optional[str]:
        """Buscar CVE ID nos aliases."""
        aliases = item.get('aliases', '')
        if not aliases:
            return None
            
        # Aliases vêm separados por \n
        for alias in aliases.split('\n'):
            alias = alias.strip()
            if alias.startswith('CVE-'):
                return alias
        return None

    def _map_to_model(self, item: Dict, primary_id: str) -> Dict:
        """Mapear campos da API EUVD para o modelo Vulnerability."""
        
        # Parse Dates
        published = self._parse_date(item.get('datePublished'))
        updated = self._parse_date(item.get('dateUpdated'))
        
        # CVSS
        cvss_score = item.get('baseScore')
        cvss_version = item.get('baseScoreVersion')
        cvss_vector = item.get('baseScoreVector')
        
        # Vendors/Products
        vendors = []
        products = {}

        for v_item in item.get('enisaIdVendor', []):
            v_name = v_item.get('vendor', {}).get('name')
            if v_name and v_name not in vendors:
                vendors.append(v_name)

        for p_item in item.get('enisaIdProduct', []):
            p_name = p_item.get('product', {}).get('name')
            if not p_name:
                continue
            # Tenta obter o vendor do produto diretamente (campo 'vendor' dentro do produto)
            p_vendor = (
                p_item.get('vendor', {}).get('name')
                or (p_item.get('product', {}).get('vendor') or {}).get('name')
            )
            # Associa ao vendor do produto se disponível, caso contrário a todos os vendors
            target_vendors = [p_vendor] if p_vendor else vendors
            for vendor in target_vendors:
                if vendor not in products:
                    products[vendor] = []
                if p_name not in products[vendor]:
                    products[vendor].append(p_name)

        return {
            'cve_id': primary_id,
            'euvd_id': item.get('id'),
            'enisa_alternative_id': item.get('alternativeId'),
            'enisa_exploitation_status': item.get('exploitation'),
            'enisa_source': item.get('source'),
            'enisa_last_changed': updated,
            'is_eu_csirt_coordinated': 'EU CSIRT' in (item.get('source') or ''),
            'description': item.get('description'),
            'published_date': published,
            'last_modified_date': updated,
            'cvss_score': float(cvss_score) if cvss_score else None,
            'cvss_version': cvss_version,
            'cvss_vector_string': cvss_vector,
            'nvd_vendors_data': vendors,
            'nvd_products_data': products,
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse da data da EUVD. Tenta ISO 8601 primeiro, depois formato legado."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            pass
        try:
            return datetime.strptime(date_str, "%b %d, %Y, %I:%M:%S %p")
        except ValueError:
            pass
        return None