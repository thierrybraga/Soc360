import logging
import subprocess
import sys
import os
from time import sleep

from sqlalchemy import inspect

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app, db
from app.models.system.sync_metadata import SyncMetadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto_sync")

def database_exists_and_ready():
    """
    Verifica se o banco está acessível e tabelas existem.
    """
    try:
        # Testa conexão
        engine = db.get_engine()
        conn = engine.connect()
        conn.close()

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if not tables:
            logger.warning("Database connected but no tables found.")
            return False

        logger.info(f"Database OK. Tables found: {tables}")
        return True

    except Exception as e:
        logger.error(f"Database not ready: {e}")
        return False


def ensure_tables():
    """
    Garante que todas as tabelas existam
    """
    try:
        logger.info("Ensuring database tables exist...")
        db.create_all()
        db.create_all(bind='public')
        logger.info("Tables ensured.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")


def should_run_sync():
    """
    Decide se deve rodar sync
    """
    try:
        value = SyncMetadata.get_value('nvd_first_sync_completed')

        if value == 'true':
            logger.info("Sync already completed previously.")
            return False

        logger.info("First sync NOT completed.")
        return True

    except Exception as e:
        logger.warning(f"Metadata not found or error: {e}")
        return True  # força sync se metadata falhar


def run_sync():
    """
    Executa o sync completo
    """
    logger.info("Starting full CVE sync...")

    process = subprocess.Popen(
        [sys.executable, 'force_sync.py'],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    logger.info(f"Sync process started (PID {process.pid})")

    return_code = process.wait()

    if return_code == 0:
        logger.info("Sync completed successfully.")
    else:
        logger.error(f"Sync failed with code {return_code}")


def main():
    sleep(5)  # aguarda DB subir

    app = create_app()

    with app.app_context():
        # 1. Verifica DB
        if not database_exists_and_ready():
            logger.warning("Database not ready. Trying to create tables...")
            ensure_tables()

        # 2. Garante tabelas
        ensure_tables()

        # 3. Decide se roda sync
        if should_run_sync():
            run_sync()
        else:
            logger.info("Skipping sync.")


if __name__ == "__main__":
    main()