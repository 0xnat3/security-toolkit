from flask import current_app, g, jsonify

from .. import repository as repo
from ..extensions import limiter
from . import bp


@bp.get("/dashboard")
@limiter.limit("60 per minute")
def dashboard():
    uid = g.user["id"]
    scans = repo.recent_port_scans(uid, 5)
    audits = repo.recent_audits(uid, 10)
    network = repo.recent_network_logs(uid, 10)
    baselines = repo.recent_baselines(uid, 1)

    scans_chrono, audits_chrono, network_chrono = scans[::-1], audits[::-1], network[::-1]  # oldest first for charts
    return jsonify(
        {
            "activity": repo.activity_summary(uid),
            "recent": {
                "port_scan": scans[0] if scans else None,
                "audit": audits[0] if audits else None,
                "baseline": baselines[0] if baselines else None,
            },
            "charts": {
                "network": {
                    "labels": [r["created_at"] for r in network_chrono],
                    "upload": [r["upload_kb_s"] for r in network_chrono],
                    "download": [r["download_kb_s"] for r in network_chrono],
                },
                "port_scans": {
                    "labels": [r["host"] for r in scans_chrono],
                    "open": [r["open_count"] for r in scans_chrono],
                },
                "cpu": {
                    "labels": [r["created_at"] for r in audits_chrono],
                    "values": [r["cpu_percent"] for r in audits_chrono],
                },
            },
        }
    )


@bp.get("/history")
@limiter.limit("60 per minute")
def history():
    uid = g.user["id"]
    return jsonify(
        {
            "port_scans": repo.recent_port_scans(uid, 50),
            "audits": repo.recent_audits(uid, 50),
            "integrity_baselines": repo.recent_baselines(uid, 50),
            "network_logs": repo.recent_network_logs(uid, 50),
        }
    )


@bp.delete("/history")
@limiter.limit("5 per hour")
def clear_history():
    deleted = repo.clear_history(g.user["id"])
    current_app.logger.info("History cleared by %s (%d rows)", g.user["username"], deleted)
    return jsonify({"deleted": deleted})