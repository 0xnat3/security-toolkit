import pytest

from app import create_app
from app.config import Config


class BaseTestConfig(Config):
    TESTING = True
    SECRET_KEY = "test-secret-key-" + "x" * 32
    RATELIMIT_ENABLED = False
    WTF_CSRF_ENABLED = False
    ADMIN_PASSWORD = ""  # never inherit a real password from your .env


@pytest.fixture
def make_app(tmp_path):
    """Build an app with its own temporary database and log folder."""

    def _make(**overrides):
        attrs = {
            "INSTANCE_DIR": tmp_path,
            "LOG_DIR": tmp_path / "logs",
            "DB_PATH": tmp_path / "test.db",
            **overrides,
        }
        return create_app(type("Cfg", (BaseTestConfig,), attrs))

    return _make


@pytest.fixture
def app(make_app):
    return make_app()