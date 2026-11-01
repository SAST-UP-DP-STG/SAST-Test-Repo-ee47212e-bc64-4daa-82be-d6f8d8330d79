from flask import Blueprint, jsonify, redirect, render_template, request

from extensions import db, bcrypt
from models import AuditLog, User
from auth import current_user, require_auth

bp = Blueprint("admin", __name__)
bp.before_request(require_auth)


def _require_manager():
    if current_user().role != "manager":
        return jsonify({"error": "manager role required"}), 403
    return None


@bp.route("/admin/staff", methods=["GET"])
def staff_list():
    guard = _require_manager()
    if guard is not None:
        return guard
    staff = User.query.order_by(User.id).all()
    return render_template("staff.html", user=current_user(), staff=staff)


@bp.route("/admin/staff", methods=["POST"])
def staff_create():
    guard = _require_manager()
    if guard is not None:
        return guard

    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role", "cashier")
    full_name = request.form.get("full_name", username)
    if not username or not password:
        return redirect("/admin/staff")
    if User.query.filter_by(username=username).first() is not None:
        return redirect("/admin/staff")

    user = User(
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
        full_name=full_name,
        active=True,
    )
    db.session.add(user)
    db.session.add(
        AuditLog(action="STAFF_CREATE", detail=f"username={username} role={role}")
    )
    db.session.commit()
    return redirect("/admin/staff")
