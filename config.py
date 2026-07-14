"""
Vaetan — HR Payroll Management System
config.py  |  All environment configurations
"""

import os
from dotenv import load_dotenv

load_dotenv()  # reads .env from project root


class BaseConfig:
    """Shared settings across all environments."""

    # ── Security ──────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-before-going-live")

    # ── Database ──────────────────────────────────────────────
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # set True in dev to log SQL queries

    # ── File uploads ──────────────────────────────────────────
    UPLOAD_FOLDER          = os.path.join(os.path.dirname(__file__), "app", "static", "uploads")
    MAX_CONTENT_LENGTH     = 2 * 1024 * 1024   # 2 MB max upload size
    ALLOWED_EXTENSIONS     = {"png", "jpg", "jpeg", "webp"}

    # ── Email (Flask-Mail) ────────────────────────────────────
    MAIL_SERVER   = os.environ.get("MAIL_SERVER",   "smtp.gmail.com")
    MAIL_PORT     = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS  = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_USERNAME")

    # ── AI / Anthropic ────────────────────────────────────────
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

    # ── Payroll rules (Indian statutory defaults) ─────────────
    PF_RATE            = 0.12    # 12% of basic salary
    ESI_RATE           = 0.0075  # 0.75% of gross (if gross <= ESI_LIMIT)
    ESI_SALARY_LIMIT   = 21000   # ESI applies only if gross <= ₹21,000/month
    EMPLOYER_PF_RATE   = 0.12    # employer's matching PF contribution

    # ── App metadata ──────────────────────────────────────────
    APP_NAME    = "Vaetan"
    APP_TAGLINE = "Smart HR, Seamless Pay."


class DevelopmentConfig(BaseConfig):
    DEBUG    = True
    TESTING  = False
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "postgresql://hr_user:yourpassword@localhost/hr_payroll"
    )
    SQLALCHEMY_ECHO = True   # prints SQL to terminal — helpful while building


class TestingConfig(BaseConfig):
    DEBUG   = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"   # in-memory DB for tests
    WTF_CSRF_ENABLED = False


class ProductionConfig(BaseConfig):
    DEBUG   = False
    TESTING = False
    # Fix Render's postgres:// prefix → postgresql://
    _db_url = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_DATABASE_URI = _db_url.replace("postgres://", "postgresql://", 1) if _db_url else None

    # Enforce strong secret key in production
    @classmethod
    def init_app(cls, app):
        BaseConfig.init_app(app) if hasattr(BaseConfig, "init_app") else None
        assert os.environ.get("SECRET_KEY"), "SECRET_KEY env var must be set in production!"


# ── Map name → class (used in create_app) ────────────────────
config_map = {
    "development": DevelopmentConfig,
    "testing":     TestingConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,  # default to dev
}
