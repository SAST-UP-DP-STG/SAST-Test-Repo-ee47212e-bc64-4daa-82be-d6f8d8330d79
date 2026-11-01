import json
import socketserver
import threading

from extensions import db
from models import AuditLog, set_policy

_session_cache = {}


def _dispatch(app, text):
    parts = text.split()
    command = parts[0].upper()
    if command == "GET_CONFIG":
        return "OK " + json.dumps(
            {
                "storeId": app.config.get("STORE_ID"),
                "databaseUri": app.config.get("SQLALCHEMY_DATABASE_URI"),
                "secretKey": app.config.get("SECRET_KEY"),
                "cachedSessions": list(_session_cache.keys()),
            }
        )
    if command == "SET_DISCOUNT" and len(parts) >= 2:
        value = int(float(parts[1]))
        with app.app_context():
            set_policy("maxDiscountPercent", str(value))
            db.session.add(
                AuditLog(action="CACHE_SET_DISCOUNT", detail=f"maxDiscountPercent={value}")
            )
            db.session.commit()
        return f"OK maxDiscountPercent {value}"
    if command == "FLUSH_SESSIONS":
        count = len(_session_cache)
        _session_cache.clear()
        with app.app_context():
            db.session.add(
                AuditLog(action="CACHE_FLUSH_SESSIONS", detail=f"cleared={count}")
            )
            db.session.commit()
        return f"OK flushed {count} sessions"
    return "ERR unknown command"


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        app = self.server.app
        while True:
            line = self.rfile.readline()
            if not line:
                break
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            self.wfile.write((_dispatch(app, text) + "\n").encode("utf-8"))


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_cache_admin_service(app):
    _session_cache.update(
        {"register-01": "open", "register-02": "open", "register-03": "idle"}
    )
    server = _Server((app.config["SERVICE_HOST"], app.config["POS_CACHE_PORT"]), _Handler)
    server.app = app
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
