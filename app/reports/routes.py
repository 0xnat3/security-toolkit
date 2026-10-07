from datetime import datetime, timezone
from io import BytesIO

from flask import abort, current_app, g, send_file

from .. import repository as repo
from ..extensions import limiter
from ..security import login_required
from . import bp
from .definitions import REPORTS
from .render import to_csv, to_pdf

# format -> (mimetype, maximum rows)
FORMATS = {
    "csv": ("text/csv", 10_000),
    "pdf": ("application/pdf", 500),
}


@bp.get("/<report_type>/<fmt>")
@login_required
@limiter.limit("20 per hour")
def export(report_type, fmt):
    report = REPORTS.get(report_type)
    if report is None or fmt not in FORMATS:
        abort(404)

    mimetype, max_rows = FORMATS[fmt]
    rows = repo.export_rows(g.user["id"], report_type, max_rows + 1)  # one extra row tells us if we truncated
    truncated = len(rows) > max_rows
    rows = rows[:max_rows]

    now = datetime.now(timezone.utc)
    if fmt == "csv":
        data = to_csv(report, rows)
    else:
        note = f"Showing the {max_rows} most recent entries. Export CSV to get more." if truncated else None
        data = to_pdf(report, rows, username=g.user["username"], generated_at=now, note=note)

    current_app.logger.info("Export by %s: %s as %s (%d rows)", g.user["username"], report_type, fmt, len(rows))
    return send_file(
        BytesIO(data),
        mimetype=mimetype,
        as_attachment=True,
        download_name=f"{report.filename}-{now:%Y%m%d-%H%M%S}.{fmt}",
    )