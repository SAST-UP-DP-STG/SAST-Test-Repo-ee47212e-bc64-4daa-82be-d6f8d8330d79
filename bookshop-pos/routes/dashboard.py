from flask import Blueprint, render_template

from models import Book, Order
from auth import current_user, require_auth

bp = Blueprint("dashboard", __name__)
bp.before_request(require_auth)


@bp.route("/dashboard")
def dashboard():
    total_orders = Order.query.count()
    pending_refunds = Order.query.filter_by(
        status="REFUND_PENDING_MANAGER_APPROVAL"
    ).count()
    low_stock = Book.query.filter(Book.stock < 5).count()
    return render_template(
        "dashboard.html",
        user=current_user(),
        total_orders=total_orders,
        pending_refunds=pending_refunds,
        low_stock=low_stock,
    )
