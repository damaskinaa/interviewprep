"""Choose who runs the mock interview, and score interviews held outside the app.

Two ways to practise a live interview:
  inside   /mock, with the interviewer played by the engine chosen here (TensorX, Lua, Claude subscription, Gemini);
  outside  a real voice call in ChatGPT, Claude, Gemini Live or a Lua voice agent. The app writes the interviewer's
           brief for that tool (company, round, questions from the competency map, how to probe), and afterwards
           scores the pasted transcript with the same rubric scorer as rehearsal.
"""
import json
import random
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from nailit import library, llm, scoring

router = APIRouter()
STATIC = Path(__file__).resolve().parent / "static"
OUTSIDE_TOOLS = {
    "chatgpt": {"label": "ChatGPT voice", "cost": "Included in ChatGPT Plus; voice time is capped per day",
                "how": "Create a Project or custom GPT named “NailIt interviewer”, paste the brief as its instructions, "
                       "then start voice mode in a new chat and say “Start”."},
    "claude": {"label": "Claude voice", "cost": "Included in your Claude plan; counts toward its usage limits",
               "how": "Open a new chat in the Claude app, paste the brief, then turn on voice mode and say “Start”. "
                      "Voice works best on the phone app. Claude voice takes turns; it doesn't interrupt."},
    "gemini": {"label": "Gemini Live", "cost": "Free",
               "how": "Gems don't work in Live, so paste the brief as the first message in a normal Gemini chat, then tap "
                      "the Live button in that chat and say “Start”."},
    "granola": {"label": "Any call, recorded with Granola", "cost": "Granola's free plan covers a limited number of meetings",
                "how": "Run the call in any tool above (or with a friend) while Granola records it. Afterwards copy Granola's "
                       "transcript and paste it below; speaker labels like “Me” and “Them” are fine. You don't need to "
                       "ask the tool to print the transcript."},
    "lua": {"label": "Lua voice agent", "cost": "Lua credits",
            "how": "In your Lua workspace, paste the brief as the agent's persona (or run `lua persona` in the agent's "
                   "folder), publish, and start a voice chat with the agent in the web widget."},
}


def _settings():
    try:
        return json.loads(llm.settings_path().read_text())
    except (OSError, ValueError):
        return {}


@router.get("/settings")
def get_settings():
    current = llm.provider()
    return {"engine": current,
            "engines": [{"id": k, **v, "ready": llm.engine_ready(k), "selected": k == current} for k, v in llm.ENGINES.items()],
            "outside": [{"id": k, **v} for k, v in OUTSIDE_TOOLS.items()]}


class EngineChoice(BaseModel):
    engine: str = Field(pattern="^[a-z]+$", max_length=20)


@router.post("/settings")
def set_engine(choice: EngineChoice):
    if choice.engine not in llm.ENGINES:
        raise HTTPException(status_code=422, detail="Unknown engine")
    if not llm.engine_ready(choice.engine):
        needs = llm.ENGINES[choice.engine]["needs"] or ["the `claude` command, signed in"]
        raise HTTPException(status_code=409, detail=f"{llm.ENGINES[choice.engine]['label']} isn't set up yet. It needs: "
                                                    + ", ".join(needs) + " (Keychain service “nailit”).")
    data = {**_settings(), "engine": choice.engine}
    llm.settings_path().write_text(json.dumps(data, indent=1))
    return get_settings()


@router.post("/settings/test")
def test_engine():
    started = time.time()
    try:
        reply = llm.ask_llm("You are an interviewer. Ask the candidate one short opening question about handling conflict. "
                            "Reply with only the words you say.", max_tokens=120, retries=1)
    except llm.LLMError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {"engine": llm.provider(), "seconds": round(time.time() - started, 1), "reply": reply}


