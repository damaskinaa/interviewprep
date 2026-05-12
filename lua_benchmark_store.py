import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("lua_benchmark_sessions.db")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS benchmark_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    return conn


def save_benchmark_event(session_id, event_type, payload):
    conn = connect()
    conn.execute(
        "INSERT INTO benchmark_events (session_id, event_type, payload, created_at) VALUES (?, ?, ?, ?)",
        (
            session_id or "default",
            event_type,
            json.dumps(payload, ensure_ascii=False),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def load_benchmark_session(session_id, limit=200):
    conn = connect()
    rows = conn.execute(
        """
        SELECT event_type, payload, created_at
        FROM benchmark_events
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id or "default", limit),
    ).fetchall()
    conn.close()

    rows.reverse()
    return [
        {
            "event_type": event_type,
            "payload": json.loads(payload),
            "created_at": created_at,
        }
        for event_type, payload, created_at in rows
    ]
