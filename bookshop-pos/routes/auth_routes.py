from flask import Blueprint, jsonify, make_response, redirect, render_template, request

from extensions import bcrypt
from models import User
from auth import issue_token

bp = Blueprint("auth", __name__)


def _credentials():
    if request.is_json:
        body = request.get_json(silent=True) or {}
        return body.get("username"), body.get("password")
    return request.form.get("username"), request.form.get("password")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username, password = _credentials()
    user = User.query.filter_by(username=username).first()
    if user is None or not user.active or not bcrypt.check_password_hash(
        user.password_hash, password or ""
    ):
        if request.is_json:
            return jsonify({"error": "invalid credentials"}), 401
        return render_template("login.html", error="Invalid username or password"), 401

    token = issue_token(user)
    if request.is_json:
        return jsonify({"token": token, "role": user.role})

    response = make_response(redirect("/dashboard"))
    response.set_cookie("session_token", token, httponly=True)
    return response


@bp.route("/logout")
def logout():
    response = make_response(redirect("/login"))
    response.delete_cookie("session_token")
    return response
