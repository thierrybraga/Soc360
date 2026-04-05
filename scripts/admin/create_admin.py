
import sys
import os
import logging
from dotenv import load_dotenv

# Forçar uso do SQLite
os.environ['USE_SQLITE'] = '1'

load_dotenv()

from app import create_app, db
from app.models.auth.role import Role
from app.models.auth.user import User
from app.models.system.sync_metadata import SyncMetadata

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_admin")

def init_system():
    app = create_app()
    with app.app_context():
        logger.info("Initializing system configuration...")

        # 1. Create Roles
        logger.info("Checking roles...")
        for role_name, role_data in Role.DEFAULT_ROLES.items():
            role = Role.query.filter_by(name=role_name).first()
            if not role:
                logger.info(f"Creating role: {role_name}")
                role = Role(
                    name=role_name,
                    description=role_data['description'],
                    permissions=role_data['permissions']
                )
                db.session.add(role)
            else:
                logger.debug(f"Role already exists: {role_name}")
        db.session.commit()

        # 2. Create Admin User
        logger.info("Checking admin user...")
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            logger.info("Creating admin user...")
            admin_role = Role.query.filter_by(name=Role.ADMIN).first()
            admin_user = User(
                username='admin',
                email='admin@openmonitor.local',
                is_admin=True,
                is_active=True,
                email_confirmed=True
            )
            admin_user.set_password('admin123')
            if admin_role:
                admin_user.roles.append(admin_role)
            db.session.add(admin_user)
            db.session.commit()
            logger.info("Admin user created successfully.")
            logger.info("Username: admin")
            logger.info("Password: admin123")
        else:
            logger.info("Admin user already exists")

        # 3. Trigger Initial Sync Logic
        try:
            logger.info("Setting initial sync status...")
            # Ensure metadata exists
            if not SyncMetadata.get_value('nvd_first_sync_completed'):
                 SyncMetadata.set_value('nvd_first_sync_completed', 'false')
                 SyncMetadata.set_value('nvd_sync_progress_status', 'pending')
                 logger.info("Sync status set to pending.")
        except Exception as e:
            logger.error(f"Error setting sync status: {e}")

if __name__ == "__main__":
    init_system()
