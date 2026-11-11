"""Rehearsal mode (Level 1): hear the question, hear the best answer, say it yourself, get a score, next.

Cards come from ~/NailIt/library/model_level/deck.json (built by nailit.answers.generate). Model answers are
practice-only: they're spoken by a different voice from the interviewer, and their numbers are never yours.
"""
import json
import os
import re
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from nailit import library
from nailit.interview import voice
from nailit.llm import parse_json_object

router = APIRouter()
STATIC = Path(__file__).resolve().parent / "static"
INTERVIEWER_VOICE, CANDIDATE_VOICE = "ash", "coral"
SPEAK_STYLE = {
    "question": "A friendly, professional interviewer asking a question in a video call. Natural pace.",
    "answer": "A confident, calm senior candidate answering in an interview. Warm, measured, clear; land the results "
              "with a falling tone and a short pause after numbers. Not salesy.",
}
# Chosen by nailit.answers.calibrate (Nov 2026): DeepSeek V4.1 Flash keeps strong, weak and off-topic attempts in
# the right order in about 3.5 s; GLM 5.3 took 20-50 s and MiniMax M3.1 Flash gave unstable scores.
SCORER = os.getenv("NAILIT_SCORER") or "tx:deepseek/deepseek-v4.1-flash-1017"
FILLERS = re.compile(r"\b(um+|uh+|er+|erm|like|you know|basically|sort of|kind of|actually)\b", re.I)


def deck_path():
    return library.home() / "library" / "model_level" / "deck.json"


def load_deck():
    path = deck_path()
    if not path.exists():
        raise HTTPException(status_code=404, detail="No rehearsal deck yet. Run: uv run python -m nailit.answers.generate")
    return json.loads(path.read_text())


def card(card_id):
    base_id, _, follow = card_id.partition("__f")
    for c in load_deck()["cards"]:
        if c["id"] == base_id:
            if not follow:
                return c
            items = c.get("followups") or []
            if follow.isdigit() and int(follow) < len(items):
                f = items[int(follow)]
                return {"id": card_id, "question": f["q"], "answer": f["a"], "moves": [], "type": "followup",
                        "competency": c.get("competency")}
    raise HTTPException(status_code=404, detail="Card not found")


def progress_path():
    return library.home() / "rehearse_progress.jsonl"


def history():
    path = progress_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


@router.get("/rehearse", response_class=HTMLResponse)
def page():
    return (STATIC / "rehearse.html").read_text(encoding="utf8")


@router.get("/rehearse/deck")
def deck(kind: str = "", limit: int = 400):
    data = load_deck()
    best = {}
    for row in history():
        best[row["card_id"]] = max(best.get(row["card_id"], 0), row["score"])
    TYPE_FIX = {"behavioral": "behavioural"}
    norm = lambda q: re.sub(r"[^a-z0-9]+", " ", q.lower().replace("résumé", "resume")).replace(" us ", " me ").strip()
    for c in data["cards"]:
        c["type"] = TYPE_FIX.get(c.get("type"), c.get("type"))
        seen, variants = {norm(c["question"])}, []
        for v in c.get("variants") or []:  # show only genuinely different wordings
            if norm(v) not in seen:
                seen.add(norm(v))
                variants.append(v)
        c["variants"] = variants
    cards = [{k: c.get(k) for k in ("id", "question", "answer", "moves", "hook", "frequency", "type", "why_it_won", "followups", "variants",
                                     "roles", "companies", "win_rate", "candidates", "origin", "competency")} | {"best_score": best.get(c["id"])}
             for c in data["cards"] if not kind or c.get("type") == kind]
    return {"cards": cards[:limit], "built": data.get("built"), "total": len(data["cards"]),
            "types": sorted({c.get("type") for c in data["cards"] if c.get("type")})}


class SpeakRequest(BaseModel):
    card_id: str = Field(min_length=1, max_length=120)
    part: str = Field(pattern="^(question|answer)$")
    engine: str = Field(default="openai", max_length=10)


