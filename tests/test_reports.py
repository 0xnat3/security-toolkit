import codecs
import csv
import io
import re

import pytest

from app import repository as repo
from app.reports import routes as report_routes
from app.reports.definitions import REPORTS
from app.reports.render import csv_safe

REPORT_TYPES = ["port_scans", "audits", "integrity_baselines", "network_logs"]


def signed_in(app, username="alice"):
    with app.app_context():
        uid = repo.create_user(username, "unused-hash")
    client = app.test_client()
    with client.session_transaction() as session:
        session["uid"] = uid
    return client, uid


def parse_csv(response):
    text = response.get_data(as_text=True).lstrip("\ufeff")
    return list(csv.reader(io.StringIO(text)))


@pytest.fixture
def alice(app):
    return signed_in(app)


def test_export_requires_login(app):
    r = app.test_client().get("/export/port_scans/csv")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


@pytest.mark.parametrize("path", ["/export/users/csv", "/export/port_scans/xlsx", "/export/port_scans/csv.exe"])
def test_unknown_report_or_format_is_404(alice, path):
    client, _ = alice
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("fmt", ["csv", "pdf"])
@pytest.mark.parametrize("report_type", REPORT_TYPES)
def test_empty_exports_work(alice, report_type, fmt):
    client, _ = alice
    r = client.get(f"/export/{report_type}/{fmt}")
    assert r.status_code == 200
    if fmt == "pdf":
        assert r.data.startswith(b"%PDF")
    else:
        assert len(parse_csv(r)) == 1  # header only


def test_csv_contents(app, alice):
    client, uid = alice
    found = [
        {"port": 80, "service": "HTTP", "banner": "", "risk": None},
        {"port": 22, "service": "SSH", "banner": "", "risk": None},
    ]
    with app.app_context():
        repo.add_port_scan(uid, "localhost", "127.0.0.1", 1, 1024, found)

    r = client.get("/export/port_scans/csv")
    assert r.mimetype == "text/csv"
    assert r.data.startswith(codecs.BOM_UTF8)

    header, row = parse_csv(r)
    assert header == [c.header for c in REPORTS["port_scans"].columns]
    record = dict(zip(header, row))
    assert record["Host"] == "localhost"
    assert record["Address"] == "127.0.0.1"
    assert record["Ports"] == "1-1024"
    assert record["Open"] == "2"
    assert record["Open ports"] == "22, 80"


def test_csv_only_contains_own_data(app, alice):
    client, uid = alice
    _, bob_id = signed_in(app, "bob")
    with app.app_context():
        repo.add_port_scan(uid, "alice-host", "127.0.0.1", 1, 10, [])
        repo.add_port_scan(bob_id, "bob-host", "127.0.0.1", 1, 10, [])
    text = client.get("/export/port_scans/csv").get_data(as_text=True)
    assert "alice-host" in text and "bob-host" not in text


def test_csv_neutralises_spreadsheet_formulas(app, alice):
    client, uid = alice
    with app.app_context():
        repo.add_baseline(uid, '=HYPERLINK("http://evil.example")', "sha256", {})
    header, row = parse_csv(client.get("/export/integrity_baselines/csv"))
    assert dict(zip(header, row))["Folder"].startswith("'=")


@pytest.mark.parametrize(
    "value, expected",
    [("=1+1", "'=1+1"), ("+cmd", "'+cmd"), ("-cmd", "'-cmd"), ("@SUM(A1)", "'@SUM(A1)"), ("normal", "normal"), (5, 5)],
)
def test_csv_safe(value, expected):
    assert csv_safe(value) == expected


def test_pdf_handles_markup_in_data(app, alice):
    client, uid = alice
    with app.app_context():
        repo.add_port_scan(uid, "<b>bad</i> & <font>", "127.0.0.1", 1, 10, [])
    r = client.get("/export/port_scans/pdf")
    assert r.status_code == 200 and r.data.startswith(b"%PDF")


def test_download_headers(alice):
    client, _ = alice
    disposition = client.get("/export/network_logs/csv").headers["Content-Disposition"]
    assert disposition.startswith("attachment")
    assert re.search(r"network-logs-\d{8}-\d{6}\.csv", disposition)


def test_csv_row_cap(app, alice, monkeypatch):
    client, uid = alice
    monkeypatch.setitem(report_routes.FORMATS, "csv", ("text/csv", 2))
    with app.app_context():
        for i in range(5):
            repo.add_network_log(uid, i, i)
    assert len(parse_csv(client.get("/export/network_logs/csv"))) == 3  # header + 2 rows


def test_history_page_links_to_exports(alice):
    client, _ = alice
    html = client.get("/history").get_data(as_text=True)
    assert "/export/port_scans/csv" in html and "/export/port_scans/pdf" in html