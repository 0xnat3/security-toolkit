"""Threaded TCP connect scanner with best-effort banner grabbing.

Pure logic: no Flask, no database. Deciding which hosts may be scanned is the
caller's job (see app/security.py); this module only validates the numbers.
"""
import logging
import socket
import ssl
from concurrent.futures import ThreadPoolExecutor

from .ports import risk_note, service_name

log = logging.getLogger(__name__)

MAX_WORKERS = 200
MIN_TIMEOUT, MAX_TIMEOUT = 0.1, 10.0
BANNER_LIMIT = 200

HTTP_PORTS = {80, 3000, 5000, 8000, 8080, 8888}
TLS_PORTS = {443, 8443}


def resolve_host(host: str) -> str:
    """Resolve once to an IPv4 address so we don't do a DNS lookup for every port."""
    host = (host or "").strip()
    if not host:
        raise ValueError("Host is required")
    try:
        return socket.gethostbyname(host)
    except (socket.gaierror, UnicodeError) as exc:
        raise ValueError(f"Could not resolve host: {host}") from exc


def _clean(text: str) -> str:
    text = "".join(ch if ch.isprintable() or ch.isspace() else "." for ch in text)
    return " ".join(text.split())[:BANNER_LIMIT]


def _recv(sock, size: int = 1024) -> str:
    try:
        return sock.recv(size).decode("utf-8", errors="replace")
    except OSError:  # includes timeouts
        return ""


def _passive_banner(sock) -> str:
    """Services like SSH, FTP and SMTP speak first. For others, nudge with a newline."""
    text = _recv(sock)
    if not text:
        try:
            sock.sendall(b"\r\n")
        except OSError:
            return ""
        text = _recv(sock, 512)
    return _clean(text)


def _http_banner(sock, host: str) -> str:
    """Web servers wait for a request, so a plain recv() would just time out."""
    host = host.replace("\r", "").replace("\n", "")
    request = f"HEAD / HTTP/1.0\r\nHost: {host}\r\nUser-Agent: security-toolkit\r\nConnection: close\r\n\r\n"
    try:
        sock.sendall(request.encode("ascii", errors="ignore"))
    except OSError:
        return ""
    lines = _recv(sock, 2048).splitlines()
    if not lines:
        return ""
    parts = [lines[0]]
    parts += [ln for ln in lines[1:] if ln.lower().startswith("server:")][:1]
    return _clean(" | ".join(parts))


def _tls_banner(sock, host: str) -> str:
    # Certificate verification is off on purpose: we are fingerprinting, not trusting.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            return _http_banner(tls, host)
    except OSError:  # includes ssl.SSLError
        return ""


def _scan_one(ip: str, host: str, port: int, timeout: float) -> dict | None:
    """Return a result dict if the port is open, otherwise None."""
    try:
        sock = socket.create_connection((ip, port), timeout=timeout)
    except OSError:
        return None
    try:
        sock.settimeout(timeout)
        if port in TLS_PORTS:
            banner = _tls_banner(sock, host)
        elif port in HTTP_PORTS:
            banner = _http_banner(sock, host)
        else:
            banner = _passive_banner(sock)
    except Exception:
        log.debug("Banner grab failed on %s:%s", ip, port, exc_info=True)
        banner = ""
    finally:
        sock.close()
    return {
        "port": port,
        "status": "OPEN",
        "service": service_name(port),
        "banner": banner,
        "risk": risk_note(port),
    }


def scan_ports(host, start_port=1, end_port=1024, workers=100, timeout=1.0) -> dict:
    """Scan start_port..end_port and return only the open ports."""
    try:
        start, end = int(start_port), int(end_port)
        workers, timeout = int(workers), float(timeout)
    except (TypeError, ValueError) as exc:
        raise ValueError("Ports, workers and timeout must be numbers") from exc
    if not 1 <= start <= end <= 65535:
        raise ValueError("Port range must satisfy 1 <= start <= end <= 65535")

    workers = max(1, min(workers, MAX_WORKERS))
    timeout = max(MIN_TIMEOUT, min(timeout, MAX_TIMEOUT))

    ip = resolve_host(host)
    host = host.strip()
    ports = range(start, end + 1)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        found = [r for r in pool.map(lambda p: _scan_one(ip, host, p, timeout), ports) if r]

    return {"host": host, "ip": ip, "ports_scanned": len(ports), "results": found}