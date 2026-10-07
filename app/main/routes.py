from flask import current_app, render_template

from ..security import login_required
from . import bp


@bp.get("/")
@login_required
def dashboard():
    return render_template("dashboard.html", integrity_roots=current_app.config["INTEGRITY_ROOTS"])


@bp.get("/history")
@login_required
def history():
    return render_template("history.html")