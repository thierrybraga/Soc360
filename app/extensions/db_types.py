"""
SOC360 Database Types
Database type definitions and utilities.
"""
import json
import os
from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, INET as PG_INET, ARRAY as PG_ARRAY
from sqlalchemy.types import TypeDecorator

# Determine SQLite usage from environment and known fallback path
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(basedir, 'instance', 'app.db')

_db_url = os.getenv('DATABASE_URL', '')
# Use PostgreSQL-specific types only when explicitly connecting to Postgres.
# Default to SQLite-compatible types for local dev (empty DATABASE_URL).
USE_SQLITE = not _db_url.startswith(('postgresql', 'postgres'))

# JSON type - use JSONB for PostgreSQL, JSON for SQLite
JSONB = JSON if USE_SQLITE else PG_JSONB

# INET type - use String for SQLite
INET = String(43) if USE_SQLITE else PG_INET

# ARRAY type - proper TypeDecorator for SQLite, stores arrays as JSON text
if USE_SQLITE:
    class JSONEncodedArray(TypeDecorator):
        """Stores a Python list as a JSON-encoded TEXT string for SQLite compatibility.

        Accepts an optional ``item_type`` argument (like PostgreSQL ARRAY) so it can
        be used as a drop-in replacement: ``ARRAY(String(255))``.
        """
        impl = Text
        cache_ok = True

        def __init__(self, item_type=None, **kwargs):
            # item_type is ignored; all values serialised as JSON text
            super().__init__()

        def process_bind_param(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, list):
                return json.dumps(value)
            return value  # pass-through if already a string (e.g. during migrations)

        def process_result_value(self, value, dialect):
            if value is None:
                return None
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (TypeError, ValueError):
                    return value
            return value  # already a list (shouldn't happen in SQLite, but safe)

    ARRAY = JSONEncodedArray
else:
    ARRAY = PG_ARRAY