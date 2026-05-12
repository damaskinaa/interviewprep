import json
import sqlite3
from datetime import datetime
import os
from pathlib import Path
from lua_session_store import save_turn, load_session, transcript_text

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent_v2 import run_pipeline
from lua_coach import build_lua_coach_response
from lua_benchmark_coach import build_benchmark_question, build_selected_answer_training_card


APP_API_KEY = os.getenv("APP_API_KEY")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "")

allowed_origins = []
if FRONTEND_ORIGIN:
    allowed_origins.append(FRONTEND_ORIGIN)

allowed_origins.append("http://localhost:3000")

app = FastAPI()

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
    extra: str = Field(default="", max_length=120000)


def require_app_key(x_app_key: str = Header(default="")):
    if not APP_API_KEY:
        raise HTTPException(status_code=500, detail="Server key is not configured")
    if x_app_key != APP_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/")
def home():
    return {"status": "running", "message": "Interview Intel API is live"}


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
    product_json_file = Path(str(output_path).replace("interview_prep_", "product_brief_"))
    lua_brief_file = Path(str(output_path).replace("interview_prep_", "lua_brief_")).with_suffix(".json")

    markdown = markdown_file.read_text() if markdown_file.exists() else ""
    product_json = None
    lua_mock_interview_brief = None

    if product_json_file.exists():
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


@app.post("/lua-coach")
async def lua_coach(payload: dict):
    response = build_lua_coach_response(
        company=payload.get("company", ""),
        role=payload.get("role", ""),
        question=payload.get("question", ""),
        candidate_answer=payload.get("candidate_answer", ""),
        lua_brief=payload.get("lua_brief", {}),
    )
    return response




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
    response["session_id"] = session_id
    response["conversation"] = load_lua_session(session_id)
    return response



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

    coach["session_id"] = session_id
    coach["conversation"] = load_session(session_id)
    return coach


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
    return build_benchmark_question(
        session_id=payload.get("session_id", "default"),
        company=payload.get("company", ""),
        role=payload.get("role", payload.get("role_name", "")),
        question_number=int(payload.get("question_number", 1)),
        nailit_pack=payload.get("nailit_pack", ""),
        uploaded_memory=payload.get("uploaded_memory", ""),
        focus_area=payload.get("focus_area", ""),
    )


@app.post("/lua-select-benchmark-answer")
async def lua_select_benchmark_answer(payload: dict):
    return build_selected_answer_training_card(
        session_id=payload.get("session_id", "default"),
        selected_answer=payload.get("selected_answer", {}),
        user_choice=payload.get("user_choice", ""),
    )
