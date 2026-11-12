import logging
import os
import shutil
import statistics
import threading
import uuid
from datetime import datetime

from nailit.prep.questions import run_session_module
from nailit.prep.answers import generate_answer_options
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pathlib import Path
from urllib.parse import urlsplit
from nailit import library
from nailit.interview import interviewer, voice
logger = logging.getLogger("nailit.api")
from nailit.store import (
    create_session,
    load_mock,
    log_voice,
    set_voice_latency,
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
from nailit import call, manuals, rehearse  # noqa: E402
app.include_router(rehearse.router)
app.include_router(call.router)
app.include_router(manuals.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


MAX_UPLOAD = 200 * 1024 * 1024  # one request; a long spoken answer is a few megabytes
MAX_VIDEO = 4 * 1024 ** 3  # one mock's webcam file: about two hours of browser webm
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _TEST_HOSTS():  # noqa: N802 - Starlette's TestClient sends `Host: testserver`; only accepted while pytest runs
    return {"testserver"} if os.getenv("PYTEST_CURRENT_TEST") else set()


def _hostname(value):
    """The host name of a Host header or an Origin, lower-cased, without port or IPv6 brackets; None if malformed."""
    value = (value or "").strip()
    if not value or any(c in value for c in "/\\@?# ") and "://" not in value:
        return None
    try:
        parts = urlsplit(value if "://" in value else "//" + value)
        parts.port  # noqa: B018 - raises on a non-numeric port
    except ValueError:
        return None
    if parts.username or parts.password or (parts.path not in ("", "/")) or parts.query or parts.fragment:
        return None
    return parts.hostname


class _TooLarge(HTTPException):
    def __init__(self):
        super().__init__(status_code=413, detail="That upload is too large.")


def _json_reply(status, error):
    return JSONResponse(status_code=status, content={"error": error, "status_code": status})


class LocalOnly:
    """The app has no login because it only serves this Mac. Refuse requests that reach it under another host name
    (DNS rebinding), writes sent by another website's page (cross-site form posts), and bodies over MAX_UPLOAD, whether
    or not they declare a Content-Length (chunked uploads are counted as they stream in)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers") or []}
        if _hostname(headers.get("host")) not in LOCAL_HOSTS | _TEST_HOSTS():
            return await _json_reply(403, "NailIt only answers on this computer.")(scope, receive, send)
        length = headers.get("content-length")
        if length is not None and (not length.isdigit() or int(length) > MAX_UPLOAD):
            return await _json_reply(413, "That upload is too large.")(scope, receive, send)
        origin = headers.get("origin")
        if scope["method"] not in ("GET", "HEAD", "OPTIONS") and origin is not None \
                and _hostname(origin) not in LOCAL_HOSTS:
            return await _json_reply(403, "Cross-site request refused.")(scope, receive, send)
        if headers.get("sec-fetch-site") == "cross-site" and scope["method"] not in ("GET", "HEAD", "OPTIONS"):
            return await _json_reply(403, "Cross-site request refused.")(scope, receive, send)
        received, started = 0, False

        async def counted_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > MAX_UPLOAD:
                    raise _TooLarge
            return message

        async def tracked_send(message):
            nonlocal started
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.app(scope, counted_receive, tracked_send)
        except _TooLarge:
            if started:  # the route already answered; nothing more can be sent on this connection
                logger.warning("upload to %s passed the size cap after the reply had started", scope.get("path"))
            else:
                await _json_reply(413, "That upload is too large.")(scope, receive, send)


app.add_middleware(LocalOnly)


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


@app.get("/", response_class=HTMLResponse)
def home():
    return (Path(__file__).resolve().parent / "static" / "home.html").read_text(encoding="utf8")


@app.get("/health")
def health():
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


def mock_pairs(state):
    """Each main question of a mock with everything the candidate said to it and its follow-ups."""
    pairs = []
    for turn in state["turns"]:
        if turn.get("role") == "interviewer":
            if turn.get("kind") == "question":
                pairs.append({"question_id": turn.get("question_id"), "question": turn.get("question_text") or turn["say"],
                              "followups": [], "answers": []})
            elif turn.get("kind") == "followup" and pairs:
                pairs[-1]["followups"].append(turn["say"])
            elif turn.get("kind") in ("candidate_questions", "closing", "answer", "end"):
                break
        elif turn.get("role") == "candidate" and pairs:
            pairs[-1]["answers"].append(turn.get("say") or "")
    return [p for p in pairs if " ".join(p["answers"]).strip()]


@app.get("/interview/debrief")
def interview_debrief(mock_id: str):
    """Score a finished mock against the rubric from the manuals, the same scorer rehearsal uses. The live 1-5 marks
    only steer follow-ups (they are keyword checks); this is the mark to trust."""
    import time as _time
    from concurrent.futures import ThreadPoolExecutor

    from nailit import scoring
    state = load_mock(mock_id)
    if not state:
        raise HTTPException(status_code=404, detail="Mock not found")
    if state.get("debrief"):
        return state["debrief"]
    types = {q["id"]: q.get("type") for q in library._questions(_library()["questions"])[0]}

    def one(pair):
        text = " ".join(pair["answers"])
        qtype = types.get(pair["question_id"]) or "behavioural"
        card = {"question": pair["question"], "type": "behavioural" if qtype in interviewer.STORY_TYPES else qtype,
                "competency": None, "answer": "", "moves": []}
        try:
            result = scoring.score(card, text, level=2)
        except Exception as error:  # noqa: BLE001
            return {"question": pair["question"], "error": str(error)[:200]}
        return {"question": pair["question"], "question_id": pair["question_id"], "followups": pair["followups"],
                "words": len(text.split()), **result}

    with ThreadPoolExecutor(4) as pool:
        answers = list(pool.map(one, mock_pairs(state)[:20]))
    scored = [a for a in answers if "score" in a]
    misses = {}
    for a in scored:
        for rule in a["rules"]:
            if rule["verdict"] == "fail":
                misses[rule["name"]] = misses.get(rule["name"], 0) + 1
    overall = round(sum(a["score"] for a in scored) / len(scored), 1) if scored else None
    debrief = {"overall": overall, "answers": answers, "count": len(scored),
               "verdict": None if overall is None else "Strong Hire" if overall >= 9 else "Hire" if overall >= 7
               else "Lean No Hire" if overall >= 5 else "No Hire",
               "repeat_misses": sorted(misses.items(), key=lambda kv: -kv[1])[:3]}
    if scored and state["phase"] == "done":
        with _mock_lock(mock_id):
            state = load_mock(mock_id)
            if state.get("debrief"):  # another request scored it while this one was waiting: keep one record, one log entry
                return state["debrief"]
            state["debrief"] = debrief
            save_mock(state)
        from nailit.rehearse import append_progress
        stamp = _time.strftime("%Y-%m-%d %H:%M:%S")
        append_progress([{"at": stamp, "card_id": "mock:" + (a["question_id"] or "other"), "score": a["score"],
                          "verdict": a["verdict"], "quality": a["quality"], "fidelity": None, "competency": None,
                          "source": "mock", "rules_failed": [r["id"] for r in a["rules"] if r["verdict"] == "fail"]}
                         for a in scored])
    return debrief


STATIC = Path(__file__).resolve().parent / "static"


class VoiceSayRequest(BaseModel):
    mock_id: str = Field(min_length=1, max_length=80)
    engine: str = Field(default="", max_length=10)


class VoiceLatencyRequest(BaseModel):
    mock_id: str = Field(min_length=1, max_length=80)
    turn: int = Field(ge=0)
    latency_s: float = Field(ge=0, le=600)


def _speak_last_turn(state, engine, timer=None):
    index = len(state["turns"]) - 1
    try:
        path, used = voice.speak(state["turns"][index]["say"], state["id"], f"interviewer_{index:03d}", engine or None)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if timer:
        timer.mark("tts_s")
    audio_url = f"/voice/audio/{state['id']}/{path.name}" if path else None
    return {"turn_index": index, "audio_url": audio_url, "tts_engine": used}


class MockEndRequest(BaseModel):
    mock_id: str = Field(min_length=1, max_length=80)


@app.post("/interview/end")
def interview_end(req: MockEndRequest):
    """End the mock now (the candidate pressed End); returns the summary so far."""
    with _mock_lock(req.mock_id):
        state = load_mock(req.mock_id)
        if not state:
            raise HTTPException(status_code=404, detail="Mock not found")
        result = interviewer.end_mock(state) if state["phase"] != "done" else interviewer.summary(state)
        save_mock(state)
    return {**result, "turns": state["turns"]}


@app.post("/voice/preview")
def voice_preview(mock_id: str = Form(...), audio: UploadFile = File(...), take: str = Form("")):
    """Live caption while you speak; also transcribes finished chunks early so the final answer is fast."""
    try:
        path = voice.save_upload(mock_id, "preview_live.webm", audio.file.read())
        return {"text": voice.live_update(mock_id, take or "default", path)}
    except voice.VoiceUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # noqa: BLE001 - a partial webm can be cut mid-frame; the next preview will catch up
        logger.info("preview transcription skipped: %s", error)
        return {"text": ""}


@app.get("/mock", response_class=HTMLResponse)
def mock_page():
    return (STATIC / "mock.html").read_text(encoding="utf8")


@app.post("/voice/say")
def voice_say(req: VoiceSayRequest):
    """Audio for the interviewer's latest line (the first question, or a reply to a typed answer)."""
    with _mock_lock(req.mock_id):
        state = load_mock(req.mock_id)
        if not state:
            raise HTTPException(status_code=404, detail="Mock not found")
        timer = voice.Timer()
        spoken = _speak_last_turn(state, req.engine, timer)
        log_voice(state["id"], spoken["turn_index"], tts_s=timer.marks["tts_s"], engine=spoken["tts_engine"])
    return {**spoken, "turn": state["turns"][-1], "done": state["phase"] == "done"}


@app.post("/voice/answer")
def voice_answer(mock_id: str = Form(...), audio: UploadFile = File(...), engine: str = Form(""),
                 gap_before_record_s: float = Form(0.0), take: str = Form("")):
    """One spoken answer: save, transcribe locally (fillers kept), run the interviewer, speak the reply."""
    if engine and engine not in voice.TTS_ENGINES:
        raise HTTPException(status_code=400, detail=f"unknown TTS engine {engine}")
    with _mock_lock(mock_id):
        state = load_mock(mock_id)
        if not state:
            raise HTTPException(status_code=404, detail="Mock not found")
        timer = voice.Timer()
        suffix = Path(audio.filename or "").suffix.lstrip(".").lower()
        name = f"answer_{len(state['turns']):03d}.{suffix if suffix in ('webm', 'wav', 'ogg', 'mp4', 'm4a') else 'webm'}"
        try:
            path = voice.save_upload(mock_id, name, audio.file.read())
            transcript = voice.transcribe(path, mock_id=mock_id, take=take or None)
        except voice.VoiceUnavailable as error:
            raise HTTPException(status_code=503, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        timer.mark("stt_s")
        if not transcript["text"]:
            raise HTTPException(status_code=422, detail="No speech found in the recording")
        silence = None if transcript["first_word_s"] is None else round(gap_before_record_s + transcript["first_word_s"], 2)
        try:
            turn = interviewer.answer(state, transcript["text"], transcript["speech_s"], silence, lib=_library())
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        candidate_turn = next(t for t in reversed(state["turns"]) if t.get("role") == "candidate")
        candidate_turn.update(audio=name, words=transcript["words"], filled_pauses=transcript["filled_pauses"])
        timer.mark("llm_s")
        save_mock(state)
    spoken = _speak_last_turn(state, engine, timer)
    log_voice(mock_id, spoken["turn_index"], stt_s=timer.marks["stt_s"], llm_s=timer.marks["llm_s"],
              tts_s=timer.marks["tts_s"], engine=spoken["tts_engine"])
    return {**spoken, "turn": turn, "done": state["phase"] == "done", "transcript": transcript,
            "timings": timer.marks}


@app.post("/voice/latency")
def voice_latency(req: VoiceLatencyRequest):
    set_voice_latency(req.mock_id, req.turn, req.latency_s)
    return {"ok": True}


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
    video.file.seek(0, 2)
    size = video.file.tell()
    video.file.seek(0)
    with _mock_lock(mock_id), path.open("ab") as out:
        if out.tell() + size > MAX_VIDEO:  # whole chunks only: a cut-off webm chunk would corrupt the recording
            raise HTTPException(status_code=413, detail="This mock's webcam recording is at its size limit.")
        shutil.copyfileobj(video.file, out)
    return {"saved": str(path)}


@app.get("/voice/audio/{mock_id}/{name}")
def voice_audio(mock_id: str, name: str):
    if not (voice.SAFE_NAME.match(mock_id) and voice.SAFE_NAME.match(name)) or ".." in name:
        raise HTTPException(status_code=400, detail="bad path")
    path = voice.recordings_dir(mock_id) / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path)
