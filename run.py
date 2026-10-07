from app import create_app
from app.config import Config, ConfigError

try:
    app = create_app()
except ConfigError as exc:
    raise SystemExit(f"Configuration error: {exc}")

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)