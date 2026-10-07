import pytest
from werkzeug.security import generate_password_hash

from app import repository as repo
from app.db import get_db

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "another long passphrase 42"


@pytest.fixture
def client(app):
    with app.app_context():
        repo.create_user("alice", generate_password_hash(PASSWORD))
    return app.test_client()


@pytest.fixture
def reg_client(make_app):
    return make_app(REGISTRATION_ENABLED=True).test_client()


def login(client, username="alice", password=PASSWORD, query=""):
    return client.post(f"/login{query}", data={"username": username, "password": password})


def register(client, username="bob", password="a perfectly fine passphrase"):
    return client.post(
        "/register", data={"username": username, "password": password, "confirm_password": password}
    )


def test_dashboard_requires_login(client):
    r = client.get("/")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_login_success(client):
    r = login(client)
    assert r.status_code == 302 and r.headers["Location"] == "/"
    page = client.get("/")
    assert page.status_code == 200 and b"alice" in page.data


def test_wrong_password_and_unknown_user_look_identical(client):
    wrong = login(client, password="wrong-password-123")
    unknown = login(client, username="nobody")
    for r in (wrong, unknown):
        assert r.status_code == 200
        assert b"Invalid username or password." in r.data


def test_login_honours_safe_next(client):
    r = login(client, query="?next=/account/password")
    assert r.headers["Location"] == "/account/password"


@pytest.mark.parametrize("target", ["https://evil.example", "//evil.example", "/\\evil.example"])
def test_login_ignores_external_next(client, target):
    r = login(client, query=f"?next={target}")
    assert r.headers["Location"] == "/"


def test_logout_requires_post_and_clears_session(client):
    login(client)
    assert client.get("/logout").status_code == 405
    assert client.post("/logout").status_code == 302
    assert client.get("/").status_code == 302


def test_registration_disabled_by_default(client):
    assert client.get("/register").status_code == 404


def test_registration_when_enabled(reg_client):
    assert register(reg_client).status_code == 302
    r = login(reg_client, "bob", "a perfectly fine passphrase")
    assert r.status_code == 302 and r.headers["Location"] == "/"


def test_duplicate_username_rejected(reg_client):
    register(reg_client)
    r = register(reg_client, username="BOB")
    assert r.status_code == 200 and b"already taken" in r.data


def test_short_password_rejected(reg_client):
    r = register(reg_client, password="short")
    assert r.status_code == 200 and b"at least 12" in r.data


def test_change_password(client):
    login(client)
    bad = client.post(
        "/account/password",
        data={"current_password": "nope-nope-nope", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
    )
    assert bad.status_code == 200 and b"incorrect" in bad.data

    ok = client.post(
        "/account/password",
        data={"current_password": PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
    )
    assert ok.status_code == 302

    client.post("/logout")
    assert login(client, password=PASSWORD).status_code == 200  # old password rejected
    assert login(client, password=NEW_PASSWORD).status_code == 302


def test_csrf_is_enforced(make_app):
    app = make_app(WTF_CSRF_ENABLED=True)
    r = app.test_client().post("/login", data={"username": "a", "password": "b"})
    assert r.status_code == 400


def test_disabled_account_is_signed_out(app, client):
    login(client)
    assert client.get("/").status_code == 200
    with app.app_context():
        with get_db() as db:
            db.execute("UPDATE users SET is_active = 0")
    assert client.get("/").status_code == 302


def test_security_headers(client):
    r = client.get("/login")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Cache-Control"] == "no-store"