"""
Open-Monitor Bulk Database Service
Operações de inserção em lote para CVEs do NVD.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from sqlalchemy import text, inspect
from app.extensions.db_types import USE_SQLITE

if USE_SQLITE:
    from sqlalchemy.dialects.sqlite import insert
else:
    from sqlalchemy.dialects.postgresql import insert

from app.extensions import db
from app.models.nvd import Vulnerability, CvssMetric, Weakness, Reference, Mitigation
from app.models.system import SyncMetadata


logger = logging.getLogger(__name__)


class BulkDatabaseService:
    """
    Serviço para inserção em lote de CVEs no banco de dados.
    
    Features:
    - Upsert eficiente com ON CONFLICT
    - Batch processing com controle de memória
    - Normalização de vendors/products
    - Progress tracking
    """
    
    BATCH_SIZE = 500
    
    def __init__(self):
        self.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    def clear_all_data(self) -> None:
        """
        Limpar todos os dados de vulnerabilidades (TRUNCATE).
        Usado para Full Sync forçado.
        """
        logger.info("Clearing existing vulnerability data (TRUNCATE)...")
        try:
            # Ensure tables exist in ALL DBs (core and public)
            db.create_all() # Creates for default bind (core) where SyncMetadata lives
            db.create_all(bind='public') # Creates for public bind where Vulnerabilities live

            engine = db.get_engine(bind='public')
            inspector = inspect(engine)
            
            # Check for table existence
            if inspector.has_table("vulnerabilities"):
                try:
                    # Use TRUNCATE for PostgreSQL (faster)
                    # Use CASCADE to clear asset_vulnerabilities and other related tables
                    with engine.connect() as conn:
                        conn.execute(text('TRUNCATE TABLE vulnerabilities CASCADE'))
                        conn.commit()
                    logger.info("Data cleared successfully.")
                except Exception as trunc_err:
                    logger.warning(f"Could not truncate 'vulnerabilities' table: {trunc_err}")
            else:
                logger.warning("Table 'vulnerabilities' not found in public DB. Skipping TRUNCATE.")

        except Exception as e:
            logger.error(f"Error clearing data: {e}")

    @contextmanager
    def bulk_session(self):
        """Context manager para operações em lote."""
        try:
            yield db.session
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f'Bulk session error: {e}')
            raise
    
    def process_vulnerabilities(
        self,
        vulnerabilities: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """
        Processar lista de vulnerabilidades do NVD.
        
        Args:
            vulnerabilities: Lista de CVEs do NVD API
            progress_callback: Callback(processed, total, stats)
            
        Returns:
            Estatísticas de processamento
        """
        total = len(vulnerabilities)
        processed = 0
        
        # Processar em batches
        for i in range(0, total, self.BATCH_SIZE):
            batch = vulnerabilities[i:i + self.BATCH_SIZE]
            
            try:
                self._process_batch(batch)
                processed += len(batch)
                
                if progress_callback:
                    progress_callback(processed, total, self.stats)
                    
            except Exception as e:
                logger.error(f'Batch processing error: {e}')
                self.stats['errors'] += len(batch)
        
        logger.info(
            f'Processing complete: {self.stats["inserted"]} inserted, '
            f'{self.stats["updated"]} updated, '
            f'{self.stats["errors"]} errors'
        )
        
        return self.stats
    
    def _process_batch(self, batch: List[Dict]) -> None:
        """Processar um batch de vulnerabilidades."""
        logger.info(f"Processing batch of {len(batch)} items")
        vuln_records = []
        cvss_records = []
        weakness_records = []
        reference_records = []
        
        for item in batch:
            cve = item.get('cve', {})
            cve_id = cve.get('id')
            
            if not cve_id:
                self.stats['skipped'] += 1
                continue
            
            # Extrair dados da vulnerabilidade
            vuln_data = self._extract_vulnerability_data(cve)
            if vuln_data:
                vuln_records.append(vuln_data)
            
            # Extrair métricas CVSS
            cvss_data = self._extract_cvss_data(cve)
            cvss_records.extend(cvss_data)
            
            # Extrair weaknesses (CWEs)
            weakness_data = self._extract_weakness_data(cve)
            weakness_records.extend(weakness_data)
            
            # Extrair referências
            ref_data = self._extract_reference_data(cve)
            reference_records.extend(ref_data)
        
        # Inserir em lote
        with self.bulk_session():
            if vuln_records:
                self._upsert_vulnerabilities(vuln_records)
            
            if cvss_records:
                self._upsert_cvss(cvss_records)
            
            if weakness_records:
                self._upsert_weaknesses(weakness_records)
            
            if reference_records:
                self._upsert_references(reference_records)
    
    def _extract_vulnerability_data(self, cve: Dict) -> Optional[Dict]:
        """Extrair dados da vulnerabilidade."""
        cve_id = cve.get('id')
        
        # Descrição em inglês
        descriptions = cve.get('descriptions', [])
        description = next(
            (d['value'] for d in descriptions if d.get('lang') == 'en'),
            descriptions[0]['value'] if descriptions else ''
        )
        
        # Datas
        published = cve.get('published')
        modified = cve.get('lastModified')
        
        # Métricas CVSS (pegar maior severidade)
        metrics = cve.get('metrics', {})
        cvss_score, severity = self._get_highest_cvss(metrics)
        
        # Vendors e Products (do configurations)
        vendors_data, products_data = self._extract_affected_products(cve)
        
        # Status CISA KEV
        cisa_data = cve.get('cisaExploitAdd')
        cisa_action_due = cve.get('cisaActionDue')
        
        return {
            'cve_id': cve_id,
            'description': description[:10000] if description else '',
            'published_date': datetime.fromisoformat(published.replace('Z', '+00:00')) if published else None,
            'last_modified_date': datetime.fromisoformat(modified.replace('Z', '+00:00')) if modified else None,
            'vuln_status': cve.get('vulnStatus'),
            'cvss_score': cvss_score,
            'base_severity': severity,
            'nvd_vendors_data': vendors_data,
            'nvd_products_data': products_data,
            'cpe_configurations': cve.get('configurations'),
            'cisa_exploit_add': datetime.fromisoformat(cisa_data.replace('Z', '+00:00')) if cisa_data else None,
            'cisa_action_due': datetime.fromisoformat(cisa_action_due.replace('Z', '+00:00')) if cisa_action_due else None,
            'is_in_cisa_kev': cisa_data is not None
        }
    
    def _get_highest_cvss(self, metrics: Dict) -> tuple:
        """Obter maior score CVSS e severidade."""
        score = None
        severity = 'UNKNOWN'
        
        # Verificar CVSS v4, v3.1, v3.0, v2 (em ordem de prioridade)
        for version in ['cvssMetricV40', 'cvssMetricV31', 'cvssMetricV30', 'cvssMetricV2']:
            if version in metrics and metrics[version]:
                metric = metrics[version][0]
                cvss_data = metric.get('cvssData', {})
                
                score = cvss_data.get('baseScore')
                severity = cvss_data.get('baseSeverity', 'UNKNOWN')
                break
        
        return score, severity
    
    def _extract_affected_products(self, cve: Dict) -> tuple:
        """Extrair vendors e products afetados."""
        vendors = set()
        products = {}
        
        configurations = cve.get('configurations', [])
        
        for config in configurations:
            for node in config.get('nodes', []):
                for cpe_match in node.get('cpeMatch', []):
                    criteria = cpe_match.get('criteria', '')
                    
                    # Parse CPE: cpe:2.3:a:vendor:product:version:...
                    parts = criteria.split(':')
                    if len(parts) >= 5:
                        vendor = parts[3]
                        product = parts[4]
                        
                        if vendor and vendor != '*':
                            vendors.add(vendor)
                            
                            if product and product != '*':
                                if vendor not in products:
                                    products[vendor] = []
                                if product not in products[vendor]:
                                    products[vendor].append(product)
        
        return list(vendors), products
    
    def _extract_cvss_data(self, cve: Dict) -> List[Dict]:
        """Extrair todas as métricas CVSS."""
        cve_id = cve.get('id')
        records = []
        metrics = cve.get('metrics', {})
        
        # Helper to ensure all fields exist
        def create_record(version, source, type_, cvss_data, metric_data):
            return {
                'cve_id': cve_id,
                'version': version,
                'source': source,
                'type': type_,
                'base_score': cvss_data.get('baseScore'),
                'base_severity': cvss_data.get('baseSeverity') or metric_data.get('baseSeverity'),
                'vector_string': cvss_data.get('vectorString'),
                'exploitability_score': metric_data.get('exploitabilityScore'),
                'impact_score': metric_data.get('impactScore'),
                # V3/V4 fields (default None)
                'attack_vector': cvss_data.get('attackVector'),
                'attack_complexity': cvss_data.get('attackComplexity'),
                'privileges_required': cvss_data.get('privilegesRequired'),
                'user_interaction': cvss_data.get('userInteraction'),
                'scope': cvss_data.get('scope'),
                'confidentiality_impact': cvss_data.get('confidentialityImpact'),
                'integrity_impact': cvss_data.get('integrityImpact'),
                'availability_impact': cvss_data.get('availabilityImpact'),
                # V2 fields (default None)
                'access_vector': cvss_data.get('accessVector'),
                'access_complexity': cvss_data.get('accessComplexity'),
                'authentication': cvss_data.get('authentication')
            }

        # CVSS v4.0
        for metric in metrics.get('cvssMetricV40', []):
            records.append(create_record(
                '4.0', metric.get('source'), metric.get('type'),
                metric.get('cvssData', {}), metric
            ))
        
        # CVSS v3.1
        for metric in metrics.get('cvssMetricV31', []):
            records.append(create_record(
                '3.1', metric.get('source'), metric.get('type'),
                metric.get('cvssData', {}), metric
            ))
        
        # CVSS v3.0
        for metric in metrics.get('cvssMetricV30', []):
            records.append(create_record(
                '3.0', metric.get('source'), metric.get('type'),
                metric.get('cvssData', {}), metric
            ))
        
        # CVSS v2
        for metric in metrics.get('cvssMetricV2', []):
            records.append(create_record(
                '2.0', metric.get('source'), metric.get('type'),
                metric.get('cvssData', {}), metric
            ))
        
        return records
    
    def _extract_weakness_data(self, cve: Dict) -> List[Dict]:
        """Extrair CWEs associados."""
        cve_id = cve.get('id')
        records = []
        
        for weakness in cve.get('weaknesses', []):
            source = weakness.get('source')
            weakness_type = weakness.get('type')
            
            for desc in weakness.get('description', []):
                cwe_id = desc.get('value')
                if cwe_id:
                    records.append({
                        'cve_id': cve_id,
                        'cwe_id': cwe_id,
                        'source': source,
                        'type': weakness_type
                    })
        
        return records
    
    def _extract_reference_data(self, cve: Dict) -> List[Dict]:
        """Extrair referências."""
        cve_id = cve.get('id')
        records = []
        seen_urls = set()
        
        for ref in cve.get('references', []):
            url = ref.get('url')
            if url:
                # Ensure URL is clean and truncated if necessary (though Text is unlimited, good to be safe)
                clean_url = url.replace('\x00', '')[:2048]
                
                # Skip duplicates within the same CVE
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)
                
                # Ensure tags is a list of strings
                raw_tags = ref.get('tags')
                tags = list(raw_tags) if raw_tags else []
                
                # Compute derived fields
                tags_lower = [t.lower() for t in tags]
                is_patch = 'patch' in tags_lower
                is_vendor_advisory = 'vendor advisory' in tags_lower
                is_exploit = 'exploit' in tags_lower
                
                records.append({
                    'cve_id': cve_id,
                    'url': clean_url,
                    'source': ref.get('source'),
                    'tags': tags,
                    'is_patch': is_patch,
                    'is_vendor_advisory': is_vendor_advisory,
                    'is_exploit': is_exploit
                })
        
        return records
    
    def _upsert_vulnerabilities(self, records: List[Dict]) -> None:
        """Upsert de vulnerabilidades."""
        if not records:
            return

        chunk_size = 1000
        total_records = len(records)
        
        for i in range(0, total_records, chunk_size):
            chunk = records[i:i + chunk_size]
            stmt = insert(Vulnerability).values(chunk)
            
            update_dict = {
                'description': stmt.excluded.description,
                'last_modified_date': stmt.excluded.last_modified_date,
                'vuln_status': stmt.excluded.vuln_status,
                'cvss_score': stmt.excluded.cvss_score,
                'base_severity': stmt.excluded.base_severity,
                'nvd_vendors_data': stmt.excluded.nvd_vendors_data,
                'nvd_products_data': stmt.excluded.nvd_products_data,
                'cpe_configurations': stmt.excluded.cpe_configurations,
                'cisa_exploit_add': stmt.excluded.cisa_exploit_add,
                'cisa_action_due': stmt.excluded.cisa_action_due,
                'is_in_cisa_kev': stmt.excluded.is_in_cisa_kev,
                'updated_at': datetime.utcnow()
            }
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['cve_id'],
                set_=update_dict
            )
            
            result = db.session.execute(stmt)
            self.stats['inserted'] += result.rowcount
    
    def _upsert_cvss(self, records: List[Dict]) -> None:
        """Upsert de métricas CVSS."""
        if not records:
            return
            
        chunk_size = 1000
        total_records = len(records)
        
        for i in range(0, total_records, chunk_size):
            chunk = records[i:i + chunk_size]
            stmt = insert(CvssMetric).values(chunk)
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['cve_id', 'version', 'source'],
                set_={
                    'type': stmt.excluded.type,
                    'base_score': stmt.excluded.base_score,
                    'base_severity': stmt.excluded.base_severity,
                    'vector_string': stmt.excluded.vector_string,
                    'attack_vector': stmt.excluded.attack_vector,
                    'attack_complexity': stmt.excluded.attack_complexity,
                    'privileges_required': stmt.excluded.privileges_required,
                    'user_interaction': stmt.excluded.user_interaction,
                    'scope': stmt.excluded.scope,
                    'confidentiality_impact': stmt.excluded.confidentiality_impact,
                    'integrity_impact': stmt.excluded.integrity_impact,
                    'availability_impact': stmt.excluded.availability_impact,
                    'exploitability_score': stmt.excluded.exploitability_score,
                    'impact_score': stmt.excluded.impact_score,
                    'access_vector': stmt.excluded.access_vector,
                    'access_complexity': stmt.excluded.access_complexity,
                    'authentication': stmt.excluded.authentication,
                    'updated_at': datetime.utcnow()
                }
            )
            
            db.session.execute(stmt)
    
    def _upsert_weaknesses(self, records: List[Dict]) -> None:
        """Upsert de CWEs."""
        if not records:
            return
            
        chunk_size = 1000
        total_records = len(records)
        
        for i in range(0, total_records, chunk_size):
            chunk = records[i:i + chunk_size]
            stmt = insert(Weakness).values(chunk)
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['cve_id', 'cwe_id', 'source'],
                set_={
                    'type': stmt.excluded.type,
                    'updated_at': datetime.utcnow()
                }
            )
            
            db.session.execute(stmt)
    
    def _upsert_references(self, records: List[Dict]) -> None:
        """Upsert de referências."""
        if not records:
            return

        # Chunking to avoid parameter limit (65535 parameters max in Postgres)
        # Each reference has ~9 parameters. 65535 / 9 ≈ 7281.
        # We use 1000 as a safe chunk size.
        chunk_size = 1000
        total_records = len(records)
        
        for i in range(0, total_records, chunk_size):
            chunk = records[i:i + chunk_size]
            stmt = insert(Reference).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=['cve_id', 'url'],
                set_={
                    'source': stmt.excluded.source,
                    'tags': stmt.excluded.tags,
                    'is_patch': stmt.excluded.is_patch,
                    'is_vendor_advisory': stmt.excluded.is_vendor_advisory,
                    'is_exploit': stmt.excluded.is_exploit,
                    'updated_at': datetime.utcnow()
                }
            )
            
            db.session.execute(stmt)
    
    def get_last_sync_date(self) -> Optional[datetime]:
        """Obter data do último sync bem sucedido."""
        value = SyncMetadata.get('nvd_last_successful_sync')
        if value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None
    
    def update_sync_metadata(self, key: str, value: Any) -> None:
        """Atualizar metadata de sync."""
        SyncMetadata.set(key, value)