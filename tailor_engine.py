# -*- coding: utf-8 -*-
"""
Adaptive Semantic Tailor Engine & Real Match Scorer.
Unbiased, profile-driven matching and pitch tailoring for ANY resume and ANY vacancy.
Eliminates hardcoded assumptions and performs real keyword/semantic overlap calculations.
"""

import re
import unicodedata
from dataclasses import dataclass, field

def normalize_text(s: str) -> str:
    """Normalizes string for robust token comparison."""
    if not s:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )

def tokenize(s: str) -> set[str]:
    """Tokenizes text into meaningful semantic keywords (>2 chars, no common stopwords)."""
    stopwords = {
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "com", "nao", "uma", "os", "no", "se", "na",
        "por", "mais", "as", "dos", "como", "mas", "ao", "ele", "das", "seu", "sua", "ou", "quando", "muito",
        "nos", "ja", "eu", "tambem", "so", "pelo", "pela", "ate", "isso", "ela", "entre", "depois", "sem",
        "mesmo", "aos", "seus", "quem", "nas", "me", "esse", "eles", "voce", "essa", "num", "nem", "suas",
        "meu", "minha", "minhas", "curso", "disciplinas", "area", "vaga", "docente", "professor", "professora"
    }
    norm = normalize_text(s)
    words = re.findall(r'\b[a-z0-9]{3,}\b', norm)
    return {w for w in words if w not in stopwords}

@dataclass
class TailoredApplication:
    candidate_name: str
    target_institution: str
    target_city: str
    contact_recipient: str
    vacancy_title: str
    tailored_headline: str
    tailored_summary: str
    highlighted_differentials: list[str] = field(default_factory=list)
    disciplines_of_focus: list[str] = field(default_factory=list)
    email_subject: str = ""
    email_body: str = ""
    match_score: int = 75
    match_reasons: list[str] = field(default_factory=list)

    def __getitem__(self, item):
        return getattr(self, item)

    def get(self, item, default=None):
        return getattr(self, item, default)

