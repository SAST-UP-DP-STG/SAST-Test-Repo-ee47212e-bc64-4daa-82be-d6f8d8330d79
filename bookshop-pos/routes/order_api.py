import csv
import io

from flask import Blueprint, Response, jsonify, request

from extensions import db
from models import AuditLog, Book, Customer, Order, get_policy

bp = Blueprint("order_api", __name__)


@bp.route("/api/orders/<int:order_id>/refund", methods=["POST"])
def refund_order(order_id):
    order = Order.query.get(order_id)
    if order is None:
        return jsonify({"error": "order not found"}), 404

    approval_required = get_policy("refundApprovalRequired", "true") == "true"
    if approval_required:
        order.status = "REFUND_PENDING_MANAGER_APPROVAL"
    else:
        order.status = "REFUNDED"
    db.session.add(
        AuditLog(action="REFUND", detail=f"order={order_id} status={order.status}")
    )
    db.session.commit()
    return jsonify({"orderId": order.id, "status": order.status})


@bp.route("/api/books/<int:book_id>/price", methods=["POST"])
def change_price(book_id):
    data = request.get_json(silent=True) or request.form
    book = Book.query.get(book_id)
    if book is None:
        return jsonify({"error": "book not found"}), 404

    book.price = float(data.get("price"))
    db.session.add(
        AuditLog(action="PRICE_CHANGE", detail=f"book={book_id} price={book.price}")
    )
    db.session.commit()
    return jsonify({"bookId": book.id, "isbn": book.isbn, "price": book.price})


@bp.route("/api/customers/export", methods=["GET"])
def export_customers():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["customer_id", "name", "email", "phone", "order_id", "total", "status"]
    )
    for customer in Customer.query.order_by(Customer.id).all():
        customer_orders = Order.query.filter_by(customer_id=customer.id).all()
        if customer_orders:
            for order in customer_orders:
                writer.writerow(
                    [
                        customer.id,
                        customer.name,
                        customer.email,
                        customer.phone,
                        order.id,
                        order.total,
                        order.status,
                    ]
                )
        else:
            writer.writerow(
                [customer.id, customer.name, customer.email, customer.phone, "", "", ""]
            )

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@bp.route("/api/catalog/import", methods=["POST"])
def import_catalog():
    data = request.get_json(silent=True) or {}
    entries = data.get("books", [])
    imported = 0
    updated = 0
    for entry in entries:
        isbn = str(entry.get("isbn"))
        book = Book.query.filter_by(isbn=isbn).first()
        if book is None:
            db.session.add(
                Book(
                    isbn=isbn,
                    title=entry.get("title", ""),
                    author=entry.get("author", ""),
                    price=float(entry.get("price", 0)),
                    stock=int(entry.get("stock", 0)),
                )
            )
            imported += 1
        else:
            book.title = entry.get("title", book.title)
            book.author = entry.get("author", book.author)
            book.price = float(entry.get("price", book.price))
            book.stock = int(entry.get("stock", book.stock))
            updated += 1
    db.session.add(
        AuditLog(
            action="CATALOG_IMPORT", detail=f"imported={imported} updated={updated}"
        )
    )
    db.session.commit()
    return jsonify({"imported": imported, "updated": updated})
