from flask import jsonify, render_template, request
from flask_wtf.csrf import CSRFError

MESSAGES = {
    400: ("Bad request", "The request could not be understood."),
    401: ("Sign in required", "You need to sign in to do that."),
    403: ("Forbidden", "You don't have permission to do that."),
    404: ("Page not found", "That page doesn't exist."),
    405: ("Method not allowed", "That action isn't allowed here."),
    413: ("Request too large", "The request was too large."),
    429: ("Too many requests", "You're going too fast. Wait a moment and try again."),
    500: ("Something went wrong", "An internal error occurred. It has been logged."),
}


def _respond(code: int, title: str | None = None, message: str | None = None):
    default_title, default_message = MESSAGES.get(code, ("Error", "Something went wrong."))
    title, message = title or default_title, message or default_message
    if request.path.startswith("/api/"):
        return jsonify({"error": title, "message": message}), code
    return render_template("errors/error.html", code=code, title=title, message=message), code


def register_error_handlers(app) -> None:
    for code in MESSAGES:
        app.register_error_handler(code, lambda exc, c=code: _respond(c))

    @app.errorhandler(CSRFError)
    def csrf_error(exc):
        app.logger.warning("CSRF failure on %s from %s: %s", request.path, request.remote_addr, exc.description)
        return _respond(400, "Session expired", "Your form expired or was invalid. Reload the page and try again.")