import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = os.environ.get("DATABASE_PATH", "data/clinic.db")


def db_file():
    return str(BASE_DIR / DATABASE_PATH)


def connect():
    conn = sqlite3.connect(db_file())
    conn.row_factory = sqlite3.Row
    return conn


def ensure_analytics_tables():
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_export (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requested_by INTEGER,
            requested_by_name TEXT,
            clinic_id INTEGER,
            scope TEXT,
            row_count INTEGER,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS analytics_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scope TEXT,
            weight REAL,
            refresh_minutes INTEGER,
            internal_flag INTEGER
        )
        """
    )
    cur.execute("SELECT COUNT(*) AS c FROM analytics_config")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO analytics_config (scope, weight, refresh_minutes, internal_flag) VALUES (?, ?, ?, ?)",
            ("clinic", 1.0, 60, 0),
        )
    conn.commit()
    conn.close()


def ensure_finance_tables():
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS finance_invoice (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            clinic_id INTEGER,
            amount REAL,
            status TEXT,
            memo TEXT,
            created_by TEXT,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS finance_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            currency TEXT,
            tax_rate REAL,
            late_fee REAL,
            statement_footer TEXT
        )
        """
    )
    cur.execute("SELECT COUNT(*) AS c FROM finance_config")
    if cur.fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO finance_config (currency, tax_rate, late_fee, statement_footer) VALUES (?, ?, ?, ?)",
            ("USD", 0.0, 0.0, "Thank you for choosing our clinic."),
        )
    conn.commit()
    conn.close()
