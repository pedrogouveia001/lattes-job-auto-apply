# -*- coding: utf-8 -*-
"""
Database & Multi-User Layer for LattesJobAutoApply.
Provides schema creation, user authentication, profile storage, vacancy management,
and audit logs with strict tenant isolation.
Supports SQLite (local/Streamlit) and PostgreSQL (Supabase/Production).
"""

import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path
from config import DATA_DIR, encrypt_secret, decrypt_secret

DB_PATH = DATA_DIR / "app_database.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema with multi-tenant tables."""
    conn = get_connection()
    c = conn.cursor()

    # Users Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Candidate Profiles Table (1 per user)
    c.execute("""
    CREATE TABLE IF NOT EXISTS candidate_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        lattes_url TEXT,
        lattes_pdf_path TEXT,
        lattes_data_json TEXT,
        linkedin_url TEXT,
        target_locations TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # User SMTP Configurations Table (1 per user)
    c.execute("""
    CREATE TABLE IF NOT EXISTS user_smtp_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        smtp_host TEXT NOT NULL DEFAULT 'smtp.gmail.com',
        smtp_port INTEGER NOT NULL DEFAULT 587,
        smtp_user TEXT NOT NULL,
        smtp_password_enc TEXT NOT NULL,
        sender_name TEXT NOT NULL,
        use_ssl INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # Vacancies Table (Isolated per user)
    c.execute("""
    CREATE TABLE IF NOT EXISTS vacancies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        institution TEXT NOT NULL,
        campus_city TEXT,
        emails TEXT NOT NULL,
        contact_name TEXT,
        job_title TEXT,
        target_disciplines TEXT,
        priority TEXT DEFAULT '1 - Alta',
        source TEXT DEFAULT 'Importada',
        status TEXT DEFAULT 'A Enviar',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    """)

    # Dispatches & Audit Log Table
    c.execute("""
    CREATE TABLE IF NOT EXISTS dispatches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        vacancy_id INTEGER,
        institution TEXT,
        recipient_email TEXT NOT NULL,
        subject TEXT NOT NULL,
        body_text TEXT NOT NULL,
        tailored_pdf_path TEXT,
        status TEXT NOT NULL, -- 'Enviado', 'Simulado', 'Erro'
        error_message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        FOREIGN KEY (vacancy_id) REFERENCES vacancies (id) ON DELETE SET NULL
    )
    """)

    conn.commit()
    conn.close()

# ----------------- User Auth Functions -----------------

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  (username.strip().lower(), email.strip().lower(), hash_password(password)))
        conn.commit()
        return True, "Usuário cadastrado com sucesso!"
    except sqlite3.IntegrityError:
        return False, "Nome de usuário ou e-mail já cadastrado."
    finally:
        conn.close()

def authenticate_user(username_or_email: str, password: str):
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM users WHERE (username = ? OR email = ?) AND password_hash = ?"
    user = c.execute(query, (username_or_email.strip().lower(), username_or_email.strip().lower(), hash_password(password))).fetchone()
    conn.close()
    return dict(user) if user else None

# ----------------- Profile Management -----------------

def save_profile(user_id: int, full_name: str, phone: str, lattes_url: str,
                 linkedin_url: str, target_locations: str, lattes_data: dict, lattes_pdf_path: str = ""):
    conn = get_connection()
    c = conn.cursor()
    lattes_json = json.dumps(lattes_data, ensure_ascii=False)
    
    existing = c.execute("SELECT id FROM candidate_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        c.execute("""
            UPDATE candidate_profiles 
            SET full_name = ?, phone = ?, lattes_url = ?, linkedin_url = ?, 
                target_locations = ?, lattes_data_json = ?, lattes_pdf_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (full_name, phone, lattes_url, linkedin_url, target_locations, lattes_json, lattes_pdf_path, user_id))
    else:
        c.execute("""
            INSERT INTO candidate_profiles 
            (user_id, full_name, phone, lattes_url, linkedin_url, target_locations, lattes_data_json, lattes_pdf_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, full_name, phone, lattes_url, linkedin_url, target_locations, lattes_json, lattes_pdf_path))
    conn.commit()
    conn.close()

def get_profile(user_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM candidate_profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    if data.get("lattes_data_json"):
        try:
            data["lattes_data"] = json.loads(data["lattes_data_json"])
        except Exception:
            data["lattes_data"] = {}
    else:
        data["lattes_data"] = {}
    return data

# ----------------- SMTP Config Management -----------------

def save_smtp_config(user_id: int, smtp_host: str, smtp_port: int, smtp_user: str,
                     smtp_password_plain: str, sender_name: str, use_ssl: bool = False):
    conn = get_connection()
    c = conn.cursor()
    enc_pwd = encrypt_secret(smtp_password_plain)
    existing = c.execute("SELECT id FROM user_smtp_configs WHERE user_id = ?", (user_id,)).fetchone()
    if existing:
        c.execute("""
            UPDATE user_smtp_configs
            SET smtp_host = ?, smtp_port = ?, smtp_user = ?, smtp_password_enc = ?, 
                sender_name = ?, use_ssl = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (smtp_host, smtp_port, smtp_user, enc_pwd, sender_name, 1 if use_ssl else 0, user_id))
    else:
        c.execute("""
            INSERT INTO user_smtp_configs (user_id, smtp_host, smtp_port, smtp_user, smtp_password_enc, sender_name, use_ssl)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, smtp_host, smtp_port, smtp_user, enc_pwd, sender_name, 1 if use_ssl else 0))
    conn.commit()
    conn.close()

def get_smtp_config(user_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM user_smtp_configs WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["smtp_password"] = decrypt_secret(data.get("smtp_password_enc", ""))
    return data

# ----------------- Vacancy Management -----------------

def add_vacancy(user_id: int, institution: str, campus_city: str, emails: str,
                contact_name: str = "", job_title: str = "", target_disciplines: str = "",
                priority: str = "1 - Alta", source: str = "Importada"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO vacancies (user_id, institution, campus_city, emails, contact_name, job_title, target_disciplines, priority, source, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'A Enviar')
    """, (user_id, institution, campus_city, emails, contact_name, job_title, target_disciplines, priority, source))
    vac_id = c.lastrowid
    conn.commit()
    conn.close()
    return vac_id

def get_user_vacancies(user_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM vacancies WHERE user_id = ? ORDER BY priority ASC, id DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_vacancy_status(user_id: int, vacancy_id: int, new_status: str):
    conn = get_connection()
    conn.execute("UPDATE vacancies SET status = ? WHERE id = ? AND user_id = ?", (new_status, vacancy_id, user_id))
    conn.commit()
    conn.close()

def delete_user_vacancies(user_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM vacancies WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# ----------------- Dispatch Audit Logging -----------------

def log_dispatch(user_id: int, vacancy_id: int, institution: str, recipient_email: str,
                 subject: str, body_text: str, tailored_pdf_path: str, status: str, error_message: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO dispatches (user_id, vacancy_id, institution, recipient_email, subject, body_text, tailored_pdf_path, status, error_message)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, vacancy_id, institution, recipient_email, subject, body_text, tailored_pdf_path, status, error_message))
    conn.commit()
    conn.close()

def get_user_dispatches(user_id: int):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM dispatches WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Auto-initialize DB on import
init_db()
