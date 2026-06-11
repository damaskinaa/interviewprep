import json
import sqlite3
import threading
import uuid
from datetime import datetime
import os
from pathlib import Path
from lua_session_store import save_turn, load_session, transcript_text

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from answer_generator import generate_answer_options
from agent_v2 import run_pipeline, run_session_module
from job_store import create_job, create_session, delete_old_jobs, find_running_module_job, get_job, get_session, get_sessions_for_followup, mark_followup_sent, update_job
from lua_coach import build_lua_coach_response, adapt_lua_response
from lua_benchmark_coach import build_benchmark_question, build_selected_answer_training_card, build_benchmark_practice_feedback
from lua_benchmark_store import save_benchmark_event, load_benchmark_session
from lua_mastery_store import update_mastery, get_mastery, question_key
from lua_drill_engine import build_retry_drill
from lua_escalation_engine import build_escalation_challenge
from lua_state_engine import build_interview_state
from lua_pressure_engine import build_pressure_response
from lua_pressure_repair_engine import build_pressure_repair_feedback
from lua_memory_engine import add_coach_memory, get_coach_memory, get_relevant_coach_memory


APP_API_KEY = os.getenv("APP_API_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")

allowed_origins = []
if FRONTEND_ORIGIN:
    allowed_origins.append(FRONTEND_ORIGIN)

allowed_origins.append("http://localhost:3000")

app = FastAPI()

from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )

@app.on_event("startup")
async def startup_cleanup():
    delete_old_jobs(days=7)


import logging as _api_logging
_followup_logger = _api_logging.getLogger("nailit.followup")

def send_email(to_address: str, subject: str, body: str) -> None:
    """Stub — replace with real email provider (Resend, SendGrid, SES, etc.)."""
    _followup_logger.info(
        "FOLLOWUP EMAIL (stub) → %s | subject: %s", to_address, subject
    )
    print(f"[send_email stub] to={to_address!r} subject={subject!r}")


@app.post("/internal/send-followups")
async def send_followups():
    """Called by a daily cron job.
    Sends 30-day offer-rate email to eligible sessions."""
    sessions = get_sessions_for_followup(days_ago=30)
    sent = 0
    for session in sessions:
        subject = "Did you get the job?"
        body = f"""Hi,

30 days ago you prepared for your {session['company_name']} interview with NAILIT.

One quick question: did you get the offer?

Yes → [link]
No → [link]
Still in process → [link]

Your answer helps us improve NAILIT for every candidate after you.

— NAILIT"""
        send_email(session["user_email"], subject, body)
        mark_followup_sent(session["session_id"])
        sent += 1
    return {"sent": sent}


DB_PATH = Path("lua_sessions.db")

def init_lua_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS lua_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        con.commit()

def save_lua_turn(session_id, role, text):
    init_lua_db()
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO lua_turns (session_id, role, text, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, text, datetime.now().isoformat()),
        )
        con.commit()

def load_lua_session(session_id):
    init_lua_db()
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT role, text, created_at FROM lua_turns WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    return [{"role": r, "text": t, "created_at": c} for r, t, c in rows]


app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-App-Key"],
)


class PrepRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    role_name: str = Field(min_length=1, max_length=120)
    job_description: str = Field(min_length=1, max_length=120000)
    cv: str = Field(min_length=1, max_length=120000)
    extra: str = Field(default="", max_length=900000)


class SessionCreateRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    role_name: str = Field(min_length=1, max_length=120)
    job_description: str = Field(min_length=1, max_length=120000)
    cv: str = Field(min_length=1, max_length=120000)
    answer_bank: str = Field(default="", max_length=240000)
    company_description: str = Field(default="", max_length=120000)
    youtube_transcripts: str = Field(default="", max_length=900000)


class ModuleRunRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=160)
    module_name: str = Field(min_length=1, max_length=80)


class AnswerGenerateRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=160)
    question: str = Field(min_length=1, max_length=4000)
    round_name: str = Field(default="", max_length=240)
    assigned_story_id: str = Field(default="", max_length=240)
    assigned_story_title: str = Field(default="", max_length=500)
    company_name: str = Field(default="", max_length=120)
    role_name: str = Field(default="", max_length=120)


def require_app_key(x_app_key: str = Header(default="")):
    if not APP_API_KEY:
        raise HTTPException(status_code=500, detail="Server key is not configured")
    if x_app_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def home():
    return {"status": "running", "message": "Interview Intel API is live"}


