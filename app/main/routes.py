from flask import render_template

from ..security import login_required
from . import bp


@bp.get("/")
@login_required
def dashboard():
    return render_template("dashboard.html")