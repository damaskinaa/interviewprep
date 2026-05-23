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
