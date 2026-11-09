import json
import logging
import sqlite3
from datetime import datetime, timedelta

from nailit.paths import data_path

logger = logging.getLogger(__name__)

LUA_DB_BASE_DIR_ENV = "LUA_DB_BASE_DIR"


_SESSION_LIMITS = {
    "company_name":          200,
    "role_name":             200,
    "raw_jd":               120000,
    "raw_cv":               120000,
    "raw_answer_bank":      240000,
    "raw_company_context":  120000,
    "raw_youtube_transcripts": 900000,
    "user_email":            320,
    "user_id":               160,
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


DB_PATH = data_path("nailit_jobs.db")


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
            user_id TEXT DEFAULT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS mocks (
            mock_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS drill_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drill_id TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT '',
            score REAL,
            created_at TEXT NOT NULL
        )
    """)
    # Migrate existing DBs — add columns if they were created before this schema version
    for col, definition in [
        ("user_email",    "TEXT DEFAULT NULL"),
        ("followup_sent", "DATETIME DEFAULT NULL"),
        ("user_id",       "TEXT DEFAULT NULL"),
    ]:
        try:
            con.execute(f"ALTER TABLE sessions ADD COLUMN {col} {definition}")
        except Exception:
            pass  # column already exists — safe to ignore
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


def get_or_create_job(session_id: str, module_name: str, job_id: str) -> tuple:
    """
    Atomically return an existing running/queued job for this session+module,
    or create a new one.

    Returns (actual_job_id, created: bool).
    Uses BEGIN IMMEDIATE to serialise concurrent callers so only one job
    is ever created for the same session+module at a time.
    """
    now = _now()
    payload = json.dumps({"session_id": session_id, "module_name": module_name},
                         ensure_ascii=False)
    con = _connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        row = con.execute(
            """
            SELECT job_id FROM jobs
            WHERE status IN ('running', 'queued')
              AND json_extract(input_payload, '$.session_id') = ?
              AND json_extract(input_payload, '$.module_name') = ?
            LIMIT 1
            """,
            (session_id, module_name),
        ).fetchone()
        if row:
            con.execute("COMMIT")
            return row["job_id"], False
        con.execute(
            """
            INSERT INTO jobs (
                job_id, status, stage, progress, input_payload,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, "queued", "Job created", 0, payload, now, now),
        )
        con.execute("COMMIT")
        return job_id, True
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        con.close()


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
        user_email=payload.get("user_email", ""),
        user_id=payload.get("user_id", ""),
    )
    with _connect() as con:
        con.execute(
            """
            INSERT INTO sessions (
                session_id, company_name, role_name, raw_jd, raw_cv,
                raw_answer_bank, raw_company_context, raw_youtube_transcripts,
                created_at, updated_at, user_email, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                safe["user_email"],
                safe["user_id"] or session_id,
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
        "user_id": row["user_id"],
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


def fail_stale_jobs(minutes: int = 30) -> int:
    """Mark queued/running jobs with no progress update for `minutes` as failed.

    Thread-dispatched jobs die with the process, so after a restart they would
    otherwise stay "running" forever and block reruns of the same module.
    """
    cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    with _connect() as con:
        cursor = con.execute(
            "UPDATE jobs SET status = 'failed', stage = 'Failed', "
            "error = 'Job was interrupted (no progress update). Please run it again.', updated_at = ? "
            "WHERE status IN ('queued', 'running') AND updated_at < ?",
            (_now(), cutoff),
        )
        con.commit()
        return cursor.rowcount or 0




def save_mock(state):
    now = _now()
    with _connect() as con:
        con.execute(
            "INSERT INTO mocks (mock_id, state, created_at, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(mock_id) DO UPDATE SET state = excluded.state, updated_at = excluded.updated_at",
            (state["id"], json.dumps(state), now, now),
        )


def load_mock(mock_id):
    with _connect() as con:
        row = con.execute("SELECT state FROM mocks WHERE mock_id = ?", (mock_id,)).fetchone()
    return json.loads(row["state"]) if row else None


def log_drill(drill_id, kind="", score=None, when=None):
    with _connect() as con:
        con.execute("INSERT INTO drill_log (drill_id, kind, score, created_at) VALUES (?, ?, ?, ?)",
                    (drill_id, kind, score, (when or datetime.now()).isoformat()))


def mode_c_progress():
    """Freeze drills done and the average drill score in days 8-14 after the first logged drill."""
    with _connect() as con:
        freeze = con.execute("SELECT COUNT(*) FROM drill_log WHERE kind = 'freeze'").fetchone()[0]
        first = con.execute("SELECT MIN(created_at) FROM drill_log").fetchone()[0]
        average = None
        if first:
            start = datetime.fromisoformat(first)
            average = con.execute(
                "SELECT AVG(score) FROM drill_log WHERE score IS NOT NULL AND created_at >= ? AND created_at < ?",
                ((start + timedelta(days=7)).isoformat(), (start + timedelta(days=14)).isoformat()),
            ).fetchone()[0]
    return {"freeze_drills": freeze, "week2_average": average}
