from flask import Blueprint

bp = Blueprint("reports", __name__, url_prefix="/export")

from . import routes  # noqa: E402,F401