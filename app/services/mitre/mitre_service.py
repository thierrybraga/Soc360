import logging
import threading
from typing import Dict, Optional, List, Any
from sqlalchemy.dialects.postgresql import insert
from flask import current_app
from app.extensions import db
from app.models.nvd import Vulnerability, CvssMetric, Weakness, Reference, Mitigation, Credit, AffectedProduct
from app.models.system import SyncMetadata
from app.jobs.fetchers import MitreFetcher
from datetime import datetime, timezone
from app.services.monitoring.alert_service import AlertService

logger = logging.getLogger(__name__)

from app.services.core.base_sync_service import BaseSyncService, SyncStatus

class MitreService(BaseSyncService):
    """
    Serviço para sincronização e consolidação de dados da MITRE (CVE Services).
    """
    
    def __init__(self):
        super().__init__(prefix='mitre')
        self.fetcher = MitreFetcher()

    def get_status(self) -> Dict:
        """Obter status atual da sincronização."""
        return self.get_progress()

    def sync_cve(self, cve_id: str, force: bool = False) -> Dict:
        """Sincronizar um único CVE da MITRE."""
        try:
            data = self.fetcher.fetch_cve(cve_id)
            if data:
                self._process_mitre_data(data, force)
                db.session.commit()
                self.stats['processed'] += 1
                self.stats['updated'] += 1
            else:
                self.stats['skipped'] += 1
            
            self._update_progress(**self.stats)
            return self.stats
        except Exception as e:
            db.session.rollback()
            self.fail_sync(str(e))
            raise

    def start_enrichment_task(self, limit: int = 0, force: bool = False) -> bool:
        """
        Iniciar tarefa de enriquecimento em background.
        Retorna True se iniciou, False se já estiver rodando.
        """
        current_status = SyncMetadata.get('mitre_sync_status')
        if current_status == 'running':
            logger.warning("MITRE enrichment already running.")
            return False

        # Capture app context for thread
        app = current_app._get_current_object()
        
        thread = threading.Thread(
            target=self._run_enrichment,
            args=(app, limit, force),
            daemon=True
        )
        thread.start()
        return True

    def _run_enrichment(self, app, limit: int, force: bool):
        """Executar enriquecimento dentro do contexto da aplicação."""
        with app.app_context():
            try:
                self.enrich_existing_vulnerabilities(limit, force)
            except Exception as e:
                logger.error(f"Thread error: {e}")
                # Status update is handled inside enrich_existing_vulnerabilities

    def _update_status(self, status: str, message: str, stats: Optional[Dict] = None):
        """Helper to update status and message in sync metadata."""
        data = {
            f'{self.prefix}_sync_status': status,
            f'{self.prefix}_sync_message': message,
            f'{self.prefix}_sync_last_updated': datetime.now(timezone.utc).isoformat()
        }
        if stats:
            # Map stats keys to prefixed metadata keys
            for k, v in stats.items():
                data[f'{self.prefix}_sync_progress_{k}'] = v
        SyncMetadata.set_multi(data)

    def enrich_existing_vulnerabilities(self, limit: int = 0, force: bool = False):
        """
        Enriquecer vulnerabilidades existentes.
        limit=0 processa todas as correspondentes.
        force=True processa todas as CVEs salvas, ignorando filtros de 'faltando dados'.
        """
        try:
            self._update_status('running', f'Starting enrichment...')
            
            query = Vulnerability.query
            if not force:
                # Se não for forçado, busca apenas as que precisam de dados
                query = query.filter(
                    (Vulnerability.description == None) | 
                    (Vulnerability.vuln_status == 'Awaiting Analysis')
                )
            
            # Count total to process
            total_matches = query.count()
            
            if limit > 0:
                total_to_process = min(total_matches, limit)
            else:
                total_to_process = total_matches
                
            self.stats['total'] = total_to_process
            self._update_status('running', f'Found {total_to_process} vulnerabilities to enrich...', self.stats)
            
            processed_count = 0
            page_size = 100
            
            while processed_count < total_to_process:
                # Calcular limite do lote atual
                remaining = total_to_process - processed_count
                current_batch_size = min(page_size, remaining)
                
                # Fetch batch
                if not force:
                    # Com filtro ativo (fila dinâmica), pegamos sempre os primeiros
                    batch = query.order_by(Vulnerability.published_date.desc()).limit(current_batch_size).all()
                else:
                    # Sem filtro (lista estática), usamos offset
                    batch = query.order_by(Vulnerability.published_date.desc()).offset(processed_count).limit(current_batch_size).all()
                    
                if not batch:
                    break
                    
                for vuln in batch:
                    try:
                        self.sync_cve(vuln.cve_id, force)
                    except Exception as e:
                        self.stats['errors'] += 1
                        logger.error(f"Failed to enrich {vuln.cve_id}: {e}")
                    
                    processed_count += 1
                    if processed_count % 5 == 0: # Update mais frequente
                        self._update_status(
                            'running', 
                            f'Processed {processed_count}/{total_to_process}...', 
                            self.stats
                        )
                
                # Commit a cada lote para liberar memória e salvar progresso
                # Nota: sync_cve já faz commit individualmente, mas aqui garantimos limpar a sessão se necessário
                # db.session.commit() 
            
            SyncMetadata.set('mitre_last_sync_date', datetime.now(timezone.utc).isoformat())
            self._update_status('completed', 'Enrichment completed', self.stats)
            return self.stats
            
        except Exception as e:
            logger.error(f"Error enriching vulnerabilities: {e}")
            self._update_status('failed', str(e))
            # No need to raise in thread, just log

    def _process_mitre_data(self, data: Dict, force: bool = False):
        """Processar JSON da MITRE e atualizar modelo."""
        cve_id = data.get('cveMetadata', {}).get('cveId')
        if not cve_id:
            return
        cve_id = cve_id.upper()

        vuln = Vulnerability.query.filter_by(cve_id=cve_id).first()
        if not vuln:
            # Se não existe no NVD, podemos criar? 
            # Sim, mas com cuidado. Por enquanto vamos focar em enriquecimento.
            # Se quisermos criar, precisamos instanciar Vulnerability(cve_id=cve_id)
            vuln = Vulnerability(cve_id=cve_id)
            db.session.add(vuln)

        # Extrair dados do container 'cna' (Authority)
        containers = data.get('containers', {})
        cna = containers.get('cna', {})
        
        updated = False

        # Descrição
        descriptions = cna.get('descriptions', [])
        desc_en = next((d['value'] for d in descriptions if d.get('lang') == 'en'), None)
        
        # Só atualiza se o NVD não tiver, se quisermos forçar (force=True), ou se status for 'Awaiting Analysis'
        if desc_en and (force or not vuln.description or vuln.vuln_status == 'Awaiting Analysis'):
            vuln.description = desc_en
            updated = True

        # Processar dados adicionais (Metrics, Weaknesses, References)
        self._save_cvss_metrics(cve_id, cna)
        self._save_weaknesses(cve_id, cna)
        self._save_references(cve_id, cna)
        self._save_mitigations(cve_id, cna)
        self._save_credits(cve_id, cna)
        self._save_affected_products(cve_id, cna)

        if updated:
            self.stats['updated'] += 1
            
        # Trigger alert processing for this vulnerability
        # Note: Mitre usually enriches existing NVD data, but can also create new entries.
        # We should check alerts if important fields changed or if it's new.
        if updated or not vuln.description: 
             AlertService.process_new_vulnerability(vuln)

    def _save_mitigations(self, cve_id: str, cna: Dict):
        """Processar e salvar mitigações/workarounds."""
        solutions = cna.get('solutions', [])
        workarounds = cna.get('workarounds', [])
        
        items = []
        for s in solutions:
            items.append({'desc': s.get('value'), 'type': 'Solution'})
        for w in workarounds:
            items.append({'desc': w.get('value'), 'type': 'Workaround'})
            
        for item in items:
            if not item['desc']:
                continue
                
            mitigation_data = {
                'cve_id': cve_id,
                'description': item['desc'],
                'type': item['type'],
                'source': 'mitre',
                'updated_at': datetime.utcnow()
            }
            
            try:
                exists = Mitigation.query.filter_by(
                    cve_id=cve_id, 
                    description=item['desc'],
                    type=item['type']
                ).first()
                
                if not exists:
                    db.session.add(Mitigation(**mitigation_data))
            except Exception as e:
                logger.warning(f"Failed to save MITRE mitigation for {cve_id}: {e}")

    def _save_credits(self, cve_id: str, cna: Dict):
        """Processar e salvar créditos."""
        credits = cna.get('credits', [])
        
        for credit in credits:
            value = credit.get('value')
            if not value:
                continue
                
            credit_data = {
                'cve_id': cve_id,
                'value': value,
                'user': credit.get('user'),
                'type': ','.join(credit.get('type', [])) if isinstance(credit.get('type'), list) else credit.get('type'),
                'updated_at': datetime.utcnow()
            }
            
            try:
                exists = Credit.query.filter_by(
                    cve_id=cve_id,
                    value=value
                ).first()
                
                if not exists:
                    db.session.add(Credit(**credit_data))
            except Exception as e:
                logger.warning(f"Failed to save MITRE credit for {cve_id}: {e}")

    def _save_affected_products(self, cve_id: str, cna: Dict):
        """Processar e salvar produtos afetados."""
        affected = cna.get('affected', [])
        
        for item in affected:
            vendor = item.get('vendor')
            product = item.get('product')
            
            if not vendor or not product or product == 'n/a':
                continue
                
            product_data = {
                'cve_id': cve_id,
                'vendor': vendor,
                'product': product,
                'versions': item.get('versions', []),
                'platforms': item.get('platforms', []),
                'updated_at': datetime.utcnow()
            }
            
            try:
                exists = AffectedProduct.query.filter_by(
                    cve_id=cve_id,
                    vendor=vendor,
                    product=product
                ).first()
                
                if exists:
                    exists.versions = item.get('versions', [])
                    exists.platforms = item.get('platforms', [])
                    exists.updated_at = datetime.utcnow()
                else:
                    db.session.add(AffectedProduct(**product_data))
            except Exception as e:
                logger.warning(f"Failed to save MITRE affected product for {cve_id}: {e}")

    def _save_cvss_metrics(self, cve_id: str, cna: Dict):
        """Processar e salvar métricas CVSS da MITRE."""
        metrics = cna.get('metrics', [])
        
        for metric in metrics:
            # Tentar identificar versão CVSS
            cvss_data = None
            version = None
            
            if 'cvssV3_1' in metric:
                cvss_data = metric['cvssV3_1']
                version = '3.1'
            elif 'cvssV3_0' in metric:
                cvss_data = metric['cvssV3_0']
                version = '3.0'
            elif 'cvssV4_0' in metric:
                cvss_data = metric['cvssV4_0']
                version = '4.0'
            elif 'cvssV2_0' in metric:
                cvss_data = metric['cvssV2_0']
                version = '2.0'
                
            if not cvss_data or not cvss_data.get('baseScore'):
                continue
                
            metric_data = {
                'cve_id': cve_id,
                'version': version,
                'source': 'mitre',  # Simplificação, idealmente extrair do CNA providerMetadata
                'type': 'Secondary',
                'base_score': cvss_data.get('baseScore'),
                'base_severity': cvss_data.get('baseSeverity'),
                'vector_string': cvss_data.get('vectorString'),
                'attack_vector': cvss_data.get('attackVector'),
                'attack_complexity': cvss_data.get('attackComplexity'),
                'privileges_required': cvss_data.get('privilegesRequired'),
                'user_interaction': cvss_data.get('userInteraction'),
                'scope': cvss_data.get('scope'),
                'confidentiality_impact': cvss_data.get('confidentialityImpact'),
                'integrity_impact': cvss_data.get('integrityImpact'),
                'availability_impact': cvss_data.get('availabilityImpact'),
                'updated_at': datetime.utcnow()
            }
            
            try:
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
            except Exception as e:
                logger.warning(f"Failed to save MITRE metric for {cve_id}: {e}")

    def _save_weaknesses(self, cve_id: str, cna: Dict):
        """Processar e salvar CWEs da MITRE."""
        problem_types = cna.get('problemTypes', [])
        
        for pt in problem_types:
            for desc in pt.get('descriptions', []):
                cwe_id = desc.get('cweId')
                if not cwe_id or not cwe_id.startswith('CWE-'):
                    continue
                    
                weakness_data = {
                'cve_id': cve_id,
                'cwe_id': cwe_id,
                'source': 'mitre',
                'type': 'Secondary',
                'description': desc.get('description'),
                'name': Weakness.COMMON_CWES.get(cwe_id, desc.get('description')),
                'updated_at': datetime.utcnow()
            }
                
                try:
                    stmt = insert(Weakness).values(weakness_data)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=['cve_id', 'cwe_id', 'source']
                    )
                    db.session.execute(stmt)
                except Exception as e:
                    logger.warning(f"Failed to save MITRE weakness for {cve_id}: {e}")

    def _save_references(self, cve_id: str, cna: Dict):
        """Processar e salvar referências da MITRE."""
        references = cna.get('references', [])
        
        for ref in references:
            url = ref.get('url')
            if not url:
                continue
                
            ref_data = {
                'cve_id': cve_id,
                'url': url,
                'source': 'mitre',
                'tags': ref.get('tags', []),
                'updated_at': datetime.utcnow()
            }
            
            try:
                # Usar insert padrão com ignore para duplicatas de URL
                stmt = insert(Reference).values(ref_data)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=['cve_id', 'url']
                )
                db.session.execute(stmt)
            except Exception as e:
                logger.warning(f"Failed to save MITRE reference for {cve_id}: {e}")