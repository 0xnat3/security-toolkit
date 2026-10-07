"""All database access. Routes call these functions and never write SQL themselves."""
import json
import sqlite3

from .db import get_db, utcnow

NETWORK_LOG_KEEP = 1000  # per user; older rows are pruned so the table can't grow forever
_HISTORY_TABLES = ("port_scans", "audits", "integrity_baselines", "network_logs")


class DuplicateUsername(Exception):
    pass


def _one(cursor) -> dict | None:
    row = cursor.fetchone()
    return dict(row) if row else None


def _all(cursor) -> list[dict]:
    return [dict(r) for r in cursor.fetchall()]


# ---------------- users ----------------
def create_user(username: str, password_hash: str, role: str = "user") -> int:
    try:
        with get_db() as db:
            cur = db.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
                (username.strip(), password_hash, role, utcnow()),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError as exc:
        if "UNIQUE" in str(exc):
            raise DuplicateUsername(username) from exc
        raise


def get_user(user_id: int) -> dict | None:
    return _one(get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)))


def get_user_by_username(username: str) -> dict | None:
    # The column is COLLATE NOCASE, so "Alice" and "alice" are the same account.
    return _one(get_db().execute("SELECT * FROM users WHERE username = ?", (username.strip(),)))


def count_users() -> int:
    return get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]


def set_password(user_id: int, password_hash: str) -> None:
    with get_db() as db:
        db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))


def record_login(user_id: int) -> None:
    with get_db() as db:
        db.execute("UPDATE users SET last_login_at = ? WHERE id = ?", (utcnow(), user_id))


# ---------------- writes ----------------
def add_port_scan(user_id: int, host: str, ip: str, start_port: int, end_port: int, results: list) -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO port_scans (user_id, host, ip, start_port, end_port, open_count, results, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (user_id, host, ip, start_port, end_port, len(results), json.dumps(results), utcnow()),
        )
        return cur.lastrowid


def add_audit(user_id: int, info: dict) -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO audits (user_id, cpu_percent, ram_percent, results, created_at) VALUES (?,?,?,?,?)",
            (user_id, info["cpu_percent"], info["ram_percent"], json.dumps(info), utcnow()),
        )
        return cur.lastrowid


BASELINES_KEEP = 5  # per user, directory and algorithm


def add_baseline(user_id: int, directory: str, algorithm: str, files: dict) -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO integrity_baselines (user_id, directory, algorithm, file_count, files, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, directory, algorithm, len(files), json.dumps(files), utcnow()),
        )
        db.execute(
            "DELETE FROM integrity_baselines WHERE user_id = ? AND directory = ? AND algorithm = ? AND id NOT IN "
            "(SELECT id FROM integrity_baselines WHERE user_id = ? AND directory = ? AND algorithm = ? "
            "ORDER BY id DESC LIMIT ?)",
            (user_id, directory, algorithm, user_id, directory, algorithm, BASELINES_KEEP),
        )
        return cur.lastrowid


def add_network_log(user_id: int, upload_kb_s: float, download_kb_s: float) -> int:
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO network_logs (user_id, upload_kb_s, download_kb_s, created_at) VALUES (?,?,?,?)",
            (user_id, upload_kb_s, download_kb_s, utcnow()),
        )
        db.execute(
            "DELETE FROM network_logs WHERE user_id = ? AND id NOT IN "
            "(SELECT id FROM network_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?)",
            (user_id, user_id, NETWORK_LOG_KEEP),
        )
        return cur.lastrowid


# ---------------- reads (newest first; reverse in the caller for charts) ----------------
def latest_baseline(user_id: int, directory: str, algorithm: str) -> dict | None:
    row = _one(
        get_db().execute(
            "SELECT * FROM integrity_baselines WHERE user_id = ? AND directory = ? AND algorithm = ? "
            "ORDER BY id DESC LIMIT 1",
            (user_id, directory, algorithm),
        )
    )
    if row:
        row["files"] = json.loads(row["files"])
    return row

def last_baseline_target(user_id: int) -> dict | None:
    """Directory and algorithm of the user's most recent baseline."""
    return _one(
        get_db().execute(
            "SELECT directory, algorithm FROM integrity_baselines WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        )
    )


def recent_port_scans(user_id: int, limit: int = 50) -> list[dict]:
    return _all(
        get_db().execute(
            "SELECT id, host, ip, start_port, end_port, open_count, created_at FROM port_scans "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
    )


def recent_audits(user_id: int, limit: int = 50) -> list[dict]:
    return _all(
        get_db().execute(
            "SELECT id, json_extract(results, '$.os') AS os, cpu_percent, ram_percent, created_at FROM audits "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
    )


def recent_baselines(user_id: int, limit: int = 50) -> list[dict]:
    return _all(
        get_db().execute(
            "SELECT id, directory, algorithm, file_count, created_at FROM integrity_baselines "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
    )


def recent_network_logs(user_id: int, limit: int = 50) -> list[dict]:
    return _all(
        get_db().execute(
            "SELECT id, upload_kb_s, download_kb_s, created_at FROM network_logs "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
    )


def activity_summary(user_id: int) -> dict:
    """Counts and last-activity time per tool. Replaces both old duplicate stats endpoints."""
    db = get_db()
    summary = {}
    for table in _HISTORY_TABLES:  # constants, never user input
        row = db.execute(
            f"SELECT COUNT(*) AS n, MAX(created_at) AS last FROM {table} WHERE user_id = ?", (user_id,)
        ).fetchone()
        summary[table] = {"count": row["n"], "last": row["last"]}
    return summary


def clear_history(user_id: int) -> int:
    """Delete one user's history (the old 'Clear History' button only pretended to)."""
    deleted = 0
    with get_db() as db:
        for table in _HISTORY_TABLES:
            deleted += db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,)).rowcount
    return deleted

# ---------------- exports ----------------
_EXPORT_QUERIES = {
    "port_scans": (
        "SELECT created_at, host, ip, start_port || '-' || end_port AS port_range, open_count, results "
        "FROM port_scans WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    ),
    "audits": (
        "SELECT created_at, json_extract(results, '$.os') || ' ' || json_extract(results, '$.release') AS system, "
        "cpu_percent, ram_percent, json_extract(results, '$.ram_gb') AS ram_gb, "
        "json_extract(results, '$.uptime') AS uptime FROM audits WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    ),
    "integrity_baselines": (
        "SELECT created_at, directory, algorithm, file_count "
        "FROM integrity_baselines WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    ),
    "network_logs": (
        "SELECT created_at, upload_kb_s, download_kb_s FROM network_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    ),
}


def export_rows(user_id: int, report_type: str, limit: int) -> list[dict]:
    """Newest first. The caller must have validated report_type against the REPORTS whitelist."""
    rows = _all(get_db().execute(_EXPORT_QUERIES[report_type], (user_id, limit)))
    if report_type == "port_scans":
        for row in rows:
            found = json.loads(row.pop("results"))
            row["open_ports"] = ", ".join(str(p["port"]) for p in sorted(found, key=lambda p: p["port"]))
    return rows