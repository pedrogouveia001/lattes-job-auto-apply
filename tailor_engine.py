# -*- coding: utf-8 -*-
"""
Generalized Tailor Engine for Academic & Professional Resumes.
Adapts candidate profiles to specific institutions and vacancies, generating:
- Tailored Executive Summary
- Prioritized Key Disciplines / Core Competencies
- Personalized Email Subject & Message to Coordinators / Selection Committees
"""

import re
from dataclasses import dataclass, field

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
    match_score: int = 85

    def __getitem__(self, item):
        return getattr(self, item)

    def get(self, item, default=None):
        return getattr(self, item, default)

def tailor_for_vacancy(profile: dict, vacancy: dict) -> TailoredApplication:
    """
    Produces a tailored profile and email pitch based on candidate profile and target vacancy.
    Works for any area (Engineering, Health, Humanities, Tech, Management).
    """
    full_name = profile.get("full_name", "Candidato(a)")
    phone = profile.get("phone", "")
    lattes_url = profile.get("lattes_url", "")
    linkedin_url = profile.get("linkedin_url", "")
    lattes_data = profile.get("lattes_data", {})
    
    inst = vacancy.get("institution", "Instituição de Ensino")
    city = vacancy.get("campus_city", "")
    contact_name = vacancy.get("contact_name", "").strip()
    job_title = vacancy.get("job_title", "Docência no Ensino Superior").strip()
    target_disciplines = vacancy.get("target_disciplines", "")

    # Analyze vacancy type: EAD vs Presencial vs Técnico vs Concurso
    inst_low = (inst + " " + job_title + " " + target_disciplines).lower()
    is_ead = any(w in inst_low for w in ["ead", "distância", "distancia", "remoto", "virtual", "conteudista", "tutor"])
    is_technical = any(w in inst_low for w in ["senai", "sest", "ifpe", "ifrn", "ifpb", "técnico", "tecnico", "pronatec"])
    is_public = any(w in inst_low for w in ["ufpe", "ufrpe", "upe", "ufrn", "ufersa", "concurso", "substituto"])

    # Extract academic title
    highest_degree = "Especialista"
    degrees = lattes_data.get("degrees", [])
    deg_str = " ".join([d.get("description", "") for d in degrees]).lower()
    if "doutorad" in deg_str or "doutor" in deg_str:
        highest_degree = "Doutoranda" if "andamento" in deg_str or "bolsista" in deg_str else "Doutora"
    elif "mestrad" in deg_str or "mestre" in deg_str:
        highest_degree = "Mestre"

    # Headline
    headline = f"Docência no Ensino Superior | {job_title if job_title != 'Docência no Ensino Superior' else 'Engenharia de Produção & Gestão'}"
    if is_ead:
        headline = f"Docência & Conteudismo EAD | {job_title}"
    elif is_technical:
        headline = f"Formação Profissional & Docência Técnica | {job_title}"

    # Build Tailored Summary
    orig_summary = lattes_data.get("summary", "")
    if not orig_summary:
        orig_summary = f"{highest_degree} com sólida formação acadêmica e experiência em docência no ensino superior e pesquisa aplicada."

    tailored_summary = orig_summary
    differentials = []

    # Inject specific differentials
    advising = lattes_data.get("advising_count", 0)
    juries = lattes_data.get("jury_count", 0)

    if is_ead:
        differentials.append("Autoria e Conteudismo Digital: Elaboração de materiais didáticos estruturados, roteirização de videoaulas e questões no padrão ENADE.")
        differentials.append("Mediação em Ambientes Virtuais: Domínio de plataformas AVA (Moodle, Blackboard, Canvas) com foco em engajamento e combate à evasão discente.")
        if advising > 0:
            differentials.append(f"Orientação Remota em Escala: Histórico de {advising} TCCs concluídos com metodologia ágil de acompanhamento.")
    elif is_technical:
        differentials.append("Vivência Prática & Segurança: Formação técnica com imersão em ambientes industriais e cumprimento de Normas Regulamentadoras (NRs).")
        differentials.append("Metodologia de Ensino Aplicado: Integração entre fundamentos teóricos e projetos operacionais para o ecossistema empresarial local.")
    else:
        # Higher ed private / public
        differentials.append(f"Elevação de Indicadores Regulatórios MEC/ENADE: Titulação de {highest_degree} em programa de excelência CAPES, agregando pontuação máxima de corpo docente.")
        if advising > 0:
            differentials.append(f"Agilidade no Fluxo de Formatura: {advising} orientações de TCC concluídas com 0% de evasão discente.")
        differentials.append("Metodologias Ativas (PBL): Aplicação de Problem-Based Learning com estudos de caso reais e ferramentas de mercado (Bizagi BPMN, MS Project, Solver).")

    # Email Subject & Body
    salutation = f"Prezado(a) {contact_name}," if contact_name and not contact_name.lower().startswith("coord") else "Prezado(a) Coordenador(a),"
    
    email_subject = f"Apresentação Docente - {job_title} | Profa. {full_name}"
    if is_ead:
        email_subject = f"Disponibilidade para Conteudismo e Docência EAD - {job_title} | Profa. {full_name}"

    email_body = f"""{salutation}

Escrevo para apresentar minha disponibilidade docente para ministrar disciplinas no curso de {job_title} e áreas correlatas de Gestão e Operações na {inst}{f' ({city})' if city else ''}.

Sou {highest_degree} com sólida trajetória acadêmica e atuação comprovada na regência de turmas, planejamento pedagógico e orientação de formandos.

Principais contribuições e diferenciais para o colegiado e indicadores do MEC:
• Elevação de Indicadores Regulatórios: Titulação e produção em programa de excelência (CAPES 7) garantem pontuação máxima de corpo docente nas avaliações do MEC/INEP.
• Polivalência Curricular: Capacidade didática para assumir disciplinas estruturantes do ciclo quantitativo/estratégico e normativo.
• Metodologias Ativas (PBL): Implementação de estudos de caso aplicados com foco em retenção discente e preparação para o ENADE.

Disponho de horários flexíveis para atendimento às demandas da instituição.

Seguem em anexo meu Currículo Executivo formatado e o link para o Currículo Lattes completo.

Currículo Lattes: {lattes_url if lattes_url else 'Disponível na plataforma CNPq'}
{f'LinkedIn: {linkedin_url}' if linkedin_url else ''}
Telefone / WhatsApp: {phone}

Agradeço a atenção e coloco-me à disposição para entrevista ou aula-teste.

Atenciosamente,
{full_name}"""

    return TailoredApplication(
        candidate_name=full_name,
        target_institution=inst,
        target_city=city,
        contact_recipient=contact_name,
        vacancy_title=job_title,
        tailored_headline=headline,
        tailored_summary=tailored_summary,
        highlighted_differentials=differentials,
        disciplines_of_focus=[d.strip() for d in target_disciplines.split(",") if d.strip()] if target_disciplines else [],
        email_subject=email_subject,
        email_body=email_body,
        match_score=92 if is_ead or is_public else 88
    )
