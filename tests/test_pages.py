import re

import pytest
from markupsafe import escape

from app import repository as repo


def signed_in(app, username="alice"):
    with app.app_context():
        uid = repo.create_user(username, "unused-hash")
    client = app.test_client()
    with client.session_transaction() as session:
        session["uid"] = uid
    return client


@pytest.fixture
def client(app):
    return signed_in(app)


def test_history_requires_login(app):
    r = app.test_client().get("/history")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_dashboard_has_every_panel(client):
    html = client.get("/").get_data(as_text=True)
    for name in ("overview", "integrity", "ports", "audit", "network"):
        assert f'id="panel-{name}"' in html
        assert f'data-panel="{name}"' in html


def test_history_page_renders(client):
    r = client.get("/history")
    assert r.status_code == 200 and b'id="history-table"' in r.data


@pytest.mark.parametrize("path", ["/", "/history", "/account/password"])
def test_pages_have_no_inline_script_or_style(client, path):
    html = client.get(path).get_data(as_text=True)
    assert not re.search(r"<script(?![^>]*\bsrc=)", html), "inline <script> would be blocked by the CSP"
    assert "<style" not in html
    assert not re.search(r"\sstyle=", html)


def test_dashboard_lists_allowed_integrity_folder(make_app, tmp_path):
    client = signed_in(make_app(INTEGRITY_ROOTS=(str(tmp_path),)))
    assert str(escape(str(tmp_path))) in client.get("/").get_data(as_text=True)