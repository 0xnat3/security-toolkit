from flask import current_app, g, jsonify

from .. import repository as repo
from ..db import utcnow
from ..extensions import limiter
from ..security import TargetNotAllowed, resolve_scan_directory
from ..services import integrity as fim
from . import ApiError, bp, parse_form
from .forms import IntegrityForm

MAX_LISTED = 500  # cap the file lists in a response; counts are always exact


def _resolve(directory: str) -> str:
    try:
        return resolve_scan_directory(directory)
    except TargetNotAllowed as exc:
        raise ApiError(str(exc), 403) from exc
    except ValueError as exc:
        raise ApiError(str(exc), fields={"directory": [str(exc)]}) from exc


def _snapshot(directory: str, algorithm: str) -> dict:
    try:
        return fim.snapshot(directory, algorithm)
    except ValueError as exc:
        raise ApiError(str(exc)) from exc


@bp.post("/integrity/baseline")
@limiter.limit("20 per hour")
def create_baseline():
    form = parse_form(IntegrityForm)
    if not form.directory.data:
        raise ApiError("Directory is required.", fields={"directory": ["Directory is required."]})

    algorithm = form.algorithm.data or fim.DEFAULT_ALGORITHM
    directory = _resolve(form.directory.data)
    snap = _snapshot(directory, algorithm)
    repo.add_baseline(g.user["id"], directory, algorithm, snap["files"])

    current_app.logger.info(
        "Baseline by %s: %s (%s), %d files", g.user["username"], directory, algorithm, len(snap["files"])
    )
    return jsonify(
        {
            "directory": directory,
            "algorithm": algorithm,
            "file_count": len(snap["files"]),
            "skipped": snap["skipped"][:MAX_LISTED],
            "skipped_count": len(snap["skipped"]),
            "created_at": utcnow(),
        }
    )


@bp.post("/integrity/check")
@limiter.limit("30 per hour")
def check_integrity():
    form = parse_form(IntegrityForm)
    uid = g.user["id"]

    if form.directory.data:
        directory = _resolve(form.directory.data)
        algorithm = form.algorithm.data or fim.DEFAULT_ALGORITHM
    else:  # no folder given: re-check the most recent baseline
        target = repo.last_baseline_target(uid)
        if target is None:
            raise ApiError("No baseline yet. Create one first.", 409)
        directory, algorithm = _resolve(target["directory"]), target["algorithm"]

    baseline = repo.latest_baseline(uid, directory, algorithm)
    if baseline is None:
        raise ApiError("No baseline for that folder and algorithm. Create one first.", 409)

    snap = _snapshot(directory, algorithm)
    diff = fim.compare(baseline["files"], snap["files"])
    current_app.logger.info("Integrity check by %s: %s (%s)", g.user["username"], directory, diff["summary"])

    return jsonify(
        {
            "directory": directory,
            "algorithm": algorithm,
            "baseline_created_at": baseline["created_at"],
            "checked_at": utcnow(),
            "summary": diff["summary"],
            "counts": {k: len(diff[k]) for k in ("added", "removed", "modified")},
            "added": diff["added"][:MAX_LISTED],
            "removed": diff["removed"][:MAX_LISTED],
            "modified": diff["modified"][:MAX_LISTED],
            "truncated": any(len(diff[k]) > MAX_LISTED for k in ("added", "removed", "modified")),
            "skipped_count": len(snap["skipped"]),
        }
    )