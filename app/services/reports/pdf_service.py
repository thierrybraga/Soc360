"""
PDF generation service for reports.

Renders a complete PDF containing:
- Report header (title, type, period, generation date, model)
- Inventory summary (registered assets, coverage)
- AI-generated narrative (markdown -> HTML)
- Structured data tables per report type (affected assets, timelines, ranking)

Uses WeasyPrint (installed via requirements.txt). Output is saved to
``REPORTS_DIR`` and the absolute path is returned.
"""
import logging
import os
from datetime import datetime
from io import BytesIO
from typing import Optional

from flask import current_app, render_template

logger = logging.getLogger(__name__)


def _markdown_to_html(md_text: str) -> str:
    """Converte markdown em HTML compatível com WeasyPrint."""
    if not md_text:
        return ""
    try:
        import markdown as md_lib
        return md_lib.markdown(
            md_text,
            extensions=['tables', 'fenced_code', 'sane_lists'],
        )
    except ImportError:
        import html
        escaped = html.escape(md_text)
        return f"<pre>{escaped}</pre>"


def _ensure_reports_dir() -> str:
    """Garante que o diretório de relatórios exista e retorna o caminho absoluto."""
    reports_dir = current_app.config.get('REPORTS_DIR', '/app/reports')
    if reports_dir in ('/app/reports', '\\app\\reports') or not os.path.isabs(reports_dir):
        if not os.path.exists(reports_dir):
            reports_dir = os.path.abspath(
                os.path.join(current_app.root_path, '..', 'reports')
            )
    try:
        os.makedirs(reports_dir, exist_ok=True)
    except (OSError, PermissionError):
        fallback = os.path.abspath(os.path.join(current_app.root_path, '..', 'reports'))
        os.makedirs(fallback, exist_ok=True)
        reports_dir = fallback
    return reports_dir


def _safe_filename(text: str) -> str:
    import re
    name = re.sub(r'[^\w\-. ]', '_', text or 'report').strip().replace(' ', '_')
    return name[:120] or 'report'


def _normalize_recommendations(recs):
    """Normaliza ``ai_recommendations`` em lista de dicts {title, description, priority}."""
    if not recs:
        return []
    normalized = []
    for rec in recs:
        if isinstance(rec, dict):
            description = rec.get('description') or rec.get('text') or rec.get('body') or ''
            title = rec.get('title')
            if not isinstance(title, str):
                title = ''
            if not title and description:
                title = description.split('.')[0][:120]
            normalized.append({
                'title': title.strip(),
                'description': (description or '').strip(),
                'priority': rec.get('priority') or '-',
            })
        elif isinstance(rec, str):
            text = rec.strip()
            if not text:
                continue
            normalized.append({
                'title': text.split('.')[0][:120],
                'description': text,
                'priority': '-',
            })
        else:
            text = str(rec).strip()
            if text:
                normalized.append({'title': text[:120], 'description': text, 'priority': '-'})
    return normalized


def build_report_html(report) -> str:
    """Renderiza o HTML completo do relatório (para PDF ou preview)."""
    narrative_html = _markdown_to_html(report.ai_summary or '')
    data = report.data or {}
    recommendations = _normalize_recommendations(report.ai_recommendations)

    context = {
        'report': report,
        'narrative_html': narrative_html,
        'data': data,
        'recommendations': recommendations,
        'generated_at': report.ai_generated_at or report.generation_completed_at or datetime.utcnow(),
        'assets_overview': data.get('assets_overview') or [],
        'total_assets': data.get('total_assets', 0),
        'assets_with_vulns': data.get('assets_with_vulns', 0),
        'period_days': (report.filters or {}).get('time_range_days', 30),
    }
    return render_template('reports/pdf.html', **context)


def render_pdf_bytes(report) -> bytes:
    """Renderiza o PDF em bytes (em memória) usando WeasyPrint."""
    from weasyprint import HTML

    html_string = build_report_html(report)
    # base_url='.' permite que WeasyPrint resolva fontes/imagens relativas
    pdf = HTML(string=html_string, base_url='.').write_pdf()
    return pdf


def generate_report_pdf(report) -> str:
    """
    Gera o PDF e persiste em REPORTS_DIR.

    Atualiza ``report.file_path`` e ``report.file_size`` e retorna o caminho
    absoluto do arquivo.
    """
    from app.extensions import db

    reports_dir = _ensure_reports_dir()
    filename = f"report_{report.id}_{_safe_filename(report.title)}.pdf"
    out_path = os.path.join(reports_dir, filename)

    pdf_bytes = render_pdf_bytes(report)
    with open(out_path, 'wb') as fh:
        fh.write(pdf_bytes)

    report.file_path = out_path
    report.file_size = len(pdf_bytes)
    db.session.commit()
    logger.info("PDF gerado para report %s em %s (%d bytes)", report.id, out_path, len(pdf_bytes))
    return out_path


def ensure_report_pdf(report) -> Optional[str]:
    """
    Garante que o PDF do relatório existe.

    - Se ``report.file_path`` existe no disco, retorna direto.
    - Caso contrário, gera o PDF sob demanda.
    - Retorna ``None`` se o relatório ainda não tem conteúdo de IA.
    """
    if not (report.ai_summary or report.data):
        return None
    if report.file_path and os.path.exists(report.file_path):
        return report.file_path
    return generate_report_pdf(report)