def _questions(company, n, role, seed=None):
    """Questions for the call: opening and why-us first, then the company's most-probed competencies, weakest first."""
    from nailit import rehearse
    cards = rehearse.load_deck()["cards"]
    best = {}
    for row in rehearse.history():
        best[row["card_id"]] = max(best.get(row["card_id"], 0), row["score"])
    rng = random.Random(seed)
    by_comp = {}
    for card in cards:
        if card.get("company") and card["company"] != company:
            continue
        if role and card.get("roles") and not any(role.lower() in r.lower() for r in card["roles"]):
            continue
        by_comp.setdefault(card.get("competency") or "other", []).append(card)
    picked = []
    for cid in ("tmay", "why_company"):
        pool = [c for c in by_comp.pop(cid, []) if cid != "why_company" or c.get("company") == company] or by_comp.get(cid, [])
        if pool:
            picked.append(pool[0])
    rest = [min(pool, key=lambda c: (best.get(c["id"], -1), rng.random())) for cid, pool in by_comp.items()
            if cid not in ("salary_logistics", "questions_for_them", "other")]
    rest.sort(key=lambda c: (company not in ("generic", None) and not c.get(company if company != "aws" else "amazon"),
                             best.get(c["id"], -1), -(c.get("frequency") or 0)))
    return (picked + rest)[:n]


@router.get("/call/pack")
def pack(company: str = "generic", round_id: str = "behavioural", n: int = 8, role: str = "", tool: str = "chatgpt"):
    lib = library.load_library()
    companies = {c["id"]: c for c in lib["personas"]["companies"]}
    persona = companies.get(company) or ({**companies["aws"], "name": "Amazon"} if company == "amazon" and "aws" in companies
                                         else {"name": "the company"})
    rounds = {r["id"]: r for r in lib["personas"]["rounds"]}
    label = (rounds.get(round_id) or {}).get("label", round_id.replace("_", " "))
    questions = _questions(company, max(3, min(n, 15)), role)
    lines = [
        f"You are an interviewer at {persona.get('name', 'the company')} running a {label.lower()} interview"
        + (f" for a {role} role" if role else "") + ". This is a spoken mock interview for my practice. Stay in character for the whole call.",
        "", "How to behave:",
        "- Speak as a real interviewer: brief, neutral, professional. One question at a time, then wait.",
        "- Never coach, praise, score or hint during the interview. No “great answer”.",
        f"- Probing style: {persona.get('probing_style', 'ask for specifics')}",
        "- After each answer ask up to two follow-ups aimed at what was missing: what I personally decided (if I said “we”), "
        "the number and its baseline, the result and what it led to, the option I rejected, or who pushed back.",
        "- If an answer runs past about two minutes, cut in politely and move on.",
        "- If I give a vague or generic answer, ask for one specific time it happened.",
        f"- Values to listen for: {', '.join(persona.get('values') or []) or 'ownership, judgement, results'}.",
        "", "Start by greeting me in one sentence and asking the first question. Ask these questions in order, in your own words:",
    ]
    lines += [f"{i}. {c['question']}" for i, c in enumerate(questions, 1)]
    lines += ["", "Then ask whether I have questions for you and answer them briefly in character.",
              "", "When I say “end interview”, stop being the interviewer and print the full transcript of this call, every turn, "
                  "word for word as best you can, in this exact format and nothing else:",
              "INTERVIEWER: …", "CANDIDATE: …"]
    return {"brief": "\n".join(lines), "questions": [c["question"] for c in questions],
            "tool": OUTSIDE_TOOLS.get(tool, OUTSIDE_TOOLS["chatgpt"]), "company": persona.get("name"), "round": label}


class Transcript(BaseModel):
    text: str = Field(min_length=40, max_length=120000)
    company: str = Field(default="generic", max_length=30)
    tool: str = Field(default="", max_length=20)


SPLIT_PROMPT = """Below is the transcript of a mock job interview. Group it into the interviewer's MAIN questions, each
with everything the candidate said in reply to it and to its follow-ups (join the candidate's turns in order). Speaker
labels vary by tool: INTERVIEWER / CANDIDATE, Them / Me, a name, or none at all; work out who is who from the content. Skip
greetings and the part where the candidate asks questions. For each, pick the competency it tests from this list:
{comps}

Reply JSON {{"items": [{{"question": "the main question", "followups": ["..."], "answer": "the candidate's words, verbatim, joined",
"competency": "id from the list"}}]}}

Transcript:
{text}"""


_TIME = r"\[?\(?\d{1,2}:\d{2}(?::\d{2})?\)?\]?"
_LABEL = re.compile(rf"^\s*(?:{_TIME}\s*)?(?:(?P<who>[^\W\d][\w .'-]{{0,40}}?)\s*(?:{_TIME})?\s*(?::|\s[-–—])\s+)?(?:{_TIME}\s*)?")


