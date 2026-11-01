from flask import Blueprint, jsonify, render_template

from extensions import db
from models import AuditLog, Order
from auth import current_user, require_auth

bp = Blueprint("orders", __name__)
bp.before_request(require_auth)


def _require_manager():
    if current_user().role != "manager":
        return jsonify({"error": "manager role required"}), 403
    return None


@bp.route("/orders")
def orders():
    order_list = Order.query.order_by(Order.id).all()
    return render_template("orders.html", user=current_user(), orders=order_list)


@bp.route("/orders/<int:order_id>/approve-refund", methods=["POST"])
def approve_refund(order_id):
    guard = _require_manager()
    if guard is not None:
        return guard
    order = Order.query.get(order_id)
    if order is None:
        return jsonify({"error": "order not found"}), 404
    if order.status != "REFUND_PENDING_MANAGER_APPROVAL":
        return jsonify({"error": "order is not pending approval"}), 409
    order.status = "REFUNDED"
    db.session.add(AuditLog(action="REFUND_APPROVE", detail=f"order={order_id}"))
    db.session.commit()
    return jsonify({"orderId": order.id, "status": order.status})


@bp.route("/orders/<int:order_id>/void", methods=["POST"])
def void_order(order_id):
    guard = _require_manager()
    if guard is not None:
        return guard
    order = Order.query.get(order_id)
    if order is None:
        return jsonify({"error": "order not found"}), 404
    if order.status == "VOIDED":
        return jsonify({"error": "order already voided"}), 409
    order.status = "VOIDED"
    for item in order.items:
        if item.book is not None:
            item.book.stock += item.quantity
    db.session.add(AuditLog(action="ORDER_VOID", detail=f"order={order_id}"))
    db.session.commit()
    return jsonify({"orderId": order.id, "status": order.status})
