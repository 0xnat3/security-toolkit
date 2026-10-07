# Security Toolkit

A small Flask web app for running basic security checks on your own machine and network, with per-user history, charts and CSV/PDF reports.

**Use it only on systems you own or are authorised to test.**

## Features

- **Port scanner**: threaded TCP connect scan with banner grabbing and short risk notes for well-known ports.
- **File integrity**: take a snapshot of a folder's file hashes, then check for modified, added and removed files.
- **System audit**: OS, CPU, memory and uptime of the machine running the app.
- **Network monitor**: upload and download speed samples, with optional auto-refresh.
- **Dashboard and history**: counts, recent activity and charts, plus a searchable history of every run.
- **Reports**: export any history table as CSV or PDF.

## Security design

- Passwords are hashed (Werkzeug scrypt). Failed logins look identical whether or not the username exists, and login attempts are rate limited.
- CSRF protection on every form and every API call, a strict Content-Security-Policy, and no inline scripts or styles.
- No default credentials. The first admin is created from `.env` only if the password is at least 12 characters.
- Registration is off by default.
- Each user sees only their own data.
- **Scan targets are restricted.** By default only loopback and private-network addresses can be scanned. Cloud metadata, link-local, multicast and other reserved addresses are always blocked. The hostname is resolved once, checked, and the checked IP is the one scanned.
- **Integrity checks are restricted** to folders inside `INTEGRITY_ROOTS` (your home folder by default). Symlinks and `..` are resolved before the check.
- Scanned banners and file names are untrusted and are always rendered as plain text. CSV exports neutralise spreadsheet formulas, and PDF text is escaped.

## Quick start

Requires Python 3.10 or newer.

```powershell
git clone https://github.com/0xnat3/security-toolkit.git
cd security-toolkit
python -m venv venv
.\venv\Scripts\Activate.ps1          # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
Copy-Item .env.example .env          # Linux/macOS: cp .env.example .env
```

Generate a secret key and set it, plus the first admin account, in `.env`:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

```
SECRET_KEY=<the generated value>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<at least 12 characters>
```

Start the app, then open http://127.0.0.1:5000 and sign in:

```powershell
python run.py
```

Once the admin account exists, **delete the `ADMIN_PASSWORD` line from `.env`**. It is only read while the users table is empty.

## Configuration

All settings are environment variables, read from `.env`.

| Variable                                                            | Default                               | Purpose                                                                          |
| ------------------------------------------------------------------- | ------------------------------------- | -------------------------------------------------------------------------------- |
| `SECRET_KEY`                                                        | none (required)                       | Signs sessions. At least 32 characters.                                          |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD`                                 | `admin` / blank                       | First-run admin. No account is created without a 12+ character password.         |
| `REGISTRATION_ENABLED`                                              | `false`                               | Allow people to create their own accounts.                                       |
| `SCAN_ALLOW_PUBLIC`                                                 | `false`                               | Allow scanning public IP addresses. Only for systems you are authorised to test. |
| `SCAN_MAX_PORTS`                                                    | `5000`                                | Largest port range per scan.                                                     |
| `INTEGRITY_ROOTS`                                                   | your home folder                      | Folders users may monitor, separated by `;` on Windows or `:` on Linux.          |
| `SESSION_MINUTES`                                                   | `30`                                  | Session lifetime.                                                                |
| `SESSION_COOKIE_SECURE`                                             | `false`                               | Set to `true` when served over HTTPS.                                            |
| `RATELIMIT_ENABLED` / `RATELIMIT_DEFAULT` / `RATELIMIT_STORAGE_URI` | `true` / `300 per hour` / `memory://` | Rate limiting.                                                                   |
| `HOST` / `PORT`                                                     | `127.0.0.1` / `5000`                  | Where the development server listens.                                            |
| `FLASK_DEBUG`                                                       | `false`                               | Debug mode. Never enable it on a shared machine.                                 |
| `LOG_LEVEL`                                                         | `INFO`                                | Logging level.                                                                   |

## Tests

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

## Project layout

```
run.py                   entry point
app/
  __init__.py            application factory, logging, security headers
  config.py              settings from the environment
  db.py, repository.py   SQLite schema and all SQL
  security.py            login guards and scan-target rules
  auth/                  login, logout, registration, password change
  main/                  dashboard and history pages
  api/                   JSON API (port scan, integrity, audit, network, stats)
  reports/               CSV and PDF export
  services/              port scanner, integrity, system info (no Flask code)
  templates/, static/    pages, CSS and JavaScript (Chart.js is self-hosted)
tests/                   pytest suite
instance/                database and logs, created at runtime (not committed)
```

## API

All endpoints need a signed-in session and return JSON. Send the CSRF token in an `X-CSRFToken` header on every request that changes data.

| Method and path                   | Purpose                                                |
| --------------------------------- | ------------------------------------------------------ |
| `POST /api/port-scan`             | Scan `host`, `start_port`, `end_port`, `timeout`       |
| `POST /api/integrity/baseline`    | Snapshot `directory` with `algorithm`                  |
| `POST /api/integrity/check`       | Compare a folder with its latest baseline              |
| `POST /api/system/audit`          | Record and return a system audit                       |
| `POST /api/network/sample`        | Record and return a one-second speed sample            |
| `GET /api/dashboard`              | Counts, recent activity and chart data                 |
| `GET /api/history`                | The 50 most recent entries per tool                    |
| `DELETE /api/history`             | Delete the current user's history, including baselines |
| `GET /export/<report>/<csv\|pdf>` | Download a report                                      |

## Running it for real

`python run.py` starts Flask's development server, which is meant for local use only. To serve it to others, run it with a production server (for example `waitress` on Windows or `gunicorn` on Linux) behind HTTPS, and set `SESSION_COOKIE_SECURE=true`. With more than one worker, point `RATELIMIT_STORAGE_URI` at Redis, because the default in-memory limiter is not shared between processes.

## Known limits

- Sessions are signed cookies, so signing out clears your browser's copy but cannot revoke one that was stolen. The session lifetime limits the exposure.
- Login throttling is per IP address, not per account.
- There is no two-factor authentication and no self-service password reset. To reset a password, run this from the project folder with the virtual environment active:

```powershell
  python -c "import getpass; from app import create_app, repository as repo; from werkzeug.security import generate_password_hash as h; pw=getpass.getpass('New password (12+ chars): '); assert len(pw)>=12; app=create_app(); app.app_context().push(); u=repo.get_user_by_username('admin'); repo.set_password(u['id'], h(pw)); print('password reset')"
```

- Port scans and integrity checks run inside the request, so a very large scan can take a while.
- PDF reports use ReportLab's built-in fonts, which cover Latin characters only. CSV exports keep every character.
