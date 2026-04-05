"""
Open-Monitor Database Types
Database type definitions and utilities.
"""
import os
from sqlalchemy import JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB, INET as PG_INET, ARRAY as PG_ARRAY

# Determine SQLite usage from environment and known fallback path
basedir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
db_path = os.path.join(basedir, 'instance', 'app.db')

_db_url = os.getenv('DATABASE_URL', '')
USE_SQLITE = _db_url.startswith('sqlite://') or (not _db_url and os.path.exists(db_path))

# JSON type - use JSONB for PostgreSQL, JSON for SQLite
JSONB = JSON if USE_SQLITE else PG_JSONB

# INET type - use String for SQLite
INET = String(43) if USE_SQLITE else PG_INET

# ARRAY type - use Text for SQLite (store as JSON)
# Note: For SQLite, we need a wrapper class that returns Text() when instantiated
if USE_SQLITE:
    class SQLiteARRAY:
        """Wrapper for ARRAY type in SQLite - returns Text() regardless of item_type."""
        def __init__(self, item_type=None):
            # Ignore the item_type parameter for SQLite, use Text
            self._type = Text()
        
        def __getattr__(self, name):
            return getattr(self._type, name)
    
    ARRAY = SQLiteARRAY
else:
    ARRAY = PG_ARRAY