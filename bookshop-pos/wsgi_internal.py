import json

from auth import verify_token
from models import User


def make_internal_app(app):
    def internal_app(environ, start_response):
        config_view = {
            "storeId": app.config.get("STORE_ID"),
            "databaseUri": app.config.get("SQLALCHEMY_DATABASE_URI"),
            "secretKey": app.config.get("SECRET_KEY"),
            "servicePorts": {
                "tcpCommand": app.config.get("POS_TCP_CMD_PORT"),
                "broker": app.config.get("POS_BROKER_PORT"),
                "cache": app.config.get("POS_CACHE_PORT"),
                "rpc": app.config.get("POS_RPC_PORT"),
            },
        }
        body = json.dumps(config_view).encode("utf-8")
        start_response("200 OK", [("Content-Type", "application/json")])
        return [body]

    return internal_app


class PerimeterAuthMiddleware:
    def __init__(self, wsgi_app, app, prefix="/internal-tools"):
        self.wsgi_app = wsgi_app
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        if path.startswith(self.prefix) and not self._authenticated(environ):
            start_response(
                "401 Unauthorized", [("Content-Type", "application/json")]
            )
            return [b'{"error":"authentication required"}']
        return self.wsgi_app(environ, start_response)

    def _token(self, environ):
        header = environ.get("HTTP_AUTHORIZATION", "")
        if header.startswith("Bearer "):
            return header[7:]
        cookies = environ.get("HTTP_COOKIE", "")
        for part in cookies.split(";"):
            name, _, value = part.strip().partition("=")
            if name == "session_token":
                return value
        return None

    def _authenticated(self, environ):
        token = self._token(environ)
        if not token:
            return False
        with self.app.app_context():
            try:
                payload = verify_token(token)
            except Exception:
                return False
            user = User.query.get(int(payload.get("sub")))
            return user is not None and user.active
