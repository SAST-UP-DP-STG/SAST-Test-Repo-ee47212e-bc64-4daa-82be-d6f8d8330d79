import json
import socketserver
import threading

from extensions import db
from models import AuditLog, Book, Order


def _dump_config(app):
    return "OK " + json.dumps(
        {
            "storeId": app.config.get("STORE_ID"),
            "databaseUri": app.config.get("SQLALCHEMY_DATABASE_URI"),
            "secretKey": app.config.get("SECRET_KEY"),
        }
    )


def _dispatch(app, text):
    parts = text.split()
    command = parts[0].upper()
    with app.app_context():
        if command == "VOID_SALE" and len(parts) >= 2:
            order = Order.query.get(int(parts[1]))
            if order is None:
                return "ERR order not found"
            order.status = "VOIDED"
            for item in order.items:
                if item.book is not None:
                    item.book.stock += item.quantity
            db.session.add(AuditLog(action="TCP_VOID_SALE", detail=f"order={order.id}"))
            db.session.commit()
            return f"OK order {order.id} VOIDED"
        if command == "SET_PRICE" and len(parts) >= 3:
            book = Book.query.get(int(parts[1]))
            if book is None:
                return "ERR book not found"
            book.price = float(parts[2])
            db.session.add(
                AuditLog(action="TCP_SET_PRICE", detail=f"book={book.id} price={book.price}")
            )
            db.session.commit()
            return f"OK book {book.id} price {book.price}"
        if command == "DUMP_CONFIG":
            return _dump_config(app)
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


def start_tcp_command_service(app):
    server = _Server((app.config["SERVICE_HOST"], app.config["POS_TCP_CMD_PORT"]), _Handler)
    server.app = app
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