def _product_json_path(output_path):
    legacy_path = Path(str(output_path).replace("interview_prep_", "product_brief_"))
    workspace_path = output_path.parent / "product_brief.json"

    if legacy_path != output_path and legacy_path.exists():
        return legacy_path
    if workspace_path.exists():
        return workspace_path
    return None


@app.post("/prepare", dependencies=[Depends(require_app_key)])
def prepare(req: PrepRequest):
    output_file = run_pipeline(
        job_description=req.job_description,
        cv=req.cv,
        extra=req.extra,
        company_name=req.company_name,
        role_name=req.role_name,
    )

    output_path = Path(output_file)
    markdown_file = output_path.with_suffix(".md")
    product_json_file = _product_json_path(output_path)
    lua_brief_file = output_path.parent / "lua_brief.json"

    markdown = markdown_file.read_text() if markdown_file.exists() else ""
    product_json = None
    lua_mock_interview_brief = None

    if product_json_file:
        product_json = json.loads(product_json_file.read_text())

    if lua_brief_file.exists():
        lua_mock_interview_brief = json.loads(lua_brief_file.read_text())

    return {
        "status": "done",
        "output_file": output_file,
        "markdown": markdown,
        "product_json": product_json,
        "lua_brief_file": str(lua_brief_file) if lua_brief_file.exists() else None,
        "lua_mock_interview_brief": lua_mock_interview_brief,
    }


def _payload_from_request(req: PrepRequest):
    if hasattr(req, "model_dump"):
        return req.model_dump()
    return req.dict()


def _read_pipeline_files(output_file):
    output_path = Path(output_file)
    markdown_file = output_path.with_suffix(".md")
    product_json_file = _product_json_path(output_path)
    source_manifest_file = output_path.parent / "source_manifest.txt"

    markdown = markdown_file.read_text() if markdown_file.exists() else ""
    product_json = None
    source_manifest = source_manifest_file.read_text() if source_manifest_file.exists() else ""

    if product_json_file:
        product_json = json.loads(product_json_file.read_text())

    return markdown, product_json, source_manifest


def _run_prepare_job(job_id, payload):
    try:
        update_job(job_id, status="running", stage="Job created", progress=1)

        def progress_callback(stage, progress):
            update_job(
                job_id,
                status="running",
                stage=stage,
                progress=progress,
            )

        output_file = run_pipeline(
            job_description=payload.get("job_description", ""),
            cv=payload.get("cv", ""),
            extra=payload.get("extra", ""),
            company_name=payload.get("company_name", ""),
            role_name=payload.get("role_name", ""),
            progress_callback=progress_callback,
            job_id=job_id,
        )

        markdown, product_json, source_manifest = _read_pipeline_files(output_file)
        update_job(
            job_id,
            status="done",
            stage="Final prep pack complete",
            progress=100,
            markdown_output=markdown,
            product_json=product_json or {},
            source_manifest=source_manifest,
            output_file=output_file,
            error="",
        )
    except Exception as error:
        update_job(
            job_id,
            status="failed",
            stage="Failed",
            error=str(error),
        )


@app.post("/session/create", dependencies=[Depends(require_app_key)])
def session_create(req: SessionCreateRequest):
    # Payload size guard — reject before touching the DB
    _PAYLOAD_LIMIT = 25_000
    field_lengths = {
        "company_name":       len(req.company_name),
        "role_name":          len(req.role_name),
        "job_description":    len(req.job_description),
        "cv":                 len(req.cv),
        "answer_bank":        len(req.answer_bank),
        "company_description": len(req.company_description),
        "youtube_transcripts": len(req.youtube_transcripts),
    }
    total = sum(field_lengths.values())
    if total > _PAYLOAD_LIMIT:
        oversized = sorted(
            ((k, v) for k, v in field_lengths.items() if v > 500),
            key=lambda x: x[1],
            reverse=True,
        )
        detail_lines = ", ".join(f"{k} ({v} chars)" for k, v in oversized[:4])
        raise HTTPException(
            status_code=400,
            detail=(
                f"Payload too large: {total} characters total (limit {_PAYLOAD_LIMIT}). "
                f"Shorten these fields: {detail_lines}. "
                "Recommended limits: job_description 8000, cv 8000, answer_bank 4000, "
                "company_description 2000, youtube_transcripts 4000."
            ),
        )
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    session_id = "sess_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    session = create_session(session_id, payload)
    return {
        "session_id": session["session_id"],
        "company_name": session["company_name"],
        "role_name": session["role_name"],
        "created_at": session["created_at"],
    }


