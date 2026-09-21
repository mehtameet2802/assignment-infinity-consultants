import os

from flask import Flask, jsonify, send_from_directory

from app.database import Base, engine

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
from app.routes.analytics import analytics_bp
from app.routes.dashboard import dashboard_bp
from app.routes.expenses import expenses_bp


def create_app(config_overrides: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder=_STATIC_DIR, static_url_path="/static")
    app.config.from_mapping(DB_SESSION=None)
    if config_overrides:
        app.config.update(config_overrides)

    with app.app_context():
        Base.metadata.create_all(bind=engine)

    app.register_blueprint(expenses_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(analytics_bp)

    def spa_index():
        return send_from_directory(_STATIC_DIR, "index.html")

    @app.get("/")
    def index_page():
        return spa_index()

    @app.get("/analytics")
    def analytics_page():
        return spa_index()

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"})

    @app.teardown_appcontext
    def close_db(exception=None):
        from flask import g

        db = g.pop("db", None)
        if db is not None and db is not app.config.get("DB_SESSION"):
            db.close()

    return app
