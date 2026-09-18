# -*- coding: utf-8 -*-
"""
Multi-User SMTP Dispatcher & Email Connectivity Engine.
Handles TLS/SSL connections, attachments, test verifications, dry-run simulation,
and dispatch audit logging.
"""

import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from database import log_dispatch, update_vacancy_status

def test_smtp_connection(smtp_host: str, smtp_port: int, smtp_user: str, smtp_pass: str, use_ssl: bool = False) -> tuple[bool, str]:
    """Tests if the provided SMTP credentials can connect and authenticate."""
    try:
        if use_ssl or smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.ehlo()
            server.starttls()
            server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.quit()
        return True, "Conexão e autenticação SMTP realizadas com sucesso!"
    except Exception as e:
        return False, f"Falha na autenticação SMTP: {str(e)}"

def send_tailored_application_email(
    user_id: int,
    vacancy_id: int,
    institution: str,
    recipient_emails: str,
    subject: str,
    body_text: str,
    pdf_attachment_path: str,
    smtp_config: dict,
    is_dry_run: bool = False
) -> tuple[bool, str]:
    """
    Dispatches a personalized email with the tailored PDF resume attached.
    If is_dry_run=True, simulates the dispatch and logs it without contacting the mail server.
    """
    first_email = [e.strip() for e in recipient_emails.replace(";", ",").split(",") if e.strip() and "@" in e]
    if not first_email:
        return False, "Nenhum endereço de e-mail válido encontrado para esta vaga."
    
    target_email = first_email[0]

    # Dry-run / Simulation mode
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
        return True, f"Simulação bem-sucedida para {target_email}."

    # Real SMTP Dispatch
    smtp_host = smtp_config.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(smtp_config.get("smtp_port", 587))
    smtp_user = smtp_config.get("smtp_user", "")
    smtp_pass = smtp_config.get("smtp_password", "")
    sender_name = smtp_config.get("sender_name", smtp_user)
    use_ssl = bool(smtp_config.get("use_ssl", 0))

    if not smtp_user or not smtp_pass:
        return False, "Configurações de SMTP incompletas. Cadastre seu e-mail e senha de aplicativo."

    msg = MIMEMultipart()
    msg['From'] = f"{sender_name} <{smtp_user}>"
    msg['To'] = target_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

    # Attach PDF
    pdf_path = Path(pdf_attachment_path)
    if pdf_path.exists():
        with open(pdf_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=pdf_path.name)
            part['Content-Disposition'] = f'attachment; filename="{pdf_path.name}"'
            msg.attach(part)
    else:
        return False, f"Arquivo PDF anexado não foi encontrado em: {pdf_attachment_path}"

    try:
        if use_ssl or smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.ehlo()
            server.starttls()
            server.ehlo()

        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [target_email], msg.as_string())
        server.quit()

        log_dispatch(
            user_id=user_id,
            vacancy_id=vacancy_id,
            institution=institution,
            recipient_email=target_email,
            subject=subject,
            body_text=body_text,
            tailored_pdf_path=pdf_attachment_path,
            status="Enviado",
            error_message=""
        )
        update_vacancy_status(user_id, vacancy_id, "Enviado")
        return True, f"E-mail enviado com sucesso para {target_email}!"

    except Exception as e:
        err_msg = str(e)
        log_dispatch(
            user_id=user_id,
            vacancy_id=vacancy_id,
            institution=institution,
            recipient_email=target_email,
            subject=subject,
            body_text=body_text,
            tailored_pdf_path=pdf_attachment_path,
            status="Erro",
            error_message=err_msg
        )
        return False, f"Erro ao enviar para {target_email}: {err_msg}"
