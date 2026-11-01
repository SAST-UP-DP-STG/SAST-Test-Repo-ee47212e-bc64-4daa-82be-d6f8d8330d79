import os

from flask import Flask, redirect
from flask_sock import Sock
from werkzeug.middleware.dispatcher import DispatcherMiddleware

from config import Config, DATA_DIR
from extensions import db, bcrypt
from perimeter import register_perimeter
from services.cache_admin import start_cache_admin_service
from services.command_tcp import start_tcp_command_service
from services.command_watcher import start_watcher
from services.event_broker import start_event_broker
from services.rpc_server import start_rpc_server
from services.ws_feed import register_ws
from wsgi_internal import PerimeterAuthMiddleware, make_internal_app


def _ensure_directories(app):
    for path in (
        app.config["DATA_DIR"],
        app.config["POS_CMD_INBOX"],
        app.config["POS_CMD_PROCESSED"],
        app.config["POS_CMD_FAILED"],
        app.config["POS_CMD_OUTBOX"],
    ):
        os.makedirs(path, exist_ok=True)


def _register_blueprints(app):
    from routes.auth_routes import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.catalog import bp as catalog_bp
    from routes.orders import bp as orders_bp
    from routes.customers import bp as customers_bp
    from routes.shift import bp as shift_bp
    from routes.admin import bp as admin_bp
    from routes.management import bp as management_bp
    from routes.order_api import bp as order_api_bp
    from routes.setup import bp as setup_bp
    from routes.management_api import bp as management_api_bp
    from routes.maintenance import bp as maintenance_bp
    from routes.webhooks import bp as webhooks_bp
    from routes.graphql_api import bp as graphql_bp
    from routes.operations import bp as operations_bp
    from routes.devconsole import bp as devconsole_bp
    from routes.integrations import bp as integrations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(shift_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(management_bp)
    app.register_blueprint(order_api_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(management_api_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(webhooks_bp)
    app.register_blueprint(graphql_bp)
    app.register_blueprint(operations_bp)
    app.register_blueprint(devconsole_bp)
    app.register_blueprint(integrations_bp)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config["DATA_DIR"] = DATA_DIR
    _ensure_directories(app)

    db.init_app(app)
    bcrypt.init_app(app)

    _register_blueprints(app)
    register_perimeter(app)

    sock = Sock(app)
    register_ws(sock, app)

    @app.route("/")
    def index():
        return redirect("/dashboard")

    with app.app_context():
        import models  # noqa: F401
        from seed import seed_data

        seed_data()

    start_watcher(app)
    start_tcp_command_service(app)
    start_event_broker(app)
    start_cache_admin_service(app)
    start_rpc_server(app)

    internal_app = make_internal_app(app)
    app.wsgi_app = DispatcherMiddleware(
        PerimeterAuthMiddleware(app.wsgi_app, app),
        {"/internal-tools": internal_app},
    )
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False, use_evalex=True)
