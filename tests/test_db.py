import pytest

from app import repository as repo
from app.db import get_db


def test_schema_created(app):
    with app.app_context():
        names = {r["name"] for r in get_db().execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "port_scans", "audits", "integrity_baselines", "network_logs"} <= names


def test_no_admin_without_password(app):
    with app.app_context():
        assert repo.count_users() == 0


def test_admin_created_from_config(make_app):
    app = make_app(ADMIN_USERNAME="root", ADMIN_PASSWORD="a-long-enough-password")
    with app.app_context():
        user = repo.get_user_by_username("ROOT")  # usernames are case-insensitive
        assert user["role"] == "admin"
        assert user["password_hash"] != "a-long-enough-password"


def test_duplicate_username_rejected(app):
    with app.app_context():
        repo.create_user("alice", "hash")
        with pytest.raises(repo.DuplicateUsername):
            repo.create_user("Alice", "hash")


def test_history_is_scoped_per_user(app):
    with app.app_context():
        a = repo.create_user("alice", "h")
        b = repo.create_user("bob", "h")
        repo.add_network_log(a, 1.0, 2.0)
        assert len(repo.recent_network_logs(a)) == 1
        assert repo.recent_network_logs(b) == []


def test_clear_history_only_touches_that_user(app):
    with app.app_context():
        a = repo.create_user("alice", "h")
        b = repo.create_user("bob", "h")
        repo.add_network_log(a, 1, 2)
        repo.add_network_log(b, 3, 4)
        assert repo.clear_history(a) == 1
        assert repo.recent_network_logs(a) == []
        assert len(repo.recent_network_logs(b)) == 1


def test_network_logs_are_pruned(app, monkeypatch):
    monkeypatch.setattr(repo, "NETWORK_LOG_KEEP", 5)
    with app.app_context():
        uid = repo.create_user("alice", "h")
        for i in range(8):
            repo.add_network_log(uid, i, i)
        assert len(repo.recent_network_logs(uid, 100)) == 5


def test_baseline_round_trip(app):
    with app.app_context():
        uid = repo.create_user("alice", "h")
        repo.add_baseline(uid, "/data", "sha256", {"a.txt": "abc"})
        assert repo.latest_baseline(uid, "/data", "sha256")["files"] == {"a.txt": "abc"}
        assert repo.latest_baseline(uid, "/data", "md5") is None
        assert repo.activity_summary(uid)["integrity_baselines"]["count"] == 1