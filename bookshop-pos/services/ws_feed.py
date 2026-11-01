import json

from extensions import db
from models import AuditLog, Book, Order


def _apply_message(app, data):
    msg_type = str(data.get("type", "")).upper()
    with app.app_context():
        if msg_type == "VOID_SALE":
            order = Order.query.get(int(data.get("saleId")))
            if order is None:
                return {"error": "order not found"}
            order.status = "VOIDED"
            for item in order.items:
                if item.book is not None:
                    item.book.stock += item.quantity
            db.session.add(AuditLog(action="WS_VOID_SALE", detail=f"order={order.id}"))
            db.session.commit()
            return {"ok": True, "orderId": order.id, "status": order.status}
        if msg_type == "PRICE_SET":
            book = Book.query.get(int(data.get("bookId")))
            if book is None:
                return {"error": "book not found"}
            book.price = float(data.get("price"))
            db.session.add(
                AuditLog(action="WS_PRICE_SET", detail=f"book={book.id} price={book.price}")
            )
            db.session.commit()
            return {"ok": True, "bookId": book.id, "price": book.price}
        return {"error": "unknown message type"}


def register_ws(sock, app):
    @sock.route("/ws/register")
    def register_feed(ws):
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                data = json.loads(raw)
            except (TypeError, ValueError):
                ws.send(json.dumps({"error": "invalid json"}))
                continue
            result = _apply_message(app, data)
            ws.send(json.dumps(result))
