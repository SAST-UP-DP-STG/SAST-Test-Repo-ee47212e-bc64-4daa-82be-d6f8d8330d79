from flask import Blueprint, render_template

from models import get_policy
from auth import current_user, require_auth

bp = Blueprint("management", __name__)
bp.before_request(require_auth)


@bp.route("/management/policies")
def policies_view():
    refund_required = get_policy("refundApprovalRequired", "true") == "true"
    max_discount = get_policy("maxDiscountPercent", "20")
    return render_template(
        "policies.html",
        user=current_user(),
        refund_required=refund_required,
        max_discount=max_discount,
    )
