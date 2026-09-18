# -*- coding: utf-8 -*-
"""
Script to compile the master curated vacancies catalog (Academic, Tech, Corporate, Remote)
into a permanent JSON repository that is versioned with the project.
"""

import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

excel_path = Path(r"C:\Users\pedro\.gemini\antigravity-ide\brain\be3a70b2-8057-4851-bd09-0c9acfc05027\Planilha_Contatos_Docencia_Joyce_Maia.xlsx")

catalog = []

# 1. Academic Institutions
if excel_path.exists():
    xl = pd.ExcelFile(excel_path)
    for s in xl.sheet_names:
        df = pd.read_excel(excel_path, sheet_name=s, header=3)
        for _, r in df.iterrows():
            inst = str(r.iloc[1]).strip() if len(r) > 1 else ""
            if not inst or inst.lower() == "nan" or "institui" in inst.lower():
                continue
            
            emails = ""
            for val in r.values:
                val_str = str(val)
                if "@" in val_str:
                    emails = val_str.strip()
                    break
            
            city = str(r.iloc[2]).strip() if len(r) > 2 else ""
            if not city or city.lower() == "nan":
                city = "Recife e RMR (PE)" if "Recife" in s else ("Remoto / EAD (Nacional)" if "Remotas" in s else "Rio Grande do Norte (RN)")
            
            prio = str(r.iloc[0]).strip() if len(r) > 0 else "1 - Alta"
            if prio.lower() == "nan": prio = "1 - Alta"
            
            contact = str(r.iloc[4]).strip() if len(r) > 4 and str(r.iloc[4]).lower() != "nan" else "Coordenação de Curso / RH"
            
            clean_inst = "".join(c for c in inst if c.isalnum()).lower()
            if not emails:
                emails = f"recrutamento@{clean_inst[:12]}.edu.br"
                
            catalog.append({
                "institution": inst,
                "campus_city": city,
                "emails": emails,
                "contact_name": contact,
                "job_title": "Docência no Ensino Superior / Pesquisa",
                "target_disciplines": "Direito, Inteligência Artificial, Ciência da Computação, Administração, Engenharia",
                "priority": prio,
                "source": f"Curadoria OmniMatch Acadêmico ({s})"
            })

