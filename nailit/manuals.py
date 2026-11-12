"""The parts of the manuals that are plain checks, applied in code: phrases to cut, answer length and pace, and the
practice plan (checklists, programmes, drills). They come from ~/NailIt/library, where every item cites its manual."""
import re
import statistics
from functools import lru_cache
from pathlib import Path

import yaml
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from nailit import library

router = APIRouter()
ORDER = {"fail": 0, "warn": 1, "info": 2}
NUMBER = re.compile(r"\d")


def _yaml(*parts):
    path = library.home().joinpath("library", *parts)
    try:
        return _parsed(str(path), path.stat().st_mtime)
    except (OSError, yaml.YAMLError):
        return None


@lru_cache(maxsize=16)
def _parsed(path, _mtime):
    return yaml.safe_load(Path(path).read_text(encoding="utf8"))


def _scope(text, scope):
    """The part of the answer a check looks at."""
    words = text.split()
    if scope == "answer_start":
        return " ".join(words[:25])
    if scope == "answer_end":
        return " ".join(words[-30:])
    if scope == "result_sentences":
        return " ".join(s for s in re.split(r"(?<=[.!?])\s+", text) if NUMBER.search(s))
    return text


def phrase_hits(text, card=None, limit=6):
    """Weak phrases from the manuals found in the answer: [{id, label, fix, severity, quote, count}], worst first."""
    detectors = (_yaml("detectors.yaml") or {}).get("phrase_detectors") or []
    lowered, hits = text.lower(), []
    is_failure = (card or {}).get("competency") == "failure" or (card or {}).get("type") == "failure"
    for d in detectors:
        if d.get("kind") not in ("phrase", "regex") or (d.get("scope") == "failure_answers" and not is_failure):
            continue
        if any(str(c).lower() in lowered for c in d.get("except_context") or []):
            continue
        part, found = _scope(text, d.get("scope")), []
        for pattern in d.get("patterns") or []:
            try:
                expr = pattern if d["kind"] == "regex" else r"(?<!\w)" + re.escape(pattern) + r"(?!\w)"
                found += [m.group(0) for m in re.finditer(expr, part, re.I)]
            except re.error:
                continue
        threshold = d.get("threshold") or 1  # written as {per_answer: 2} in the library
        if isinstance(threshold, dict):
            threshold = next(iter(threshold.values()), 1)
        if len(found) >= int(threshold):
            hits.append({"id": d["id"], "label": d.get("label", d["id"]), "fix": d.get("fix") or d.get("replacement") or "",
                         "severity": d.get("severity", "warn"), "quote": found[0], "count": len(found)})
    hits.sort(key=lambda h: (ORDER.get(h["severity"], 3), -h["count"]))
    return hits[:limit]


def delivery_notes(seconds, wpm, card=None, past_wpm=()):
    """Length and pace against the manuals' limits. Pace is judged against your own calm baseline (the median of
    your earlier answers), as the manuals define it, so it stays silent until there are three earlier answers."""
    measured = {d["id"]: d for d in (_yaml("detectors.yaml") or {}).get("measured_detectors") or []}
    notes, card = [], card or {}

    def add(key, fallback):
        d = measured.get(key) or {}
        notes.append({"id": key, "label": d.get("label") or fallback, "fix": d.get("fix") or ""})
    if seconds:
        tmay = card.get("competency") == "tmay"
        if tmay and seconds > 180:
            add("tmay_too_long", "Opening runs past three minutes")
        elif not tmay and seconds > 120:
            add("too_long", "Longer than two minutes")
        elif card.get("type") == "behavioural" and seconds < 40:
            add("too_short", "Shorter than 40 seconds")
    if wpm and len(past_wpm) >= 3 and wpm > statistics.median(past_wpm) * 1.2:
        add("pace_fast", "Faster than your calm baseline")
    return notes


@router.get("/plan/data")
def plan_data():
    phrases = _yaml("phrases.yaml") or {}
    drills = {name: _yaml("drills", f"{name}.yaml") or [] for name in ("core", "voice")}
    return {"checklist": _yaml("checklists", "day_of.yaml") or {},
            "programmes": [p for p in (_yaml("programmes", "14day.yaml"), _yaml("programmes", "30day.yaml")) if p],
            "drills": {k: (v if isinstance(v, list) else v.get("drills") or v.get("days") or []) for k, v in drills.items()},
            "bridges": phrases.get("bridges") or [], "anchors": phrases.get("anchor_lines") or [],
            "swaps": phrases.get("swaps") or []}


@router.get("/plan", response_class=HTMLResponse)
def plan_page():
    return (Path(__file__).resolve().parent / "static" / "plan.html").read_text(encoding="utf8")
