import json
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("lua_memory.db")

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS coach_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        scope TEXT NOT NULL,
        source_type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        summary TEXT NOT NULL,
        tags TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    return conn

def save_memory(session_id, scope, source_type, title, content, summary, tags):
    conn = connect()
    conn.execute(
        """
        INSERT INTO coach_memory
        (session_id, scope, source_type, title, content, summary, tags, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id or "default",
            scope or "session",
            source_type or "pasted_text",
            title or "Untitled memory",
            content or "",
            summary or "",
            json.dumps(tags or [], ensure_ascii=False),
            datetime.utcnow().isoformat(),
        ),
    )
    conn.commit()
    conn.close()

def load_memory(session_id, limit=50):
    conn = connect()
    rows = conn.execute(
        """
        SELECT scope, source_type, title, content, summary, tags, created_at
        FROM coach_memory
        WHERE session_id = ? OR scope = 'global'
        ORDER BY id DESC
        LIMIT ?
        """,
        (session_id or "default", limit),
    ).fetchall()
    conn.close()
    return [
        {
            "scope": scope,
            "source_type": source_type,
            "title": title,
            "content": content,
            "summary": summary,
            "tags": json.loads(tags or "[]"),
            "created_at": created_at,
        }
        for scope, source_type, title, content, summary, tags, created_at in rows
    ]

def memory_text(session_id, limit=20):
    items = load_memory(session_id, limit=limit)
    blocks = []
    for item in items:
        blocks.append(
            f"TITLE: {item['title']}\n"
            f"SCOPE: {item['scope']}\n"
            f"TAGS: {', '.join(item['tags'])}\n"
            f"SUMMARY: {item['summary']}\n"
            f"CONTENT: {item['content'][:3000]}"
        )
    return "\n\n".join(blocks)
