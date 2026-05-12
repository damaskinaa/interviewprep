import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("lua_sessions.db")


def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS lua_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                meta TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)
        con.commit()


def save_turn(session_id, role, text, meta=None):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO lua_turns (session_id, role, text, meta, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                session_id or "default",
                role or "user",
                text or "",
                json.dumps(meta or {}, ensure_ascii=False),
                datetime.now().isoformat(),
            ),
        )
        con.commit()


def load_session(session_id, limit=80):
    init_db()
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            """
            SELECT role, text, meta, created_at
            FROM lua_turns
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id or "default", limit),
        ).fetchall()

    rows.reverse()
    return [
        {
            "role": role,
            "text": text,
            "meta": json.loads(meta or "{}"),
            "created_at": created_at,
        }
        for role, text, meta, created_at in rows
    ]


def transcript_text(session_id, limit=80):
    turns = load_session(session_id, limit=limit)
    return "\n".join(f"{t['role'].upper()}: {t['text']}" for t in turns)
