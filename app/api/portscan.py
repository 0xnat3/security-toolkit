from flask import current_app, g, jsonify

from .. import repository as repo
from ..db import utcnow
from ..extensions import limiter
from ..security import TargetNotAllowed, validate_scan_target
from ..services import portscan as scanner
from . import ApiError, bp, parse_form
from .forms import PortScanForm


@bp.post("/port-scan")
@limiter.limit("6 per minute")
def port_scan():
    form = parse_form(PortScanForm)
    start, end, timeout = form.start_port.data, form.end_port.data, form.timeout.data

    max_ports = current_app.config["SCAN_MAX_PORTS"]
    if end - start + 1 > max_ports:
        message = f"Scan at most {max_ports} ports at a time."
        raise ApiError(message, fields={"end_port": [message]})

    try:
        host, ip = validate_scan_target(form.host.data)
    except TargetNotAllowed as exc:
        raise ApiError(str(exc), 403) from exc
    except ValueError as exc:
        raise ApiError(str(exc), fields={"host": [str(exc)]}) from exc

    try:
        result = scanner.scan_ports(host, start, end, workers=100, timeout=timeout, ip=ip)
    except ValueError as exc:
        raise ApiError(str(exc)) from exc

    results = result["results"]
    scan_id = repo.add_port_scan(g.user["id"], host, ip, start, end, results)
    current_app.logger.info(
        "Port scan by %s: %s (%s) ports %d-%d, %d open", g.user["username"], host, ip, start, end, len(results)
    )
    return jsonify(
        {
            "id": scan_id,
            "host": host,
            "ip": ip,
            "start_port": start,
            "end_port": end,
            "ports_scanned": result["ports_scanned"],
            "open_count": len(results),
            "results": results,
            "created_at": utcnow(),
        }
    )