from flask import Blueprint, render_template

from auth import current_user, require_auth
from models import AuditLog

bp = Blueprint("integrations", __name__)
bp.before_request(require_auth)


@bp.route("/integrations")
def integrations():
    events = AuditLog.query.order_by(AuditLog.id.desc()).limit(25).all()
    return render_template("integrations.html", user=current_user(), events=events)
