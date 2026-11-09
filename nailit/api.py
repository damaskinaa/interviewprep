import os
import shutil
import statistics
import threading
import uuid
from datetime import datetime

from nailit.prep.questions import run_session_module
from nailit.prep.answers import generate_answer_options
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pathlib import Path
from nailit import library
from nailit.interview import interviewer, voice
from nailit.store import (
    create_session,
    load_mock,
    voice_latencies,
    mode_c_progress,
    save_mock,
    fail_stale_jobs,
    get_job,
    get_or_create_job,
    get_session,
    update_job,
)
from nailit.coach import (
    adapt_lua_response,
    build_lua_coach_response,
    build_session_lua_brief,
)
from pydantic import BaseModel, Field

app = FastAPI(title="NailIt")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail, "status_code": exc.status_code})


@app.on_event("startup")
async def startup_cleanup():
    # Jobs run as in-process threads, so any job still marked active is dead after a restart.
    fail_stale_jobs(minutes=0)


def dispatch_job(func, *args):
    threading.Thread(target=func, args=args, daemon=True).start()


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


REQUIRES_ARTIFACTS = {
    "candidate_profile": ["company_intelligence", "role_intelligence"],
    "gap_map": ["company_intelligence", "role_intelligence", "candidate_profile"],
    "interview_strategy": ["company_intelligence", "role_intelligence", "candidate_profile", "gap_map"],
    "prep_pack": ["company_intelligence", "role_intelligence", "candidate_profile", "gap_map", "interview_strategy"],
}


def _require_session(session_id, include_raw=False):
    session = get_session(session_id, include_raw=include_raw)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.get("/")
def home():
    return {"status": "running", "app": "nailit"}


@app.post("/session/create")
def session_create(req: SessionCreateRequest):
    payload = req.model_dump()
    session_id = "sess_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    session = create_session(session_id, payload)
    return {
        "session_id": session["session_id"],
        "company_name": session["company_name"],
        "role_name": session["role_name"],
        "created_at": session["created_at"],
    }


@app.get("/session/get")
def session_get(session_id: str):
    return _require_session(session_id)


def _run_module_job(job_id, session_id, module_name):
    try:
        update_job(job_id, status="running", stage="Module queued", progress=1)
        session = _require_session(session_id, include_raw=True)

        def progress_callback(stage, progress):
            update_job(job_id, status="running", stage=stage, progress=progress)

        result = run_session_module(session=session, module_name=module_name, progress_callback=progress_callback)
        update_job(
            job_id,
            status="done",
            stage=result.get("stage", "Module complete"),
            progress=100,
            markdown_output=result.get("markdown", ""),
            product_json=result.get("product_json", {}),
            output_file=result.get("output_file", ""),
            error="",
        )
    except Exception as error:
        update_job(job_id, status="failed", stage="Failed", progress=100, error=str(error))


@app.post("/module/run")
def module_run(req: ModuleRunRequest):
    _require_session(req.session_id)
    jobs_base = os.path.join("jobs", req.session_id)
    missing = [
        name for name in REQUIRES_ARTIFACTS.get(req.module_name, [])
        if not os.path.exists(os.path.join(jobs_base, name, f"{name}.json"))
    ]
    if missing:
        raise HTTPException(status_code=400, detail=f"Required modules not complete: {', '.join(missing)}. Run them first.")

    new_job_id = "mod_" + datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:8]
    job_id, created = get_or_create_job(req.session_id, req.module_name, new_job_id)
    if created:
        dispatch_job(_run_module_job, job_id, req.session_id, req.module_name)
    job = get_job(job_id)
    return {
        "job_id": job_id,
        "session_id": req.session_id,
        "module_name": req.module_name,
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
    }


@app.get("/module/status")
def module_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.pop("input_payload", None)
    return job


@app.post("/answers/generate")
def answers_generate(req: AnswerGenerateRequest):
    session = _require_session(req.session_id, include_raw=True)
    try:
        return generate_answer_options(session, req.model_dump())
    except Exception as error:
        status = 400 if isinstance(error, FileNotFoundError) else 500
        raise HTTPException(status_code=status, detail=str(error)) from error


@app.post("/lua-coach")
async def lua_coach(payload: dict):
    session_id = payload.get("session_id") or ""
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    _require_session(session_id)
    response = build_lua_coach_response(
        company=payload.get("company", ""),
        role=payload.get("role", ""),
        question=payload.get("question", ""),
        candidate_answer=payload.get("candidate_answer", ""),
        lua_brief=payload.get("lua_brief") or build_session_lua_brief(session_id),
    )
    return adapt_lua_response(response)


