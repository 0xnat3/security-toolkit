import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask

from .config import Config
from .extensions import csrf, limiter


def _configure_logging(app: Flask) -> None:
    os.makedirs(app.config["LOG_DIR"], exist_ok=True)
    level = getattr(logging, app.config["LOG_LEVEL"], logging.INFO)

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

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    # TEMPORARY: replaced by the main blueprint in a later step
    @app.get("/")
    def index():
        return "Security Toolkit skeleton is running."

    app.logger.info("Security Toolkit started")
    return app