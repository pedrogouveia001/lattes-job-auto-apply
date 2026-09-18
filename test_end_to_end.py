# -*- coding: utf-8 -*-
"""
End-to-end integration test for DocênciaMatch / LattesJobAutoApply.
Tests user creation, Google OAuth user handling, profile storage, vacancy import,
dynamic tailoring, PDF resume generation, and zero-password email dispatch.
"""

from pathlib import Path
from database import (
    register_user, authenticate_user, get_or_create_google_user,
    save_profile, get_profile,
    save_api_config, get_api_config,
    get_user_vacancies, get_user_dispatches
)
from tailor_engine import tailor_for_vacancy
from pdf_engine import generate_tailored_pdf
from email_engine import send_tailored_application_email, generate_gmail_web_intent
from vacancy_service import import_vacancies_from_file

def run_tests():
    print("=== TEST 1: User Registration & Auth ===")
    ok, msg = register_user("joyce_test", "joyce.test@ufpe.br", "senhaSegura123!")
    print("Register result:", ok, msg)
    user = authenticate_user("joyce_test", "senhaSegura123!")
    assert user is not None, "Authentication failed!"
    print("User authenticated:", user["username"], "ID:", user["id"])

    user_id = user["id"]

    print("\n=== TEST 2: Google OAuth User Handling ===")
    google_user = get_or_create_google_user("pedrogouveia001@gmail.com", "Pedro Gouveia")
    assert google_user is not None, "Google OAuth user creation failed!"
    assert google_user["email"] == "pedrogouveia001@gmail.com"
    print("Google OAuth User verified:", google_user["username"], "ID:", google_user["id"])

    print("\n=== TEST 3: Candidate Profile Management ===")
    profile_data = {
        "summary": "Engenheira de Produção com sólida atuação na docência do ensino superior, Doutoranda UFPE (CAPES 7) e Mestre UFRN.",
        "degrees": [
            {"type": "Doutorado", "description": "Doutorado em Engenharia de Produção - UFPE (Em andamento)"},
            {"type": "Mestrado", "description": "Mestrado em Engenharia de Produção - UFRN"},
            {"type": "Graduação", "description": "Graduação em Engenharia de Produção - UFERSA"}
        ],
        "teaching_experience": [
            "Professora Substituta do Magistério Superior - UFERSA (2022–2024)"
        ]
    }

    save_profile(
        user_id=user_id,
        full_name="Joyce Abreu Maia",
        phone="(81) 99763-7186",
        lattes_url="http://lattes.cnpq.br/4988358485750015",
        linkedin_url="https://linkedin.com/in/joyceabreumaia",
        target_locations="Recife - PE / Mossoró - RN / Natal - RN / Remoto EAD",
        lattes_data=profile_data
    )
    saved_prof = get_profile(user_id)
    assert saved_prof["full_name"] == "Joyce Abreu Maia"
    print("Profile successfully saved & retrieved:", saved_prof["full_name"])

    print("\n=== TEST 4: Zero-Password API Configuration ===")
    save_api_config(
        user_id=user_id,
        provider="gmail_web",
        sender_email="joyce.maia@ufpe.br",
        sender_name="Joyce Abreu Maia"
    )
    api_cfg = get_api_config(user_id)
    assert api_cfg["provider"] == "gmail_web"
    assert "smtp_password" not in api_cfg, "Personal password detected! Security violation."
    print("Zero-Password API Config successfully verified (no passwords stored).")

    print("\n=== TEST 5: Vacancy Import from Master Spreadsheet ===")
    excel_path = Path("g:/Meu Drive/Planilha_Contatos_Docencia_Joyce_Maia.xlsx")
    if excel_path.exists():
        count = import_vacancies_from_file(user_id, excel_path)
        print(f"Imported {count} vacancies from Excel.")
        vacancies = get_user_vacancies(user_id)
        assert len(vacancies) > 0, "No vacancies imported!"
        print(f"Total vacancies in user account: {len(vacancies)}")
    else:
        print("Spreadsheet not found, skipping excel test.")

    print("\n=== TEST 6: Tailoring & Dynamic PDF Generation ===")
    sample_vac = {
        "id": 1,
        "institution": "UNICAP",
        "campus_city": "Recife (Boa Vista)",
        "emails": "mario.junior@unicap.br",
        "contact_name": "Prof. Dr. Mário Gomes da Silva Júnior",
        "job_title": "Engenharia de Produção",
        "target_disciplines": "PCP, Pesquisa Operacional, Custos, Projetos"
    }

    tailored_app = tailor_for_vacancy(saved_prof.get("lattes_data", {}), sample_vac)
    pdf_output = generate_tailored_pdf(tailored_app, sample_vac["institution"], sample_vac["id"])
    assert Path(pdf_output).exists(), "Tailored PDF was not generated!"
    print("Tailored PDF generated successfully at:", pdf_output)

    print("\n=== TEST 7: Zero-Password Dispatch (Gmail Web Intent & Dry-Run) ===")
    # 1. Test Gmail Web Intent link generation
    gmail_link = generate_gmail_web_intent(sample_vac["emails"], tailored_app["email_subject"], tailored_app["email_body"])
    assert "mail.google.com" in gmail_link
    assert "mario.junior%40unicap.br" in gmail_link
    print("Gmail Web Intent URL generated successfully.")

    # 2. Test Dry-Run dispatch
    ok, msg = send_tailored_application_email(
        user_id=user_id,
        vacancy_id=sample_vac["id"],
        institution=sample_vac["institution"],
        recipient_emails=sample_vac["emails"],
        subject=tailored_app["email_subject"],
        body_text=tailored_app["email_body"],
        pdf_attachment_path=pdf_output,
        api_config=api_cfg,
        is_dry_run=True
    )
    assert ok, f"Dispatch simulation failed: {msg}"
    print("Dispatch result:", ok, msg)

    dispatches = get_user_dispatches(user_id)
    assert len(dispatches) > 0, "No dispatches logged in audit table!"
    print(f"Audit log verified: {len(dispatches)} dispatches recorded.")

    print("\n[ALL 7 TESTS PASSED WITH ZERO PASSWORD REQUIREMENT!]")

if __name__ == "__main__":
    run_tests()