@app.get("/session/get", dependencies=[Depends(require_app_key)])
def session_get(session_id: str):
    session = get_session(session_id, include_raw=False)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def _run_module_job(job_id, session_id, module_name):
    try:
        update_job(job_id, status="running", stage="Module queued", progress=1)
        session = get_session(session_id, include_raw=True)
        if not session:
            raise ValueError("Session not found")

        def progress_callback(stage, progress):
            update_job(
                job_id,
                status="running",
                stage=stage,
                progress=progress,
            )

        result = run_session_module(
            session=session,
            module_name=module_name,
            progress_callback=progress_callback,
        )
        markdown = result.get("markdown", "") if isinstance(result, dict) else ""
        product_json = result.get("product_json", {}) if isinstance(result, dict) else {}
        update_job(
            job_id,
            status="done",
            stage=result.get("stage", "Module complete") if isinstance(result, dict) else "Module complete",
            progress=100,
            markdown_output=markdown,
            product_json=product_json,
            output_file=result.get("output_file", "") if isinstance(result, dict) else "",
            error="",
        )
    except Exception as error:
        update_job(
            job_id,
            status="failed",
            stage="Failed",
            progress=100,
            error=str(error),
        )


@app.post("/module/run", dependencies=[Depends(require_app_key)])
def module_run(req: ModuleRunRequest):
    session = get_session(req.session_id, include_raw=False)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    # Idempotency guard: return existing running job instead of spawning a duplicate
    existing_job_id = find_running_module_job(req.session_id, req.module_name)
    if existing_job_id:
        existing = get_job(existing_job_id)
        return {
            "job_id": existing_job_id,
            "session_id": req.session_id,
            "module_name": req.module_name,
            "status": existing["status"],
            "stage": existing["stage"],
            "progress": existing["progress"],
        }
    job_id = "mod_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    payload = {"session_id": req.session_id, "module_name": req.module_name}
    job = create_job(job_id, payload)
    thread = threading.Thread(
        target=_run_module_job,
        args=(job_id, req.session_id, req.module_name),
        daemon=True,
    )
    thread.start()
    return {
        "job_id": job_id,
        "session_id": req.session_id,
        "module_name": req.module_name,
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
    }


@app.get("/module/status", dependencies=[Depends(require_app_key)])
def module_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/prepare/start", dependencies=[Depends(require_app_key)])
def prepare_start(req: PrepRequest):
    payload = _payload_from_request(req)
    job_id = "prep_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    job = create_job(job_id, payload)

    thread = threading.Thread(
        target=_run_prepare_job,
        args=(job_id, payload),
        daemon=True,
    )
    thread.start()

    return {
        "job_id": job_id,
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
    }


@app.get("/prepare/status/{job_id}", dependencies=[Depends(require_app_key)])
def prepare_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/answers/generate", dependencies=[Depends(require_app_key)])
def answers_generate(req: AnswerGenerateRequest):
    payload = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    session = get_session(req.session_id, include_raw=True)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        return generate_answer_options(session, payload)
    except FileNotFoundError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.post("/lua-coach")
async def lua_coach(payload: dict):
    response = build_lua_coach_response(
        company=payload.get("company", ""),
        role=payload.get("role", ""),
        question=payload.get("question", ""),
        candidate_answer=payload.get("candidate_answer", ""),
        lua_brief=payload.get("lua_brief", {}),
    )
    return adapt_lua_response(response)




@app.post("/lua-session/save")
async def lua_session_save(payload: dict):
    session_id = payload.get("session_id") or "default"
    role = payload.get("role") or "user"
    text_value = payload.get("text") or ""
    if text_value.strip():
        save_lua_turn(session_id, role, text_value)
    return {
        "status": "saved",
        "session_id": session_id,
        "conversation": load_lua_session(session_id),
    }


@app.get("/lua-session/{session_id}")
async def lua_session_get(session_id: str):
    return {
        "status": "found",
        "session_id": session_id,
        "conversation": load_lua_session(session_id),
    }


