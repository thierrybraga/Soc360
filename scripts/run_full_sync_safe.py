#!/usr/bin/env python3
"""
Script seguro para executar sincronização full da NVD.
Importa todos os modelos necessários antes de criar as tabelas.
"""
import os
import sys
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import text

# =========================
# FIX PATH
# =========================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nvd_sync")

# =========================
# MAIN
# =========================

def main():
    # Importar a aplicação primeiro
    from app import create_app
    from app.extensions import db
    
    app = create_app()
    
    with app.app_context():
        logger.info("=== STARTING FULL NVD SYNC ===")
        
        # 1. Importar TODOS os modelos antes de criar tabelas
        # Isso garante que todas as tabelas sejam registradas no metadata
        logger.info("Importing all models...")
        
        # System models
        from app.models.system import (
            SyncMetadata, ChatSession, ChatMessage, ChatLog,
            NewsletterSubscription, NewsletterSubscriber
        )
        
        # Auth models
        from app.models.auth import User, Role, UserRole
        
        # MITRE models
        from app.models.mitre import Tactic, Technique, AttackMitigation
        
        # NVD models - VULNERABILITY PRIMEIRO
        from app.models.nvd.vulnerability import Vulnerability
        from app.models.nvd import (
            CvssMetric, Weakness, Reference, Mitigation,
            CVEProduct, CVEVendor, ReferenceTypeModel, VersionReference
        )
        
        # Inventory models
        from app.models.inventory import Asset, AssetVulnerability, Vendor, Product, AssetCategory
        
        # Monitoring models
        from app.models.monitoring import MonitoringRule, Alert, Report, RiskAssessment, ApiCallLog
        
        # Wazuh models
        from app.models.wazuh import WazuhAlert, WazuhTreatmentNote
        
        # Umbrella models
        from app.models.umbrella import (
            UmbrellaOrganization, UmbrellaNetwork, UmbrellaRoamingComputer,
            UmbrellaVirtualAppliance, UmbrellaReportData, UmbrellaGeneratedReport
        )
        
        # D3FEND models - DEPOIS de Vulnerability
        from app.models.d3fend import (
            D3fendTechnique, D3fendArtifact, D3fendTactic,
            D3fendOffensiveMapping, CveD3fendCorrelation
        )
        
        logger.info("All models imported successfully.")
        
        # 2. Verificar conexão com banco
        try:
            engine = db.engine
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection OK")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return
        
        # 3. Criar todas as tabelas
        logger.info("Creating database tables...")
        try:
            db.create_all()
            logger.info("Tables created successfully.")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 4. Agora executar o sync full
        from app.jobs.fetchers import NVDFetcher
        from app.services.nvd.bulk_database_service import BulkDatabaseService
        
        # Reset metadata
        now = datetime.now(timezone.utc).isoformat()
        SyncMetadata.set('nvd_sync_progress_status', 'running')
        SyncMetadata.set('nvd_sync_progress_processed_cves', 0)
        SyncMetadata.set('nvd_sync_progress_total_cves', 0)
        SyncMetadata.set('nvd_sync_progress_inserted', 0)
        SyncMetadata.set('nvd_sync_progress_updated', 0)
        SyncMetadata.set('nvd_sync_progress_errors', 0)
        SyncMetadata.set('nvd_sync_progress_message', 'Initializing')
        SyncMetadata.set('nvd_sync_progress_started_at', now)
        
        # Services
        fetcher = NVDFetcher()
        db_service = BulkDatabaseService()
        
        db_service.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        # Windows
        start_date = datetime(1999, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        
        windows = fetcher.generate_date_windows(start_date, end_date)
        logger.info(f"Generated {len(windows)} windows")
        
        # Calcular total
        logger.info("Calculating total CVEs...")
        total = 0
        for i, (start, end) in enumerate(windows):
            try:
                resp = fetcher.fetch_page(
                    results_per_page=1,
                    pub_start_date=start,
                    pub_end_date=end
                )
                if resp:
                    total += resp.total_results
                    if i % 5 == 0:
                        SyncMetadata.set('nvd_sync_progress_total_cves', total)
            except Exception as e:
                logger.error(f"Error counting window {i+1}: {e}")
        
        logger.info(f"Total CVEs: {total}")
        SyncMetadata.set('nvd_sync_progress_total_cves', total)
        SyncMetadata.set('nvd_sync_progress_message', 'Downloading CVEs')
        
        # Processar windows
        processed = 0
        for i, (start, end) in enumerate(windows):
            logger.info(f"[{i+1}/{len(windows)}] {start.date()} → {end.date()}")
            
            SyncMetadata.set('nvd_sync_progress_current_window', i + 1)
            SyncMetadata.set('nvd_sync_progress_total_windows', len(windows))
            
            def fetch_progress(current, total):
                SyncMetadata.set(
                    'nvd_sync_progress_processed_cves',
                    processed + current
                )
            
            def db_progress(_, __, stats):
                SyncMetadata.set('nvd_sync_progress_inserted', stats['inserted'])
                SyncMetadata.set('nvd_sync_progress_updated', stats['updated'])
                SyncMetadata.set('nvd_sync_progress_errors', stats['errors'])
            
            try:
                vulns = fetcher.fetch_all_pages(
                    pub_start_date=start,
                    pub_end_date=end,
                    progress_callback=fetch_progress
                )
                
                if vulns:
                    logger.info(f"Saving {len(vulns)} CVEs...")
                    db_service.process_vulnerabilities(
                        vulns,
                        progress_callback=db_progress
                    )
                    processed += len(vulns)
                    SyncMetadata.set(
                        'nvd_sync_progress_processed_cves',
                        processed
                    )
            except Exception as e:
                logger.error(f"Error in window {i+1}: {e}")
        
        # Finalizar
        SyncMetadata.set('nvd_sync_progress_status', 'completed')
        SyncMetadata.set('nvd_last_successful_sync', datetime.now(timezone.utc).isoformat())
        SyncMetadata.set('nvd_first_sync_completed', 'true')
        
        logger.info(f"Sync completed. Total processed: {processed}")


if __name__ == "__main__":
    main()