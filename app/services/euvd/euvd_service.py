import logging
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.dialects.postgresql import insert
from app.extensions import db
from app.models.nvd import Vulnerability, CvssMetric
from app.jobs.euvd_fetcher import EUVDFetcher
from app.models.system import SyncMetadata
from app.services.monitoring.alert_service import AlertService

logger = logging.getLogger(__name__)

class EUVDService:
    """
    Serviço para sincronização e consolidação de dados da EUVD.
    """
    
    def __init__(self):
        self.fetcher = EUVDFetcher()
        self.stats = {
            'processed': 0,
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'total': 0
        }

    def get_status(self) -> Dict:
        """Obter status atual da sincronização."""
        return {
            'status': SyncMetadata.get('euvd_sync_status') or 'idle',
            'last_sync': SyncMetadata.get('euvd_last_sync_date'),
            'message': SyncMetadata.get('euvd_sync_message'),
            'stats': {
                'processed': int(SyncMetadata.get('euvd_sync_stats_processed') or 0),
                'inserted': int(SyncMetadata.get('euvd_sync_stats_inserted') or 0),
                'updated': int(SyncMetadata.get('euvd_sync_stats_updated') or 0),
                'errors': int(SyncMetadata.get('euvd_sync_stats_errors') or 0),
                'total': int(SyncMetadata.get('euvd_sync_stats_total') or 0)
            }
        }

    def _update_status(self, status: str, message: str = None, stats: Dict = None):
        """Atualizar metadados de status."""
        SyncMetadata.set('euvd_sync_status', status)
        if message:
            SyncMetadata.set('euvd_sync_message', message)
        
        if stats:
            for key, value in stats.items():
                SyncMetadata.set(f'euvd_sync_stats_{key}', value)

    def sync_latest(self):
        """Sincronizar últimas vulnerabilidades."""
        try:
            self._update_status('running', 'Fetching latest vulnerabilities...')
            items = self.fetcher.fetch_latest()
            
            self._update_status('running', f'Processing {len(items)} items...')
            self._process_items(items)
            
            SyncMetadata.set('euvd_last_sync_date', datetime.utcnow().isoformat())
            self._update_status('completed', 'Sync completed successfully', self.stats)
            
            return self.stats
        except Exception as e:
            logger.error(f"Error syncing latest EUVD: {e}")
            self._update_status('failed', str(e))
            raise

    def sync_by_date(self, from_date: str, to_date: str):
        """Sincronizar por intervalo de datas."""
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
            
            # Check if we reached the end
            total = response.get('total', 0)
            if (page + 1) * 100 >= total:
                break
                
            page += 1

    def _process_items(self, items: List[Dict]):
        """Processar lista de itens da EUVD."""
        total = len(items)
        self.stats['total'] = total
        for i, item in enumerate(items):
            try:
                self._process_single_item(item)
                self.stats['processed'] += 1
            except Exception as e:
                logger.error(f"Error processing item {item.get('id')}: {e}")
                self.stats['errors'] += 1
            
            # Update status every 10 items
            if (i + 1) % 10 == 0:
                self._update_status(
                    'running', 
                    f'Processing item {i+1}/{total}...', 
                    self.stats
                )
        
        # Commit after batch
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Commit error: {e}")

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
            # Apenas atualizamos se o campo estiver vazio ou se quisermos forçar
            # Por segurança, vamos atualizar apenas campos complementares ou se a fonte for "mais rica"
            # Aqui faremos um update simples dos campos principais se eles vierem da EUVD
            updated = False
            
            if not existing.description and data['description']:
                existing.description = data['description']
                updated = True
                
            if not existing.cvss_score and data['cvss_score']:
                existing.cvss_score = data['cvss_score']
                updated = True
            
            # Save EUVD specific CVSS Metric
            self._save_cvss_metric(primary_id, data)
            
            # TODO: Adicionar lógica mais complexa de merge de vendors/products
            
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
        
        # Vendors/Products (Simplificado)
        vendors = []
        products = {}
        
        for v_item in item.get('enisaIdVendor', []):
            v_name = v_item.get('vendor', {}).get('name')
            if v_name:
                vendors.append(v_name)
                
        for p_item in item.get('enisaIdProduct', []):
            p_name = p_item.get('product', {}).get('name')
            # Tentar associar produto ao vendor (difícil sem estrutura clara, assumindo primeiro vendor)
            # Na estrutura da EUVD, product e vendor são listas separadas no JSON de exemplo?
            # O exemplo mostra enisaIdProduct contendo product info.
            if p_name and vendors:
                vendor = vendors[0] # Simplificação
                if vendor not in products:
                    products[vendor] = []
                products[vendor].append(p_name)

        return {
            'cve_id': primary_id,
            'description': item.get('description'),
            'published_date': published,
            'last_modified_date': updated,
            'cvss_score': float(cvss_score) if cvss_score else None,
            'cvss_version': cvss_version,
            'cvss_vector_string': cvss_vector,
            'nvd_vendors_data': vendors,
            'nvd_products_data': products,
            'vuln_status': 'Analyzed' # Assumindo analisado se está na EUVD
        }

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse da data da EUVD (Apr 15, 2025, 8:30:58 PM)."""
        if not date_str:
            return None
        try:
            # Tentar formato documentado
            return datetime.strptime(date_str, "%b %d, %Y, %I:%M:%S %p")
        except ValueError:
            try:
                # Fallback ISO
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                return None