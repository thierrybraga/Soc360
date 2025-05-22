import io
import os
import sqlite3
import logging
from typing import Any, Dict, List, Optional, Tuple
from flask import Blueprint, render_template, request, send_file, jsonify, redirect
from app.LLMReport import create_pdf_in_memory

# Constantes
TARGET_PRODUCTS = [
    "Aruba",
    "Blockbit",
    "Cisco",
    "Fortinet",
    "Sophos",
    "Meraki",
    "Palo Alto Networks",
    "Trend Micro",
]

# Configuração do logging
logging.basicConfig(level=logging.DEBUG)

# Configuração do Blueprint e do diretório de templates (templates dentro de static)
main_blueprint = Blueprint('main', __name__, template_folder='static/templates')
db_path = os.path.join(os.path.dirname(__file__), "vulnerabilities.db")


def safe_float(value: Any) -> float:
    """
    Converte de forma segura um valor para float.
    Retorna 0.0 em caso de falha.
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


class Database:
    """
    Abstração de acesso ao banco SQLite para operações com vulnerabilidades.
    """
    def __init__(self, db_name: str) -> None:
        self.db_name = db_name

    def get_connection(self) -> sqlite3.Connection:
        """
        Retorna uma conexão com o banco de dados com rows acessíveis por nome de coluna.
        """
        try:
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logging.exception("Error connecting to database: %s", e)
            raise

    def _execute_query(self, query: str, params: List[Any]) -> List[sqlite3.Row]:
        """
        Executa uma query SQL com parâmetros e retorna os resultados.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(params))
                return cursor.fetchall()
        except sqlite3.Error as e:
            logging.exception("Error executing query: %s", e)
            return []

    def fetch_vulnerabilities(
        self,
        year: Optional[str] = None,
        vendor: Optional[str] = None,
        severity: Optional[str] = None,
        page: Optional[int] = None,
        items_per_page: Optional[int] = None,
    ) -> List[sqlite3.Row]:
        """
        Recupera vulnerabilidades com filtros opcionais e paginação.
        """
        query = """
            SELECT cve_id, description, published_date, baseSeverity, cvssScore, reference_links, vendor
            FROM vulnerabilities WHERE 1=1
        """
        params: List[Any] = []

        if year:
            query += " AND published_date LIKE ?"
            params.append(f"{year}%")
        if vendor:
            query += " AND vendor = ?"
            params.append(vendor)
        if severity:
            query += " AND lower(baseSeverity) = ?"
            params.append(severity.lower())

        # Aplica paginação se nenhum filtro for especificado
        if not (year or vendor or severity) and page is not None and items_per_page is not None:
            query += " LIMIT ? OFFSET ?"
            offset = (page - 1) * items_per_page
            params.extend([items_per_page, offset])

        return self._execute_query(query, params)

    def _fetch_distinct(self, cursor: sqlite3.Cursor, column: str) -> List[str]:
        """
        Retorna os valores distintos de uma coluna.
        """
        cursor.execute(f"SELECT DISTINCT {column} FROM vulnerabilities")
        return [row[0] for row in cursor.fetchall()]

    def fetch_filters(self) -> Tuple[List[str], List[str]]:
        """
        Recupera os filtros disponíveis: vendors e severities.
        O vendors é definido por TARGET_PRODUCTS.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                severities = self._fetch_distinct(cursor, "baseSeverity")
            return TARGET_PRODUCTS, severities
        except Exception as e:
            logging.exception("Error fetching filters: %s", e)
            return TARGET_PRODUCTS, []

    def fetch_vulnerability_by_id(self, cve_id: str) -> Optional[sqlite3.Row]:
        """
        Recupera uma vulnerabilidade específica pelo seu CVE ID.
        """
        query = """
            SELECT cve_id, description, risks, vendor, reference_links, baseSeverity, published_date
            FROM vulnerabilities WHERE cve_id = ?
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, (cve_id,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            logging.exception("Error fetching vulnerability %s: %s", cve_id, e)
            return None


def serialize_vulnerability(vuln: sqlite3.Row) -> Dict[str, Any]:
    """
    Serializa uma row de vulnerabilidade para um dicionário.
    """
    return {
        "CVE ID": vuln["cve_id"],
        "Description": vuln["description"],
        "Published Date": vuln["published_date"],
        "Severity": vuln["baseSeverity"],
        "CVSS Score": vuln["cvssScore"],
        "reference_links": vuln["reference_links"],
        "Vendor": vuln["vendor"],
    }


def format_vulnerabilities(vulnerabilities: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """
    Formata as rows de vulnerabilidade para exibição na página principal.
    """
    return [serialize_vulnerability(v) for v in vulnerabilities]


def count_severity(vulnerabilities: List[sqlite3.Row]) -> Dict[str, int]:
    """
    Conta a distribuição de severidades entre as vulnerabilidades.
    """
    return {
        "low": sum(1 for vuln in vulnerabilities if vuln["baseSeverity"].lower() == "low"),
        "medium": sum(1 for vuln in vulnerabilities if vuln["baseSeverity"].lower() == "medium"),
        "high": sum(1 for vuln in vulnerabilities if vuln["baseSeverity"].lower() == "high"),
        "critical": sum(1 for vuln in vulnerabilities if vuln["baseSeverity"].lower() == "critical"),
    }


def count_top_vendors(vulnerabilities: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """
    Conta o número de vulnerabilidades por vendor.
    """
    vendor_set = {vuln["vendor"] for vuln in vulnerabilities}
    return [
        {"name": vendor, "quantity": sum(1 for vuln in vulnerabilities if vuln["vendor"] == vendor)}
        for vendor in vendor_set
    ]


def process_vulnerability_data(vulnerabilities: List[sqlite3.Row]) -> Dict[str, Any]:
    """
    Processa os dados das vulnerabilidades para a dashboard.
    Inclui média do CVSS, distribuição de severidades, histogramas e histórico diário.
    """
    total_vulnerabilities = len(vulnerabilities)
    avg_cvss_score = (
        sum(safe_float(vuln["cvssScore"]) for vuln in vulnerabilities) / total_vulnerabilities
        if total_vulnerabilities else 0
    )
    severity_distribution = count_severity(vulnerabilities)
    top_vendors = count_top_vendors(vulnerabilities)
    cvss_bins = [0, 0, 0, 0, 0]

    for vuln in vulnerabilities:
        score = safe_float(vuln["cvssScore"])
        if score <= 2:
            cvss_bins[0] += 1
        elif score <= 4:
            cvss_bins[1] += 1
        elif score <= 6:
            cvss_bins[2] += 1
        elif score <= 8:
            cvss_bins[3] += 1
        else:
            cvss_bins[4] += 1

    # Construção do histórico de CVEs por dia (YYYY-MM-DD)
    history: Dict[str, int] = {}
    for vuln in vulnerabilities:
        date_str = vuln["published_date"][:10]
        history[date_str] = history.get(date_str, 0) + 1
    sorted_dates = sorted(history.keys())
    history_labels = sorted_dates
    history_data = [history[date] for date in sorted_dates]

    return {
        "totalVulnerabilities": total_vulnerabilities,
        "avgCvssScore": avg_cvss_score,
        "severity": severity_distribution,
        "topVendors": top_vendors,
        "vendors": TARGET_PRODUCTS,
        "cvssScoreDistribution": cvss_bins,
        "cveHistoryLabels": history_labels,
        "cveHistoryData": history_data
    }


# Rotas da API e Renderização de Templates

@main_blueprint.route('/api/vulnerabilities', methods=['GET'])
def api_vulnerabilities() -> Any:
    """
    Retorna as vulnerabilidades como JSON, aplicando filtros e paginação se necessário.
    """
    year = request.args.get('year')
    vendor_filter = request.args.get('vendor')
    severity = request.args.get('severity')
    page = request.args.get('page', type=int)
    items_per_page = request.args.get('items_per_page', type=int)

    try:
        db = Database(db_path)
        vulnerabilities = db.fetch_vulnerabilities(year, vendor_filter, severity, page, items_per_page)
        processed_vulns = [serialize_vulnerability(v) for v in vulnerabilities]
        _, severities = db.fetch_filters()

        return jsonify({
            "vulnerabilities": processed_vulns,
            "totalVulnerabilities": len(processed_vulns),
            "vendors": TARGET_PRODUCTS,
            "severities": severities,
        })
    except Exception as e:
        logging.exception("Error fetching vulnerabilities: %s", e)
        return jsonify({"error": "Error accessing vulnerabilities"}), 500


@main_blueprint.route('/generate_report', methods=['GET'])
def generate_report() -> Any:
    """
    Gera e retorna um relatório em PDF para uma vulnerabilidade específica.
    """
    cve_id = request.args.get('cve_id')
    if not cve_id:
        return "CVE ID not provided.", 400

    try:
        db = Database(db_path)
        data = db.fetch_vulnerability_by_id(cve_id)
        if data:
            pdf_data = create_pdf_in_memory(data)
            return send_file(
                io.BytesIO(pdf_data),
                as_attachment=True,
                download_name=f"relatorio_vulnerabilidade_{cve_id}.pdf",
                mimetype="application/pdf"
            )
        else:
            return "CVE ID not found.", 404
    except Exception as e:
        logging.exception("Error generating report for %s: %s", cve_id, e)
        return "Error generating report.", 500


@main_blueprint.route('/analytics', methods=['GET'])
def analytics() -> Any:
    """
    Renderiza a página de Analytics.
    """
    return render_template('analytics.html')


@main_blueprint.route('/contact', methods=['GET'])
def contact() -> Any:
    """
    Renderiza a página de Contact.
    """
    return render_template('newslatter.html')


@main_blueprint.route('/about', methods=['GET'])
def about() -> Any:
    """
    Renderiza a página de About.
    """
    return render_template('about.html')


@main_blueprint.route('/api/cves', methods=['GET'])
def api_get_cves() -> Any:
    """
    Retorna os dados processados das vulnerabilidades para a dashboard.
    """
    vendor_filter = request.args.get('vendor', '')
    db = Database(db_path)

    try:
        vulnerabilities = db.fetch_vulnerabilities(vendor=vendor_filter)
        data = process_vulnerability_data(vulnerabilities)
        data["vendors"] = TARGET_PRODUCTS
        return jsonify(data)
    except Exception as e:
        logging.exception("Error fetching dashboard data: %s", e)
        return jsonify({"error": "Error accessing dashboard data"}), 500


@main_blueprint.route('/', methods=['GET'])
def index() -> Any:
    """
    Renderiza a página principal com filtros e lista de vulnerabilidades.
    """
    year = request.args.get('year')
    vendor_filter = request.args.get('vendor')
    severity = request.args.get('severity')

    try:
        db = Database(db_path)
        vulnerabilities = db.fetch_vulnerabilities(year, vendor_filter, severity)
        processed_vulns = format_vulnerabilities(vulnerabilities)
        _, severities = db.fetch_filters()
        return render_template('index.html', vulnerabilities=processed_vulns, vendors=TARGET_PRODUCTS, severities=severities)
    except Exception as e:
        logging.exception("Error fetching vulnerabilities for the homepage: %s", e)
        return "Error loading the homepage.", 500


@main_blueprint.route('/redirect_reference', methods=['GET'])
def redirect_reference() -> Any:
    """
    Redireciona para uma URL de referência fornecida via parâmetro 'link'.
    Adiciona 'http://' se necessário.
    """
    link = request.args.get('link', '')
    if link and not link.startswith('http'):
        link = 'http://' + link
    if link:
        return redirect(link)
    return "Invalid link", 400