class MockStartRequest(BaseModel):
    round_id: str = Field(min_length=1, max_length=80)
    mode: str = Field(default="A", pattern="^[ABC]$")
    company_id: str | None = Field(default=None, max_length=80)
    temperament_id: str | None = Field(default=None, max_length=80)
    seed: int | None = None


class MockAnswerRequest(BaseModel):
    mock_id: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=20000)
    seconds: float | None = Field(default=None, ge=0)
    pre_answer_silence_s: float | None = Field(default=None, ge=0)


_mock_locks: dict = {}
_mock_locks_guard = threading.Lock()


def _mock_lock(mock_id):
    with _mock_locks_guard:
        return _mock_locks.setdefault(mock_id, threading.Lock())


def _library():
    try:
        return library.load_library()
    except library.LibraryError as error:
        raise HTTPException(status_code=500, detail="Library invalid: " + "; ".join(error.errors[:5])) from error


@app.get("/interview/options")
def interview_options():
    personas = _library()["personas"]
    progress = mode_c_progress()
    pick = lambda key, *fields: [{f: item.get(f) for f in ("id", *fields)} for item in personas[key]]  # noqa: E731
    return {
        "rounds": pick("rounds", "label", "minutes"),
        "companies": pick("companies", "name"),
        "temperaments": pick("temperaments", "label"),
        "modes": [{**mode, "locked": mode["id"] == "C" and not interviewer.mode_c_unlocked(progress)}
                  for mode in pick("modes", "label", "unlock")],
        "progress": progress,
    }


@app.post("/interview/start")
def interview_start(req: MockStartRequest):
    try:
        state, turn = interviewer.start_mock(req.round_id, req.mode, req.company_id, req.temperament_id, req.seed,
                                             progress=mode_c_progress(), lib=_library())
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    save_mock(state)
    return {"mock_id": state["id"], "turn": turn, "done": False}


@app.post("/interview/answer")
def interview_answer(req: MockAnswerRequest):
    with _mock_lock(req.mock_id):
        state = load_mock(req.mock_id)
        if not state:
            raise HTTPException(status_code=404, detail="Mock not found")
        try:
            turn = interviewer.answer(state, req.text, req.seconds, req.pre_answer_silence_s, lib=_library())
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        save_mock(state)
    return {"mock_id": state["id"], "turn": turn, "done": state["phase"] == "done"}


@app.get("/interview/get")
def interview_get(mock_id: str):
    state = load_mock(mock_id)
    if not state:
        raise HTTPException(status_code=404, detail="Mock not found")
    return {**interviewer.summary(state), "turns": state["turns"]}


STATIC = Path(__file__).resolve().parent / "static"


@app.get("/mock", response_class=HTMLResponse)
def mock_page():
    return (STATIC / "mock.html").read_text(encoding="utf8")


@app.websocket("/voice/ws/{mock_id}")
async def voice_ws(websocket: WebSocket, mock_id: str, input: str = "ptt"):
    """Pipecat voice session for one mock (see nailit/interview/pipeline.py)."""
    state = load_mock(mock_id)
    await websocket.accept()
    if not state:
        await websocket.close(code=4404, reason="Mock not found")
        return
    from nailit.interview import pipeline
    if mock_id in pipeline.ACTIVE:
        await websocket.close(code=4409, reason="This mock already has a voice session open")
        return
    await pipeline.run(websocket, state, _library(), input_mode=input if input in ("ptt", "vad", "text") else None)
    try:
        await websocket.close()
    except RuntimeError:
        pass  # already closed by the page


@app.get("/voice/latency")
def voice_latency_get(mock_id: str = ""):
    rows = voice_latencies(mock_id or None)
    measured = sorted(row["latency_s"] for row in rows if row["latency_s"] is not None)
    return {"rows": rows, "median_s": statistics.median(measured) if measured else None}


@app.post("/voice/video")
def voice_video(mock_id: str = Form(...), video: UploadFile = File(...)):
    if not load_mock(mock_id):
        raise HTTPException(status_code=404, detail="Mock not found")
    path = voice.recordings_dir(mock_id) / "webcam.webm"
    with path.open("ab") as out:
        shutil.copyfileobj(video.file, out)
    return {"saved": str(path)}
