import sqlite3
import os
import logging

# Configuração básica do logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

DATABASE_FILE = os.path.join(os.path.dirname(__file__), "vulnerabilities.db")

def get_connection():
    # É possível configurar opções adicionais, se necessário.
    return sqlite3.connect(DATABASE_FILE)

def create_table():
    with get_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS vulnerabilities (
                cve_id TEXT PRIMARY KEY,
                description TEXT,
                published_date TEXT,
                baseSeverity TEXT,
                cvssScore REAL,
                reference_links TEXT,
                vendor TEXT,
                risks TEXT
            )
        ''')

def validate_vulnerability(vuln):
    """Valida e normaliza os dados da vulnerabilidade."""
    required_keys = ['cve_id', 'description', 'published_date', 'baseSeverity', 'cvssScore', 'references', 'vendor']
    for key in required_keys:
        if key not in vuln:
            logging.error(f"Chave '{key}' faltando na vulnerabilidade: {vuln}")
            return None
    try:
        vuln['cvssScore'] = float(vuln['cvssScore'])
    except (ValueError, TypeError):
        logging.error(f"Valor inválido para cvssScore em vulnerabilidade: {vuln}")
        return None
    # Aqui podem ser adicionadas outras validações, como formato de data, tamanho dos campos, etc.
    return vuln

def check_cve_exists(conn, cve_id):
    try:
        cursor = conn.execute("SELECT EXISTS(SELECT 1 FROM vulnerabilities WHERE cve_id = ?)", (cve_id,))
        return cursor.fetchone()[0] == 1
    except sqlite3.Error as e:
        logging.error(f"Erro ao verificar CVE ({cve_id}): {e}")
        return False

def get_cve(conn, cve_id):
    try:
        cursor = conn.execute("SELECT * FROM vulnerabilities WHERE cve_id = ?", (cve_id,))
        row = cursor.fetchone()
        if row:
            return {
                "cve_id": row[0],
                "description": row[1],
                "published_date": row[2],
                "baseSeverity": row[3],
                "cvssScore": row[4],
                "reference_links": row[5],
                "vendor": row[6],
                "risks": row[7]
            }
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter CVE ({cve_id}): {e}")
    return None

def update_cve(conn, cve):
    try:
        conn.execute('''
            UPDATE vulnerabilities
            SET description = ?, published_date = ?, baseSeverity = ?, cvssScore = ?, 
                reference_links = ?, vendor = ?, risks = ?
            WHERE cve_id = ?
        ''', (
            cve['description'],
            cve['published_date'],
            cve['baseSeverity'],
            cve['cvssScore'],
            ', '.join(cve['references']),
            cve['vendor'],
            cve.get('risks', None),
            cve['cve_id']
        ))
    except sqlite3.Error as e:
        logging.error(f"Erro ao atualizar CVE ({cve['cve_id']}): {e}")

def populate_database(data):
    try:
        with get_connection() as conn:
            for vuln in data.get('vulnerabilities', []):
                vuln = validate_vulnerability(vuln)
                if vuln is None:
                    continue  # Pula vulnerabilidades com dados inválidos

                cve_id = vuln['cve_id']
                if not check_cve_exists(conn, cve_id):
                    conn.execute('''
                        INSERT INTO vulnerabilities (
                            cve_id, description, published_date, baseSeverity, cvssScore, 
                            reference_links, vendor, risks
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        cve_id,
                        vuln['description'],
                        vuln['published_date'],
                        vuln['baseSeverity'],
                        vuln['cvssScore'],
                        ', '.join(vuln['references']),
                        vuln['vendor'],
                        vuln.get('risks', None)
                    ))
                    logging.info(f"CVE {cve_id} inserido no banco.")
                else:
                    existing = get_cve(conn, cve_id)
                    # Atualiza o registro se houver alterações relevantes
                    if existing and (existing["baseSeverity"] != vuln['baseSeverity'] or existing["cvssScore"] != vuln['cvssScore']):
                        update_cve(conn, vuln)
                        logging.info(f"CVE {cve_id} atualizado no banco.")
            conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Erro ao popular banco de dados: {e}")

def get_latest_cve_date(vendor):
    try:
        with get_connection() as conn:
            cursor = conn.execute('''
                SELECT MAX(published_date) FROM vulnerabilities
                WHERE vendor = ? AND published_date >= '2024-01-01'
            ''', (vendor,))
            result = cursor.fetchone()[0]
            return result
    except sqlite3.Error as e:
        logging.error(f"Erro ao obter última data de CVE para fornecedor ({vendor}): {e}")
        return None

# Exemplo de uso:
if __name__ == "__main__":
    create_table()
    # Suponha que 'data' seja um dicionário contendo a lista de vulnerabilidades
    # data = {"vulnerabilities": [...]}
    # populate_database(data)
