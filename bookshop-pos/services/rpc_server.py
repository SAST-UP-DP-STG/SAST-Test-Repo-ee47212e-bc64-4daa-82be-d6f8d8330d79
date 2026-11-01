import threading
from xmlrpc.server import SimpleXMLRPCRequestHandler, SimpleXMLRPCServer

from extensions import db
from models import AuditLog, Book, Order


def _build_functions(app):
    def set_price(book_id, price):
        with app.app_context():
            book = Book.query.get(int(book_id))
            if book is None:
                return {"error": "book not found"}
            book.price = float(price)
            db.session.add(
                AuditLog(action="RPC_SET_PRICE", detail=f"book={book.id} price={book.price}")
            )
            db.session.commit()
            return {"bookId": book.id, "price": book.price}

    def set_stock(book_id, stock):
        with app.app_context():
            book = Book.query.get(int(book_id))
            if book is None:
                return {"error": "book not found"}
            book.stock = int(stock)
            db.session.add(
                AuditLog(action="RPC_SET_STOCK", detail=f"book={book.id} stock={book.stock}")
            )
            db.session.commit()
            return {"bookId": book.id, "stock": book.stock}

    def refund_order(order_id):
        with app.app_context():
            order = Order.query.get(int(order_id))
            if order is None:
                return {"error": "order not found"}
            order.status = "REFUNDED"
            db.session.add(AuditLog(action="RPC_REFUND", detail=f"order={order.id}"))
            db.session.commit()
            return {"orderId": order.id, "status": order.status}

    def dump_config():
        return {
            "storeId": app.config.get("STORE_ID"),
            "databaseUri": app.config.get("SQLALCHEMY_DATABASE_URI"),
            "secretKey": app.config.get("SECRET_KEY"),
        }

    return {
        "set_price": set_price,
        "set_stock": set_stock,
        "refund_order": refund_order,
        "dump_config": dump_config,
    }


class _RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ("/RPC2", "/")


def start_rpc_server(app):
    server = SimpleXMLRPCServer(
        (app.config["SERVICE_HOST"], app.config["POS_RPC_PORT"]),
        requestHandler=_RequestHandler,
        allow_none=True,
        logRequests=False,
    )
    for name, fn in _build_functions(app).items():
        server.register_function(fn, name)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
