
import os
import logging

# Set environment to use SQLite BEFORE imports
os.environ['USE_SQLITE'] = '1'
os.environ['FLASK_ENV'] = 'development'
os.environ['FLASK_DEBUG'] = '1'

from app import create_app, db
from init_admin import init_system

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup_local")


def setup():
    logger.info("Setting up local SQLite environment...")
    app = create_app('development')
    
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        logger.info("Tables created.")
        
        logger.info("Initializing admin user and roles...")
        # We need to mock the logger in init_admin or just let it run
        try:
            init_system()
        except Exception as e:
            logger.error(f"Error in init_system: {e}")
            # If init_system fails, we might still want to proceed if tables are there
            pass
            
    logger.info("Setup complete. You can now run the app with: set USE_SQLITE=1 && flask run")

if __name__ == "__main__":
    setup()
