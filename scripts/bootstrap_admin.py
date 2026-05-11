#!/usr/bin/env python3
"""
Bootstrap admin user on first deploy (idempotent).

- Creates the `admin` user if it doesn't exist.
- Initial password from env var `ADMIN_INITIAL_PASSWORD`; if not set,
  generates a random one and prints it ONCE to stdout for the operator.
- Subsequent runs are no-ops if the admin already exists.

Safe to run on every container startup.
"""
import os
import secrets
import sys

from app import create_app
from app.extensions import db
from app.models.auth.user import User


def main():
    app = create_app()
    with app.app_context():
        existing = User.query.filter_by(username='admin').first()
        if existing:
            # Already bootstrapped — nothing to do.
            print('[bootstrap] admin user already exists, skipping')
            return 0

        password = os.environ.get('ADMIN_INITIAL_PASSWORD')
        generated = False
        if not password:
            password = secrets.token_urlsafe(16)
            generated = True

        admin = User(
            username='admin',
            email=os.environ.get('ADMIN_EMAIL', 'admin@soc360.local'),
            is_active=True,
            is_admin=True,
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()

        if generated:
            # Print to stdout so it's captured in container logs ONLY ONCE.
            print('=' * 60)
            print('[bootstrap] ADMIN USER CREATED')
            print(f'[bootstrap]   username: admin')
            print(f'[bootstrap]   password: {password}')
            print('[bootstrap] STORE THIS PASSWORD — it will NOT be shown again.')
            print('[bootstrap] Change it immediately via Account Settings.')
            print('=' * 60)
        else:
            print('[bootstrap] admin user created with ADMIN_INITIAL_PASSWORD')

        return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        # Non-fatal — log to stderr so deploy continues even if bootstrap fails
        print(f'[bootstrap] error: {e}', file=sys.stderr)
        sys.exit(0)
