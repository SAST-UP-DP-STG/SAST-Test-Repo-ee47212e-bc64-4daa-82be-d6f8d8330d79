from flask import Blueprint, jsonify, request

from extensions import db
from models import AuditLog, Order

bp = Blueprint("webhooks", __name__)


def _apply_event(event, order_id):
    order = Order.query.get(order_id)
    if order is None:
        return None
    if event == "payment.refunded":
        order.status = "REFUNDED"
    elif event == "payment.captured":
        order.status = "PAID"
    elif event == "payment.failed":
        order.status = "PAYMENT_FAILED"
    else:
        return order
    db.session.add(
        AuditLog(
            action="WEBHOOK_PAYMENT",
            detail=f"event={event} order={order_id} status={order.status}",
        )
    )
    db.session.commit()
    return order


@bp.route("/webhooks/payments", methods=["POST"])
def payments_webhook():
    payload = request.get_json(silent=True) or {}
    event = str(payload.get("event", ""))
    order_id = payload.get("orderId")
    if order_id is None:
        return jsonify({"error": "orderId required"}), 400
    order = _apply_event(event, int(order_id))
    if order is None:
        return jsonify({"error": "order not found"}), 404
    return jsonify({"orderId": order.id, "status": order.status})
