"""JSON API. Every route requires a signed-in user and returns JSON, errors included."""
from flask import Blueprint, abort, g, jsonify, request
from werkzeug.datastructures import MultiDict

bp = Blueprint("api", __name__, url_prefix="/api")


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, fields: dict | None = None):
        super().__init__(message)
        self.message, self.status, self.fields = message, status, fields


@bp.errorhandler(ApiError)
def _handle_api_error(exc: ApiError):
    body = {"error": exc.message}
    if exc.fields:
        body["fields"] = exc.fields
    return jsonify(body), exc.status


@bp.before_request
def _require_login():
    if g.get("user") is None:
        abort(401)


def parse_form(form_class):
    """Validate the JSON body with a WTForms form. Missing keys fall back to the field defaults."""
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        raise ApiError("The request body must be a JSON object.")
    formdata = MultiDict(
        (key, str(value))
        for key, value in payload.items()
        if isinstance(value, (str, int, float)) and not isinstance(value, bool)
    )
    form = form_class(formdata=formdata)
    if not form.validate():
        raise ApiError("Some fields are invalid.", fields=form.errors)
    return form


from . import integrity, portscan, stats, system  # noqa: E402,F401