@app.post("/lua-coach-resume")
async def lua_coach_resume(payload: dict):
    session_id = payload.get("session_id") or "default"
    question = payload.get("question") or ""
    answer = payload.get("candidate_answer") or ""
    is_final = bool(payload.get("is_final", False))

    if answer.strip():
        save_lua_turn(session_id, "user", answer)

    if not is_final:
        return {
            "status": "listening",
            "should_respond": False,
            "message": "Saved. Waiting for final answer signal.",
            "session_id": session_id,
            "conversation": load_lua_session(session_id),
        }

    response = build_lua_coach_response(
        company=payload.get("company", ""),
        role=payload.get("role", ""),
        question=question,
        candidate_answer=answer,
        lua_brief=payload.get("lua_brief", {}),
    )

    save_lua_turn(session_id, "coach", json.dumps(response, ensure_ascii=False))
    adapted = adapt_lua_response(response)
    adapted["session_id"] = session_id
    adapted["conversation"] = load_lua_session(session_id)
    return adapted



@app.post("/lua-call-turn")
async def lua_call_turn(payload: dict):
    session_id = payload.get("session_id") or "default"
    role = payload.get("role") or "user"
    text_value = payload.get("text") or ""
    is_final = bool(payload.get("is_final", False))

    if text_value.strip():
        save_turn(
            session_id=session_id,
            role=role,
            text=text_value,
            meta={
                "is_final": is_final,
                "company": payload.get("company", ""),
                "role_name": payload.get("role_name", ""),
                "question": payload.get("question", ""),
            },
        )

    if not is_final:
        return {
            "status": "saved_listening",
            "should_respond": False,
            "session_id": session_id,
            "message": "Saved. Still listening.",
            "conversation": load_session(session_id),
        }

    history = transcript_text(session_id)
    answer_with_context = f"""
Conversation so far:
{history}

Latest final answer:
{text_value}
"""

    coach = build_lua_coach_response(
        company=payload.get("company", ""),
        role=payload.get("role_name", payload.get("role", "")),
        question=payload.get("question", ""),
        candidate_answer=answer_with_context,
        lua_brief=payload.get("lua_brief", {}),
    )

    save_turn(
        session_id=session_id,
        role="coach",
        text=json.dumps(coach, ensure_ascii=False),
        meta={"type": "coach_feedback"},
    )

    adapted_coach = adapt_lua_response(coach)
    adapted_coach["session_id"] = session_id
    adapted_coach["conversation"] = load_session(session_id)
    return adapted_coach


@app.get("/lua-call-session/{session_id}")
async def lua_call_session(session_id: str):
    return {
        "status": "found",
        "session_id": session_id,
        "conversation": load_session(session_id),
        "transcript": transcript_text(session_id),
    }


@app.post("/lua-benchmark-question")
async def lua_benchmark_question(payload: dict):
    result = build_benchmark_question(
        session_id=payload.get("session_id", "default"),
        company=payload.get("company", ""),
        role=payload.get("role", payload.get("role_name", "")),
        question_number=int(payload.get("question_number", 1)),
        nailit_pack=payload.get("nailit_pack", ""),
        uploaded_memory=payload.get("uploaded_memory", ""),
        focus_area=payload.get("focus_area", ""),
    )
    save_benchmark_event(payload.get("session_id", "default"), "benchmark_question", result)
    return result


@app.post("/lua-select-benchmark-answer")
async def lua_select_benchmark_answer(payload: dict):
    result = build_selected_answer_training_card(
        session_id=payload.get("session_id", "default"),
        selected_answer=payload.get("selected_answer", {}),
        user_choice=payload.get("user_choice", ""),
    )
    save_benchmark_event(payload.get("session_id", "default"), "selected_answer", {
        "user_choice": payload.get("user_choice", ""),
        "selected_answer": payload.get("selected_answer", {}),
        "training_card": result,
    })
    return result


@app.post("/lua-practice-benchmark-turn")
async def lua_practice_benchmark_turn(payload: dict):
    session_id = payload.get("session_id", "default")
    selected_answer = payload.get("selected_answer", {})
    spoken_attempt = payload.get("spoken_attempt", payload.get("text", ""))

    result = build_benchmark_practice_feedback(
        session_id=session_id,
        selected_answer=selected_answer,
        spoken_attempt=spoken_attempt,
        chunk_name=payload.get("chunk_name", "full_answer"),
        is_final=bool(payload.get("is_final", True)),
    )

    if result.get("status") != "saved_listening":
        q_key = payload.get("question_key") or question_key(
            company=payload.get("company", ""),
            role=payload.get("role", ""),
            question=selected_answer.get("question", payload.get("question", "")),
            focus_area=payload.get("focus_area", ""),
        )

        score = result.get("score_out_of_10", 0) or 0

        if score <= 4:
            result["pressure_followup"] = build_pressure_response(
                company=payload.get("company", ""),
                role=payload.get("role", ""),
                focus_area=payload.get("focus_area", ""),
                spoken_attempt=spoken_attempt,
                score=score,
            )

        mastery_result = update_mastery(session_id, q_key, result)
        result["mastery"] = (
            mastery_result.get("mastery", [None])[0]
            if mastery_result.get("mastery")
            else None
        )

        save_benchmark_event(
            session_id,
            "practice_turn",
            {
                "selected_answer": selected_answer,
                "spoken_attempt": spoken_attempt,
                "feedback": result,
                "mastery": result.get("mastery"),
            },
        )

    return result

