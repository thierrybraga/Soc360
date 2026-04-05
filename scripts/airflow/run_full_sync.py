import os
import sys
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import text, inspect

# =========================
# FIX PATH
# =========================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# =========================
# LOAD ENV
# =========================
load_dotenv()

# =========================
# IMPORTS
# =========================
from app import create_app
from app.extensions import db
from app.models.system.sync_metadata import SyncMetadata
from app.jobs.fetchers import NVDFetcher
from app.services.nvd.bulk_database_service import BulkDatabaseService

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nvd_sync")


# =========================
# DATABASE
# =========================

def check_database_connection():
    """
    Verifica conexão com o banco
    """
    try:
        engine = db.engine
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def ensure_database():
    """
    Garante que as tabelas existam
    """
    logger.info("Ensuring database structure...")

    try:
        db.create_all()  # ✔ compatível com SQLAlchemy 2.x
        logger.info("Tables ensured.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise


def is_sqlite():
    return "sqlite" in str(db.engine.url)


# =========================
# CLEAN
# =========================

def clean_database():
    """
    Limpa dados de forma segura (Postgres + SQLite)
    """
    logger.info("Cleaning vulnerabilities table...")

    try:
        if is_sqlite():
            logger.warning("SQLite detected → using DELETE")
            db.session.execute(text("DELETE FROM vulnerabilities"))
        else:
            db.session.execute(text("TRUNCATE TABLE vulnerabilities CASCADE"))

        db.session.commit()
        logger.info("Database cleaned.")

    except Exception as e:
        logger.error(f"Error cleaning DB: {e}")
        raise


# =========================
# METADATA
# =========================

def reset_metadata():
    logger.info("Resetting metadata...")

    now = datetime.now(timezone.utc).isoformat()

    SyncMetadata.set('nvd_sync_progress_status', 'running')
    SyncMetadata.set('nvd_sync_progress_processed_cves', 0)
    SyncMetadata.set('nvd_sync_progress_total_cves', 0)
    SyncMetadata.set('nvd_sync_progress_inserted', 0)
    SyncMetadata.set('nvd_sync_progress_updated', 0)
    SyncMetadata.set('nvd_sync_progress_errors', 0)
    SyncMetadata.set('nvd_sync_progress_message', 'Initializing')
    SyncMetadata.set('nvd_sync_progress_started_at', now)


# =========================
# FETCH
# =========================

def calculate_total(fetcher, windows):
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

    return total


# =========================
# PROCESS
# =========================

def process_windows(fetcher, db_service, windows):
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

    return processed


# =========================
# MAIN
# =========================

def force_full_sync():
    app = create_app()

    with app.app_context():
        logger.info("=== STARTING FULL NVD SYNC ===")

        # 1. DB CONNECTION
        if not check_database_connection():
            logger.error("Aborting: database not reachable")
            return

        # ⚠️ alerta importante
        if is_sqlite():
            logger.warning("⚠️ Running on SQLite (not recommended for full sync)")

        # 2. TABLES
        ensure_database()

        # 3. CLEAN
        clean_database()

        # 4. METADATA
        reset_metadata()

        # 5. SERVICES
        fetcher = NVDFetcher()
        db_service = BulkDatabaseService()

        db_service.stats = {
            'inserted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }

        # 6. WINDOWS
        start_date = datetime(1999, 1, 1, tzinfo=timezone.utc)
        end_date = datetime.now(timezone.utc)

        windows = fetcher.generate_date_windows(start_date, end_date)

        logger.info(f"Generated {len(windows)} windows")

        # 7. TOTAL
        calculate_total(fetcher, windows)

        SyncMetadata.set('nvd_sync_progress_message', 'Downloading CVEs')

        # 8. PROCESS
        total_processed = process_windows(fetcher, db_service, windows)

        # 9. FINALIZE
        SyncMetadata.set('nvd_sync_progress_status', 'completed')
        SyncMetadata.set('nvd_last_successful_sync', datetime.now(timezone.utc).isoformat())
        SyncMetadata.set('nvd_first_sync_completed', 'true')

        logger.info(f"Sync completed. Total processed: {total_processed}")


if __name__ == "__main__":
    force_full_sync()