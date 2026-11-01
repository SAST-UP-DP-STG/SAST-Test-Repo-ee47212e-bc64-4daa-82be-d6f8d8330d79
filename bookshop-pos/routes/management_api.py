from flask import Blueprint, jsonify, request

from extensions import db
from models import AuditLog, set_policy

bp = Blueprint("management_api", __name__)


def _as_bool(raw):
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("true", "1", "yes", "on")


@bp.route("/management/policies/refunds", methods=["POST"])
def set_refund_policy():
    data = request.get_json(silent=True) or request.form
    value = "true" if _as_bool(data.get("refundApprovalRequired")) else "false"
    set_policy("refundApprovalRequired", value)
    db.session.add(
        AuditLog(action="POLICY_REFUNDS", detail=f"refundApprovalRequired={value}")
    )
    db.session.commit()
    return jsonify({"refundApprovalRequired": value == "true"})


@bp.route("/management/policies/discounts", methods=["POST"])
def set_discount_policy():
    data = request.get_json(silent=True) or request.form
    max_discount = int(float(data.get("maxDiscountPercent")))
    set_policy("maxDiscountPercent", str(max_discount))
    db.session.add(
        AuditLog(action="POLICY_DISCOUNTS", detail=f"maxDiscountPercent={max_discount}")
    )
    db.session.commit()
    return jsonify({"maxDiscountPercent": max_discount})
