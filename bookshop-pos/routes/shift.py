from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, render_template, request

from extensions import db
from models import Book, Customer, Order, OrderItem, Shift, get_policy
from auth import current_user, require_auth

bp = Blueprint("shift", __name__)
bp.before_request(require_auth)


@bp.route("/shift")
def shift_view():
    user = current_user()
    open_shift = Shift.query.filter_by(cashier_id=user.id, status="OPEN").first()
    books = Book.query.order_by(Book.title).all()
    customers = Customer.query.order_by(Customer.name).all()
    return render_template(
        "shift.html",
        user=user,
        open_shift=open_shift,
        books=books,
        customers=customers,
    )


@bp.route("/shift/open", methods=["POST"])
def shift_open():
    user = current_user()
    existing = Shift.query.filter_by(cashier_id=user.id, status="OPEN").first()
    if existing is None:
        db.session.add(Shift(cashier_id=user.id, status="OPEN"))
        db.session.commit()
    return redirect("/shift")


@bp.route("/shift/close", methods=["POST"])
def shift_close():
    user = current_user()
    open_shift = Shift.query.filter_by(cashier_id=user.id, status="OPEN").first()
    if open_shift is not None:
        open_shift.status = "CLOSED"
        open_shift.closed_at = datetime.now(timezone.utc)
        db.session.commit()
    return redirect("/shift")


@bp.route("/shift/sale", methods=["POST"])
def shift_sale():
    data = request.get_json(silent=True) or request.form
    book = Book.query.get(int(data.get("book_id")))
    if book is None:
        return jsonify({"error": "book not found"}), 404

    quantity = int(data.get("quantity", 1))
    discount_percent = float(data.get("discountPercent", 0))
    max_discount = float(get_policy("maxDiscountPercent", "20"))
    if discount_percent > max_discount:
        return (
            jsonify(
                {
                    "error": "discount exceeds store policy",
                    "maxDiscountPercent": max_discount,
                }
            ),
            400,
        )

    customer_id = data.get("customer_id") or None
    subtotal = round(book.price * quantity, 2)
    total = round(subtotal * (1 - discount_percent / 100.0), 2)

    order = Order(
        customer_id=int(customer_id) if customer_id else None,
        cashier_id=current_user().id,
        subtotal=subtotal,
        discount_percent=discount_percent,
        total=total,
        status="PAID",
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(
        OrderItem(
            order_id=order.id,
            book_id=book.id,
            quantity=quantity,
            unit_price=book.price,
        )
    )
    book.stock = max(0, book.stock - quantity)
    db.session.commit()
    return jsonify(
        {
            "orderId": order.id,
            "subtotal": subtotal,
            "discountPercent": discount_percent,
            "total": total,
            "status": order.status,
        }
    )
