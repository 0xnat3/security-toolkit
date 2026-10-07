from flask import abort, current_app, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .. import repository as repo
from ..extensions import limiter
from ..security import is_safe_next_url, login_required
from . import bp
from .forms import ChangePasswordForm, LoginForm, RegistrationForm

# Checked against when the username doesn't exist, so response time doesn't reveal valid usernames.
_DUMMY_HASH = generate_password_hash("not-a-real-password")


def _start_session(user_id: int) -> None:
    session.clear()  # fresh session on every login (prevents session fixation)
    session["uid"] = user_id
    session.permanent = True


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if g.user:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        user = repo.get_user_by_username(form.username.data)
        valid = check_password_hash(user["password_hash"] if user else _DUMMY_HASH, form.password.data)

        if user and user["is_active"] and valid:
            _start_session(user["id"])
            repo.record_login(user["id"])
            current_app.logger.info("Login: %s", user["username"])
            target = request.args.get("next")
            return redirect(target if is_safe_next_url(target) else url_for("main.dashboard"))

        current_app.logger.warning("Failed login for %r from %s", form.username.data, request.remote_addr)
        flash("Invalid username or password.", "danger")  # same message for every failure

    return render_template("auth/login.html", form=form)


@bp.post("/logout")
def logout():
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour", methods=["POST"])
def register():
    if not current_app.config["REGISTRATION_ENABLED"]:
        abort(404)

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            repo.create_user(form.username.data, generate_password_hash(form.password.data))
        except repo.DuplicateUsername:
            form.username.errors.append("That username is already taken.")
        else:
            current_app.logger.info("Registered user: %s", form.username.data)
            flash("Account created. Please sign in.", "success")
            return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
@limiter.limit("5 per hour", methods=["POST"])
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(g.user["password_hash"], form.current_password.data):
            form.current_password.errors.append("Current password is incorrect.")
        else:
            repo.set_password(g.user["id"], generate_password_hash(form.new_password.data))
            current_app.logger.info("Password changed: %s", g.user["username"])
            _start_session(g.user["id"])
            flash("Password changed.", "success")
            return redirect(url_for("main.dashboard"))

    return render_template("auth/change_password.html", form=form)