from flask import Blueprint, jsonify

from config import Config
from extensions import db
from models import AuditLog, Order
from auth import require_auth

bp = Blueprint("maintenance", __name__)
if not Config.SETUP_MODE:
    bp.before_request(require_auth)


@bp.route("/maintenance/rebuild-order-totals", methods=["POST"])
def rebuild_order_totals():
    orders = Order.query.all()
    grand_total = 0.0
    for order in orders:
        subtotal = sum((item.unit_price or 0) * item.quantity for item in order.items)
        order.subtotal = round(subtotal, 2)
        order.total = round(subtotal * (1 - (order.discount_percent or 0) / 100.0), 2)
        grand_total += order.total
    db.session.add(
        AuditLog(action="REBUILD_TOTALS", detail=f"orders={len(orders)}")
    )
    db.session.commit()
    return jsonify(
        {"ordersProcessed": len(orders), "grandTotal": round(grand_total, 2)}
    )
