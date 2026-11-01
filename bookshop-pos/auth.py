from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app, g, jsonify, redirect, request

from models import User


def issue_token(user):
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def verify_token(token):
    return jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])


def _read_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:]
    return request.cookies.get("session_token")


def current_user():
    return getattr(g, "user", None)


def _deny():
    accepts_html = "text/html" in request.headers.get("Accept", "")
    if request.method == "GET" and accepts_html:
        return redirect("/login")
    return jsonify({"error": "authentication required"}), 401


def require_auth():
    token = _read_token()
    if not token:
        return _deny()
    try:
        payload = verify_token(token)
    except jwt.PyJWTError:
        return _deny()
    user = User.query.get(int(payload.get("sub")))
    if user is None or not user.active:
        return _deny()
    g.user = user
    return None
