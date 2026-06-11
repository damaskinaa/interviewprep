import json
import logging
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")


def get_db():
    """Returns a connection.
    Uses Postgres (psycopg2) if DATABASE_URL starts with 'postgresql',
    otherwise falls back to SQLite via _connect() — the default for local dev.
    """
    if DATABASE_URL.startswith("postgresql"):
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    return _connect()

_SESSION_LIMITS = {
    "company_name":          200,
    "role_name":             200,
    "raw_jd":               8000,
    "raw_cv":               8000,
    "raw_answer_bank":      4000,
    "raw_company_context":  2000,
    "raw_youtube_transcripts": 4000,
}

def _truncate_session_fields(**fields):
    """Truncate session fields to their storage limits. Logs a warning per truncated field."""
    result = {}
    for key, value in fields.items():
        limit = _SESSION_LIMITS.get(key)
        if limit and isinstance(value, str) and len(value) > limit:
            logger.warning(
                "create_session: field '%s' truncated from %d to %d characters",
                key, len(value), limit,
            )
            result[key] = value[:limit]
        else:
            result[key] = value
    return result


DB_PATH = Path("nailit_jobs.db")


def _now():
    return datetime.now().isoformat()


def _connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            stage TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0,
            input_payload TEXT NOT NULL DEFAULT '{}',
            markdown_output TEXT NOT NULL DEFAULT '',
            product_json TEXT NOT NULL DEFAULT '{}',
            source_manifest TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT '',
            output_file TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            role_name TEXT NOT NULL,
            raw_jd TEXT NOT NULL DEFAULT '',
            raw_cv TEXT NOT NULL DEFAULT '',
            raw_answer_bank TEXT NOT NULL DEFAULT '',
            raw_company_context TEXT NOT NULL DEFAULT '',
            raw_youtube_transcripts TEXT NOT NULL DEFAULT '',
            user_email TEXT DEFAULT NULL,
            followup_sent DATETIME DEFAULT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    # Migrate existing DBs — add columns if they were created before this schema version
    for col, definition in [
        ("user_email",    "TEXT DEFAULT NULL"),
        ("followup_sent", "DATETIME DEFAULT NULL"),
    ]:
        try:
            con.execute(f"ALTER TABLE sessions ADD COLUMN {col} {definition}")
        except Exception:
            pass  # column already exists — safe to ignore
    con.execute("""
        CREATE TABLE IF NOT EXISTS credits (
            user_id TEXT PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS credit_transactions (
            tx_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            created_at TEXT
        )
    """)
    con.commit()
    return con


def create_job(job_id, input_payload):
    now = _now()
    with _connect() as con:
        con.execute(
            """
            INSERT INTO jobs (
                job_id, status, stage, progress, input_payload,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                "queued",
                "Job created",
                0,
                json.dumps(input_payload, ensure_ascii=False),
                now,
                now,
            ),
        )
        con.commit()
    return get_job(job_id)


def update_job(job_id, **fields):
    if not fields:
        return get_job(job_id)

    allowed = {
        "status",
        "stage",
        "progress",
        "markdown_output",
        "product_json",
        "source_manifest",
        "error",
        "output_file",
    }
    updates = []
    values = []

    for key, value in fields.items():
        if key not in allowed:
            continue
        updates.append(f"{key} = ?")
        if key == "product_json" and not isinstance(value, str):
            value = json.dumps(value or {}, ensure_ascii=False)
        values.append(value if value is not None else "")

    updates.append("updated_at = ?")
    values.append(_now())
    values.append(job_id)

    with _connect() as con:
        con.execute(
            f"UPDATE jobs SET {', '.join(updates)} WHERE job_id = ?",
            values,
        )
        con.commit()
    return get_job(job_id)


def get_job(job_id):
    with _connect() as con:
        row = con.execute(
            "SELECT * FROM jobs WHERE job_id = ?",
            (job_id,),
        ).fetchone()

    if not row:
        return None

    product_json = row["product_json"] or "{}"
    input_payload = row["input_payload"] or "{}"

    try:
        parsed_product_json = json.loads(product_json)
    except Exception:
        parsed_product_json = {}

    try:
        parsed_input_payload = json.loads(input_payload)
    except Exception:
        parsed_input_payload = {}

    return {
        "job_id": row["job_id"],
        "status": row["status"],
        "stage": row["stage"],
        "progress": row["progress"],
        "input_payload": parsed_input_payload,
        "markdown": row["markdown_output"],
        "product_json": parsed_product_json,
        "source_manifest": row["source_manifest"],
        "error": row["error"],
        "output_file": row["output_file"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def find_running_module_job(session_id, module_name):
    """Return job_id of an existing running job for this session+module, or None."""
    with _connect() as con:
        row = con.execute(
            """
            SELECT job_id FROM jobs
            WHERE status = 'running'
              AND json_extract(input_payload, '$.session_id') = ?
              AND json_extract(input_payload, '$.module_name') = ?
            LIMIT 1
            """,
            (session_id, module_name),
        ).fetchone()
    return row["job_id"] if row else None


def create_session(session_id, payload):
    now = _now()
    safe = _truncate_session_fields(
        company_name=payload.get("company_name", ""),
        role_name=payload.get("role_name", ""),
        raw_jd=payload.get("job_description", ""),
        raw_cv=payload.get("cv", ""),
        raw_answer_bank=payload.get("answer_bank", ""),
        raw_company_context=payload.get("company_description", ""),
        raw_youtube_transcripts=payload.get("youtube_transcripts", ""),
    )
    with _connect() as con:
        con.execute(
            """
            INSERT INTO sessions (
                session_id, company_name, role_name, raw_jd, raw_cv,
                raw_answer_bank, raw_company_context, raw_youtube_transcripts,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                safe["company_name"],
                safe["role_name"],
                safe["raw_jd"],
                safe["raw_cv"],
                safe["raw_answer_bank"],
                safe["raw_company_context"],
                safe["raw_youtube_transcripts"],
                now,
                now,
            ),
        )
        con.commit()
    return get_session(session_id, include_raw=True)


