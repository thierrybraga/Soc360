import logging
import time
from datetime import datetime, timezone
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Carregar variáveis de ambiente do .env ANTES de importar app
# Isso garante que BaseConfig (avaliado no import) pegue os valores corretos
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    logger.info(f"Loading .env from: {env_path}")
    load_dotenv(env_path)
except ImportError:
    logger.error("python-dotenv not installed. Environment variables might not be loaded.")
    raise

from sqlalchemy import text
from app import create_app, db
from app.models.nvd import Vulnerability
from app.models.system.sync_metadata import SyncMetadata
from app.jobs.nvd_fetcher import NVDFetcher
from app.services.nvd.bulk_database_service import BulkDatabaseService

app = create_app()

def force_sync():
    with app.app_context():
        logger.info("Starting FORCED FULL NVD SYNC...")
        
        # 1. Clear Data
        logger.info("Clearing existing vulnerability data (TRUNCATE)...")
        try:
            # Ensure tables exist in ALL DBs (core and public)
            # This is critical after a full environment reset
            db.create_all() # Creates for default bind (core) where SyncMetadata lives
            db.create_all(bind='public') # Creates for public bind where Vulnerabilities live

            # Check if table exists before truncating to avoid UndefinedTable error
            from sqlalchemy import inspect
            engine = db.get_engine(bind='public')
            inspector = inspect(engine)
            
            # Check for table existence (handling potential schema issues)
            if inspector.has_table("vulnerabilities"):
                try:
                    # Use TRUNCATE for PostgreSQL (faster)
                    # Use CASCADE to clear asset_vulnerabilities and other related tables
                    with engine.connect() as conn:
                        conn.execute(text('TRUNCATE TABLE vulnerabilities CASCADE'))
                        conn.commit()
                    logger.info("Data cleared successfully.")
                except Exception as trunc_err:
                    logger.warning(f"Could not truncate 'vulnerabilities' table (might be empty or schema issue): {trunc_err}")
            else:
                logger.warning("Table 'vulnerabilities' not found in public DB. Skipping TRUNCATE.")

        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            # Continue even if clear fails - maybe table is empty or just created
            # return

        # 2. Reset Metadata
        SyncMetadata.set('nvd_sync_progress_status', 'running')
        SyncMetadata.set('nvd_sync_progress_mode', 'full_forced')
        SyncMetadata.set('nvd_sync_progress_processed_cves', 0)
        SyncMetadata.set('nvd_sync_progress_total_cves', 0)
        SyncMetadata.set('nvd_sync_progress_started_at', datetime.now(timezone.utc).isoformat())
        
        fetcher = NVDFetcher()
        db_service = BulkDatabaseService()
        
        start_date = datetime(1999, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        
        # 3. Generate Windows
        windows = fetcher.generate_date_windows(start_date, end_date)
        total_windows = len(windows)
        logger.info(f"Generated {total_windows} time windows for sync.")

        # 4. Pre-calculate Total CVEs (Grand Total)
        logger.info("Calculating total CVEs to fetch (this may take a minute)...")
        grand_total = 0
        
        # We need to sum up totalResults for all windows
        for i, (w_start, w_end) in enumerate(windows):
            try:
                # resultsPerPage=1 just to get totalResults
                resp = fetcher.fetch_page(
                    results_per_page=1, 
                    pub_start_date=w_start, 
                    pub_end_date=w_end
                )
                if resp:
                    grand_total += resp.total_results
                    
                    # Update partial total to give user feedback if it takes long
                    # But don't overwrite if 0 (failed fetch)
                    if resp.total_results > 0:
                         SyncMetadata.set('nvd_sync_progress_total_cves', grand_total)
                         
                logger.info(f"Checking window {i+1}/{total_windows}: {resp.total_results if resp else 0} CVEs (Accumulated: {grand_total})")
                
            except Exception as e:
                logger.error(f"Error checking window {i}: {e}")
        
        logger.info(f"Grand Total CVEs to fetch: {grand_total}")
        SyncMetadata.set('nvd_sync_progress_total_cves', grand_total)

        # 5. Execution Loop
        global_processed = 0
        
        for i, (w_start, w_end) in enumerate(windows):
            logger.info(f"Processing window {i+1}/{total_windows}: {w_start.date()} to {w_end.date()}")
            
            SyncMetadata.set('nvd_sync_progress_current_window', i + 1)
            SyncMetadata.set('nvd_sync_progress_total_windows', total_windows)
            
            # Helper to capture current window context
            # We use a mutable container (list) to store processed count in this window
            window_stats = {'processed': 0}
            
            def progress_adapter(current_window_count, total_window_count):
                window_stats['processed'] = current_window_count
                current_global = global_processed + current_window_count
                
                SyncMetadata.set('nvd_sync_progress_processed_cves', current_global)
                SyncMetadata.set('nvd_sync_progress_last_updated', datetime.now(timezone.utc).isoformat())

            # Fetch
            vulns = fetcher.fetch_all_pages(
                pub_start_date=w_start,
                pub_end_date=w_end,
                progress_callback=progress_adapter
            )
            
            # Persist
            if vulns:
                db_service.process_vulnerabilities(vulns)
                
                # Increment global_processed by the actual number of vulns processed in this window
                # We use window_stats['processed'] or len(vulns)
                global_processed += len(vulns)
                
                # Final update for this window to be sure
                SyncMetadata.set('nvd_sync_progress_processed_cves', global_processed)
                logger.info(f"Window {i+1} complete. Global progress: {global_processed}/{grand_total}")

        # 6. Finish
        SyncMetadata.set('nvd_sync_progress_status', 'completed')
        SyncMetadata.set('nvd_sync_progress_processed_cves', grand_total)
        SyncMetadata.set('nvd_first_sync_completed', 'true')
        logger.info("Forced Full Sync Completed Successfully!")

if __name__ == '__main__':
    force_sync()