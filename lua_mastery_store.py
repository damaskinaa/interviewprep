import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("lua_mastery.db")


def _now():
    return datetime.now(timezone.utc).isoformat()


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mastery (
            session_id TEXT NOT NULL,
            question_key TEXT NOT NULL,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_score REAL,
            best_score REAL,
            move_on_allowed INTEGER NOT NULL DEFAULT 0,
            weak_points TEXT NOT NULL DEFAULT '[]',
            memory_used TEXT NOT NULL DEFAULT '[]',
            last_feedback TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (session_id, question_key)
        )
    """)
    conn.commit()
    return conn


def _safe_json(value, fallback):
    try:
        if value is None:
            return fallback
        if isinstance(value, str):
            return json.loads(value)
        return value
    except Exception:
        return fallback


def question_key(company="", role="", question="", focus_area=""):
    raw = f"{company}|{role}|{question}|{focus_area}".lower().strip()
    return " ".join(raw.split())[:500]


def update_mastery(session_id, question_key, feedback):
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM mastery WHERE session_id=? AND question_key=?",
        (session_id, question_key),
    ).fetchone()

    score = feedback.get("score_out_of_10")
    try:
        score = float(score)
    except Exception:
        score = None

    move_on_allowed = bool(feedback.get("move_on_allowed", False))
    weak_points = feedback.get("what_was_missing") or feedback.get("what_was_weak") or []
    memory_used = feedback.get("memory_used") or []

    if row:
        attempt_count = int(row["attempt_count"]) + 1
        previous_best = row["best_score"]
        try:
            previous_best = float(previous_best) if previous_best is not None else None
        except Exception:
            previous_best = None
        best_score = max([s for s in [previous_best, score] if s is not None], default=None)
    else:
        attempt_count = 1
        best_score = score

    conn.execute(
        """
        INSERT OR REPLACE INTO mastery (
            session_id, question_key, attempt_count, last_score, best_score,
            move_on_allowed, weak_points, memory_used, last_feedback, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            question_key,
            attempt_count,
            score,
            best_score,
            1 if move_on_allowed else 0,
            json.dumps(weak_points, ensure_ascii=False),
            json.dumps(memory_used, ensure_ascii=False),
            json.dumps(feedback, ensure_ascii=False),
            _now(),
        ),
    )
    conn.commit()
    return get_mastery(session_id, question_key)


def get_mastery(session_id, question_key=None):
    conn = _connect()

    if question_key:
        rows = conn.execute(
            "SELECT * FROM mastery WHERE session_id=? AND question_key=?",
            (session_id, question_key),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM mastery WHERE session_id=? ORDER BY updated_at DESC",
            (session_id,),
        ).fetchall()

    items = []
    for row in rows:
        items.append({
            "session_id": row["session_id"],
            "question_key": row["question_key"],
            "attempt_count": row["attempt_count"],
            "last_score": row["last_score"],
            "best_score": row["best_score"],
            "move_on_allowed": bool(row["move_on_allowed"]),
            "weak_points": _safe_json(row["weak_points"], []),
            "memory_used": _safe_json(row["memory_used"], []),
            "last_feedback": _safe_json(row["last_feedback"], {}),
            "updated_at": row["updated_at"],
        })

    return {
        "status": "found",
        "session_id": session_id,
        "count": len(items),
        "mastery": items,
    }
