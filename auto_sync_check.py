import logging
import subprocess
import sys
import os
from time import sleep

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app
from app.models.system.sync_metadata import SyncMetadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auto_sync_check")

def check_and_run_sync():
    """
    Checks if the first NVD sync has been completed.
    If not, triggers the force_full_nvd_sync.py script.
    """
    app = create_app()
    with app.app_context():
        try:
            # Check metadata
            is_completed = SyncMetadata.get_value('nvd_first_sync_completed')
            
            if is_completed == 'true':
                logger.info("NVD Sync already completed. Skipping auto-sync.")
                return

            logger.info("First NVD Sync pending (nvd_first_sync_completed != true).")
            logger.info("Starting forced full NVD sync...")

            # Run force_full_nvd_sync.py as a subprocess
            # We use the same python executable
            process = subprocess.Popen(
                [sys.executable, 'force_full_nvd_sync.py'],
                stdout=sys.stdout,
                stderr=sys.stderr
            )
            
            logger.info(f"Sync process started with PID {process.pid}")
            
            # We do NOT wait for it if we want this script to exit quickly,
            # BUT the entrypoint calls this in background anyway.
            # To ensure logs are captured, we can wait.
            # Since entrypoint will background *this* script, we can block here.
            return_code = process.wait()
            
            if return_code == 0:
                logger.info("Sync process completed successfully.")
            else:
                logger.error(f"Sync process failed with return code {return_code}")

        except Exception as e:
            logger.error(f"Error in auto_sync_check: {e}")

if __name__ == "__main__":
    # Wait a bit for DB to be fully ready if called immediately after init
    sleep(5)
    check_and_run_sync()