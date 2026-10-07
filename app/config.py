import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or unsafe."""


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}
def _env_paths(name: str) -> tuple[str, ...]:
    return tuple(p.strip() for p in os.getenv(name, "").split(os.pathsep) if p.strip())


class Config:
    # Paths (everything generated at runtime lives in instance/)
    BASE_DIR = BASE_DIR
    INSTANCE_DIR = BASE_DIR / "instance"
    LOG_DIR = INSTANCE_DIR / "logs"
    DB_PATH = INSTANCE_DIR / "toolkit.db"

    # Core
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    DEBUG = _env_bool("FLASK_DEBUG", False)
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    MAX_CONTENT_LENGTH = 1024 * 1024  # JSON bodies here are tiny; reject anything bigger

    # Sessions
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=int(os.getenv("SESSION_MINUTES", "30")))

    # CSRF: tokens last as long as the session so the dashboard JS doesn't break after an hour
    WTF_CSRF_TIME_LIMIT = None

    # Rate limiting
    RATELIMIT_ENABLED = _env_bool("RATELIMIT_ENABLED", True)
    RATELIMIT_DEFAULT = os.getenv("RATELIMIT_DEFAULT", "300 per hour")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # First-run admin (no default password on purpose)
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    REGISTRATION_ENABLED = _env_bool("REGISTRATION_ENABLED", False)
    
        # Tool limits
    SCAN_ALLOW_PUBLIC = _env_bool("SCAN_ALLOW_PUBLIC", False)
    SCAN_MAX_PORTS = int(os.getenv("SCAN_MAX_PORTS", "5000"))
    INTEGRITY_ROOTS = _env_paths("INTEGRITY_ROOTS") or (str(Path.home()),)

    @classmethod
    def validate(cls) -> None:
        if len(cls.SECRET_KEY) < 32:
            raise ConfigError(
                "SECRET_KEY is missing or shorter than 32 characters. Generate one with:\n"
                '  python -c "import secrets; print(secrets.token_hex(32))"\n'
                "and put it in your .env file."
            )