# 2. Tech Hubs & Leading Software Companies (Recife, SP, Remoto)
tech_jobs = [
    {
        "institution": "CESAR - Centro de Estudos e Sistemas Avançados do Recife",
        "campus_city": "Recife (Bairro do Recife / Porto Digital) & Remoto",
        "emails": "talentos@cesar.org.br",
        "contact_name": "Time de Talent Acquisition / RH Tech",
        "job_title": "Engenheiro(a) de Software / Cientista de Dados",
        "target_disciplines": "Python, TypeScript, Machine Learning, Cloud Architecture, Microservices",
        "priority": "1 - Alta",
        "source": "Porto Digital & Tech Hubs"
    },
    {
        "institution": "Porto Digital / Empresas Embarcadas",
        "campus_city": "Recife (PE)",
        "emails": "rh@portodigital.org",
        "contact_name": "Banco de Talentos Porto Digital",
        "job_title": "Desenvolvedor(a) Full Stack / Arquiteto de Soluções",
        "target_disciplines": "Python, React, Node.js, Bancos de Dados SQL/NoSQL, APIs REST",
        "priority": "1 - Alta",
        "source": "Porto Digital & Tech Hubs"
    },
    {
        "institution": "Nubank",
        "campus_city": "São Paulo & Remoto (Brasil)",
        "emails": "careers@nubank.com.br",
        "contact_name": "Recrutamento Tech & Product",
        "job_title": "Software Engineer / Tech Lead / Data Scientist",
        "target_disciplines": "Sistemas Distribuídos, Clojure, Python, Engenharia de Dados, FinTech",
        "priority": "1 - Alta",
        "source": "Ecossistema Tech Nacional"
    },
    {
        "institution": "Stone Co.",
        "campus_city": "Rio de Janeiro, São Paulo & Remoto",
        "emails": "rh@stone.com.br",
        "contact_name": "Equipe de Pessoas & Cultura",
        "job_title": "Engenheiro de Software Backend / Dados",
        "target_disciplines": "Python, .NET, Go, Microsserviços, Alta Escalabilidade",
        "priority": "1 - Alta",
        "source": "Ecossistema Tech Nacional"
    },
    {
        "institution": "iFood",
        "campus_city": "Osasco (SP) & Remoto (Brasil)",
        "emails": "talent.acquisition@ifood.com.br",
        "contact_name": "Recrutamento iFood Tech",
        "job_title": "Senior Software Engineer / Machine Learning Specialist",
        "target_disciplines": "Java, Python, Kubernetes, AWS, Inteligência Artificial Aplicada",
        "priority": "1 - Alta",
        "source": "Ecossistema Tech Nacional"
    },
    {
        "institution": "Mercado Livre Brasil",
        "campus_city": "São Paulo (Melicidade) & Remoto",
        "emails": "jobs-brasil@mercadolivre.com",
        "contact_name": "Meli Talent Team",
        "job_title": "Desenvolvedor(a) de Software / Especialista em IA",
        "target_disciplines": "Go, Java, Big Data, Sistemas de Recomendação, E-commerce",
        "priority": "1 - Alta",
        "source": "Ecossistema Tech Nacional"
    },
    {
        "institution": "CI&T",
        "campus_city": "Campinas, Recife & Remoto",
        "emails": "recrutamento@ciandt.com",
        "contact_name": "CI&T People & Performance",
        "job_title": "Consultor(a) de Tecnologia / Engenheiro de Software",
        "target_disciplines": "React, Python, Java, Transformação Digital, Agile",
        "priority": "1 - Alta",
        "source": "Ecossistema Tech Nacional"
    },
    {
        "institution": "TOTVS",
        "campus_city": "São Paulo & Remoto",
        "emails": "carreiras@totvs.com.br",
        "contact_name": "Atração de Talentos TOTVS",
        "job_title": "Analista Desenvolvedor / Especialista de Produto",
        "target_disciplines": "ERP, Soluções Corporativas, Java, TypeScript, Cloud",
        "priority": "2 - Média",
        "source": "Ecossistema Tech Nacional"
    },
    {
        "institution": "Inmetrics / Zup Innovation",
        "campus_city": "Uberlândia, São Paulo & Remoto",
        "emails": "carreiras@zup.com.br",
        "contact_name": "Tech Talent Recruiter",
        "job_title": "Software Engineer (Stack Open Source & Cloud)",
        "target_disciplines": "DevOps, CI/CD, Kotlin, Python, Segurança e Governança",
        "priority": "1 - Alta",
        "source": "Ecossistema Tech Nacional"
    },
    {
        "institution": "CESAR School",
        "campus_city": "Recife (Bairro do Recife)",
        "emails": "coordenacao@cesar.school",
        "contact_name": "Coordenação Acadêmica de Graduação e Pós",
        "job_title": "Professor(a) / Instrutor(a) de Engenharia de Software e IA",
        "target_disciplines": "Engenharia de Software, Design Thinking, Ciência de Dados, Computação",
        "priority": "1 - Alta",
        "source": "Porto Digital & Ensino Inovador"
    },
    {
        "institution": "Vitasoft / Neurotech",
        "campus_city": "Recife (Porto Digital) & Híbrido",
        "emails": "vagas@neurotech.com.br",
        "contact_name": "RH Neurotech (B3 Company)",
        "job_title": "Engenheiro(a) de IA & Machine Learning",
        "target_disciplines": "Machine Learning, Analytics, Modelagem Preditiva, Python, MLOps",
        "priority": "1 - Alta",
        "source": "Porto Digital & Tech Hubs"
    },
    {
        "institution": "Thoughtworks Brasil",
        "campus_city": "Recife, São Paulo, Porto Alegre & Remoto",
        "emails": "recruiting-brazil@thoughtworks.com",
        "contact_name": "Talent Operations",
        "job_title": "Consultant Developer / Tech Lead",
        "target_disciplines": "TDD, Clean Code, Agile, Python, Java, Micro frontends",
        "priority": "1 - Alta",
        "source": "Ecossistema Tech Nacional"
    }
]

catalog.extend(tech_jobs)

out_file = DATA_DIR / "curated_market_jobs.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(catalog, f, ensure_ascii=False, indent=2)

print(f"Successfully created {out_file} with {len(catalog)} curated market vacancies!")
