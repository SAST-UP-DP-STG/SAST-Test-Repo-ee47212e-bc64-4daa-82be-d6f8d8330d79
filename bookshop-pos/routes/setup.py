from flask import Blueprint, jsonify, request

from extensions import db, bcrypt
from models import AuditLog, User

bp = Blueprint("setup", __name__)


@bp.route("/setup/bootstrap-user", methods=["POST"])
def bootstrap_user():
    data = request.get_json(silent=True) or request.form
    username = data.get("username")
    password = data.get("password")
    role = data.get("role", "cashier")
    full_name = data.get("full_name", username)

    if not username or not password:
        return jsonify({"error": "username and password required"}), 400
    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"error": "user already exists"}), 409

    user = User(
        username=username,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
        full_name=full_name,
        active=True,
    )
    db.session.add(user)
    db.session.add(
        AuditLog(action="BOOTSTRAP_USER", detail=f"username={username} role={role}")
    )
    db.session.commit()
    return jsonify({"userId": user.id, "username": user.username, "role": user.role})
