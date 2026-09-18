# -*- coding: utf-8 -*-
"""
Universal Resume & CV Extractor Module.
Extracts structured information from ANY resume format:
- Academic CVs (Lattes, CNPq, Memorial Acadêmico)
- Corporate & Business Resumes (Word/PDF exports, Gupy, Catho, Vagas)
- Tech & LinkedIn Resumes (LinkedIn PDF exports, GitHub/Portfolio resumes)
- Executive & Freelancer CVs
"""

import re
import unicodedata
from pathlib import Path
from pypdf import PdfReader

def normalize_str(s: str) -> str:
    """Removes accents and converts to lowercase for resilient matching."""
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )

def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """Extracts raw text from any PDF resume."""
    try:
        reader = PdfReader(str(pdf_path))
        text_parts = []
        for page in reader.pages:
            txt = page.extract_text()
            if txt:
                text_parts.append(txt)
        return "\n".join(text_parts)
    except Exception as e:
        return f"Erro ao ler PDF: {str(e)}"

def extract_contact_info(text: str) -> dict:
    """Extracts emails, phones, and social links using regex."""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    
    # Phone numbers (Brazilian formats with DDD, mobile 9 digits, or international)
    phone_pattern = r'(?:(?:\+|00)?55\s?)?(?:\(?([1-9]{2})\)?\s?)?(?:(9\d{4})|(\d{4}))[-.\s]?(\d{4})'
    phones = []
    for m in re.finditer(phone_pattern, text):
        raw = m.group(0).strip()
        if len(re.sub(r'\D', '', raw)) >= 8:
            phones.append(raw)

    # Social / Professional links
    linkedin_match = re.search(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', text, re.IGNORECASE)
    lattes_match = re.search(r'lattes\.cnpq\.br/(\d{16})', text, re.IGNORECASE)
    github_match = re.search(r'github\.com/([a-zA-Z0-9_-]+)', text, re.IGNORECASE)

    return {
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else "",
        "linkedin": f"https://www.linkedin.com/in/{linkedin_match.group(1)}" if linkedin_match else "",
        "lattes": f"http://lattes.cnpq.br/{lattes_match.group(1)}" if lattes_match else "",
        "github": f"https://github.com/{github_match.group(1)}" if github_match else ""
    }

def parse_universal_resume(text: str) -> dict:
    """
    Parses ANY resume text into a structured profile:
    - Name & Headline
    - Contact Details
    - Summary / About
    - Degrees & Education
    - Work & Teaching Experience
    - Key Skills & Core Competencies
    - Languages
    """
    profile = {
        "full_name": "",
        "headline": "",
        "summary": "",
        "email": "",
        "phone": "",
        "linkedin_url": "",
        "lattes_url": "",
        "github_url": "",
        "degrees": [],
        "work_experience": [],
        "teaching_experience": [],
        "skills": [],
        "languages": [],
        "publications": {"articles": []},
        "advising_count": 0,
        "jury_count": 0,
        "raw_text_length": len(text)
    }

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return profile

    # 1. Contact details
    contacts = extract_contact_info(text)
    profile["email"] = contacts["email"]
    profile["phone"] = contacts["phone"]
    profile["linkedin_url"] = contacts["linkedin"]
    profile["lattes_url"] = contacts["lattes"]
    profile["github_url"] = contacts["github"]

    # 2. Name Detection
    # Usually the first 1-3 lines of a resume, not starting with generic words
    ignore_starts = ("curriculo", "resume", "cv", "dados pessoais", "lattes", "page", "pagina", "contato", "telefone", "email")
    for line in lines[:6]:
        norm = normalize_str(line)
        if len(line.split()) >= 2 and len(line) < 50 and not any(norm.startswith(w) for w in ignore_starts):
            # Must look like a person's name (letters, spaces, hyphens)
            if re.match(r'^[A-Za-zÀ-ÖØ-öø-ÿ\s\.\-]+$', line):
                profile["full_name"] = line
                break

    # 3. Professional Headline / Title (Line immediately after name or first prominent title)
    name_idx = -1
    for idx, line in enumerate(lines[:8]):
        if line == profile["full_name"]:
            name_idx = idx
            break
    if name_idx >= 0 and name_idx + 1 < len(lines):
        candidate_headline = lines[name_idx + 1]
        if len(candidate_headline) < 80 and not "@" in candidate_headline and not re.search(r'\d{4}', candidate_headline):
            profile["headline"] = candidate_headline

    # 4. Summary / Objetivo / Perfil
    summary_match = re.search(
        r'(?:resumo|resumo profissional|resumo executivo|objetivo|perfil profissional|sobre mim|about me|summary)[\s\:\-]+(.*?)(?:experi[êe]ncia|forma[çc][ãa]o|educa[çc][ãa]o|hist[óo]rico|compet[êe]ncias|habilidades|skills)',
        text, re.DOTALL | re.IGNORECASE
    )
    if summary_match:
        clean_sum = " ".join(summary_match.group(1).split())
        if len(clean_sum) > 40:
            profile["summary"] = clean_sum
    
    if not profile["summary"]:
        # Fallback to first paragraph with > 100 characters
        for line in lines[1:15]:
            if len(line) > 100 and not line.startswith("http"):
                profile["summary"] = line
                break

    # 5. Education & Degrees
    degree_patterns = [
        ("Doutorado", r'(?:doutorado|ph\.?d|doutorando|doutora|doutor)\s*(?:em|na|no)?\s*([^\.\n\–\-\;]+)'),
        ("Mestrado", r'(?:mestrado|msc|mestre|mestrando)\s*(?:em|na|no)?\s*([^\.\n\–\-\;]+)'),
        ("Pós-Graduação / MBA", r'(?:p[óo]s[ \-]gradua[çc][ãa]o|mba|especializa[çc][ãa]o)\s*(?:em|na|no)?\s*([^\.\n\–\-\;]+)'),
        ("Graduação", r'(?:gradua[çc][ãa]o|bacharelado|licenciatura|engenharia|administra[çc][ãa]o|direito|ci[êe]ncia)\s*(?:em|na|no)?\s*([^\.\n\–\-\;]+)'),
        ("Tecnólogo", r'(?:tecn[óo]logo|curso superior de tecnologia)\s*(?:em|na|no)?\s*([^\.\n\–\-\;]+)'),
        ("Ensino Técnico", r'(?:curso t[ée]cnico|ensino m[ée]dio[ \-]t[ée]cnico)\s*(?:em|de)?\s*([^\.\n\–\-\;]+)')
    ]
    for deg_name, pattern in degree_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            deg_desc = m.group(0).strip()
            if 10 < len(deg_desc) < 140:
                profile["degrees"].append({"type": deg_name, "description": deg_desc})

    # 6. Work & Teaching Experience
    # Matches lines with common job titles and companies/institutions
    job_roles = [
        "Professor", "Professora", "Docente", "Coordenador", "Coordenadora",
        "Engenheiro", "Engenheira", "Analista", "Desenvolvedor", "Desenvolvedora",
        "Gerente", "Consultor", "Consultora", "Especialista", "Pesquisador", "Pesquisadora",
        "Tutor", "Instrutor", "Supervisor", "Assistente", "Diretor", "Diretora",
        "Médico", "Médica", "Enfermeiro", "Enfermeira", "Advogado", "Advogada",
        "Designer", "Arquiteto", "Arquiteta", "Cientista", "Contador", "Contadora",
        "Administrador", "Administradora", "Psicólogo", "Psicóloga", "Líder"
    ]
    roles_regex = r'(?:' + '|'.join(job_roles) + r')\b[\w\s\(\)\,\–\-\.\:\/]{6,150}'
    for m in re.finditer(roles_regex, text, re.IGNORECASE):
        exp_line = m.group(0).strip()
        if any(w in exp_line.lower() for w in ["professor", "docente", "turmas", "aulas", "faculdade", "universidade", "colegiado", "ensino"]):
            if exp_line not in profile["teaching_experience"]:
                profile["teaching_experience"].append(exp_line)
        else:
            if exp_line not in profile["work_experience"]:
                profile["work_experience"].append(exp_line)

    # 7. Skills & Core Competencies Extraction
    # A) Dynamic extraction from explicit sections (Skills / Competências / Conhecimentos)
    skills_found = set()
    sec_match = re.search(
        r'(?:habilidades|compet[êe]ncias|skills|conhecimentos|tecnologias|ferramentas|disciplinas|expertise)[\s\:\-]+(.*?)(?:experi[êe]ncia|forma[çc][ãa]o|educa[çc][ãa]o|hist[óo]rico|idiomas|languages|publica[çc][õo]es|\Z)',
        text, re.DOTALL | re.IGNORECASE
    )
    if sec_match:
        sec_text = sec_match.group(1)
        # Split by comma, bullet points, pipes or newlines
        tokens = re.split(r'[,;•\n\|\t]+', sec_text)
        for t in tokens:
            t_clean = t.strip()
            # If clean token is reasonable length and doesn't look like a long sentence
            if 2 <= len(t_clean) <= 40 and not any(w in t_clean.lower() for w in ["http", "www", "telefone", "email"]):
                skills_found.add(t_clean)

    # B) Multi-domain Keyword Catalog spanning Tech, Business, Engineering, Academic, Law, Health, Design
    universal_catalog = [
        # Tech & Data
        "Python", "SQL", "JavaScript", "TypeScript", "React", "Node.js", "Java", "C#", ".NET",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD", "Linux",
        "Machine Learning", "Data Science", "Inteligência Artificial", "Power BI", "Tableau",
        "Excel", "Excel Avançado", "Pandas", "NLP", "Big Data", "DevOps",
        # Engineering & Operations
        "PCP", "Pesquisa Operacional", "Gestão da Produção", "Logística", "Supply Chain",
        "Qualidade", "Six Sigma", "Lean Manufacturing", "Lean Six Sigma", "5S", "Kaizen",
        "Segurança do Trabalho", "SST", "Ergonomia", "Custos Industriais", "Custos",
        "BPMN", "Bizagi", "AutoCAD", "Revit", "SolidWorks", "Simulação", "Arena", "Solver",
        # Business, Management & Finance
        "Gestão de Projetos", "Scrum", "Kanban", "Metodologias Ágeis", "Planejamento Estratégico",
        "Gestão de Pessoas", "Liderança", "Negociação", "Vendas", "CRM", "Salesforce",
        "Finanças", "Contabilidade", "Controladoria", "Auditoria", "Orçamento", "DRE", "Fluxo de Caixa",
        # Academic & Education
        "Docência", "Ensino Superior", "EAD", "Metodologias Ativas", "PBL", "Moodle", "Canvas",
        "Google Classroom", "Orientação de TCC", "Planos de Ensino", "Avaliação da Aprendizagem",
        "Coordenação de Curso", "ENADE", "Regulação MEC", "Bancas Examinadoras",
        # Law & Compliance
        "Direito Civil", "Direito Trabalhista", "Direito Tributário", "Direito Empresarial",
        "Direito Penal", "LGPD", "Compliance", "Contratos", "Processo Civil", "Mediação",
        # Health & Science
        "Enfermagem", "Farmácia", "Fisioterapia", "Nutrição", "Psicologia", "Saúde Coletiva",
        "Bioestatística", "Metodologia Científica", "Epidemiologia", "Gestão Hospitalar",
        # Marketing & Design
        "Marketing Digital", "SEO", "SEM", "Google Analytics", "Social Media", "Copywriting",
        "Branding", "Design Gráfico", "Photoshop", "Illustrator", "Figma", "UI/UX"
    ]

    norm_text = normalize_str(text)
    for kw in universal_catalog:
        # Match whole word or exact normalized token
        kw_norm = normalize_str(kw)
        if re.search(r'\b' + re.escape(kw_norm) + r'\b', norm_text):
            skills_found.add(kw)

    profile["skills"] = sorted(list(skills_found))

    # 8. Languages
    languages = []
    for lang in ["Inglês", "Espanhol", "Francês", "Alemão", "Italiano", "Português", "Mandarim"]:
        if re.search(r'\b' + lang + r'\b', text, re.IGNORECASE):
            languages.append(lang)
    profile["languages"] = languages

    # 9. Academic specifics (Bancas, TCC, Artigos if present)
    tcc_match = re.findall(r'(\d+)\s*(?:trabalhos de conclusão|tcc|orientações|monografias)', text, re.IGNORECASE)
    if tcc_match:
        try:
            profile["advising_count"] = max([int(x) for x in tcc_match])
        except ValueError:
            profile["advising_count"] = len(tcc_match)

    bancas_match = re.findall(r'(\d+)\s*bancas', text, re.IGNORECASE)
    if bancas_match:
        try:
            profile["jury_count"] = max([int(x) for x in bancas_match])
        except ValueError:
            profile["jury_count"] = len(bancas_match)

    artigos = re.findall(r'([A-Z\s\,\.\;\–\-]{10,}\.\s*[A-Za-z0-9\s\:\,\–\-]+\.\s*(?:19\d\d|20\d\d)\.)', text)
    if artigos:
        profile["publications"]["articles"] = [a.strip() for a in artigos[:10]]

    return profile

def extract_from_file_or_text(file_path_or_text: str | Path) -> dict:
    """Universal parser entrypoint for any file path, uploaded bytes or raw string."""
    if isinstance(file_path_or_text, (str, Path)):
        p = Path(file_path_or_text)
        if p.exists() and p.is_file() and p.suffix.lower() == ".pdf":
            raw_text = extract_text_from_pdf(p)
        else:
            raw_text = str(file_path_or_text)
    else:
        raw_text = str(file_path_or_text)
    return parse_universal_resume(raw_text)

# Alias for backward compatibility
parse_lattes_text = parse_universal_resume

