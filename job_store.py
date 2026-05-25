import json
import sqlite3
from datetime import datetime
from pathlib import Path


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
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
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


def create_session(session_id, payload):
    now = _now()
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
                payload.get("company_name", ""),
                payload.get("role_name", ""),
                payload.get("job_description", ""),
                payload.get("cv", ""),
                payload.get("answer_bank", ""),
                payload.get("company_description", ""),
                payload.get("youtube_transcripts", ""),
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