@app.get("/lua-benchmark-session/{session_id}")
async def lua_benchmark_session(session_id: str):
    return {
        "status": "found",
        "session_id": session_id,
        "events": load_benchmark_session(session_id),
    }


@app.post("/lua-memory-add")
async def lua_memory_add(payload: dict):
    return add_coach_memory(
        session_id=payload.get("session_id", "default"),
        title=payload.get("title", "Untitled memory"),
        content=payload.get("content", ""),
        scope=payload.get("scope", "session"),
        source_type=payload.get("source_type", "pasted_text"),
    )


@app.get("/lua-memory/{session_id}")
async def lua_memory(session_id: str):
    return get_coach_memory(session_id)


@app.post("/lua-memory-upload-text")
async def lua_memory_upload_text(payload: dict):
    filename = payload.get("filename", "uploaded_document.txt")
    content = payload.get("content", "")
    title = payload.get("title") or filename

    return add_coach_memory(
        session_id=payload.get("session_id", "default"),
        title=title,
        content=content,
        scope=payload.get("scope", "session"),
        source_type=payload.get("source_type", "uploaded_text_file"),
    )


@app.post("/lua-memory-relevant")
async def lua_memory_relevant(payload: dict):
    return get_relevant_coach_memory(
        session_id=payload.get("session_id", "default"),
        query=payload.get("query", ""),
        limit=int(payload.get("limit", 8)),
    )


@app.get("/lua-mastery/{session_id}")
async def lua_mastery(session_id: str):
    return get_mastery(session_id)


@app.post("/lua-retry-drill")
async def lua_retry_drill(payload: dict):
    return build_retry_drill(
        session_id=payload.get("session_id", "default"),
        question_key=payload.get("question_key"),
    )


@app.post("/lua-escalation-challenge")
async def lua_escalation_challenge(payload: dict):
    return build_escalation_challenge(
        company=payload.get("company", ""),
        role=payload.get("role", ""),
        focus_area=payload.get("focus_area", ""),
        previous_answer=payload.get("previous_answer", ""),
        score=float(payload.get("score", 0)),
    )


@app.get("/lua-health")
async def lua_health():
    return {
        "status": "ok",
        "service": "lua-interview-coach",
        "features": {
            "benchmark": True,
            "memory": True,
            "memory_relevance": True,
            "practice_feedback": True,
            "mastery": True,
            "retry_drill": True,
            "escalation": True
        }
    }


@app.get("/lua-state/{session_id}")
async def lua_state(session_id: str):
    session = load_benchmark_session(session_id)

    if isinstance(session, dict):
        events = session.get("events", [])
    else:
        events = session

    return build_interview_state(events)


@app.post("/lua-pressure-response")
async def lua_pressure_response(payload: dict):
    return build_pressure_response(
        company=payload.get("company", ""),
        role=payload.get("role", ""),
        focus_area=payload.get("focus_area", ""),
        spoken_attempt=payload.get("spoken_attempt", payload.get("text", "")),
        score=payload.get("score", 0),
    )


@app.post("/lua-pressure-repair")
async def lua_pressure_repair(payload: dict):
    result = build_pressure_repair_feedback(
        company=payload.get("company", ""),
        role=payload.get("role", ""),
        focus_area=payload.get("focus_area", ""),
        original_answer=payload.get("original_answer", ""),
        pressure_question=payload.get("pressure_question", ""),
        repair_answer=payload.get("repair_answer", ""),
    )

    save_benchmark_event(
        payload.get("session_id", "default"),
        "pressure_repair",
        {
            "original_answer": payload.get("original_answer", ""),
            "pressure_question": payload.get("pressure_question", ""),
            "repair_answer": payload.get("repair_answer", ""),
            "feedback": result,
        },
    )

    return result


@app.get("/lua-ui")
async def lua_ui():
    return FileResponse("lua_frontend.html")
