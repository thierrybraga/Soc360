import logging
import os
from datetime import datetime, timezone

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("force_sync")

# =========================
# LOAD ENV
# =========================
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    logger.info(f"Loading .env from: {env_path}")
    load_dotenv(env_path)
except ImportError:
    logger.error("python-dotenv not installed.")
    raise

# =========================
# IMPORTS
# =========================
from sqlalchemy import text, inspect
from app import create_app
from app.extensions import db
from app.models.system.sync_metadata import SyncMetadata
from app.jobs.fetchers import NVDFetcher
from app.services.nvd.bulk_database_service import BulkDatabaseService

app = create_app()


# =========================
# HELPERS
# =========================

def is_sqlite():
    return "sqlite" in str(db.engine.url)


def ensure_database():
    """
    Cria tabelas (compatível com SQLAlchemy 2.x)
    """
    logger.info("Ensuring database tables...")
    db.create_all()
    logger.info("Tables ready.")


def clean_vulnerabilities():
    """
    Limpa tabela com suporte a SQLite e Postgres
    """
    logger.info("Cleaning vulnerabilities table...")

    try:
        inspector = inspect(db.engine)

        if not inspector.has_table("vulnerabilities"):
            logger.warning("Table 'vulnerabilities' does not exist. Skipping clean.")
            return

        if is_sqlite():
            logger.warning("SQLite detected → using DELETE")
            db.session.execute(text("DELETE FROM vulnerabilities"))
        else:
            db.session.execute(text("TRUNCATE TABLE vulnerabilities CASCADE"))

        db.session.commit()
        logger.info("Table cleaned.")

    except Exception as e:
        logger.error(f"Error cleaning table: {e}")
        raise


def reset_metadata():
    logger.info("Resetting metadata...")

    SyncMetadata.set('nvd_sync_progress_status', 'running')
    SyncMetadata.set('nvd_sync_progress_mode', 'full_forced')
    SyncMetadata.set('nvd_sync_progress_processed_cves', 0)
    SyncMetadata.set('nvd_sync_progress_total_cves', 0)
    SyncMetadata.set('nvd_sync_progress_started_at', datetime.now(timezone.utc).isoformat())


# =========================
# MAIN
# =========================

def force_sync():
    with app.app_context():
        logger.info("=== STARTING FORCED FULL NVD SYNC ===")

        # 1. DB
        ensure_database()

        # 2. CLEAN
        clean_vulnerabilities()

        # 3. METADATA
        reset_metadata()

        # 4. SERVICES
        fetcher = NVDFetcher()
        db_service = BulkDatabaseService()

        start_date = datetime(1999, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)

        # 5. WINDOWS
        windows = fetcher.generate_date_windows(start_date, end_date)
        total_windows = len(windows)

        logger.info(f"Generated {total_windows} windows")

        # 6. CALCULATE TOTAL
        logger.info("Calculating total CVEs...")
        grand_total = 0

        for i, (w_start, w_end) in enumerate(windows):
            try:
                resp = fetcher.fetch_page(
                    results_per_page=1,
                    pub_start_date=w_start,
                    pub_end_date=w_end
                )

                if resp:
                    grand_total += resp.total_results

                    if resp.total_results > 0:
                        SyncMetadata.set('nvd_sync_progress_total_cves', grand_total)

                logger.info(f"[{i+1}/{total_windows}] total so far: {grand_total}")

            except Exception as e:
                logger.error(f"Error counting window {i+1}: {e}")

        logger.info(f"Total CVEs: {grand_total}")
        SyncMetadata.set('nvd_sync_progress_total_cves', grand_total)

        # 7. PROCESS
        global_processed = 0

        for i, (w_start, w_end) in enumerate(windows):
            logger.info(f"[{i+1}/{total_windows}] {w_start.date()} → {w_end.date()}")

            SyncMetadata.set('nvd_sync_progress_current_window', i + 1)
            SyncMetadata.set('nvd_sync_progress_total_windows', total_windows)

            def progress_callback(current, total):
                SyncMetadata.set(
                    'nvd_sync_progress_processed_cves',
                    global_processed + current
                )

                SyncMetadata.set(
                    'nvd_sync_progress_last_updated',
                    datetime.now(timezone.utc).isoformat()
                )

            try:
                vulns = fetcher.fetch_all_pages(
                    pub_start_date=w_start,
                    pub_end_date=w_end,
                    progress_callback=progress_callback
                )

                if vulns:
                    db_service.process_vulnerabilities(vulns)

                    global_processed += len(vulns)

                    SyncMetadata.set(
                        'nvd_sync_progress_processed_cves',
                        global_processed
                    )

                    logger.info(f"Progress: {global_processed}/{grand_total}")

            except Exception as e:
                logger.error(f"Error in window {i+1}: {e}")

        # 8. FINALIZE
        SyncMetadata.set('nvd_sync_progress_status', 'completed')
        SyncMetadata.set('nvd_sync_progress_processed_cves', grand_total)
        SyncMetadata.set('nvd_first_sync_completed', 'true')

        logger.info("=== SYNC COMPLETED SUCCESSFULLY ===")


if __name__ == '__main__':
    force_sync()