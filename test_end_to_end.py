# -*- coding: utf-8 -*-
"""
End-to-end integration test for LattesJobAutoApply.
Tests user creation, profile storage, vacancy import from Excel,
dynamic tailoring, PDF resume generation, and dry-run email dispatch.
"""

from pathlib import Path
from database import (
    register_user, authenticate_user,
    save_profile, get_profile,
    save_smtp_config, get_smtp_config,
    get_user_vacancies, get_user_dispatches
)
from tailor_engine import tailor_for_vacancy
from pdf_engine import generate_tailored_pdf
from email_engine import send_tailored_application_email
from vacancy_service import import_vacancies_from_file

def run_tests():
    print("=== TEST 1: User Registration & Auth ===")
    ok, msg = register_user("joyce_test", "joyce.test@ufpe.br", "senhaSegura123!")
    print("Register result:", ok, msg)
    user = authenticate_user("joyce_test", "senhaSegura123!")
    assert user is not None, "Authentication failed!"
    print("User authenticated:", user["username"], "ID:", user["id"])

    user_id = user["id"]

    print("\n=== TEST 2: Candidate Profile Management ===")
    profile_data = {
        "summary": "Engenheira de Produção com sólida atuação na docência do ensino superior, Doutoranda UFPE (CAPES 7) e Mestre UFRN.",
        "degrees": [
            {"type": "Doutorado", "description": "Doutorado em Engenharia de Produção - UFPE (Em andamento)"},
            {"type": "Mestrado", "description": "Mestrado em Engenharia de Produção - UFRN"},
            {"type": "Graduação", "description": "Graduação em Engenharia de Produção - UFERSA"},
            {"type": "Técnico", "description": "Curso Técnico em Segurança do Trabalho - IFRN"}
        ],
        "teaching_experience": [
            "Professora Substituta do Magistério Superior - UFERSA (2022–2024)",
            "Regência de turmas: PCP I e II, Gestão de Operações em Serviços, Gestão de Projetos, Projeto Integrado, SST e Custos/POC"
        ],
        "advising_count": 23,
        "jury_count": 42,
        "publications": {
            "articles": [
                "DAMASCENO, M. A. A.; MAIA, J. A. et al. Case Studies on Transport Policy (Elsevier, 2025)."
            ]
        },
        "languages": ["Inglês", "Espanhol", "Português"]
    }

    save_profile(
        user_id=user_id,
        full_name="Joyce Abreu Maia",
        phone="(84) 9XXXX-XXXX",
        lattes_url="http://lattes.cnpq.br/1932437406947269",
        linkedin_url="https://linkedin.com/in/joyceabreumaia",
        target_locations="Recife - PE / Mossoró - RN / Natal - RN",
        lattes_data=profile_data
    )
    saved_prof = get_profile(user_id)
    assert saved_prof["full_name"] == "Joyce Abreu Maia"
    print("Profile successfully saved & retrieved:", saved_prof["full_name"])

    print("\n=== TEST 3: User SMTP Configuration ===")
    save_smtp_config(
        user_id=user_id,
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="joyce.test@gmail.com",
        smtp_password_plain="abcd efgh ijkl mnop",
        sender_name="Profa. Joyce Abreu Maia"
    )
    smtp_cfg = get_smtp_config(user_id)
    assert smtp_cfg["smtp_password"] == "abcd efgh ijkl mnop", "Password decryption failed!"
    print("SMTP credentials securely stored and decrypted correctly.")

    print("\n=== TEST 4: Vacancy Import from Master Spreadsheet ===")
    excel_path = Path("g:/Meu Drive/Planilha_Contatos_Docencia_Joyce_Maia.xlsx")
    if excel_path.exists():
        count, errs = import_vacancies_from_file(user_id, excel_path, sheet_name="Recife e RMR (PE)")
        print(f"Imported {count} vacancies from Excel. Errors: {errs}")
        vacancies = get_user_vacancies(user_id)
        print(f"Total vacancies in user account: {len(vacancies)}")
        assert len(vacancies) > 0, "No vacancies imported!"
    else:
        print("Spreadsheet not found at path, skipping excel import test.")

    print("\n=== TEST 5: Tailoring & Dynamic PDF Resume Generation ===")
    sample_vac = {
        "id": 1,
        "institution": "UNICAP",
        "campus_city": "Recife (Boa Vista)",
        "emails": "mario.junior@unicap.br",
        "contact_name": "Prof. Dr. Mário Gomes da Silva Júnior",
        "job_title": "Engenharia de Produção",
        "target_disciplines": "PCP, Pesquisa Operacional, Custos, Projetos"
    }

    tailored_app = tailor_for_vacancy(saved_prof, sample_vac)
    print("Tailored headline:", tailored_app.tailored_headline)
    print("Match score:", tailored_app.match_score)
    print("Email subject:", tailored_app.email_subject)

    pdf_output = generate_tailored_pdf(tailored_app, saved_prof)
    assert Path(pdf_output).exists(), "Tailored PDF was not generated!"
    print("Tailored PDF generated successfully at:", pdf_output)

    print("\n=== TEST 6: Simulated Email Dispatch (Dry-Run) ===")
    ok, msg = send_tailored_application_email(
        user_id=user_id,
        vacancy_id=sample_vac["id"],
        institution=sample_vac["institution"],
        recipient_emails=sample_vac["emails"],
        subject=tailored_app.email_subject,
        body_text=tailored_app.email_body,
        pdf_attachment_path=pdf_output,
        smtp_config=smtp_cfg,
        is_dry_run=True
    )
    assert ok, f"Dispatch simulation failed: {msg}"
    print("Dispatch result:", ok, msg)

    dispatches = get_user_dispatches(user_id)
    assert len(dispatches) > 0, "No dispatches logged in audit table!"
    print(f"Audit log verified: {len(dispatches)} dispatches recorded.")
    print("Sample log status:", dispatches[0]["status"], "| Recipient:", dispatches[0]["recipient_email"])

    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    run_tests()
