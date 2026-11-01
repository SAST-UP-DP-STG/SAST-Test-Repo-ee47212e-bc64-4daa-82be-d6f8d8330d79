from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, FastAPI
from pydantic import BaseModel

from .analytics_deps import get_current_user
from .service_db import connect, ensure_analytics_tables

app = FastAPI(title="Clinic Analytics Service", root_path="/svc/analytics")

ensure_analytics_tables()


class ConfigUpdate(BaseModel):
    scope: Optional[str] = None
    weight: Optional[float] = None
    refresh_minutes: Optional[int] = None
    internal_flag: Optional[int] = None


def _now():
    return datetime.now(timezone.utc).isoformat()


@app.post("/export/full")
def export_full(user=Depends(get_current_user)):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM scheduling_clinic")
    clinics = cur.fetchall()
    total = 0
    for clinic in clinics:
        cur.execute(
            "SELECT COUNT(*) AS c FROM scheduling_appointment WHERE clinic_id = ?",
            (clinic["id"],),
        )
        count = cur.fetchone()["c"]
        total += count
        cur.execute(
            "INSERT INTO analytics_export (requested_by, requested_by_name, clinic_id, scope, row_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user.get("sub"), user.get("username"), clinic["id"], "full", count, _now()),
        )
    conn.commit()
    conn.close()
    return {"status": "completed", "clinics": len(clinics), "rows_exported": total}


@app.post("/clinics/recompute")
def recompute(user=Depends(get_current_user)):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM scheduling_clinic")
    clinics = cur.fetchall()
    results = []
    for clinic in clinics:
        cur.execute(
            "SELECT COUNT(*) AS c FROM scheduling_appointment WHERE clinic_id = ?",
            (clinic["id"],),
        )
        count = cur.fetchone()["c"]
        results.append({"clinic_id": clinic["id"], "clinic": clinic["name"], "utilization": count})
    conn.close()
    return {"status": "recomputed", "clinics": results}


@app.get("/my-exports")
def my_exports(user=Depends(get_current_user)):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, requested_by, requested_by_name, clinic_id, scope, row_count, created_at "
        "FROM analytics_export ORDER BY id DESC"
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"exports": rows}


@app.patch("/config")
def update_config(payload: ConfigUpdate, user=Depends(get_current_user)):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM analytics_config ORDER BY id LIMIT 1")
    row = cur.fetchone()
    fields = payload.dict(exclude_unset=True)
    if row and fields:
        assignments = ", ".join(f"{key} = ?" for key in fields)
        values = list(fields.values()) + [row["id"]]
        cur.execute(f"UPDATE analytics_config SET {assignments} WHERE id = ?", values)
        conn.commit()
    cur.execute("SELECT scope, weight, refresh_minutes, internal_flag FROM analytics_config ORDER BY id LIMIT 1")
    current = dict(cur.fetchone())
    conn.close()
    return {"status": "updated", "config": current}
