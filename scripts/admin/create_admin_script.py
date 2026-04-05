import sys

# Add /app to sys.path if not present
if '/app' not in sys.path:
    sys.path.append('/app')

from app import create_app
from app.extensions import db
from app.models.auth import User, Role

app = create_app()

with app.app_context():
    print("Initializing roles...")
    Role.create_default_roles()

    admin_role = Role.get_by_name('ADMIN')
    if not admin_role:
        print("Error: ADMIN role not found even after initialization.")
        sys.exit(1)

    username = 'admin'
    email = 'admin@open-monitor.local'
    password = 'Admin123!'

    user = User.get_by_username(username)
    if not user:
        print(f"Creating admin user: {username}")
        user = User(
            username=username,
            email=email,
            is_admin=True,
            is_active=True,
            email_confirmed=True
        )
        user.set_password(password)
        user.roles.append(admin_role)
        db.session.add(user)
        db.session.commit()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")
        # Ensure role
        if not user.has_role('ADMIN'):
            user.roles.append(admin_role)
            db.session.commit()
            print("Added ADMIN role to existing user.")
