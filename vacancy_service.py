# -*- coding: utf-8 -*-
"""
Vacancy Ingestion & Autonomous Discovery Service.
Imports CSV and Excel files with intelligent per-sheet fuzzy column resolution
and populates the user's vacancy database.
"""

import pandas as pd
from pathlib import Path
from database import add_vacancy

def _map_columns(columns: list) -> dict:
    """Maps columns using fuzzy matching."""
    col_map = {}
    for col in columns:
        c_low = str(col).lower()
        if any(w in c_low for w in ["instituição", "instituicao", "empresa", "faculdade", "universidade", "rede", "grupo"]):
            if "institution" not in col_map:
                col_map["institution"] = col
        elif any(w in c_low for w in ["campi", "cidade", "polo", "polos", "sede", "local", "região", "regiao"]):
            if "campus_city" not in col_map:
                col_map["campus_city"] = col
        elif any(w in c_low for w in ["e-mail", "email", "emails"]):
            if "emails" not in col_map:
                col_map["emails"] = col
        elif any(w in c_low for w in ["responsável", "responsavel", "coordenação", "coordenacao", "contato", "destaques"]):
            if "contact_name" not in col_map:
                col_map["contact_name"] = col
        elif any(w in c_low for w in ["cargo", "vaga", "função", "funcao", "perfis", "cursos"]):
            if "job_title" not in col_map:
                col_map["job_title"] = col
        elif any(w in c_low for w in ["disciplina", "área", "area"]):
            if "target_disciplines" not in col_map:
                col_map["target_disciplines"] = col
        elif any(w in c_low for w in ["prioridade"]):
            if "priority" not in col_map:
                col_map["priority"] = col
    return col_map

def import_vacancies_from_file(user_id: int, file_path: str | Path, sheet_name: str = None) -> tuple[int, list[str]]:
    """
    Imports vacancies from a CSV or Excel file for a specific user.
    Processes each sheet individually with independent fuzzy column mapping.
    """
    p = Path(file_path)
    if not p.exists():
        return 0, [f"Arquivo não encontrado: {file_path}"]

    imported_count = 0
    errors = []

    try:
        if p.suffix.lower() in [".xlsx", ".xls"]:
            excel_file = pd.ExcelFile(p)
            sheets_to_read = [sheet_name] if sheet_name and sheet_name in excel_file.sheet_names else excel_file.sheet_names
            
            for s in sheets_to_read:
                # Try header row 3 first, fallback to 0
                df_sheet = pd.read_excel(p, sheet_name=s, header=3)
                col_map = _map_columns(df_sheet.columns)
                if not col_map.get("institution") or not col_map.get("emails"):
                    df_sheet = pd.read_excel(p, sheet_name=s, header=0)
                    col_map = _map_columns(df_sheet.columns)
                
                inst_col = col_map.get("institution")
                email_col = col_map.get("emails")
                
                if not inst_col or not email_col:
                    errors.append(f"Aba '{s}': Colunas de instituição ou email não encontradas.")
                    continue

                for idx, row in df_sheet.iterrows():
                    inst_val = str(row.get(inst_col, "")).strip()
                    email_val = str(row.get(email_col, "")).strip()

                    if not inst_val or not email_val or inst_val.lower() == "nan" or email_val.lower() == "nan" or "@" not in email_val:
                        continue

                    campus_val = str(row.get(col_map.get("campus_city"), "")).strip() if col_map.get("campus_city") else ""
                    contact_val = str(row.get(col_map.get("contact_name"), "")).strip() if col_map.get("contact_name") else ""
                    job_val = str(row.get(col_map.get("job_title"), "Docência no Ensino Superior")).strip() if col_map.get("job_title") else "Docência no Ensino Superior"
                    disc_val = str(row.get(col_map.get("target_disciplines"), "")).strip() if col_map.get("target_disciplines") else ""
                    prio_val = str(row.get(col_map.get("priority"), "1 - Alta")).strip() if col_map.get("priority") else "1 - Alta"

                    if campus_val.lower() == "nan": campus_val = ""
                    if contact_val.lower() == "nan": contact_val = ""
                    if job_val.lower() == "nan": job_val = "Docência no Ensino Superior"
                    if disc_val.lower() == "nan": disc_val = ""
                    if prio_val.lower() == "nan": prio_val = "1 - Alta"

                    add_vacancy(
                        user_id=user_id,
                        institution=inst_val,
                        campus_city=campus_val,
                        emails=email_val,
                        contact_name=contact_val,
                        job_title=job_val,
                        target_disciplines=disc_val,
                        priority=prio_val,
                        source=f"Aba: {s}"
                    )
                    imported_count += 1
        else:
            df = pd.read_csv(p)
            col_map = _map_columns(df.columns)
            inst_col = col_map.get("institution")
            email_col = col_map.get("emails")
            if not inst_col or not email_col:
                return 0, [f"Colunas de instituição ou email não encontradas no CSV: {list(df.columns)}"]

            for idx, row in df.iterrows():
                inst_val = str(row.get(inst_col, "")).strip()
                email_val = str(row.get(email_col, "")).strip()
                if not inst_val or not email_val or "@" not in email_val:
                    continue

                campus_val = str(row.get(col_map.get("campus_city"), "")).strip() if col_map.get("campus_city") else ""
                contact_val = str(row.get(col_map.get("contact_name"), "")).strip() if col_map.get("contact_name") else ""
                job_val = str(row.get(col_map.get("job_title"), "Docência")).strip() if col_map.get("job_title") else "Docência"
                disc_val = str(row.get(col_map.get("target_disciplines"), "")).strip() if col_map.get("target_disciplines") else ""
                prio_val = str(row.get(col_map.get("priority"), "1 - Alta")).strip() if col_map.get("priority") else "1 - Alta"

                add_vacancy(
                    user_id=user_id,
                    institution=inst_val,
                    campus_city=campus_val,
                    emails=email_val,
                    contact_name=contact_val,
                    job_title=job_val,
                    target_disciplines=disc_val,
                    priority=prio_val,
                    source="CSV Importado"
                )
                imported_count += 1

    except Exception as e:
        return imported_count, [f"Erro na importação: {str(e)}"]

    return imported_count, errors
