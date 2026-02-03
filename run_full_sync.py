import logging
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import text

# Load environment variables
load_dotenv()

from app import create_app
from app.extensions import db
from app.models.system.sync_metadata import SyncMetadata
from app.jobs.nvd_fetcher import NVDFetcher
from app.services.nvd.bulk_database_service import BulkDatabaseService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('force_sync')

def force_full_sync():
    """
    Forces a full synchronization with NVD:
    1. Truncates the vulnerabilities table (clears existing data).
    2. Resets sync metadata.
    3. Pre-calculates the grand total of CVEs for accurate progress tracking.
    4. Downloads and saves all CVEs.
    """
    app = create_app()
    with app.app_context():
        logger.info("Starting FORCED FULL NVD SYNC...")
        
        # 1. Clear Data
        logger.info("Truncating vulnerabilities table...")
        try:
            # CASCADE ensures related tables (references, cvss, etc.) are also cleared
            db.session.execute(text('TRUNCATE TABLE vulnerabilities CASCADE'))
            db.session.commit()
            logger.info("Table truncated successfully.")
        except Exception as e:
            logger.error(f"Error truncating table: {e}")
            logger.info("Attempting DELETE FROM instead...")
            try:
                db.session.execute(text('DELETE FROM vulnerabilities'))
                db.session.commit()
            except Exception as e2:
                logger.error(f"Error deleting data: {e2}")
                return

        # 2. Reset Metadata
        logger.info("Resetting sync metadata...")
        SyncMetadata.set('nvd_sync_progress_status', 'running')
        SyncMetadata.set('nvd_sync_progress_processed_cves', 0)
        SyncMetadata.set('nvd_sync_progress_total_cves', 0)
        SyncMetadata.set('nvd_sync_progress_inserted', 0)
        SyncMetadata.set('nvd_sync_progress_updated', 0)
        SyncMetadata.set('nvd_sync_progress_errors', 0)
        SyncMetadata.set('nvd_sync_progress_message', 'Calculating total CVEs...')
        
        fetcher = NVDFetcher()
        db_service = BulkDatabaseService()
        
        # Reset DB service stats
        db_service.stats = {'inserted': 0, 'updated': 0, 'errors': 0, 'skipped': 0}

        start_date = datetime(1999, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)
        
        windows = fetcher.generate_date_windows(start_date, end_date)
        total_windows = len(windows)
        logger.info(f"Generated {total_windows} time windows.")
        
        # 3. Pre-calculate Grand Total
        grand_total = 0
        logger.info("Calculating grand total of CVEs (this may take a minute)...")
        
        for i, (w_start, w_end) in enumerate(windows):
            try:
                # Fetch just one item to get totalResults efficiently
                resp = fetcher.fetch_page(results_per_page=1, pub_start_date=w_start, pub_end_date=w_end)
                if resp:
                    grand_total += resp.total_results
                    # Update metadata periodically to show activity
                    if i % 5 == 0:
                        SyncMetadata.set('nvd_sync_progress_total_cves', grand_total)
                        logger.info(f"Counting... Window {i+1}/{total_windows}")
            except Exception as e:
                logger.error(f"Error counting window {i+1}: {e}")

        logger.info(f"Grand Total CVEs to fetch: {grand_total}")
        SyncMetadata.set('nvd_sync_progress_total_cves', grand_total)
        SyncMetadata.set('nvd_sync_progress_message', 'Starting download...')
        
        # 4. Execute Sync
        processed_so_far = 0
        
        for i, (w_start, w_end) in enumerate(windows):
            logger.info(f"Processing window {i+1}/{total_windows}: {w_start.date()} to {w_end.date()}")
            SyncMetadata.set('nvd_sync_progress_current_window', i + 1)
            SyncMetadata.set('nvd_sync_progress_total_windows', total_windows)
            
            # Callback for Fetcher (updates progress bar)
            def fetch_progress_adapter(current_in_window, total_in_window):
                global_current = processed_so_far + current_in_window
                # Update processed count
                SyncMetadata.set('nvd_sync_progress_processed_cves', global_current)
            
            # Callback for DB Service (updates stats)
            def db_progress_adapter(processed, total, stats):
                SyncMetadata.set('nvd_sync_progress_inserted', stats['inserted'])
                SyncMetadata.set('nvd_sync_progress_updated', stats['updated'])
                SyncMetadata.set('nvd_sync_progress_errors', stats['errors'])
            
            try:
                vulns = fetcher.fetch_all_pages(
                    pub_start_date=w_start, 
                    pub_end_date=w_end,
                    progress_callback=fetch_progress_adapter
                )
                
                if vulns:
                    logger.info(f"Saving {len(vulns)} CVEs to database...")
                    db_service.process_vulnerabilities(vulns, progress_callback=db_progress_adapter)
                    processed_so_far += len(vulns)
                    # Ensure final count for this window is accurate
                    SyncMetadata.set('nvd_sync_progress_processed_cves', processed_so_far)
                
            except Exception as e:
                logger.error(f"Error processing window {i+1}: {e}")
                
        # Finish
        SyncMetadata.set('nvd_sync_progress_status', 'completed')
        SyncMetadata.set('nvd_sync_progress_message', 'Sync completed successfully.')
        SyncMetadata.set('nvd_last_successful_sync', datetime.now(timezone.utc).isoformat())
        logger.info("Full sync completed.")

if __name__ == "__main__":
    force_full_sync()