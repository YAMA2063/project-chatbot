"""
migrate_password.py - One-time script: migrasi password plain-text ke bcrypt
=============================================================================
Jalankan SEKALI setelah Tahap 3 diaktifkan untuk mengonversi ADMIN_PASSWORD
yang masih plain-text di .env menjadi ADMIN_PASSWORD_HASH (bcrypt).

Setelah script ini berhasil, ADMIN_PASSWORD di .env akan dikosongkan.
"""

import os, sys, secrets
sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv, set_key
import bcrypt

load_dotenv()
ENV_FILE = "./.env"

plain = os.getenv("ADMIN_PASSWORD", "")
existing_hash = os.getenv("ADMIN_PASSWORD_HASH", "")

if existing_hash.startswith("$2b$") or existing_hash.startswith("$2a$"):
    print("[OK] Password sudah dalam format bcrypt hash. Tidak perlu migrasi.")
    sys.exit(0)

if not plain:
    print("[ERROR] ADMIN_PASSWORD kosong dan belum ada hash. Set dulu password di .env!")
    sys.exit(1)

print(f"[INFO] Migrasi password '{plain[:2]}***' ke bcrypt hash...")
hashed = bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()
set_key(ENV_FILE, "ADMIN_PASSWORD_HASH", hashed)
set_key(ENV_FILE, "ADMIN_PASSWORD", "")   # Hapus plain text

# Tambah JWT_SECRET jika belum ada
jwt_secret = os.getenv("JWT_SECRET", "")
if not jwt_secret:
    new_secret = secrets.token_hex(32)
    set_key(ENV_FILE, "JWT_SECRET", new_secret)
    print(f"[INFO] JWT_SECRET dibuat otomatis (simpan baik-baik!)")

# Tambah ALLOWED_ORIGINS jika belum ada
if not os.getenv("ALLOWED_ORIGINS", ""):
    set_key(ENV_FILE, "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
    print("[INFO] ALLOWED_ORIGINS diset ke localhost. Edit .env jika deploy ke domain publik.")

print("[DONE] Migrasi selesai!")
print(f"       Hash: {hashed[:30]}...")
print("       Plain-text ADMIN_PASSWORD sudah dikosongkan.")
print("       Restart server untuk menerapkan perubahan.")
