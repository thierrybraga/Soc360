"""
SOC360 NVD Sync Service
Orquestrador de sincronização com NVD.
"""
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from enum import Enum

from flask import current_app

from app.jobs.fetchers import NVDFetcher
from app.services.nvd.bulk_database_service import BulkDatabaseService
from app.services.monitoring.alert_service import AlertService
from app.models.system import SyncMetadata
from app.models.nvd import Vulnerability


logger = logging.getLogger(__name__)


class SyncMode(Enum):
    """Modos de sincronização."""
    FULL = 'full'  # Sync completo desde 1999
    INCREMENTAL = 'incremental'  # Apenas modificações recentes
    INITIAL = 'initial'  # Último ano
    CUSTOM = 'custom'  # Range personalizado


from app.services.core.base_sync_service import BaseSyncService, SyncStatus

class NVDSyncService(BaseSyncService):
    """
    Serviço de sincronização com NVD.
    
    Features:
    - Full sync com janelas de 120 dias
    - Incremental sync (modificações das últimas 24h)
    - Initial sync (último ano)
    - Progress tracking em tempo real
    - Thread-safe
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(prefix='nvd')
        # Tentar carregar API key do SyncMetadata se não fornecida
        if not api_key:
            stored_key = SyncMetadata.get('nvd_api_key')
            if stored_key:
                api_key = stored_key
                
        self.fetcher = NVDFetcher(api_key)
        self.db_service = BulkDatabaseService()
        
        self._lock = threading.Lock()
        self._cancel_flag = False
        self._current_sync: Optional[Dict] = None
    
    @property
    def is_running(self) -> bool:
        """Verificar se sync está em execução."""
        status = SyncMetadata.get('nvd_sync_progress_status')
        return status == SyncStatus.RUNNING.value
    
    def cancel_sync(self) -> bool:
        """Cancelar sync em execução."""
        with self._lock:
            if not self.is_running:
                return False
            
            self._cancel_flag = True
            self._update_progress(status='cancelled')
            logger.info('Sync cancellation requested')
            return True
    
    def start_sync(
        self,
        mode: SyncMode = SyncMode.INCREMENTAL,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        async_mode: bool = True
    ) -> bool:
        """
        Iniciar sincronização.
        
        Args:
            mode: Modo de sincronização
            start_date: Data inicial (para CUSTOM)
            end_date: Data final (para CUSTOM)
            async_mode: Executar em thread separada
            
        Returns:
            True se iniciou, False se já em execução
        """
        with self._lock:
            if self.is_running:
                logger.warning('Sync already running')
                return False
            
            self._cancel_flag = False
            
            # Determinar range de datas
            if mode == SyncMode.FULL:
                start_date = datetime(1999, 1, 1, tzinfo=timezone.utc)
                end_date = datetime.now(timezone.utc)
            elif mode == SyncMode.INITIAL:
                start_date = datetime.now(timezone.utc) - timedelta(days=365)
                end_date = datetime.now(timezone.utc)
            elif mode == SyncMode.INCREMENTAL:
                # Últimas 24 horas ou desde último sync
                last_sync = self.db_service.get_last_sync_date()
                if last_sync:
                    start_date = last_sync - timedelta(hours=1)  # Overlap para segurança
                else:
                    start_date = datetime.now(timezone.utc) - timedelta(days=1)
                end_date = datetime.now(timezone.utc)
            
            # Validar datas
            if not start_date or not end_date:
                logger.error('Invalid date range')
                return False
            
            # Inicializar progresso e resetar stats
            self._update_progress(
                status='running',
                mode=mode.value,
                started_at=datetime.now(timezone.utc).isoformat(),
                processed=0,
                processed_cves=0,
                total=0,
                total_cves=0,
                inserted=0,
                updated=0,
                errors=0,
                skipped=0,
                error=None,
                message='Iniciando sincronização...'
            )
            
            if async_mode:
                # Capture real app object to pass to thread
                app = current_app._get_current_object()
                thread = threading.Thread(
                    target=self._run_sync,
                    args=(mode, start_date, end_date, app),
                    daemon=True
                )
                thread.start()
            else:
                # Synchronous mode (testing/scripts) - usually already has context
                # But we pass it just in case or None if not needed
                app = current_app._get_current_object() 
                self._run_sync(mode, start_date, end_date, app)
            
            return True
    
    def _run_sync(
        self,
        mode: SyncMode,
        start_date: datetime,
        end_date: datetime,
        app=None
    ) -> None:
        """Executar sincronização."""
        # Ensure we have an app context
        if app:
            with app.app_context():
                self._execute_sync_logic(mode, start_date, end_date)
        else:
            self._execute_sync_logic(mode, start_date, end_date)

    def _execute_sync_logic(self, mode: SyncMode, start_date: datetime, end_date: datetime) -> None:
        """Lógica interna de sincronização (dentro do contexto)."""
        try:
            self.db_service.reset_stats()
            logger.info(
                f'Starting NVD sync: mode={mode.value}, '
                f'range={start_date.date()} to {end_date.date()}'
            )
            
            # INTEGRATION: Logic from force_full_nvd_sync.py
            # If full sync, clear existing data to ensure clean state
            if mode == SyncMode.FULL:
                self.db_service.clear_all_data()
                
                # Reset metadata counters after clear
                self._update_progress(
                    processed_cves=0,
                    total_cves=0,
                    inserted=0,
                    updated=0,
                    errors=0,
                    skipped=0
                )

                # Pre-calculate Grand Total for FULL sync (Mirroring force_full_nvd_sync.py)
                logger.info("Calculating total CVEs to fetch (Grand Total)...")
                windows = self.fetcher.generate_date_windows(start_date, end_date)
                grand_total = 0
                for i, (w_start, w_end) in enumerate(windows):
                    if self._cancel_flag: break
                    try:
                        resp = self.fetcher.fetch_page(results_per_page=1, pub_start_date=w_start, pub_end_date=w_end)
                        if resp:
                            grand_total += resp.total_results
                            # Update partial total to give user feedback
                            if resp.total_results > 0:
                                self._update_progress(total=grand_total, total_cves=grand_total)
                    except Exception as e:
                        logger.error(f"Error calculating total for window {i}: {e}")
                
                logger.info(f"Grand Total CVEs to fetch: {grand_total}")
                self._update_progress(total=grand_total, total_cves=grand_total)
            
            if mode == SyncMode.INCREMENTAL:
                self._run_incremental_sync(start_date, end_date)
            else:
                # For full sync, we pass the grand_total to help progress tracking
                # But _run_windowed_sync needs to be careful not to overwrite total_cves with window total
                self._run_windowed_sync(start_date, end_date, is_full_sync=(mode == SyncMode.FULL))
            
            if not self._cancel_flag:
                # Atualizar último sync bem sucedido
                self.db_service.update_sync_metadata(
                    'nvd_last_successful_sync',
                    datetime.now(timezone.utc).isoformat()
                )

                # INTEGRATION: Logic from force_full_nvd_sync.py
                # If full sync completed, mark first sync as done
                if mode == SyncMode.FULL:
                    self.db_service.update_sync_metadata(
                        'nvd_first_sync_completed',
                        'true'
                    )
                
                self._update_progress(
                    status='completed',
                    message='Sincronização concluída com sucesso.',
                    last_updated=datetime.now(timezone.utc).isoformat()
                )
                
                logger.info('NVD sync completed successfully')
            
        except Exception as e:
            logger.error(f'NVD sync failed: {e}')
            self._update_progress(
                status='failed',
                error=str(e),
                message=f'Falha na sincronização: {str(e)}'
            )
    
    def _run_incremental_sync(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> None:
        """Sync incremental usando lastModified."""
        logger.info(f'Running incremental sync from {start_date}')
        
        # Buscar por lastModified
        vulnerabilities = self.fetcher.fetch_all_pages(
            last_mod_start_date=start_date,
            last_mod_end_date=end_date,
            progress_callback=self._fetch_progress_callback
        )
        
        if self._cancel_flag:
            return
        
        self._update_progress(
            total=len(vulnerabilities),
            total_cves=len(vulnerabilities)
        )
        
        # Processar
        self.db_service.process_vulnerabilities(
            vulnerabilities,
            progress_callback=self._db_progress_callback
        )
        
        # Gerar alertas
        try:
            logger.info("Generating alerts for incremental sync...")
            cve_ids = [v.get('cve', {}).get('id') for v in vulnerabilities if v.get('cve', {}).get('id')]
            cve_ids = [i for i in cve_ids if i] # Filter None
            
            if cve_ids:
                chunk_size = 100
                total_processed = 0
                for i in range(0, len(cve_ids), chunk_size):
                    chunk_ids = cve_ids[i:i + chunk_size]
                    with self.db_service.bulk_session() as session:
                        vulns = session.query(Vulnerability).filter(Vulnerability.cve_id.in_(chunk_ids)).all()
                        
                        for vuln in vulns:
                            AlertService.process_new_vulnerability(vuln)
                        
                        total_processed += len(vulns)
                    
                logger.info(f"Alert generation completed. Processed {total_processed} vulnerabilities.")
        except Exception as e:
            logger.error(f"Error generating alerts: {e}")
    
    def _run_windowed_sync(
        self,
        start_date: datetime,
        end_date: datetime,
        is_full_sync: bool = False
    ) -> None:
        """Sync com janelas de 120 dias."""
        windows = self.fetcher.generate_date_windows(start_date, end_date)
        total_windows = len(windows)
        
        logger.info(f'Running windowed sync with {total_windows} windows')
        
        self._update_progress(
            current_window=0,
            total_windows=total_windows
        )

        # Track global processed count for Full Sync to keep progress bar consistent
        # Initialize with current value from metadata (should be 0 for new full sync)
        global_processed = 0
        if is_full_sync:
            global_processed = self.get_progress().get('processed_cves') or 0
        
        for i, (window_start, window_end) in enumerate(windows):
            if self._cancel_flag:
                break
            
            logger.info(f'Processing window {i+1}/{total_windows}: {window_start.date()} to {window_end.date()}')
            
            self._update_progress(
                current_window=i + 1,
                message=f'Processing window {i+1}/{total_windows}: {window_start.date()} to {window_end.date()}'
            )

            # Custom callback to handle global progress for Full Sync
            def custom_progress_callback(current, total):
                if is_full_sync:
                    # For full sync, we want to update processed_cves cumulatively
                    # current here is just for this window
                    # We don't overwrite total_cves because we calculated Grand Total
                    self._update_progress(
                        processed=global_processed + current,
                        processed_cves=global_processed + current,
                        last_updated=datetime.now(timezone.utc).isoformat()
                    )
                else:
                    # Standard behavior
                    self._fetch_progress_callback(current, total)
            
            # Buscar CVEs da janela
            vulnerabilities = self.fetcher.fetch_all_pages(
                pub_start_date=window_start,
                pub_end_date=window_end,
                progress_callback=custom_progress_callback
            )
            
            if self._cancel_flag:
                break
            
            # Processar
            self.db_service.process_vulnerabilities(
                vulnerabilities,
                progress_callback=self._db_progress_callback
            )

            if is_full_sync:
                global_processed += len(vulnerabilities)
                # Ensure metadata is updated with exact count after window
                self._update_progress(processed=global_processed, processed_cves=global_processed)
            
            # Checkpoint
            self.db_service.update_sync_metadata(
                'nvd_sync_checkpoint',
                window_end.isoformat()
            )
    
    def _fetch_progress_callback(self, current: int, total: int) -> None:
        """Callback de progresso do fetch."""
        self._update_progress(
            processed=current,
            processed_cves=current,
            total=total,
            total_cves=total,
            last_updated=datetime.now(timezone.utc).isoformat()
        )
    
    def _db_progress_callback(self, processed: int, total: int, stats: Dict = None) -> None:
        """Callback de progresso do banco."""
        updates = {
            'processed': processed,
            'processed_cves': processed,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        if stats:
            updates.update({
                'inserted': stats.get('inserted', 0),
                'updated': stats.get('updated', 0),
                'errors': stats.get('errors', 0),
                'skipped': stats.get('skipped', 0)
            })
            
        self._update_progress(**updates)
    



def trigger_nvd_sync(mode: str = 'incremental') -> bool:
    """
    Função helper para disparar sync.
    
    Args:
        mode: 'full', 'incremental', 'initial'
        
    Returns:
        True se iniciou
    """
    sync_mode = SyncMode(mode)
    service = NVDSyncService()
    return service.start_sync(mode=sync_mode)