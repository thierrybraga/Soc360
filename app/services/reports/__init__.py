"""Reports AI generation services."""
from app.services.reports.ai_report_service import AIReportService, generate_ai_report
from app.services.reports.pdf_service import (
    generate_report_pdf,
    ensure_report_pdf,
    build_report_html,
    render_pdf_bytes,
)

__all__ = [
    'AIReportService',
    'generate_ai_report',
    'generate_report_pdf',
    'ensure_report_pdf',
    'build_report_html',
    'render_pdf_bytes',
]
