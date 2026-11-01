from flask import Blueprint, jsonify

from extensions import db
from models import AuditLog, Customer, Order

bp = Blueprint("operations", __name__)


@bp.route("/ops/export", methods=["GET"])
def ops_export():
    summary = []
    for order in Order.query.order_by(Order.id).all():
        customer = order.customer
        summary.append(
            {
                "orderId": order.id,
                "status": order.status,
                "total": order.total,
                "customer": customer.name if customer is not None else None,
                "email": customer.email if customer is not None else None,
            }
        )
    return jsonify({"orders": summary, "count": len(summary)})


@bp.route("/ops/admin/purge-audit", methods=["POST"])
def ops_purge_audit():
    removed = AuditLog.query.delete()
    db.session.commit()
    return jsonify({"purged": removed})
