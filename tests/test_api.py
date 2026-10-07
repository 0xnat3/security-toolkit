import os
import socket

import pytest

from app import repository as repo
from app.services import sysinfo


@pytest.fixture
def files_root(tmp_path):
    root = tmp_path / "files"
    (root / "data").mkdir(parents=True)
    return root


@pytest.fixture
def app(make_app, files_root):  # overrides the default app fixture for this module
    return make_app(INTEGRITY_ROOTS=(str(files_root),))


def make_client(app, username):
    """A test client that is already signed in (skips the slow password hashing)."""
    with app.app_context():
        uid = repo.create_user(username, "unused-hash")
    client = app.test_client()
    with client.session_transaction() as session:
        session["uid"] = uid
    return client


@pytest.fixture
def client(app):
    return make_client(app, "alice")


@pytest.fixture
def open_port():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(5)
    yield server.getsockname()[1]
    server.close()


def test_api_requires_login(app):
    r = app.test_client().get("/api/dashboard")
    assert r.status_code == 401
    assert "error" in r.get_json()


def test_dashboard_starts_empty(client):
    d = client.get("/api/dashboard").get_json()
    assert all(v["count"] == 0 for v in d["activity"].values())
    assert d["recent"] == {"port_scan": None, "audit": None, "baseline": None}
    assert set(d["charts"]) == {"network", "port_scans", "cpu"}


def test_port_scan_finds_open_port(client, open_port):
    r = client.post(
        "/api/port-scan",
        json={"host": "127.0.0.1", "start_port": open_port, "end_port": open_port, "timeout": 0.2},
    )
    assert r.status_code == 200
    body = r.get_json()
    assert [p["port"] for p in body["results"]] == [open_port]
    assert body["open_count"] == 1
    assert client.get("/api/history").get_json()["port_scans"][0]["open_count"] == 1


def test_port_scan_rejects_bad_range(client):
    r = client.post("/api/port-scan", json={"host": "127.0.0.1", "start_port": 100, "end_port": 10})
    assert r.status_code == 400
    assert "end_port" in r.get_json()["fields"]


def test_port_scan_rejects_oversized_range(client):
    r = client.post("/api/port-scan", json={"host": "127.0.0.1", "start_port": 1, "end_port": 65535})
    assert r.status_code == 400
    assert "at most" in r.get_json()["error"]


@pytest.mark.parametrize("host", ["169.254.169.254", "8.8.8.8"])
def test_port_scan_blocks_unsafe_targets(client, host):
    r = client.post("/api/port-scan", json={"host": host, "start_port": 1, "end_port": 10})
    assert r.status_code == 403


def test_port_scan_rejects_malformed_host(client):
    r = client.post("/api/port-scan", json={"host": "bad host;rm", "start_port": 1, "end_port": 10})
    assert r.status_code == 400
    assert "host" in r.get_json()["fields"]


def test_integrity_detects_changes(client, files_root):
    data = files_root / "data"
    (data / "a.txt").write_text("one")
    (data / "keep.txt").write_text("same")

    r = client.post("/api/integrity/baseline", json={"directory": "data"})
    assert r.status_code == 200 and r.get_json()["file_count"] == 2

    clean = client.post("/api/integrity/check", json={"directory": "data"}).get_json()
    assert clean["added"] == clean["removed"] == clean["modified"] == []

    (data / "a.txt").write_text("two")
    (data / "b.txt").write_text("new")
    (data / "keep.txt").unlink()
    changed = client.post("/api/integrity/check", json={"directory": "data"}).get_json()
    assert changed["modified"] == ["a.txt"]
    assert changed["added"] == ["b.txt"]
    assert changed["removed"] == ["keep.txt"]


@pytest.mark.parametrize("where", ["../", "ABSOLUTE_PARENT"])
def test_integrity_rejects_outside_directories(client, files_root, where):
    directory = str(files_root.parent) if where == "ABSOLUTE_PARENT" else where
    r = client.post("/api/integrity/baseline", json={"directory": directory})
    assert r.status_code == 403


def test_integrity_check_needs_a_baseline(client):
    assert client.post("/api/integrity/check", json={"directory": "data"}).status_code == 409


def test_integrity_check_defaults_to_last_baseline(client, files_root):
    (files_root / "data" / "a.txt").write_text("one")
    client.post("/api/integrity/baseline", json={"directory": "data"})
    r = client.post("/api/integrity/check", json={})
    assert r.status_code == 200
    assert r.get_json()["directory"] == os.path.realpath(files_root / "data")


def test_baseline_requires_directory(client):
    r = client.post("/api/integrity/baseline", json={})
    assert r.status_code == 400
    assert "directory" in r.get_json()["fields"]


def test_audit_is_recorded(client):
    r = client.post("/api/system/audit")
    assert r.status_code == 200
    assert "cpu_percent" in r.get_json() and "ram_percent" in r.get_json()
    assert client.get("/api/dashboard").get_json()["activity"]["audits"]["count"] == 1


def test_network_sample_is_recorded(client, monkeypatch):
    monkeypatch.setattr(sysinfo, "network_speed", lambda sample_seconds=1.0: {"upload_kb_s": 1.5, "download_kb_s": 2.5})
    assert client.post("/api/network/sample").get_json()["upload_kb_s"] == 1.5
    assert client.get("/api/dashboard").get_json()["charts"]["network"]["upload"] == [1.5]


def test_clear_history(client):
    client.post("/api/system/audit")
    assert client.delete("/api/history").get_json()["deleted"] == 1
    assert client.get("/api/dashboard").get_json()["activity"]["audits"]["count"] == 0


def test_history_is_per_user(app, client):
    client.post("/api/system/audit")
    bob = make_client(app, "bob")
    assert bob.get("/api/history").get_json()["audits"] == []


def test_api_enforces_csrf(make_app):
    app = make_app(WTF_CSRF_ENABLED=True)
    client = make_client(app, "alice")
    assert client.post("/api/system/audit").status_code == 400  # no X-CSRFToken header
    assert client.get("/api/dashboard").status_code == 200