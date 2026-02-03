from dotenv import load_dotenv
import os
import psycopg2

load_dotenv()

host = os.environ.get('DB_PUBLIC_HOST', 'localhost')
port = os.environ.get('DB_PUBLIC_PORT', '5433')
dbname = os.environ.get('DB_PUBLIC_NAME', 'openmonitor_public')
user = os.environ.get('DB_PUBLIC_USER', 'openmonitor')
password = os.environ.get('DB_PUBLIC_PASSWORD', 'password')

print(f"Connecting to {dbname} at {host}:{port}...")

try:
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port
    )
    cur = conn.cursor()
    
    print("\nTable 'references' columns:")
    cur.execute("""
        SELECT column_name, data_type, udt_name
        FROM information_schema.columns 
        WHERE table_name = 'references'
    """)
    rows = cur.fetchall()
    if not rows:
        print("Table 'references' NOT FOUND!")
    else:
        for row in rows:
            print(f"- {row[0]}: {row[1]} (udt: {row[2]})")
            
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
