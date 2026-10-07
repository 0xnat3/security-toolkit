"""SQLite connection handling, schema, and first-run admin creation."""
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g

SCHEMA_VERSION = 1
MIN_ADMIN_PASSWORD = 12

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT NOT NULL,
    last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS port_scans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    host       TEXT NOT NULL,
    ip         TEXT NOT NULL,
    start_port INTEGER NOT NULL,
    end_port   INTEGER NOT NULL,
    open_count INTEGER NOT NULL,
    results    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_port_scans_user ON port_scans (user_id, id DESC);

CREATE TABLE IF NOT EXISTS audits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cpu_percent REAL NOT NULL,
    ram_percent REAL NOT NULL,
    results     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audits_user ON audits (user_id, id DESC);

CREATE TABLE IF NOT EXISTS integrity_baselines (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    directory  TEXT NOT NULL,
    algorithm  TEXT NOT NULL,
    file_count INTEGER NOT NULL,
    files      TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_baselines_user ON integrity_baselines (user_id, directory, algorithm, id DESC);

CREATE TABLE IF NOT EXISTS network_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    upload_kb_s    REAL NOT NULL,
    download_kb_s  REAL NOT NULL,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_network_user ON network_logs (user_id, id DESC);
"""


def utcnow() -> str:
    """UTC timestamps everywhere; the browser converts to local time (Nairobi is UTC+3)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(current_app.config["DB_PATH"], timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db() -> sqlite3.Connection:
    """One connection per request, closed automatically when the request ends."""
    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(exc=None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")  # for future migrations
    conn.commit()


def ensure_admin() -> None:
    """Create the first admin from .env, only if no users exist and the password is strong enough."""
    from werkzeug.security import generate_password_hash

    from . import repository as repo

    if repo.count_users() > 0:
        return

    username = (current_app.config["ADMIN_USERNAME"] or "").strip() or "admin"
    password = current_app.config["ADMIN_PASSWORD"] or ""
    if len(password) < MIN_ADMIN_PASSWORD:
        current_app.logger.warning(
            "No users exist and ADMIN_PASSWORD is missing or shorter than %d characters; "
            "no admin account was created.",
            MIN_ADMIN_PASSWORD,
        )
        return

    repo.create_user(username, generate_password_hash(password), role="admin")
    current_app.logger.info("Created first admin account '%s'. Remove ADMIN_PASSWORD from .env now.", username)


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
        ensure_admin()