def get_session(session_id, include_raw=False):
    with _connect() as con:
        row = con.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()

    if not row:
        return None

    session = {
        "session_id": row["session_id"],
        "company_name": row["company_name"],
        "role_name": row["role_name"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "has_job_description": bool(row["raw_jd"]),
        "has_cv": bool(row["raw_cv"]),
        "has_answer_bank": bool(row["raw_answer_bank"]),
        "has_company_context": bool(row["raw_company_context"]),
        "has_youtube_transcripts": bool(row["raw_youtube_transcripts"]),
    }
    if include_raw:
        session.update({
            "raw_jd": row["raw_jd"],
            "raw_cv": row["raw_cv"],
            "raw_answer_bank": row["raw_answer_bank"],
            "raw_company_context": row["raw_company_context"],
            "raw_youtube_transcripts": row["raw_youtube_transcripts"],
        })
    return session


def delete_old_jobs(days=7):
    """Delete jobs and their workspace directories older than `days` days."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with _connect() as con:
        rows = con.execute(
            "SELECT json_extract(input_payload, '$.session_id') AS session_id "
            "FROM jobs WHERE created_at < ?",
            (cutoff,),
        ).fetchall()
        for row in rows:
            sid = row[0]
            if sid:
                workspace = Path("jobs") / sid
                if workspace.exists():
                    try:
                        shutil.rmtree(workspace)
                        logger.info("delete_old_jobs: removed workspace %s", workspace)
                    except Exception as exc:
                        logger.warning("delete_old_jobs: could not remove %s — %s", workspace, exc)
        deleted = con.execute(
            "DELETE FROM jobs WHERE created_at < ?", (cutoff,)
        ).rowcount
        con.commit()
    logger.info("delete_old_jobs: deleted %d job(s) older than %d days", deleted, days)


def get_sessions_for_followup(days_ago=30):
    """Returns sessions created exactly `days_ago` days ago
    that have not yet received a followup email."""
    target = (datetime.utcnow() - timedelta(days=days_ago)).date()
    with _connect() as con:
        rows = con.execute(
            """
            SELECT session_id, user_email, company_name
            FROM sessions
            WHERE DATE(created_at) = ?
              AND followup_sent IS NULL
              AND user_email IS NOT NULL
            """,
            (target.isoformat(),),
        ).fetchall()
    return [dict(row) for row in rows]


def mark_followup_sent(session_id):
    """Record that a followup email was sent for this session."""
    with _connect() as con:
        con.execute(
            "UPDATE sessions SET followup_sent = ? WHERE session_id = ?",
            (datetime.utcnow().isoformat(), session_id),
        )
        con.commit()


import uuid as _uuid


def get_credits(user_id: str) -> int:
    """Return current credit balance for user_id, or 0 if no record."""
    conn = get_db()
    row = conn.execute(
        "SELECT balance FROM credits WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return row[0] if row else 0


def add_credits(user_id: str, amount: int, description: str = "") -> None:
    """Add credits to a user's balance and record the transaction."""
    conn = get_db()
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO credits (user_id, balance, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            balance = balance + excluded.balance,
            updated_at = excluded.updated_at
        """,
        (user_id, amount, now),
    )
    conn.execute(
        """
        INSERT INTO credit_transactions
            (tx_id, user_id, amount, type, description, created_at)
        VALUES (?, ?, ?, 'purchase', ?, ?)
        """,
        (str(_uuid.uuid4()), user_id, amount, description, now),
    )
    conn.commit()


def deduct_credits(user_id: str, amount: int, description: str = "") -> None:
    """Deduct credits from a user's balance. Raises ValueError if insufficient."""
    conn = get_db()
    balance = get_credits(user_id)
    if balance < amount:
        raise ValueError(
            f"Insufficient credits: {balance} available, {amount} required"
        )
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE credits SET balance = balance - ?, updated_at = ? WHERE user_id = ?",
        (amount, now, user_id),
    )
    conn.execute(
        """
        INSERT INTO credit_transactions
            (tx_id, user_id, amount, type, description, created_at)
        VALUES (?, ?, ?, 'deduction', ?, ?)
        """,
        (str(_uuid.uuid4()), user_id, amount, description, now),
    )
    conn.commit()
