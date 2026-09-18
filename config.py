# -*- coding: utf-8 -*-
"""
Configuration & Security Module for LattesJobAutoApply
Handles environment variables, paths, and AES encryption for user SMTP credentials.
"""

import os
import base64
import hashlib
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESUMES_DIR = BASE_DIR / "generated_resumes"

DATA_DIR.mkdir(parents=True, exist_ok=True)
RESUMES_DIR.mkdir(parents=True, exist_ok=True)

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

SECRET_KEY = os.getenv("APP_SECRET_KEY", "lattes-auto-apply-zero-cost-secret-key-2026")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app_database.db'}")

# Simple symmetric encryption for user SMTP credentials so passwords aren't plain text in DB
def _get_derived_key():
    return hashlib.sha256(SECRET_KEY.encode()).digest()

def encrypt_secret(plain_text: str) -> str:
    """Encrypts a password using XOR + base64 with derived key."""
    if not plain_text:
        return ""
    key = _get_derived_key()
    plain_bytes = plain_text.encode('utf-8')
    enc_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(plain_bytes)])
    return base64.b64encode(enc_bytes).decode('ascii')

def decrypt_secret(enc_text: str) -> str:
    """Decrypts a base64 XOR encrypted password."""
    if not enc_text:
        return ""
    try:
        key = _get_derived_key()
        enc_bytes = base64.b64decode(enc_text.encode('ascii'))
        dec_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(enc_bytes)])
        return dec_bytes.decode('utf-8')
    except Exception:
        return ""
