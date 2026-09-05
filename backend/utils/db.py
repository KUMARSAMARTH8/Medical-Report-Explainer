"""Small SQLite persistence layer used by the report history dashboard."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone

from config import settings

DB_PATH = (
    settings.db_path
    if os.path.isabs(settings.db_path)
    else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", settings.db_path))
)


def _connect():
    parent = os.path.dirname(DB_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                parameters_json TEXT NOT NULL,
                risks_json TEXT NOT NULL,
                health_score INTEGER NOT NULL
            )
            """
        )


def save_report(filename: str, parameters: list, risks: list, health_score: int) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO reports (filename, uploaded_at, parameters_json, risks_json, health_score) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                filename,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(parameters),
                json.dumps(risks),
                int(health_score),
            ),
        )
        return int(cur.lastrowid)


def get_report(report_id: int):
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, filename, uploaded_at, parameters_json, risks_json, health_score "
            "FROM reports WHERE id = ?",
            (report_id,),
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_all_reports(limit: int = 100):
    limit = max(1, min(int(limit), 500))
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, filename, uploaded_at, parameters_json, risks_json, health_score "
            "FROM reports ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    # Return chronological order for trend rendering while still selecting
    # the newest ``limit`` rows from SQLite.
    return [_row_to_dict(row) for row in reversed(rows)]


def delete_report(report_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
        return cur.rowcount > 0


def clear_reports() -> int:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM reports")
        return cur.rowcount


def _row_to_dict(row):
    return {
        "id": row["id"],
        "filename": row["filename"],
        "uploaded_at": row["uploaded_at"],
        "parameters": json.loads(row["parameters_json"]),
        "risks": json.loads(row["risks_json"]),
        "health_score": row["health_score"],
    }
