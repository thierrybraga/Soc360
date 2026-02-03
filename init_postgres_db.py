import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

load_dotenv()

def create_database(db_name, user, password, host, port):
    # Connect to default 'postgres' database to create new databases
    try:
        # Try connecting with the specific user first (if they have create db privileges)
        # Or we might need to connect as 'postgres' user. 
        # For now, let's try with the config user.
        con = psycopg2.connect(
            dbname='postgres',
            user=user,
            host=host,
            password=password,
            port=port
        )
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        
        # Check if db exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cur.fetchone()
        
        if not exists:
            print(f"Creating database {db_name}...")
            cur.execute(f"CREATE DATABASE {db_name}")
            print(f"Database {db_name} created successfully.")
        else:
            print(f"Database {db_name} already exists.")
            
        cur.close()
        con.close()
        return True
        
    except Exception as e:
        print(f"Error creating database {db_name}: {e}")
        return False

def init_postgres():
    print("Initializing PostgreSQL databases...")
    
    # Core DB
    core_host = os.getenv('DB_CORE_HOST', 'localhost')
    core_port = os.getenv('DB_CORE_PORT', '5432')
    core_user = os.getenv('DB_CORE_USER', 'openmonitor')
    core_pass = os.getenv('DB_CORE_PASSWORD', 'password')
    core_db = os.getenv('DB_CORE_NAME', 'openmonitor_core')
    
    # Public DB
    public_host = os.getenv('DB_PUBLIC_HOST', 'localhost')
    public_port = os.getenv('DB_PUBLIC_PORT', '5432')
    public_user = os.getenv('DB_PUBLIC_USER', 'openmonitor')
    public_pass = os.getenv('DB_PUBLIC_PASSWORD', 'password')
    public_db = os.getenv('DB_PUBLIC_NAME', 'openmonitor_public')
    
    # Attempt to create Core DB
    if not create_database(core_db, core_user, core_pass, core_host, core_port):
        print("Failed to create Core DB. Please ensure PostgreSQL is running and the user has permissions.")
        # If authentication failed, maybe we need 'postgres' user?
        # But we don't have that password. We'll rely on the user seeing the error.

    # Attempt to create Public DB
    if not create_database(public_db, public_user, public_pass, public_host, public_port):
        print("Failed to create Public DB.")

if __name__ == "__main__":
    init_postgres()
