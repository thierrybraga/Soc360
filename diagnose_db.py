import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def check_db(name, host, port, user, password, db_name):
    print(f"\nChecking {name} Database ({host}:{port}/{db_name})...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=db_name
        )
        print(f"✅ Connection successful!")
        
        cur = conn.cursor()
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"Found {len(tables)} tables: {', '.join(tables)}")
        
        if name == "CORE":
            if 'users' in tables:
                cur.execute("SELECT count(*) FROM users")
                count = cur.fetchone()[0]
                print(f"✅ 'users' table exists with {count} records.")
            else:
                print("❌ 'users' table MISSING!")
                
            if 'sync_metadata' in tables:
                cur.execute("SELECT key, value FROM sync_metadata")
                rows = cur.fetchall()
                print(f"ℹ️ SyncMetadata entries: {len(rows)}")
                for row in rows:
                    print(f"   - {row[0]}: {row[1]}")
            else:
                print("❌ 'sync_metadata' table MISSING!")

        elif name == "PUBLIC":
            if 'vulnerabilities' in tables:
                cur.execute("SELECT count(*) FROM vulnerabilities")
                count = cur.fetchone()[0]
                print(f"✅ 'vulnerabilities' table exists with {count} records.")
            else:
                print("❌ 'vulnerabilities' table MISSING!")

        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

# Check Core DB
check_db(
    "CORE",
    os.getenv('DB_CORE_HOST'),
    os.getenv('DB_CORE_PORT'),
    os.getenv('DB_CORE_USER'),
    os.getenv('DB_CORE_PASSWORD'),
    os.getenv('DB_CORE_NAME')
)

# Check Public DB
check_db(
    "PUBLIC",
    os.getenv('DB_PUBLIC_HOST'),
    os.getenv('DB_PUBLIC_PORT'),
    os.getenv('DB_PUBLIC_USER'),
    os.getenv('DB_PUBLIC_PASSWORD'),
    os.getenv('DB_PUBLIC_NAME')
)