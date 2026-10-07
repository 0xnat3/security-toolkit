import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, request

from . import db, security
from .config import Config
from .errors import register_error_handlers
from .extensions import csrf, limiter

CSP = "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"


def _configure_logging(app: Flask) -> None:
    os.makedirs(app.config["LOG_DIR"], exist_ok=True)
    level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)

    for old in [h for h in app.logger.handlers if isinstance(h, RotatingFileHandler)]:
        app.logger.removeHandler(old)
        old.close()

    file_handler = RotatingFileHandler(
        os.path.join(app.config["LOG_DIR"], "toolkit.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    )
    app.logger.addHandler(file_handler)  # Flask already logs to the console
    app.logger.setLevel(level)


def create_app(config_class=Config) -> Flask:
    config_class.validate()

    app = Flask(__name__, instance_path=str(config_class.INSTANCE_DIR))
    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)

    _configure_logging(app)
    csrf.init_app(app)
    limiter.init_app(app)
    db.init_app(app)
    security.init_app(app)

    from .api import bp as api_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(reports_bp)
    register_error_handlers(app)

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if not app.debug:  # the Werkzeug debugger needs inline scripts
            response.headers.setdefault("Content-Security-Policy", CSP)
        if request.endpoint != "static":
            response.headers.setdefault("Cache-Control", "no-store")  # back button can't reveal pages after logout
        return response

    app.logger.info("Security Toolkit started")
    return app