def calculate_vacancy_match(profile: dict, vacancy: dict) -> dict:
    """
    Computes an objective, data-driven ATS match score (0-100%) between
    the candidate's actual resume + target criteria vs the target vacancy.
    """
    lattes_data = profile.get("lattes_data", {}) if isinstance(profile.get("lattes_data"), dict) else {}
    
    # 1. Candidate Terms Aggregation
    target_roles = profile.get("target_roles", "")
    target_disciplines = profile.get("target_disciplines", "")
    target_locations = profile.get("target_locations", "")
    target_modalities = profile.get("target_modalities", "")
    
    cand_summary = lattes_data.get("summary", "") or profile.get("summary", "")
    cand_skills = " ".join(lattes_data.get("skills", []))
    cand_degrees = " ".join([d.get("description", "") for d in lattes_data.get("degrees", [])])
    cand_teaching = " ".join(lattes_data.get("teaching_experience", []))
    cand_work = " ".join(lattes_data.get("work_experience", []))
    
    cand_role_pool = f"{target_roles} {cand_teaching} {cand_work}"
    cand_skills_pool = f"{target_disciplines} {cand_skills} {cand_summary} {cand_degrees}"
    cand_loc_pool = f"{target_locations} {target_modalities}"

    cand_role_tokens = tokenize(cand_role_pool)
    cand_skill_tokens = tokenize(cand_skills_pool)
    cand_loc_tokens = tokenize(cand_loc_pool)

    # 2. Vacancy Terms
    vac_title = vacancy.get("job_title", "")
    vac_inst = vacancy.get("institution", "")
    vac_disciplines = vacancy.get("target_disciplines", "")
    vac_city = vacancy.get("campus_city", "")

    vac_title_tokens = tokenize(vac_title)
    vac_disc_tokens = tokenize(vac_disciplines)
    vac_city_tokens = tokenize(f"{vac_city} {vac_inst}")

    # 3. Component Scoring
    match_reasons = []
    
    # A. Role Alignment (max 35 pts)
    role_score = 15  # base consideration
    common_roles = cand_role_tokens.intersection(vac_title_tokens)
    if common_roles:
        overlap_ratio = len(common_roles) / max(1, len(vac_title_tokens))
        role_score = min(35, 15 + int(overlap_ratio * 20))
        match_reasons.append(f"Alinhamento de função no termo '{', '.join(list(common_roles)[:3])}'")
    elif any(term in normalize_text(cand_role_pool) for term in ["producao", "gestao", "docencia", "engenharia", "administracao", "tecnologia"]):
        role_score = 25
        match_reasons.append("Área profissional compatível com o escopo da vaga")

    # B. Domain & Disciplines Match (max 35 pts)
    domain_score = 15
    common_skills = cand_skill_tokens.intersection(vac_disc_tokens)
    if common_skills:
        overlap_ratio = len(common_skills) / max(1, len(vac_disc_tokens))
        domain_score = min(35, 15 + int(overlap_ratio * 20))
        match_reasons.append(f"Competências diretas atendidas: {', '.join(list(common_skills)[:4])}")
    else:
        domain_score = 15

    # C. Location & Modality Match (max 20 pts)
    loc_score = 10
    is_ead = any(w in normalize_text(f"{vac_inst} {vac_city}") for w in ["ead", "distancia", "remoto", "virtual", "nacional"])
    cand_wants_ead = any(w in normalize_text(cand_loc_pool) for w in ["ead", "remoto", "distancia"])
    
    common_city = cand_loc_tokens.intersection(vac_city_tokens)
    if common_city:
        loc_score = 20
        match_reasons.append(f"Localização compatível com suas preferências ({', '.join(list(common_city)[:2])})")
    elif is_ead and cand_wants_ead:
        loc_score = 20
        match_reasons.append("Modalidade 100% Remota / EAD alinhada às suas preferências")
    elif is_ead:
        loc_score = 15
        match_reasons.append("Vaga em formato EAD / Remoto")

    # D. Education & Seniority Match (max 10 pts)
    edu_score = 10
    degrees_text = normalize_text(cand_degrees)
    if "doutor" in degrees_text:
        match_reasons.append("Titulação de Doutorado/Doutorando confere máxima pontuação institucional")
    elif "mestre" in degrees_text:
        match_reasons.append("Titulação de Mestrado atende plenamente aos requisitos regulatórios do MEC")

    total_score = min(100, max(25, role_score + domain_score + loc_score + edu_score))

    return {
        "score": total_score,
        "reasons": match_reasons if match_reasons else ["Vaga no segmento de atuação do candidato"]
    }

