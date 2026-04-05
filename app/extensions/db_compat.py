
import os
from sqlalchemy import String
from sqlalchemy.types import JSON

# Detectar se estamos usando SQLite
basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
db_path = os.path.join(basedir, 'instance', 'app.db')
USE_SQLITE = os.environ.get('USE_SQLITE') or not os.environ.get('DB_CORE_HOST') or not os.path.exists(db_path)

if USE_SQLITE:
    # Map Postgres types to generic types for SQLite
    JSONB = JSON
    INET = String(45) # IPv6 max length
    
    # Add other types if needed (e.g. UUID)
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
    # SQLite doesn't have native UUID, usually stored as String or Binary
    # But SQLAlchemy UUID type handles it. 
    # If code uses sqlalchemy.dialects.postgresql.UUID, we map it to generic UUID or String
    from sqlalchemy import Uuid
    UUID = Uuid
    
    # Array type in Postgres -> JSON or String in SQLite?
    # SQLAlchemy has ARRAY but SQLite doesn't support it natively without workarounds.
    # For now assuming simple types.
    ARRAY = JSON
else:
    # Use Postgres types
    from sqlalchemy.dialects.postgresql import JSONB, INET, UUID, ARRAY
