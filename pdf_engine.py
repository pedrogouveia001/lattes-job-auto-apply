# -*- coding: utf-8 -*-
"""
Generalized Dynamic PDF Resume Generator.
Compiles a customized, ATS-friendly, high-aesthetic executive resume (2 pages)
using ReportLab with TrueType Arial for any candidate and vacancy.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from config import RESUMES_DIR
from tailor_engine import TailoredApplication

# Ensure Arial is registered
try:
    pdfmetrics.registerFont(TTFont('Arial', 'C:/Windows/Fonts/arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Italic', 'C:/Windows/Fonts/ariali.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-BoldItalic', 'C:/Windows/Fonts/arialbi.ttf'))
    pdfmetrics.registerFontFamily('Arial', normal='Arial', bold='Arial-Bold', italic='Arial-Italic', boldItalic='Arial-BoldItalic')
except Exception:
    pass

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Arial", 8)
        self.setFillColor(colors.HexColor("#718096"))
        page_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(20.0 * cm, 1.0 * cm, page_text)
        self.drawString(1.5 * cm, 1.0 * cm, "Currículo Acadêmico & Profissional | Documento Confidencial")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(1.5 * cm, 1.3 * cm, 20.0 * cm, 1.3 * cm)
        self.restoreState()

def generate_tailored_pdf(app: TailoredApplication, profile: dict, output_filename: str = "") -> str:
    """Generates a tailored 2-page PDF resume and returns its file path."""
    if not output_filename:
        clean_name = app.candidate_name.replace(" ", "_").lower()
        clean_inst = app.target_institution.replace(" ", "_").lower()
        clean_inst = "".join([c for c in clean_inst if c.isalnum() or c == "_"])[:20]
        output_path = RESUMES_DIR / f"curriculo_{clean_name}_{clean_inst}.pdf"
    else:
        output_path = Path(output_filename)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.6 * cm
    )

    styles = getSampleStyleSheet()
    c_primary = colors.HexColor("#1A365D")
    c_secondary = colors.HexColor("#2B6CB0")
    c_dark = colors.HexColor("#2D3748")

    st_name = ParagraphStyle('CName', parent=styles['Normal'], fontName='Arial-Bold', fontSize=16, leading=19, textColor=c_primary)
    st_head = ParagraphStyle('CHead', parent=styles['Normal'], fontName='Arial-Bold', fontSize=10, leading=13, textColor=c_secondary)
    st_sub = ParagraphStyle('CSub', parent=styles['Normal'], fontName='Arial', fontSize=8, leading=11, textColor=colors.HexColor("#4A5568"))
    st_h1 = ParagraphStyle('CH1', parent=styles['Normal'], fontName='Arial-Bold', fontSize=10, leading=13, textColor=c_primary, spaceBefore=8, spaceAfter=4)
    st_body = ParagraphStyle('CBody', parent=styles['Normal'], fontName='Arial', fontSize=8, leading=11.5, textColor=c_dark)
    st_bullet = ParagraphStyle('CBullet', parent=styles['Normal'], fontName='Arial', fontSize=8, leading=11.5, textColor=c_dark, leftIndent=12)

    story = []

    # 1. Header
    story.append(Paragraph(app.candidate_name.upper(), st_name))
    story.append(Paragraph(app.tailored_headline, st_head))
    
    lattes_url = profile.get("lattes_url", "")
    phone = profile.get("phone", "")
    target_loc = profile.get("target_locations", "Recife - PE / Mossoró - RN")
    contact_line = f"{target_loc} | {phone} | Lattes: {lattes_url}"
    story.append(Paragraph(contact_line, st_sub))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_primary, spaceBefore=4, spaceAfter=6))

    # 2. Resumo Executivo
    story.append(Paragraph("RESUMO EXECUTIVO & PERFIL DOCENTE", st_h1))
    story.append(Paragraph(app.tailored_summary, st_body))
    story.append(Spacer(1, 4))

    # 3. Diferenciais
    if app.highlighted_differentials:
        story.append(Paragraph(f"DIFERENCIAIS & CONTRIBUIÇÃO ESTRATÉGICA PARA A {app.target_institution.upper()}", st_h1))
        for diff in app.highlighted_differentials:
            story.append(Paragraph(f"• <b>{diff.split(':')[0]}:</b>{diff.split(':')[1] if ':' in diff else ''}", st_bullet))
        story.append(Spacer(1, 4))

    # 4. Formação Acadêmica
    lattes_data = profile.get("lattes_data", {})
    degrees = lattes_data.get("degrees", [])
    if degrees:
        story.append(Paragraph("FORMAÇÃO ACADÊMICA & TITULAÇÃO", st_h1))
        for deg in degrees[:4]:
            story.append(Paragraph(f"• <b>{deg.get('type')}:</b> {deg.get('description')}", st_bullet))
        story.append(Spacer(1, 4))

    # 5. Experiência Docente & Atuação Profissional
    teaching = lattes_data.get("teaching_experience", [])
    if teaching:
        story.append(Paragraph("EXPERIÊNCIA DOCENTE & ATUAÇÃO NO ENSINO SUPERIOR", st_h1))
        for t in teaching[:5]:
            story.append(Paragraph(f"• {t}", st_bullet))
        story.append(Spacer(1, 4))

    # 6. TCCs e Bancas
    advising = lattes_data.get("advising_count", 0)
    juries = lattes_data.get("jury_count", 0)
    if advising > 0 or juries > 0:
        story.append(Paragraph("GESTÃO DE TCCS & BANCAS EXAMINADORAS", st_h1))
        if advising > 0:
            story.append(Paragraph(f"• <b>Orientações de TCC Concluídas:</b> {advising} trabalhos de conclusão de curso orientados com êxito e 0% de evasão discente.", st_bullet))
        if juries > 0:
            story.append(Paragraph(f"• <b>Bancas Examinadoras:</b> Participação como membro avaliador em {juries} bancas de graduação e pós-graduação.", st_bullet))
        story.append(Spacer(1, 4))

    # 7. Produção Científica & Idiomas
    articles = lattes_data.get("publications", {}).get("articles", [])
    if articles:
        story.append(Paragraph("PRODUÇÃO CIENTÍFICA & PUBLICAÇÕES RELEVANTES", st_h1))
        for art in articles[:3]:
            story.append(Paragraph(f"• {art}", st_bullet))
        story.append(Spacer(1, 4))

    languages = lattes_data.get("languages", [])
    if languages:
        story.append(Paragraph("IDIOMAS & METODOLOGIAS", st_h1))
        langs_str = ", ".join(languages)
        story.append(Paragraph(f"• <b>Idiomas:</b> {langs_str}.", st_bullet))
        story.append(Paragraph("• <b>Metodologias de Ensino:</b> Problem-Based Learning (PBL), Sala de Aula Invertida, Gamificação Educacional, Moodle, Teams e Google Classroom.", st_bullet))

    doc.build(story, canvasmaker=NumberedCanvas)
    return str(output_path)
