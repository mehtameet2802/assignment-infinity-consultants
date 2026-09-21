import os

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from app.config import settings
from app.database import Base, engine
from app.http import error_response

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
from app.cli.auth import register_auth_cli
from app.routes.analytics import analytics_bp
from app.routes.auth import auth_bp
from app.routes.dashboard import dashboard_bp
from app.routes.expenses import expenses_bp


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=_STATIC_DIR, static_url_path="/static")
    app.config.from_mapping(
        DB_SESSION=None,
        AUTH_ENABLED=settings.auth_enabled,
        API_KEY_PEPPER=settings.api_key_pepper,
        ADMIN_PASSWORD_HASH=settings.admin_password_hash,
    )
    if config_overrides:
        app.config.update(config_overrides)

    with app.app_context():
        Base.metadata.create_all(bind=engine)

    app.register_blueprint(expenses_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(auth_bp)
    register_auth_cli(app)

    def spa_index():
        return send_from_directory(_STATIC_DIR, "index.html")

    @app.get("/")
    def index_page():
        return spa_index()

    @app.get("/analytics")
    def analytics_page():
        return spa_index()

    @app.get("/settings/security")
    def security_page():
        return spa_index()

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        if request.path.startswith("/static/"):
            return error.get_response()
        code = {
            404: "not_found",
            405: "method_not_allowed",
        }.get(error.code, "http_error")
        message = error.description or "Request failed"
        return error_response(
            code,
            [{"field": None, "message": message}],
            error.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        if request.path.startswith("/static/"):
            raise error
        return error_response(
            "internal_error",
            [{"field": None, "message": "An unexpected error occurred"}],
            500,
        )

    @app.teardown_appcontext
    def close_db(exception=None):
        from flask import g

        db = g.pop("db", None)
        if db is not None and db is not app.config.get("DB_SESSION"):
            db.close()

    return app