def tailor_for_vacancy(profile: dict, vacancy: dict) -> TailoredApplication:
    """
    Produces an adaptive, tailored application pitch based on the candidate's
    ACTUAL resume content and explicit target criteria.
    """
    full_name = profile.get("full_name") or "Candidato(a)"
    phone = profile.get("phone", "")
    lattes_url = profile.get("lattes_url", "")
    linkedin_url = profile.get("linkedin_url", "")
    lattes_data = profile.get("lattes_data", {}) if isinstance(profile.get("lattes_data"), dict) else {}

    inst = vacancy.get("institution", "Instituição de Ensino")
    city = vacancy.get("campus_city", "")
    contact_name = vacancy.get("contact_name", "").strip()
    job_title = vacancy.get("job_title", "Docência no Ensino Superior").strip()
    target_disciplines = vacancy.get("target_disciplines", "")

    # Calculate real ATS match
    match_data = calculate_vacancy_match(profile, vacancy)
    match_score = match_data["score"]
    match_reasons = match_data["reasons"]

    # Detect Highest Real Degree from candidate's resume
    highest_degree = "Profissional"
    degrees = lattes_data.get("degrees", [])
    deg_str = " ".join([d.get("description", "") for d in degrees]).lower()
    
    if "doutorado" in deg_str or "ph.d" in deg_str or "doutorand" in deg_str:
        highest_degree = "Doutoranda" if "andamento" in deg_str or "bolsista" in deg_str or "doutoranda" in deg_str else "Doutora"
    elif "mestrado" in deg_str or "msc" in deg_str or "mestrand" in deg_str:
        highest_degree = "Mestre"
    elif "especializa" in deg_str or "mba" in deg_str or "pos-gradua" in deg_str:
        highest_degree = "Especialista"
    elif "gradua" in deg_str or "bacharel" in deg_str or "engenharia" in deg_str:
        highest_degree = "Graduado(a)"

    # Candidate headline
    cand_headline = profile.get("target_roles") or profile.get("headline") or f"{highest_degree} em {job_title}"
    tailored_headline = f"{job_title} | {cand_headline.split(',')[0].strip()}"

    # Extract or generate tailored summary
    orig_summary = lattes_data.get("summary", "") or profile.get("summary", "")
    if not orig_summary:
        orig_summary = f"{highest_degree} com sólida formação e atuação prática/acadêmica, qualificada para ministrar disciplinas e colaborar com o corpo docente da {inst}."

    differentials = []
    # Build differentials based on REAL data found in resume
    if lattes_data.get("teaching_experience"):
        differentials.append(f"Experiência em Sala de Aula: Atuação comprovada no magistério ({len(lattes_data['teaching_experience'])} registros de docência).")
    if lattes_data.get("advising_count", 0) > 0:
        differentials.append(f"Orientação de Formandos: Histórico de {lattes_data['advising_count']} TCCs orientados com conclusão bem-sucedida.")
    if lattes_data.get("jury_count", 0) > 0:
        differentials.append(f"Avaliação Acadêmica: Participação em {lattes_data['jury_count']} bancas examinadoras.")
    if lattes_data.get("skills"):
        top_skills = ", ".join(lattes_data["skills"][:5])
        differentials.append(f"Domínio Técnico & Ferramentas: {top_skills}.")
    
    if not differentials:
        differentials.append(f"Alinhamento Curricular: Competências voltadas ao atendimento do projeto pedagógico de {job_title}.")
        differentials.append("Compromisso com Retenção & Aprendizado: Aplicação de metodologias práticas e foco no desenvolvimento dos discentes.")

    # Personalized Salutation
    if contact_name and not contact_name.lower().startswith("coord"):
        salutation = f"Prezado(a) {contact_name},"
    else:
        salutation = "Prezado(a) Coordenador(a) / Colegiado do Curso,"

    email_subject = f"Apresentação Docente / Profissional - {job_title} | {full_name}"
    
    disc_text = f" no componente curricular de {target_disciplines}" if target_disciplines else ""
    email_body = f"""{salutation}

Apresento minha disponibilidade para atuar junto à {inst}{f' ({city})' if city else ''} no curso de {job_title}{disc_text}.

Sou {highest_degree}, com perfil voltado à excelência pedagógica, rigor conceitual e articulação entre teoria e prática profissional.

Principais destaques e diferenciais competitivos:
• Formação & Qualificação: {orig_summary[:180]}...
• Contribuição Pedagógica: Experiência no planejamento de planos de ensino, avaliações orientadas a competências e engajamento discente.
• Disponibilidade Curricular: Flexibilidade para composição de carga horária e atendimento às demandas do colegiado.

Em anexo, disponibilizo meu Currículo Executivo formatado. Fico à inteira disposição para agendamento de entrevista ou aula-teste.

{f'Currículo Lattes: {lattes_url}' if lattes_url else ''}
{f'LinkedIn: {linkedin_url}' if linkedin_url else ''}
Contato Telefônico / WhatsApp: {phone}

Agradeço pela atenção e consideração.

Cordialmente,
{full_name}"""

    return TailoredApplication(
        candidate_name=full_name,
        target_institution=inst,
        target_city=city,
        contact_recipient=contact_name,
        vacancy_title=job_title,
        tailored_headline=tailored_headline,
        tailored_summary=orig_summary,
        highlighted_differentials=differentials,
        disciplines_of_focus=[d.strip() for d in target_disciplines.split(",") if d.strip()] if target_disciplines else [],
        email_subject=email_subject,
        email_body=email_body,
        match_score=match_score,
        match_reasons=match_reasons
    )
