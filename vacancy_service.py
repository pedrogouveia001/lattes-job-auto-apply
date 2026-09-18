# -*- coding: utf-8 -*-
"""
Vacancy Ingestion & Autonomous Discovery Service.
Imports CSV and Excel files (with fuzzy column resolution for existing spreadsheets like Joyce's)
and runs autonomous matching against open opportunities.
"""

import pandas as pd
from pathlib import Path
from database import add_vacancy

def import_vacancies_from_file(user_id: int, file_path: str | Path, sheet_name: str = None) -> tuple[int, list[str]]:
    """
    Imports vacancies from a CSV or Excel file for a specific user.
    Fuzzy-maps columns like 'Instituição', 'Campi', 'E-mails', 'Prioridade'.
    """
    p = Path(file_path)
    if not p.exists():
        return 0, [f"Arquivo não encontrado: {file_path}"]

    try:
        if p.suffix.lower() in [".xlsx", ".xls"]:
            # If sheet_name is None, read all sheets or the first
            excel_file = pd.ExcelFile(p)
            sheets_to_read = [sheet_name] if sheet_name and sheet_name in excel_file.sheet_names else excel_file.sheet_names
            dfs = []
            for s in sheets_to_read:
                df_sheet = pd.read_excel(p, sheet_name=s, header=3) # Row 4 is header in our generated sheet
                if "Instituição" not in "".join(str(c) for c in df_sheet.columns):
                    # Try reading with header=0 if not found
                    df_sheet = pd.read_excel(p, sheet_name=s, header=0)
                df_sheet["__sheet__"] = s
                dfs.append(df_sheet)
            df = pd.concat(dfs, ignore_index=True)
        else:
            df = pd.read_csv(p)
    except Exception as e:
        return 0, [f"Erro ao abrir arquivo: {str(e)}"]

    # Fuzzy column mapping
    col_map = {}
    for col in df.columns:
        c_low = str(col).lower()
        if any(w in c_low for w in ["instituição", "instituicao", "empresa", "faculdade", "universidade"]):
            col_map["institution"] = col
        elif any(w in c_low for w in ["campi", "cidade", "polo", "local", "região", "regiao"]):
            col_map["campus_city"] = col
        elif any(w in c_low for w in ["e-mail", "email", "emails"]):
            col_map["emails"] = col
        elif any(w in c_low for w in ["responsável", "responsavel", "coordenação", "coordenacao", "contato", "destaques"]):
            col_map["contact_name"] = col
        elif any(w in c_low for w in ["cargo", "vaga", "função", "funcao", "perfis"]):
            col_map["job_title"] = col
        elif any(w in c_low for w in ["disciplina", "área", "area"]):
            col_map["target_disciplines"] = col
        elif any(w in c_low for w in ["prioridade"]):
            col_map["priority"] = col

    imported_count = 0
    errors = []

    inst_col = col_map.get("institution")
    email_col = col_map.get("emails")

    if not inst_col or not email_col:
        return 0, [f"Colunas mínimas ('Instituição' e 'E-mail') não foram identificadas automaticamente. Colunas presentes: {list(df.columns)}"]

    for idx, row in df.iterrows():
        inst_val = str(row.get(inst_col, "")).strip()
        email_val = str(row.get(email_col, "")).strip()
        
        # Skip empty or header repeated rows
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
            source="Planilha Importada"
        )
        imported_count += 1

    return imported_count, errors
