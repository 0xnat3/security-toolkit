"""Authentication helpers (current user, guards, safe redirects) and scan-target rules."""
import ipaddress
import os
from functools import wraps
from urllib.parse import urlparse

from flask import abort, current_app, flash, g, redirect, request, session, url_for

from . import repository as repo
from .services.portscan import resolve_host


# ---------------- authentication ----------------
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


# ---------------- scan-target rules ----------------
class TargetNotAllowed(ValueError):
    """The target is well-formed but policy forbids it (becomes HTTP 403)."""


_ALWAYS_BLOCKED = (ipaddress.ip_network("0.0.0.0/8"),)


def check_scan_ip(ip: str, allow_public: bool) -> None:
    addr = ipaddress.ip_address(ip)
    # Never scannable, whatever the settings: cloud metadata (169.254.169.254 is link-local),
    # 0.0.0.0, multicast, broadcast and other reserved space.
    if (
        addr.is_unspecified
        or addr.is_multicast
        or addr.is_link_local
        or addr.is_reserved
        or any(addr in net for net in _ALWAYS_BLOCKED)
    ):
        raise TargetNotAllowed(f"{ip} is not a scannable address.")
    if addr.is_loopback or addr.is_private:
        return
    if not allow_public:
        raise TargetNotAllowed(
            "Only loopback and private-network addresses can be scanned. "
            "Set SCAN_ALLOW_PUBLIC=true in .env to allow others, and only test systems you are authorised to test."
        )


def validate_scan_target(host: str) -> tuple[str, str]:
    """Resolve once, check the resolved IP, and return (host, ip). Scan that IP, not the name."""
    host = host.strip()
    ip = resolve_host(host)  # ValueError if it doesn't resolve
    check_scan_ip(ip, current_app.config["SCAN_ALLOW_PUBLIC"])
    return host, ip


def _is_within(path: str, root: str) -> bool:
    path, root = os.path.normcase(path), os.path.normcase(root)
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:  # e.g. different drives on Windows
        return False


def resolve_scan_directory(directory: str) -> str:
    """Return the real path of `directory` if it is inside an allowed root."""
    roots = [os.path.realpath(r) for r in current_app.config["INTEGRITY_ROOTS"]]
    if not roots:
        raise TargetNotAllowed("No folders are configured for integrity checks (INTEGRITY_ROOTS).")
    try:
        raw = os.path.expanduser(directory.strip())
        candidate = raw if os.path.isabs(raw) else os.path.join(roots[0], raw)  # relative = inside the first root
        real = os.path.realpath(candidate)  # resolves symlinks and ".." before we compare
    except (ValueError, OSError) as exc:
        raise ValueError("Invalid path.") from exc

    if not any(_is_within(real, root) for root in roots):
        raise TargetNotAllowed("That folder is outside the allowed locations (INTEGRITY_ROOTS).")
    if not os.path.isdir(real):
        raise ValueError("Folder not found.")
    return real


def init_app(app) -> None:
    app.before_request(load_user)

    @app.context_processor
    def inject_user():
        return {"current_user": g.get("user")}