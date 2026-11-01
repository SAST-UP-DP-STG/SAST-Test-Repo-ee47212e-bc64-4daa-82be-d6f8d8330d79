import json
import os
import threading
import time
from datetime import datetime, timezone

from extensions import db
from models import AuditLog, Book, Order


def start_watcher(app):
    thread = threading.Thread(target=_run, args=(app,), daemon=True)
    thread.start()
    return thread


def _run(app):
    poll = app.config.get("POS_CMD_POLL_SECONDS", 2)
    while True:
        try:
            _scan_once(app)
        except Exception:
            pass
        time.sleep(poll)


def _scan_once(app):
    inbox = app.config["POS_CMD_INBOX"]
    for name in sorted(os.listdir(inbox)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(inbox, name)
        with app.app_context():
            _process_file(app, path, name)


def _process_file(app, path, name):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        _dispatch(app, payload, name)
        _move(path, app.config["POS_CMD_PROCESSED"], name)
    except Exception:
        _move(path, app.config["POS_CMD_FAILED"], name)


def _dispatch(app, payload, name):
    command = str(payload.get("command", "")).upper()
    if command == "PRICE_UPDATE":
        _price_update(payload)
    elif command == "SET_STOCK":
        _set_stock(payload)
    elif command == "VOID_SALE":
        _void_sale(payload)
    elif command == "DAILY_REPORT":
        _daily_report(app, payload, name)
    else:
        raise ValueError("unknown command")


def _price_update(payload):
    book = Book.query.filter_by(isbn=str(payload.get("isbn"))).first()
    if book is None:
        raise ValueError("book not found")
    book.price = float(payload.get("price"))
    db.session.add(
        AuditLog(
            action="FILEDROP_PRICE_UPDATE",
            detail=f"isbn={book.isbn} price={book.price}",
        )
    )
    db.session.commit()


def _set_stock(payload):
    book = Book.query.filter_by(isbn=str(payload.get("isbn"))).first()
    if book is None:
        raise ValueError("book not found")
    book.stock = int(payload.get("quantity"))
    db.session.add(
        AuditLog(
            action="FILEDROP_SET_STOCK",
            detail=f"isbn={book.isbn} stock={book.stock}",
        )
    )
    db.session.commit()


def _void_sale(payload):
    order = Order.query.get(int(payload.get("saleId")))
    if order is None:
        raise ValueError("order not found")
    order.status = "VOIDED"
    for item in order.items:
        if item.book is not None:
            item.book.stock += item.quantity
    db.session.add(AuditLog(action="FILEDROP_VOID_SALE", detail=f"order={order.id}"))
    db.session.commit()


def _daily_report(app, payload, name):
    rows = []
    sales_total = 0.0
    for order in Order.query.order_by(Order.id).all():
        sales_total += order.total or 0.0
        customer = order.customer
        rows.append(
            {
                "orderId": order.id,
                "status": order.status,
                "total": order.total,
                "customer": (
                    {
                        "name": customer.name,
                        "email": customer.email,
                        "phone": customer.phone,
                    }
                    if customer is not None
                    else None
                ),
                "items": [
                    {
                        "isbn": item.book.isbn if item.book is not None else None,
                        "quantity": item.quantity,
                        "unitPrice": item.unit_price,
                    }
                    for item in order.items
                ],
            }
        )

    report = {
        "storeId": app.config["STORE_ID"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "salesTotal": round(sales_total, 2),
        "orderCount": len(rows),
        "orders": rows,
    }
    out_name = name.rsplit(".json", 1)[0] + "-report.json"
    out_path = os.path.join(app.config["POS_CMD_OUTBOX"], out_name)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    db.session.add(
        AuditLog(
            action="FILEDROP_DAILY_REPORT",
            detail=f"orders={len(rows)} total={round(sales_total, 2)}",
        )
    )
    db.session.commit()


def _move(path, target_dir, name):
    try:
        os.replace(path, os.path.join(target_dir, name))
    except OSError:
        if os.path.exists(path):
            os.remove(path)
