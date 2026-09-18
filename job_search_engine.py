# -*- coding: utf-8 -*-
"""
OmniMatch Autonomous Job Discovery & Search Engine.
Provides multi-source job hunting:
1. Internal Market Catalog (Curated Academic, Tech, Corporate & Remote opportunities)
2. Live Online APIs (Jobicy, Arbeitnow, and remote job feeds)
3. Dynamic relevance matching and automatic insertion into user's vacancy database.
"""

import json
import urllib.request
import urllib.parse
from pathlib import Path
from config import BASE_DIR, DATA_DIR
from database import add_vacancy, get_connection

CATALOG_PATH = DATA_DIR / "curated_market_jobs.json"

def fetch_online_remote_jobs(query: str = "", limit: int = 15) -> list[dict]:
    """Fetches live remote job postings from public APIs."""
    jobs = []
    
    # 1. Jobicy Remote Jobs API
    try:
        url = "https://jobicy.com/api/v2/remote-jobs?count=20"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (OmniMatch JobHunter/1.0)"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("jobs", []):
                title = item.get("jobTitle", "").strip()
                company = item.get("companyName", "").strip()
                loc = item.get("jobGeo", "Remoto Global")
                url_apply = item.get("url", "")
                excerpt = item.get("jobExcerpt", "")
                
                # Check keyword relevance if query provided
                if query:
                    q_tokens = [t.strip().lower() for t in query.split(",") if t.strip()]
                    match = any(token in (title + " " + excerpt).lower() for token in q_tokens)
                    if not match:
                        continue
                
                jobs.append({
                    "institution": company or "Empresa Remota (Jobicy)",
                    "campus_city": f"Remoto ({loc})",
                    "emails": url_apply if url_apply else f"candidatura@{company.lower().replace(' ', '')}.com",
                    "contact_name": "Portal de Carreiras / Recrutador",
                    "job_title": title,
                    "target_disciplines": excerpt[:150] if excerpt else "Tecnologia, Dados, Produto",
                    "priority": "1 - Alta",
                    "source": "Web API (Jobicy Live)"
                })
                if len(jobs) >= limit:
                    break
    except Exception:
        pass

    # 2. Arbeitnow API (if needed to complement)
    if len(jobs) < limit:
        try:
            url = "https://www.arbeitnow.com/api/job-board-api"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (OmniMatch JobHunter/1.0)"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("data", []):
                    title = item.get("title", "").strip()
                    company = item.get("company_name", "").strip()
                    loc = item.get("location", "Remoto")
                    url_apply = item.get("url", "")
                    tags = " ".join(item.get("tags", []))
                    
                    if query:
                        q_tokens = [t.strip().lower() for t in query.split(",") if t.strip()]
                        match = any(token in (title + " " + tags).lower() for token in q_tokens)
                        if not match:
                            continue
                            
                    jobs.append({
                        "institution": company or "Empresa Tech",
                        "campus_city": f"{loc} (Remoto)",
                        "emails": url_apply if url_apply else f"vagas@{company.lower().replace(' ', '')}.com",
                        "contact_name": "Talent Acquisition",
                        "job_title": title,
                        "target_disciplines": tags if tags else "Engenharia de Software, Cloud, Produto",
                        "priority": "2 - Média",
                        "source": "Web API (Arbeitnow Live)"
                    })
                    if len(jobs) >= limit:
                        break
        except Exception:
            pass

    return jobs

def load_curated_catalog() -> list[dict]:
    """Loads the pre-compiled market catalog."""
    if not CATALOG_PATH.exists():
        return []
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def search_market_vacancies(user_id: int, target_roles: str = "", target_locations: str = "", fetch_online: bool = True) -> tuple[int, list[dict]]:
    """
    Executes a comprehensive job search across both the curated market database
    and live online job APIs, populating the user's vacancies table.
    """
    conn = get_connection()
    c = conn.cursor()
    
    # Get existing vacancies for this user to avoid duplicates
    existing = c.execute("SELECT institution, job_title FROM vacancies WHERE user_id = ?", (user_id,)).fetchall()
    existing_keys = {(r["institution"].strip().lower(), r["job_title"].strip().lower()) for r in existing}
    conn.close()

    candidates_to_add = []

    # 1. Search in Curated Market Catalog
    catalog = load_curated_catalog()
    role_tokens = [t.strip().lower() for t in target_roles.replace("/", ",").split(",") if t.strip()]
    loc_tokens = [t.strip().lower() for t in target_locations.replace("/", ",").split(",") if t.strip()]

    for item in catalog:
        inst = item.get("institution", "").lower()
        title = item.get("job_title", "").lower()
        disc = item.get("target_disciplines", "").lower()
        city = item.get("campus_city", "").lower()

        # Score relevance
        role_match = True
        if role_tokens:
            role_match = any(token in (title + " " + disc + " " + inst) for token in role_tokens)
            
        loc_match = True
        if loc_tokens:
            loc_match = any(token in city for token in loc_tokens)

        if role_match or loc_match:
            key = (item["institution"].strip().lower(), item["job_title"].strip().lower())
            if key not in existing_keys:
                candidates_to_add.append(item)
                existing_keys.add(key)

    # 2. Fetch Live Online Jobs if requested
    if fetch_online and role_tokens:
        online_jobs = fetch_online_remote_jobs(query=target_roles, limit=10)
        for oj in online_jobs:
            key = (oj["institution"].strip().lower(), oj["job_title"].strip().lower())
            if key not in existing_keys:
                candidates_to_add.append(oj)
                existing_keys.add(key)

    # If no specific filter match, include top curated market jobs so user always has results
    if not candidates_to_add and not role_tokens and not loc_tokens:
        for item in catalog[:25]:
            key = (item["institution"].strip().lower(), item["job_title"].strip().lower())
            if key not in existing_keys:
                candidates_to_add.append(item)
                existing_keys.add(key)

    # Insert found vacancies into database
    added_count = 0
    for vac in candidates_to_add:
        add_vacancy(
            user_id=user_id,
            institution=vac["institution"],
            campus_city=vac["campus_city"],
            emails=vac["emails"],
            contact_name=vac.get("contact_name", "Recrutador / RH"),
            job_title=vac.get("job_title", "Oportunidade"),
            target_disciplines=vac.get("target_disciplines", ""),
            priority=vac.get("priority", "1 - Alta"),
            source=vac.get("source", "Busca de Mercado OmniMatch")
        )
        added_count += 1

    return added_count, candidates_to_add

def seed_default_vacancies_if_empty(user_id: int) -> int:
    """If user's vacancy count is zero, populates the account with the curated baseline dataset."""
    conn = get_connection()
    c = conn.cursor()
    cnt = c.execute("SELECT count(*) FROM vacancies WHERE user_id = ?", (user_id,)).fetchone()[0]
    conn.close()

    if cnt == 0:
        added_count, _ = search_market_vacancies(user_id=user_id, target_roles="", target_locations="", fetch_online=False)
        return added_count
    return 0
