from flask import g, jsonify

from .. import repository as repo
from ..db import utcnow
from ..extensions import limiter
from ..services import sysinfo
from . import bp


@bp.post("/system/audit")
@limiter.limit("60 per hour")
def run_audit():
    info = sysinfo.system_info()
    repo.add_audit(g.user["id"], info)
    return jsonify({**info, "created_at": utcnow()})


@bp.post("/network/sample")
@limiter.limit("30 per minute")
def sample_network():
    speed = sysinfo.network_speed(1.0)
    repo.add_network_log(g.user["id"], speed["upload_kb_s"], speed["download_kb_s"])
    return jsonify({**speed, "created_at": utcnow()})