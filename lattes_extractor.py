# -*- coding: utf-8 -*-
"""
Generalized Lattes Ingestion & Extractor Module.
Extracts structured academic and professional data from Lattes PDFs or raw text
for ANY field of knowledge (Engineering, Health, Humanities, Exact Sciences, Law, etc.).
"""

import re
from pathlib import Path
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extracts all text from a PDF file."""
    reader = PdfReader(str(pdf_path))
    text_parts = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            text_parts.append(txt)
    return "\n".join(text_parts)

def parse_lattes_text(text: str) -> dict:
    """
    Parses full Lattes CV text into structured sections.
    Generalizes across different academic fields and profiles.
    """
    profile = {
        "full_name": "",
        "summary": "",
        "degrees": [],
        "teaching_experience": [],
        "research_projects": [],
        "publications": {
            "articles": [],
            "books_and_chapters": [],
            "conference_papers": []
        },
        "advising_count": 0,
        "advising_items": [],
        "jury_count": 0,
        "languages": [],
        "skills_and_tools": [],
        "raw_text_length": len(text)
    }

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return profile

    # 1. Detect Name (usually in first 3-5 lines)
    for line in lines[:5]:
        if len(line.split()) >= 2 and not line.lower().startswith(("currículo", "lattes", "página", "data")):
            profile["full_name"] = line
            break

    # 2. Extract Resumo / Summary
    summary_match = re.search(
        r'(?:resumo|resumo executivo|resumo informado pelo autor)[\s\:\-]+(.*?)(?:formação acadêmica|formacao academica|atuação profissional|atuacao profissional)',
        text, re.DOTALL | re.IGNORECASE
    )
    if summary_match:
        profile["summary"] = " ".join(summary_match.group(1).split())
    else:
        # Fallback: take first substantial paragraph
        first_paras = [l for l in lines[1:15] if len(l) > 100]
        if first_paras:
            profile["summary"] = first_paras[0]

    # 3. Formação Acadêmica (Degrees)
    degree_patterns = [
        ("Doutorado", r'doutorado\s*(?:em|na|no)?\s*([^\.\n]+)'),
        ("Mestrado", r'mestrado\s*(?:em|na|no)?\s*([^\.\n]+)'),
        ("Graduação", r'gradua[çc][ãa]o\s*(?:em|na|no)?\s*([^\.\n]+)'),
        ("Especialização", r'especializa[çc][ãa]o\s*(?:em|na|no)?\s*([^\.\n]+)'),
        ("Técnico", r'(?:curso t[ée]cnico|ensino m[ée]dio[ \-]t[ée]cnico)\s*(?:em|de)?\s*([^\.\n]+)')
    ]
    for deg_name, pattern in degree_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for m in matches:
            deg_text = m.group(0).strip()
            if len(deg_text) < 150:
                profile["degrees"].append({
                    "type": deg_name,
                    "description": deg_text
                })

    # 4. Atuação Docente / Disciplinas
    # Detect lines with "Professor", "Docente", "Regência", "Disciplinas ministradas"
    docencia_matches = re.finditer(
        r'(?:professor[a]?\s+(?:substituto|adjunto|assistente|titular|convidado|horista)|doc[êe]ncia|reg[êe]ncia)[\w\s\(\)\,\–\-\.\:\/]{10,200}',
        text, re.IGNORECASE
    )
    for m in docencia_matches:
        profile["teaching_experience"].append(m.group(0).strip())

    # 5. Orientações de TCC / Dissertações / Teses
    orient_matches = re.findall(
        r'(\d+)\s*(?:trabalhos de conclusão|tcc|orientações|dissertações|teses|monografias)',
        text, re.IGNORECASE
    )
    if orient_matches:
        try:
            profile["advising_count"] = max([int(x) for x in orient_matches])
        except ValueError:
            profile["advising_count"] = len(orient_matches)

    # 6. Participação em Bancas
    bancas_matches = re.findall(r'(\d+)\s*bancas', text, re.IGNORECASE)
    if bancas_matches:
        try:
            profile["jury_count"] = max([int(x) for x in bancas_matches])
        except ValueError:
            profile["jury_count"] = len(bancas_matches)

    # 7. Artigos e Publicações
    artigos = re.findall(r'([A-Z\s\,\.\;\–\-]{10,}\.\s*[A-Za-z0-9\s\:\,\–\-]+\.\s*(?:19\d\d|20\d\d)\.)', text)
    if artigos:
        profile["publications"]["articles"] = [a.strip() for a in artigos[:10]]

    # 8. Idiomas
    idiomas_found = []
    for lang in ["Inglês", "Espanhol", "Francês", "Alemão", "Italiano", "Português"]:
        if re.search(r'\b' + lang + r'\b', text, re.IGNORECASE):
            idiomas_found.append(lang)
    profile["languages"] = idiomas_found

    return profile

def extract_from_file_or_text(file_path_or_text: str) -> dict:
    p = Path(file_path_or_text)
    if p.exists() and p.is_file() and p.suffix.lower() == ".pdf":
        raw_text = extract_text_from_pdf(p)
    else:
        raw_text = file_path_or_text
    return parse_lattes_text(raw_text)
