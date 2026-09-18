# -*- coding: utf-8 -*-
"""
Zero-Password Email & API Dispatch Engine for LattesJobAutoApply.
Eliminates the security risk of requesting user personal email passwords.
Provides:
1. Resend API (HTTP REST with Bearer token)
2. Brevo API (HTTP REST with api-key)
3. 1-Click Gmail Web Intent (Opens personal Gmail in browser with pre-filled letter)
4. Dry-Run Simulation (Tests generation and ATS matching without contacting servers)
"""

import os
import json
import base64
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from database import log_dispatch, update_vacancy_status

def generate_gmail_web_intent(recipient_email: str, subject: str, body_text: str) -> str:
    """Generates a direct URL to compose an email in Gmail Web without any credentials."""
    base = "https://mail.google.com/mail/?view=cm&fs=1"
    params = {
        "to": recipient_email,
        "su": subject,
        "body": body_text
    }
    return f"{base}&{urllib.parse.urlencode(params)}"

def send_email_via_resend(api_key: str, from_email: str, to_email: str, subject: str, body_text: str, pdf_path: Path) -> tuple[bool, str]:
    """Dispatches email via Resend API (HTTPS REST)."""
    url = "https://api.resend.com/emails"
    
    # Read PDF as base64
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": body_text,
        "attachments": [
            {
                "filename": pdf_path.name,
                "content": pdf_b64
            }
        ]
    }
    
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return True, f"Disparo realizado via Resend API! ID: {res_data.get('id', 'OK')}"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return False, f"Erro Resend API ({e.code}): {err_body}"
    except Exception as e:
        return False, f"Falha na requisição Resend: {str(e)}"

def send_email_via_brevo(api_key: str, sender_name: str, sender_email: str, to_email: str, subject: str, body_text: str, pdf_path: Path) -> tuple[bool, str]:
    """Dispatches email via Brevo API (HTTPS REST)."""
    url = "https://api.brevo.com/v3/smtp/email"
    
    with open(pdf_path, "rb") as f:
        pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email}],
        "subject": subject,
        "textContent": body_text,
        "attachment": [
            {
                "name": pdf_path.name,
                "content": pdf_b64
            }
        ]
    }
    
    headers = {
        "api-key": api_key.strip(),
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return True, f"Disparo realizado via Brevo API! ID: {res_data.get('messageId', 'OK')}"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return False, f"Erro Brevo API ({e.code}): {err_body}"
    except Exception as e:
        return False, f"Falha na requisição Brevo: {str(e)}"

def send_tailored_application_email(
    user_id: int,
    vacancy_id: int,
    institution: str,
    recipient_emails: str,
    subject: str,
    body_text: str,
    pdf_attachment_path: str,
    api_config: dict,
    is_dry_run: bool = False
) -> tuple[bool, str]:
    """
    Dispatches tailored application email without EVER requiring a user password.
    Supports Resend API, Brevo API, 1-Click Gmail Web Intent, and Dry-Run simulation.
    """
    first_email = [e.strip() for e in recipient_emails.replace(";", ",").split(",") if e.strip() and "@" in e]
    if not first_email:
        return False, "Nenhum endereço de e-mail válido encontrado para esta vaga."
    
    target_email = first_email[0]
    pdf_path = Path(pdf_attachment_path)

    # 1. Simulação / Dry-Run
    if is_dry_run:
        log_dispatch(
            user_id=user_id,
            vacancy_id=vacancy_id,
            institution=institution,
            recipient_email=target_email,
            subject=subject,
            body_text=body_text,
            tailored_pdf_path=pdf_attachment_path,
            status="Simulado (Dry-Run)",
            error_message=""
        )
        update_vacancy_status(user_id, vacancy_id, "Simulado")
        return True, f"Simulação concluída com sucesso para {target_email} (currículo PDF gerado)."

    if not pdf_path.exists():
        return False, f"Arquivo PDF não encontrado: {pdf_attachment_path}"

    provider = api_config.get("provider", "gmail_web")
    api_key = api_config.get("api_key", "").strip()
    sender_email = api_config.get("sender_email", "").strip() or "onboarding@resend.dev"
    sender_name = api_config.get("sender_name", "").strip() or "Candidata"

    # 2. Resend API Dispatch
    if provider == "resend":
        if not api_key:
            return False, "Chave de API do Resend não informada. Cadastre sua API Key ou use o modo Gmail Web."
        ok, msg = send_email_via_resend(api_key, f"{sender_name} <{sender_email}>", target_email, subject, body_text, pdf_path)
    
    # 3. Brevo API Dispatch
    elif provider == "brevo":
        if not api_key:
            return False, "Chave de API do Brevo não informada. Cadastre sua API Key ou use o modo Gmail Web."
        ok, msg = send_email_via_brevo(api_key, sender_name, sender_email, target_email, subject, body_text, pdf_path)

    # 4. Gmail Web Intent Mode (Zero Senha, Zero API Externa)
    elif provider == "gmail_web":
        gmail_url = generate_gmail_web_intent(target_email, subject, body_text)
        log_dispatch(
            user_id=user_id,
            vacancy_id=vacancy_id,
            institution=institution,
            recipient_email=target_email,
            subject=subject,
            body_text=body_text,
            tailored_pdf_path=pdf_attachment_path,
            status="Aberto no Gmail Web",
            error_message=""
        )
        update_vacancy_status(user_id, vacancy_id, "Gmail Web Preparado")
        return True, f"Gmail Web preparado para {target_email}!"

    else:
        return False, f"Provedor de API '{provider}' não suportado."

    # Log audit
    status_str = "Enviado via API" if ok else "Erro API"
    log_dispatch(
        user_id=user_id,
        vacancy_id=vacancy_id,
        institution=institution,
        recipient_email=target_email,
        subject=subject,
        body_text=body_text,
        tailored_pdf_path=pdf_attachment_path,
        status=status_str,
        error_message="" if ok else msg
    )
    if ok:
        update_vacancy_status(user_id, vacancy_id, "Enviado via API")
    return ok, msg
