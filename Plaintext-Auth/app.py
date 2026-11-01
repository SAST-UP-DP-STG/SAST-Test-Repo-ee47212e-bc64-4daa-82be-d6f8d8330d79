from flask import Flask, render_template, request, redirect, url_for, make_response
import os
import sqlite3
import secrets
from typing import Optional, Tuple

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "app.db")

session_store: dict[str, str] = {}


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def find_user(username: str) -> Optional[sqlite3.Row]:
    conn = get_db()
    try:
        cur = conn.execute("SELECT id, username, password FROM users WHERE username = ?", (username,))
        return cur.fetchone()
    finally:
        conn.close()


def create_user(username: str, password: str) -> Tuple[bool, Optional[str]]:
    conn = get_db()
    try:
        conn.execute("INSERT INTO users(username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Username already exists"
    finally:
        conn.close()


def verify_password(stored_plain: str, provided: str) -> bool:
    return stored_plain == provided


def current_username_from_request() -> Optional[str]:
    sid = request.cookies.get("SESSIONID")
    if not sid:
        return None
    return session_store.get(sid)


@app.get("/")
def index():
    username = current_username_from_request()
    if username:
        return redirect(url_for("home"))
    return render_template("login.html")


@app.get("/register")
def register_form():
    return render_template("register.html")


@app.post("/auth/register")
def auth_register():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    if not username or not password:
        return render_template("register.html", error="Username and password are required"), 400

    ok, err = create_user(username, password)
    if not ok:
        return render_template("register.html", error=err or "Registration failed"), 400
    return redirect(url_for("login_form"))


@app.get("/login")
def login_form():
    return render_template("login.html")


@app.post("/auth/login")
def auth_login():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    if not username or not password:
        return render_template("login.html", error="Username and password are required"), 400

    user = find_user(username)
    if not user or not verify_password(user["password"], password):
        return render_template("login.html", error="Invalid credentials"), 401

    sid = f"sid-{secrets.token_urlsafe(12)}"
    session_store[sid] = username

    resp = make_response(redirect(url_for("home")))
    resp.set_cookie("SESSIONID", sid, path="/")
    return resp


@app.get("/home")
def home():
    username = current_username_from_request()
    if not username:
        return redirect(url_for("login_form"))
    return render_template("welcome.html", username=username)


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        init_db()
    app.run(host="0.0.0.0", port=8082, debug=False)

