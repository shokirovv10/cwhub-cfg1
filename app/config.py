"""
Ilova sozlamalari. Barcha maxfiy qiymatlar .env faylidan o'qiladi.
Hech qachon bu yerga API secret yoki parolni qattiq (hardcode) yozmang.
"""
import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _bool(val, default=False):
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-only-insecure-key-change-me")
    DEBUG = _bool(os.environ.get("FLASK_DEBUG"), True)

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///cwhub.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.environ.get("UPLOAD_FOLDER", "uploads"))
    CONFIGS_SUBDIR = "configs"
    RECEIPTS_SUBDIR = "receipts"
    SCREENSHOTS_SUBDIR = "screenshots"
    AVATARS_SUBDIR = "avatars"

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH_MB", 25)) * 1024 * 1024

    ALLOWED_CONFIG_EXTENSIONS = {"cfg", "zip"}
    ALLOWED_RECEIPT_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
    ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

    # MIME whitelist (qo'shimcha tekshiruv, faqat extensionga ishonmaslik uchun)
    ALLOWED_CONFIG_MIMES = {
        "text/plain", "application/zip", "application/x-zip-compressed",
        "application/octet-stream",
    }
    ALLOWED_RECEIPT_MIMES = {
        "image/jpeg", "image/png", "application/pdf",
    }
    ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cwhub.local")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")

    DEFAULT_UZCARD_NUMBER = os.environ.get("DEFAULT_UZCARD_NUMBER", "")
    DEFAULT_HUMO_NUMBER = os.environ.get("DEFAULT_HUMO_NUMBER", "")
    DEFAULT_CARD_OWNER = os.environ.get("DEFAULT_CARD_OWNER", "CWHUB CFG")

    CLICK_MERCHANT_ID = os.environ.get("CLICK_MERCHANT_ID", "")
    CLICK_SERVICE_ID = os.environ.get("CLICK_SERVICE_ID", "")
    CLICK_SECRET_KEY = os.environ.get("CLICK_SECRET_KEY", "")

    PAYME_MERCHANT_ID = os.environ.get("PAYME_MERCHANT_ID", "")
    PAYME_SECRET_KEY = os.environ.get("PAYME_SECRET_KEY", "")

    PAYMENT_API_ENABLED = _bool(os.environ.get("PAYMENT_API_ENABLED"), False)

    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Productionda HTTPS orqasida ishlatilsa True qiling
    SESSION_COOKIE_SECURE = _bool(os.environ.get("SESSION_COOKIE_SECURE"), False)

    WTF_CSRF_TIME_LIMIT = None
