"""Authentication helpers: current user loading, login/admin guards, safe redirects."""
from functools import wraps
from urllib.parse import urlparse

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from . import repository as repo


def load_user() -> None:
    """Runs before every request: resolve the signed-in user from the session cookie."""
    g.user = None
    if request.endpoint == "static":
        return
    uid = session.get("uid")
    if uid is None:
        return
    user = repo.get_user(uid)
    if user is None or not user["is_active"]:
        session.clear()  # deleted or disabled accounts are signed out immediately
        return
    g.user = user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.get("user") is None:
            current_app.logger.warning("Unauthenticated access to %s from %s", request.path, request.remote_addr)
            if request.path.startswith("/api/"):
                abort(401)
            flash("Please sign in to continue.", "warning")
            target = None
            if request.method == "GET":
                target = request.full_path if request.query_string else request.path
            return redirect(url_for("auth.login", next=target))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            current_app.logger.warning("Forbidden: %s tried %s", g.user["username"], request.path)
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def is_safe_next_url(target: str | None) -> bool:
    """Only allow redirects to a path on this site (blocks open redirects like //evil.com)."""
    if not target or "\\" in target:
        return False
    parts = urlparse(target)
    return not parts.scheme and not parts.netloc and target.startswith("/") and not target.startswith("//")


def init_app(app) -> None:
    app.before_request(load_user)

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user")}