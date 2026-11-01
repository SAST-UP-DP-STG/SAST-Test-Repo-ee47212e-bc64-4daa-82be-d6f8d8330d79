from flask import Blueprint, render_template

from models import Customer
from auth import current_user, require_auth

bp = Blueprint("customers", __name__)
bp.before_request(require_auth)


@bp.route("/customers")
def customers():
    customer_list = Customer.query.order_by(Customer.id).all()
    return render_template(
        "customers.html", user=current_user(), customers=customer_list
    )