def _turns(transcript):
    """Each speaker's run of consecutive lines as one stream of words, labels and timestamps removed, so a sentence the
    transcriber split across two lines of the same speaker ("Me: I led the" / "Me: migration.") still reads as said,
    while one speaker can never finish another's sentence."""
    turns, last = [], object()
    for line in transcript.splitlines():
        if not line.strip():
            continue
        match = _LABEL.match(line)
        who = (match.group("who") or "").strip().lower() or None
        text = line[match.end():]
        if turns and who == last:
            turns[-1] += " " + text
        else:
            turns.append(text)
        last = who
    return turns


def _verbatim(item, transcript):
    """Keep only the sentences of the candidate's answer that are really in the transcript. The splitter is a model
    reading pasted text, so it can be steered into writing a better answer than the one given; scores must only ever
    be about words that were said. Drops the item when under 80% of its words survive."""
    sentences = [s for s in re.split(r"(?<=[.!?…])\s+|\n+", str(item["answer"])) if s.strip()]
    turns = _turns(transcript)
    kept = [s for s in sentences if scoring.quoted(s, transcript) or any(scoring.quoted(s, turn) for turn in turns)]
    if sum(len(s.split()) for s in kept) < 0.8 * len(str(item["answer"]).split()):
        return None
    return {**item, "answer": " ".join(kept)}


@router.post("/call/import")
def import_transcript(req: Transcript):
    """Score an interview held in another tool: split it into question/answer pairs, score each against the rubric."""
    from concurrent.futures import ThreadPoolExecutor

    from nailit.answers import ai, competencies
    from nailit.rehearse import SCORER, append_progress
    comps = competencies.load()[0]
    listing = "\n".join(f"{c['id']}: {c['name']}" for c in comps)
    try:
        split = ai.chat(SCORER, SPLIT_PROMPT.format(comps=listing, text=req.text), json_mode=True, timeout=120) or {}
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Couldn't read the transcript: {error}") from error
    items = [i for i in split.get("items") or [] if isinstance(i, dict) and i.get("question") and i.get("answer")]
    if not items:
        raise HTTPException(status_code=422, detail="No question-and-answer pairs found. Paste the transcript with "
                                                    "INTERVIEWER: and CANDIDATE: lines.")
    items = [kept for kept in (_verbatim(i, req.text) for i in items) if kept]
    if not items:
        raise HTTPException(status_code=422, detail="The answers read back from the transcript weren't in it. Paste the "
                                                    "transcript with INTERVIEWER: and CANDIDATE: lines.")
    valid = {c["id"] for c in comps}

    def one(item):
        card = {"question": item["question"], "competency": item.get("competency") if item.get("competency") in valid else None,
                "type": "behavioural", "answer": "", "moves": []}
        try:
            result = scoring.score(card, item["answer"], level=2)
        except Exception as error:  # noqa: BLE001
            return {**item, "error": str(error)[:200]}
        return {"question": item["question"], "followups": item.get("followups") or [], "answer": item["answer"],
                "competency": card["competency"], "words": len(item["answer"].split()), **result}

    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(one, items[:20]))
    scored = [r for r in results if "score" in r]
    failed = {}
    for r in scored:
        for rule in r["rules"]:
            if rule["verdict"] == "fail":
                failed[rule["name"]] = failed.get(rule["name"], 0) + 1
    overall = round(sum(r["score"] for r in scored) / len(scored), 1) if scored else None
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    append_progress([{"at": stamp, "card_id": "call:" + (r["competency"] or "other"), "score": r["score"],
                      "verdict": r["verdict"], "quality": r["quality"], "fidelity": None,
                      "competency": r["competency"], "source": "call:" + (req.tool or "outside"),
                      "rules_failed": [x["id"] for x in r["rules"] if x["verdict"] == "fail"]} for r in scored])
    return {"overall": overall, "answers": results, "count": len(scored),
            "verdict": None if overall is None else "Strong Hire" if overall >= 9 else "Hire" if overall >= 7
            else "Lean No Hire" if overall >= 5 else "No Hire",
            "repeat_misses": sorted(failed.items(), key=lambda kv: -kv[1])[:3]}


@router.get("/call", response_class=HTMLResponse)
def page():
    return (STATIC / "call.html").read_text(encoding="utf8")
