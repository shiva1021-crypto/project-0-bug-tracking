import os
import secrets
from contextlib import contextmanager
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error
from mysql.connector import pooling


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _development_secret():
    secret_file = BASE_DIR / ".dev_secret_key"
    try:
        saved = secret_file.read_text(encoding="utf-8").strip()
        if len(saved) >= 32:
            return saved
    except FileNotFoundError:
        pass

    generated = secrets.token_urlsafe(48)
    try:
        secret_file.write_text(generated, encoding="utf-8")
    except OSError:
        return generated
    return generated


def _secret_key():
    environment = os.getenv("APP_ENV", "development").lower()
    configured = os.getenv("SECRET_KEY", "")
    is_placeholder = configured == "change-this-local-dev-secret"
    is_weak = len(configured) < 32 or is_placeholder

    if environment == "production" and is_weak:
        raise RuntimeError(
            "Production requires SECRET_KEY to be set to a random value of at least 32 characters."
        )
    if configured and not is_placeholder:
        return configured
    return _development_secret()


class Config:
    APP_ENV = os.getenv("APP_ENV", "development").lower()
    SECRET_KEY = _secret_key()
    UPLOAD_FOLDER = str(BASE_DIR / "uploads" / "bug_screenshots")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = (
        APP_ENV == "production"
        or os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )
    PERMANENT_SESSION_LIFETIME = int(os.getenv("SESSION_LIFETIME_SECONDS", "7200"))
    PAGE_SIZE = max(int(os.getenv("PAGE_SIZE", "20")), 1)
    BOARD_PAGE_SIZE = max(int(os.getenv("BOARD_PAGE_SIZE", "40")), 1)
    SHOW_DEMO_CREDENTIALS = (
        APP_ENV != "production"
        and os.getenv("SHOW_DEMO_CREDENTIALS", "false").lower() == "true"
    )
    REQUIRE_EMAIL_VERIFICATION = (
        APP_ENV == "production"
        or os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"
    )
    RATELIMIT_STORAGE = os.getenv("RATELIMIT_STORAGE", "database").lower()
    NOTIFICATION_WORKER_ENABLED = (
        os.getenv("NOTIFICATION_WORKER_ENABLED", "true").lower() == "true"
    )
    TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "false").lower() == "true"
    PROXY_FIX_X_FOR = max(int(os.getenv("PROXY_FIX_X_FOR", "1")), 0)
    PROXY_FIX_X_PROTO = max(int(os.getenv("PROXY_FIX_X_PROTO", "1")), 0)
    PROXY_FIX_X_HOST = max(int(os.getenv("PROXY_FIX_X_HOST", "1")), 0)
    PROXY_FIX_X_PREFIX = max(int(os.getenv("PROXY_FIX_X_PREFIX", "1")), 0)
    TRUSTED_HOSTS = [
        host.strip()
        for host in os.getenv("TRUSTED_HOSTS", "").split(",")
        if host.strip()
    ] or None
    WTF_CSRF_ENABLED = True


class DatabaseUnavailable(RuntimeError):
    def __init__(self, original_error):
        super().__init__(str(original_error))
        self.original_error = original_error


_db_pool = None


def _db_config(include_database=True):
    config = {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "connection_timeout": 5,
        "autocommit": False,
    }
    if include_database:
        config["database"] = os.getenv("DB_NAME", "bug_tracking_db")
    return config


def get_db_connection():
    global _db_pool

    try:
        if _db_pool is None:
            _db_pool = pooling.MySQLConnectionPool(
                pool_name="bug_tracker_pool",
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                **_db_config(include_database=True),
            )
        return _db_pool.get_connection()
    except Error as exc:
        raise DatabaseUnavailable(exc) from exc


def get_server_connection():
    try:
        return mysql.connector.connect(**_db_config(include_database=False))
    except Error as exc:
        raise DatabaseUnavailable(exc) from exc


@contextmanager
def db_cursor(dictionary=False, commit=False):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=dictionary)

    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
