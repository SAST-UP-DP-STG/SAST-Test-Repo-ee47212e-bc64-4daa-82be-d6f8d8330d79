import json
import queue
import socketserver
import threading

from extensions import db
from models import AuditLog, Book, Order

_events = queue.Queue()


def _accept(text):
    parts = text.split(" ", 2)
    if parts[0].upper() != "PUBLISH" or len(parts) < 3:
        return "ERR expected PUBLISH <event> <json>"
    event = parts[1].upper()
    try:
        data = json.loads(parts[2])
    except ValueError:
        return "ERR invalid json"
    _events.put((event, data))
    return f"OK queued {event}"


def _apply(event, data):
    if event == "PRICE_UPDATED":
        book = Book.query.get(int(data.get("bookId")))
        if book is None:
            return
        book.price = float(data.get("price"))
        db.session.add(
            AuditLog(action="BROKER_PRICE_UPDATED", detail=f"book={book.id} price={book.price}")
        )
        db.session.commit()
    elif event == "REFUND_ISSUED":
        order = Order.query.get(int(data.get("orderId")))
        if order is None:
            return
        order.status = "REFUNDED"
        db.session.add(AuditLog(action="BROKER_REFUND_ISSUED", detail=f"order={order.id}"))
        db.session.commit()
    elif event == "STOCK_ADJUSTED":
        book = Book.query.get(int(data.get("bookId")))
        if book is None:
            return
        book.stock = max(0, book.stock + int(data.get("delta", 0)))
        db.session.add(
            AuditLog(action="BROKER_STOCK_ADJUSTED", detail=f"book={book.id} stock={book.stock}")
        )
        db.session.commit()


def _consume(app):
    while True:
        event, data = _events.get()
        try:
            with app.app_context():
                _apply(event, data)
        except Exception:
            pass


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        while True:
            line = self.rfile.readline()
            if not line:
                break
            text = line.decode("utf-8", "replace").strip()
            if not text:
                continue
            self.wfile.write((_accept(text) + "\n").encode("utf-8"))


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_event_broker(app):
    server = _Server((app.config["SERVICE_HOST"], app.config["POS_BROKER_PORT"]), _Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=_consume, args=(app,), daemon=True).start()
    return server
