import sqlite3
import os

# Caminho para o banco de dados
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'instance', 'vulnerabilities.db')

# Definição do schema esperado (simplificado, mas você pode expandir com base no dump anterior)
EXPECTED_SCHEMA = {
    "users": {
        "columns": {
            "id": "INTEGER PRIMARY KEY",
            "username": "VARCHAR(50) NOT NULL",
            "email": "VARCHAR(255) NOT NULL",
            "password_hash": "VARCHAR(128) NOT NULL",
            "is_active": "BOOLEAN NOT NULL",
            "is_admin": "BOOLEAN NOT NULL",
            "created_at": "DATETIME NOT NULL",
            "updated_at": "DATETIME NOT NULL"
        },
        "foreign_keys": []
    },
    "assets": {
        "columns": {
            "id": "INTEGER PRIMARY KEY",
            "name": "VARCHAR(100) NOT NULL",
            "ip_address": "VARCHAR(45) NOT NULL",
            "status": "VARCHAR(50) NOT NULL",
            "owner_id": "INTEGER",
            "created_at": "DATETIME NOT NULL",
            "updated_at": "DATETIME NOT NULL"
        },
        "foreign_keys": [("owner_id", "users", "id")]
    },
    # Adicione aqui as outras tabelas seguindo o modelo extraído anteriormente...
}


def get_current_schema(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    fks = [(row[3], row[2], row[4]) for row in cursor.fetchall()]

    return columns, fks


def sync_schema(conn):
    cursor = conn.cursor()

    for table, spec in EXPECTED_SCHEMA.items():
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        exists = cursor.fetchone()

        if not exists:
            print(f"[INFO] Criando tabela {table}...")
            columns_def = ", ".join([f"{col} {ctype}" for col, ctype in spec["columns"].items()])
            fk_defs = ", ".join([f"FOREIGN KEY({col}) REFERENCES {ref_table}({ref_col})" for col, ref_table, ref_col in spec["foreign_keys"]])
            sql = f"CREATE TABLE {table} ({columns_def}{', ' + fk_defs if fk_defs else ''});"
            cursor.execute(sql)
        else:
            current_cols, current_fks = get_current_schema(cursor, table)

            # Verificar colunas faltantes
            for col, ctype in spec["columns"].items():
                if col not in current_cols:
                    print(f"[FIX] Adicionando coluna {col} em {table}...")
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}")

            # (Obs: Ajustar tipos e FKs requer recriar tabela, não apenas ALTER)

    conn.commit()


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    sync_schema(conn)
    conn.close()
    print("[DONE] Estrutura do banco sincronizada!")
