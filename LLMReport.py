import io
import re
import json
import markdown
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from app.llmconnectorOLD import get_risk_analysis


def create_pdf_in_memory(data):
    if len(data) < 7:
        raise ValueError("Dados insuficientes para gerar o relatório. Esperado ao menos 7 campos.")

    cve_id, description, risks, vendor, reference_links, base_severity, published_date = data[:7]
    generated_on = datetime.now().strftime("%d/%m/%Y %H:%M")

    if not risks or not risks.strip():
        try:
            risks = get_risk_analysis(cve_id)
        except ImportError as e:
            raise ImportError("Erro ao importar 'get_risk_analysis'. Verifique o módulo llmconnector.") from e

    try:
        formatted_date = datetime.strptime(published_date, "%Y-%m-%dT%H:%M:%S.%f").strftime("%d/%m/%y")
    except ValueError:
        formatted_date = published_date  # fallback

    styles = define_styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=30, leftMargin=30,
                            topMargin=40, bottomMargin=30)

    content = build_content(
        cve_id, description, risks, vendor, reference_links,
        base_severity, formatted_date, generated_on, styles
    )

    doc.build(content, onFirstPage=add_page_decorations, onLaterPages=add_page_decorations)
    return buffer.getvalue()


def define_styles():
    return {
        "normal": ParagraphStyle("Normal", fontSize=10, leading=14, fontName="Helvetica"),
        "title": ParagraphStyle("Title", fontSize=18, alignment=1, spaceAfter=14,
                                fontName="Helvetica-Bold", leading=22),
        "section_title": ParagraphStyle("SectionTitle", fontSize=14, spaceBefore=12,
                                        spaceAfter=10, fontName="Helvetica-Bold", textColor=colors.darkblue),
        "text": ParagraphStyle("Text", fontSize=10, fontName="Helvetica", leading=16)
    }


def markdown_to_paragraph(text, styles):
    """Converte Markdown para HTML e aplica estilo."""
    # Remove blocos de código ```...``` do markdown
    clean_text = re.sub(r"```(?:\w+)?\s*([\s\S]*?)\s*```", r"\1", text)
    html = markdown.markdown(clean_text.strip())
    html = html.replace('<ul>', '<ul style="list-style-type: disc; margin-left: 20px;">')
    html = html.replace('<ol>', '<ol style="list-style-type: decimal; margin-left: 20px;">')
    return Paragraph(html, styles["text"])


def render_markdown_sections(markdown_text, styles):
    """Processa o conteúdo em Markdown e organiza seções e parágrafos no PDF."""
    flowables = []
    if not markdown_text.strip():
        return [Paragraph("Nenhuma informação de risco disponível.", styles["text"])]

    lines = markdown_text.splitlines()
    paragraph_buffer = []
    title_skipped = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if paragraph_buffer:
                flowables.append(markdown_to_paragraph("\n".join(paragraph_buffer), styles))
                paragraph_buffer = []
            continue

        if stripped.startswith("#"):
            if not title_skipped:
                title_skipped = True
                continue  # ignora o primeiro título
            if paragraph_buffer:
                flowables.append(markdown_to_paragraph("\n".join(paragraph_buffer), styles))
                paragraph_buffer = []
            header_level = len(stripped) - len(stripped.lstrip('#'))
            header = stripped.lstrip('#').strip()
            style = styles["title"] if header_level == 1 else styles["section_title"]
            flowables.append(Spacer(1, 12))
            flowables.append(Paragraph(header, style))
            flowables.append(Spacer(1, 8))
        else:
            paragraph_buffer.append(stripped)

    if paragraph_buffer:
        flowables.append(markdown_to_paragraph("\n".join(paragraph_buffer), styles))

    return flowables


def classify_severity(severity):
    return {
        "Critical": colors.red,
        "High": colors.orange,
        "Medium": colors.yellow,
        "Low": colors.green,
        "N/A": colors.black
    }.get(severity, colors.black)


def process_references(links, styles):
    """Cria parágrafos com os links clicáveis formatados."""
    refs = []
    if links:
        try:
            refs = json.loads(links.replace("'", '"')) if links.strip().startswith('[') else links.split(',')
        except Exception:
            refs = links.replace('[', '').replace(']', '').split(',')

    return [Paragraph(f'<a href="{r.strip()}">{r.strip()}</a>', styles["normal"]) for r in refs if r.strip()] or \
           [Paragraph("Nenhuma referência disponível.", styles["normal"])]


def create_basic_info_table(cve_id, vendor, published, severity, generated_on, styles):
    color = classify_severity(severity)
    severity_style = ParagraphStyle("Severity", parent=styles["section_title"],
                                    alignment=1, textColor=color, fontSize=styles["section_title"].fontSize)

    data = [
        ["CVE ID", cve_id],
        ["Fornecedor", vendor or "Desconhecido"],
        ["Data de Publicação", published],
        ["Severidade", Paragraph(severity, severity_style)],
        ["Gerado em", generated_on]
    ]

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("BOX", (0, 0), (-1, -1), 1, colors.black)
    ])

    return Table(data, colWidths=[130, 250], style=style)


def build_content(cve_id, description, risks, vendor, references, severity, published, generated_on, styles):
    content = [
        Spacer(1, 20),
        Paragraph(f"RELATÓRIO TÉCNICO - {cve_id}", styles["title"]),
        Spacer(1, 20),
        create_basic_info_table(cve_id, vendor, published, severity, generated_on, styles),
        Spacer(1, 20),
        Paragraph("Descrição Geral", styles["section_title"]),
        Spacer(1, 10),
        markdown_to_paragraph(description, styles),
        Spacer(1, 20)
    ]

    content += render_markdown_sections(risks, styles)

    content += [
        Spacer(1, 20),
        Paragraph("Referências", styles["section_title"]),
        Spacer(1, 10),
        *process_references(references, styles),
        Spacer(1, 20),
        PageBreak()
    ]
    return content


def add_page_decorations(canvas, doc):
    """Adiciona rodapé e cabeçalho com numeração."""
    canvas.saveState()
    canvas.setFont("Helvetica-Bold", 6)
    canvas.drawCentredString(doc.pagesize[0] / 2.0, doc.pagesize[1] - 30,
                             "Relatório gerado automaticamente pelo sistema Open CVE Report.")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(doc.pagesize[0] - 30, 20, f"Página {canvas.getPageNumber()}")
    canvas.restoreState()
