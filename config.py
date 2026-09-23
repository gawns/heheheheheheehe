"""
Ine Mebel Jepara - Konfigurasi Flask + MySQL
=============================================
Mendukung dua mode:
  - Lokal (Laragon): MySQL di 127.0.0.1:3306, user root tanpa password.
  - Produksi (Railway dst.): semua nilai diambil dari environment variable.
    Railway MySQL otomatis menyediakan MYSQLHOST/MYSQLPORT/MYSQLUSER/
    MYSQLPASSWORD/MYSQLDATABASE (atau DATABASE_URL). Keduanya didukung.

PENTING untuk deploy:
  - Set AUTH_SECRET ke nilai acak & rahasia (JANGAN pakai default).
  - Set APP_DEBUG=0.
"""

import os
import urllib.parse


def _env(*names, default=""):
    """Ambil env pertama yang ada & tidak kosong dari daftar nama."""
    for name in names:
        val = os.getenv(name)
        if val is not None and val != "":
            return val
    return default


def _parse_db_url(url):
    """Ubah DATABASE_URL (mysql://user:pass@host:port/db) jadi dict."""
    try:
        parsed = urllib.parse.urlparse(url)
        return {
            "host": parsed.hostname or "127.0.0.1",
            "port": int(parsed.port or 3306),
            "user": urllib.parse.unquote(parsed.username or "root"),
            "password": urllib.parse.unquote(parsed.password or ""),
            "name": (parsed.path or "/").lstrip("/") or "jepara_nusantara",
        }
    except Exception:
        return None


# Database.
# Prioritas: MYSQLHOST (Railway plugin) -> DB_HOST -> DATABASE_URL -> default Laragon.
_db_url = _parse_db_url(_env("DATABASE_URL", "MYSQL_URL")) if not _env("MYSQLHOST", "DB_HOST") else None

DB_HOST = _env("MYSQLHOST", "DB_HOST", default=(_db_url or {}).get("host", "127.0.0.1"))
DB_PORT = int(_env("MYSQLPORT", "DB_PORT", default=str((_db_url or {}).get("port", 3306))))
DB_USER = _env("MYSQLUSER", "DB_USER", default=(_db_url or {}).get("user", "root"))
DB_PASS = _env("MYSQLPASSWORD", "DB_PASS", default=(_db_url or {}).get("password", ""))
DB_NAME = _env("MYSQLDATABASE", "DB_NAME", default=(_db_url or {}).get("name", "jepara_nusantara"))
DB_SSL = _env("DB_SSL", default="0") == "1"

# Server Flask
HOST = os.getenv("APP_HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", os.getenv("APP_PORT", "5000")))
DEBUG = os.getenv("APP_DEBUG", "0") == "1"

# Panel admin: login wajib (password tersimpan di tabel admin_users)
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "1") == "1"
AUTH_SECRET = os.getenv("AUTH_SECRET", "ubah-secret-ini-di-hosting")
TOKEN_TTL = int(os.getenv("TOKEN_TTL", str(8 * 60 * 60)))  # 8 jam

# Admin default (dibuat otomatis saat tabel kosong).
# WAJIB diganti lewat env saat deploy!
DEFAULT_ADMIN_USER = os.getenv("DEFAULT_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = os.getenv("DEFAULT_ADMIN_PASS", "2026")

# Upload foto produk (dari perangkat lokal -> folder img/)
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "img")
UPLOAD_URL = os.getenv("UPLOAD_URL", "img")   # prefix URL publik (folder statis)
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "5"))
ALLOWED_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")