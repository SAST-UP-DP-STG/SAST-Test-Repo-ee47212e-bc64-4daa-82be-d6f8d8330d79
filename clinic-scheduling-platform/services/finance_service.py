from datetime import datetime, timezone

import jwt
from flask import Flask, abort, g, jsonify, request

from .service_db import connect, ensure_finance_tables
from .shared_auth import decode_token

app = Flask(__name__)
ensure_finance_tables()

INVOICE_FIELDS = {"amount", "status", "memo"}


def _now():
    return datetime.now(timezone.utc).isoformat()


@app.before_request
def authenticate():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        abort(401)
    try:
        g.jwt_payload = decode_token(header.split(" ", 1)[1].strip())
    except jwt.PyJWTError:
        abort(401)


@app.post("/invoices")
def issue_invoice():
    body = request.get_json(force=True, silent=True) or {}
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO finance_invoice (appointment_id, clinic_id, amount, status, memo, created_by, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            body.get("appointment_id"),
            body.get("clinic_id"),
            body.get("amount", 0.0),
            "issued",
            body.get("memo", ""),
            g.jwt_payload.get("username"),
            _now(),
        ),
    )
    conn.commit()
    invoice_id = cur.lastrowid
    conn.close()
    return jsonify({"status": "issued", "invoice_id": invoice_id}), 201


@app.patch("/invoices/<int:invoice_id>")
def adjust_invoice(invoice_id):
    body = request.get_json(force=True, silent=True) or {}
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE finance_invoice SET amount = ?, status = ? WHERE id = ?",
                (body.get("amount", 0.0), body.get("status", "adjusted"), invoice_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "adjusted", "invoice_id": invoice_id})


@app.delete("/invoices/<int:invoice_id>")
def cancel_invoice(invoice_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE finance_invoice SET status = ? WHERE id = ?", ("cancelled", invoice_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "cancelled", "invoice_id": invoice_id})


@app.get("/admin/export")
def export_invoices():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, appointment_id, clinic_id, amount, status, memo, created_by, created_at FROM finance_invoice ORDER BY id")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify({"invoices": rows})


@app.put("/admin/config")
def update_finance_config():
    body = request.get_json(force=True, silent=True) or {}
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM finance_config ORDER BY id LIMIT 1")
    row = cur.fetchone()
    cur.execute(
        "UPDATE finance_config SET currency = ?, tax_rate = ?, late_fee = ?, statement_footer = ? WHERE id = ?",
        (
            body.get("currency", "USD"),
            body.get("tax_rate", 0.0),
            body.get("late_fee", 0.0),
            body.get("statement_footer", ""),
            row["id"],
        ),
    )
    conn.commit()
    conn.close()
    return jsonify({"status": "updated"})


@app.post("/webhooks/invoice-paid")
def invoice_paid_webhook():
    body = request.get_json(force=True, silent=True) or {}
    invoice_id = body.get("invoice_id")
    conn = connect()
    cur = conn.cursor()
    cur.execute("UPDATE finance_invoice SET status = ? WHERE id = ?", ("paid", invoice_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "paid", "invoice_id": invoice_id})


@app.patch("/invoices/<int:invoice_id>/fields")
def update_invoice_fields(invoice_id):
    body = request.get_json(force=True, silent=True) or {}
    updates = {key: value for key, value in body.items() if key in INVOICE_FIELDS}
    if updates:
        conn = connect()
        cur = conn.cursor()
        assignments = ", ".join(f"{key} = ?" for key in updates)
        values = list(updates.values()) + [invoice_id]
        cur.execute(f"UPDATE finance_invoice SET {assignments} WHERE id = ?", values)
        conn.commit()
        conn.close()
    return jsonify({"status": "ok", "applied": list(updates.keys())})