@router.post("/rehearse/speak")
def speak(req: SpeakRequest):
    c = card(req.card_id)
    folder = voice.recordings_dir("rehearse")
    safe = re.sub(r"[^A-Za-z0-9_]", "_", c["id"])[:80]
    for ext in ("mp3", "wav"):
        cached = folder / f"{safe}_{req.part}.{ext}"
        if cached.exists() and cached.stat().st_mtime > deck_path().stat().st_mtime:
            return {"audio_url": f"/rehearse/audio/{cached.name}"}
    text = c["question"] if req.part == "question" else c["answer"]
    path, _ = voice.speak(text, "rehearse", f"{safe}_{req.part}", req.engine,
                          voice_name=INTERVIEWER_VOICE if req.part == "question" else CANDIDATE_VOICE,
                          instructions=SPEAK_STYLE[req.part])
    return {"audio_url": f"/rehearse/audio/{path.name}" if path else None}


@router.get("/rehearse/audio/{name}")
def audio(name: str):
    if not voice.SAFE_NAME.match(name):
        raise HTTPException(status_code=404, detail="not found")
    path = voice.recordings_dir("rehearse") / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="not found")
    return FileResponse(path)


@router.post("/rehearse/attempt")
def attempt(card_id: str = Form(...), audio: UploadFile = File(...), take: str = Form(""), test: bool = Form(False)):
    c = card(card_id)
    name = f"attempt_{re.sub(r'[^A-Za-z0-9_]', '_', card_id)[:60]}_{int(time.time())}.webm"
    try:
        path = voice.save_upload("rehearse", name, audio.file.read())
        transcript = voice.transcribe(path, mock_id="rehearse", take=take or None)
    except voice.VoiceUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    if not transcript["text"].strip():
        raise HTTPException(status_code=422, detail="No speech found in the recording")
    return _score(c, transcript["text"], transcript["speech_s"], transcript["filled_pauses"], audio_name=name, log=not test)


class TypedAttempt(BaseModel):
    card_id: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=8000)


@router.post("/rehearse/attempt_text")
def attempt_text(req: TypedAttempt):
    return _score(card(req.card_id), req.text, None, 0)


def _score(c, text, seconds, filled_pauses, audio_name=None, log=True):
    from nailit import scoring
    words = len(text.split())
    try:
        result = scoring.score(c, text, level=1)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Scoring failed: {error}") from error
    score = result["score"]
    delivery = {
        "seconds": seconds, "words": words,
        "wpm": round(words / seconds * 60) if seconds else None,
        "fillers": filled_pauses + len(FILLERS.findall(text)) if seconds else len(FILLERS.findall(text)),
        "we": len(re.findall(r"\bwe\b", text, re.I)), "i": len(re.findall(r"\bI\b", text)),
        "length_flag": ("long" if seconds and seconds > 120 else "short" if seconds and seconds < 30 else None),
    }
    row = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "card_id": c["id"], "score": score, "verdict": result.get("verdict"),
           "moves_hit": result.get("moves_hit") or [], "moves_missed": result.get("moves_missed") or [],
           "quality": result["quality"], "fidelity": result["fidelity"], "competency": c.get("competency"),
           "rules_failed": [r["id"] for r in result["rules"] if r["verdict"] == "fail"],
           "delivery": delivery, "audio": audio_name}
    if log:  # simulated-candidate test runs don't count towards your progress
        with open(progress_path(), "a") as handle:
            handle.write(json.dumps(row) + "\n")
    return {**row, "transcript": text, "one_fix": result.get("one_fix"), "best_line": result.get("best_line"),
            "rules": result["rules"],
            "model_answer": c["answer"], "moves": c.get("moves") or []}


@router.get("/rehearse/progress")
def progress():
    rows = history()
    today = time.strftime("%Y-%m-%d")
    days = sorted({r["at"][:10] for r in rows}, reverse=True)
    streak = 0
    for i, day in enumerate(days):
        expected = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400 * i))
        if day != expected:
            break
        streak += 1
    return {"attempts": len(rows), "today": sum(r["at"].startswith(today) for r in rows), "streak": streak,
            "average": round(sum(r["score"] for r in rows) / len(rows), 1) if rows else None,
            "mastered": len({r["card_id"] for r in rows if r["score"] >= 8})}
