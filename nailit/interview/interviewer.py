"""Mock interviewer. Content (questions, follow-up banks, personas, rounds, pressure events) comes from the library;
the rules live here: one question at a time, 1-3 follow-ups on gaps, probes, story reuse, regression and repeat-error
handling, ending on a strong answer, candidate questions and a closing statement. It never coaches during the round.
"""
import logging
import random
from decimal import Decimal
import re
import uuid

from nailit import library
from nailit.llm import LLMError, ask_llm

logger = logging.getLogger(__name__)

MODES = ("A", "B", "C")
EVENT_CHANCE = {"A": 0.0, "B": 0.25, "C": 0.5}
MAX_FOLLOWUPS = 3
CUT_OFF_S = 90
ANSWER_RULE_S = 3
GAP_TRIGGERS = ("missing_ownership", "missing_number", "missing_result", "missing_tradeoff", "missing_resistance",
                "vague", "ic_level_answer")
CORE_GAPS = ("missing_ownership", "missing_number", "missing_result", "missing_tradeoff", "vague")
STORY_TYPES = {"behavioural", "failure", "situational", "weakness", "strength"}
NO_QUESTIONS = re.compile(r"^\W*(no|nope|none|not really|nothing|that'?s (all|it)|i'?m good)\b", re.I)
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
NUMBER_WORDS = re.compile(r"\b(two|three|four|five|six|seven|eight|nine|ten|twelve|twenty|thirty|fifty|hundred|"
                          r"thousand|million|billion|half|double|twice|third|quarter|percent)\b", re.I)
SIGNALS = {
    "result": re.compile(r"\b(result|outcome|so that|which meant|led to|increas|reduc|cut|grew|grow|saved|improv|"
                         r"dropp|deliver|launch|shipp|won|achiev|impact)", re.I),
    "tradeoff": re.compile(r"\b(trade[- ]?off|instead of|rather than|at the cost|gave up|chose|decided against|"
                           r"option|alternative|sacrific)", re.I),
    "resistance": re.compile(r"\b(push ?back|resist|disagree|objection|concern|sceptic|skeptic|convinc|persuad|"
                             r"against)", re.I),
    "influence": re.compile(r"\b(team|stakeholder|align|convinc|influenc|led|lead|mentor|cross[- ]functional)", re.I),
    "generic": re.compile(r"\b(usually|generally|always|typically|in general|i tend to|normally|often)\b", re.I),
}
PROBES = ("Can you walk me through one specific time that happened?",
          "What exactly did you say or do at that moment?")
INTERVIEWER_RULES = (
    "You are the interviewer in a realistic job interview, speaking out loud. Stay in character. "
    "Never give feedback, hints, praise, scores or coaching. Never state facts about the candidate. "
    "Do not invent numbers about the company. Reply with only the words you say, at most three sentences."
)


TYPE_TIPS = {
    "opening": "Lead with what you're known for and one result; end with why this role. Aim for 90 seconds.",
    "motivation": "Start from their need, then your proof. Be specific about this company.",
    "behavioural": "Result first, then 2 sentences of context, the decision you made and what you rejected, the result, the lesson.",
    "failure": "Admit it in the first sentence, name your part, the concrete change, and the evidence it's different now.",
    "weakness": "A real weakness, the action you took, and evidence it's improving.",
    "strength": "Two or three strengths, each with one fact.",
    "situational": "Ask a clarifying question if needed, then give options with trade-offs.",
    "planning": "Listen and map, one pilot, then full contribution with a feedback check.",
    "self_assessment": "Specific strengths, specific gaps, no fog.",
    "hard_skills": "The method in plain words, then one real example.",
    "closing": "Ask your prepared questions, then close: who you are, the value, one proof, next step.",
    "negotiation": "Anchor on value and a researched range; pause after the number.",
    "presentation": "Outcome first, 3 blocks with mini-summaries, a memorable last line.",
    "default": "Answer in the first sentence; keep it under 90 seconds.",
}


def end_mock(state):
    """End early at the candidate's request; the summary covers the questions answered so far."""
    if state.get("current") and state["current"].get("answers"):
        _finish_question(state, library.load_library(), _load_me())
    state["phase"] = "done"
    state["ended_early"] = True
    return summary(state)


# ---------- setup ----------

def _by_id(items, item_id):
    return next((item for item in items or [] if item.get("id") == item_id), None)


def expand_flow(round_id, personas, questions, rng, seen=None):
    """A round's flow entries are question IDs, round IDs (expanded in place) or free-text instructions."""
    seen = (seen or set()) | {round_id}
    round_ = _by_id(personas["rounds"], round_id)
    if not round_:
        raise ValueError(f"unknown round {round_id}")
    items = []
    for entry in round_.get("flow") or []:
        question = _by_id(questions, entry)
        if question:
            items.append({"kind": "question", "id": question["id"]})
        elif _by_id(personas["rounds"], entry) and entry not in seen:
            items.append({"kind": "round", "id": entry, "label": _by_id(personas["rounds"], entry)["label"]})
            items += expand_flow(entry, personas, questions, rng, seen)
        else:
            items.append({"kind": "instruction", "text": entry})
    wanted = int(round_.get("questions") or 0)
    have = sum(1 for item in items if item["kind"] == "question")
    if have < wanted:
        pool = [q["id"] for q in questions if round_id in (q.get("rounds") or [])
                and q["id"] not in {i.get("id") for i in items}]
        rng.shuffle(pool)
        items += [{"kind": "question", "id": qid} for qid in pool[: wanted - have]]
    return items


def mode_c_unlocked(progress):
    return progress.get("freeze_drills", 0) >= 5 and (progress.get("week2_average") or 0) >= 3.5


def start_mock(round_id, mode="A", company_id=None, temperament_id=None, seed=None, progress=None, lib=None):
    lib = lib or library.load_library()
    personas = lib["personas"]
    questions, _ = library._questions(lib["questions"])
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    if mode == "C" and not mode_c_unlocked(progress or {}):
        raise PermissionError("Mode C unlocks after 5 freeze drills and a week-2 average of at least 3.5.")
    company = _by_id(personas["companies"], company_id) if company_id else None
    if company_id and not company:
        raise ValueError(f"unknown company {company_id}")
    temperaments = personas["temperaments"]
    cold = [t for t in temperaments if re.search(r"scep|skep|cold|hostile", f"{t['id']} {t['label']}", re.I)]
    default = (cold[0] if mode == "C" and cold else temperaments[0]) if temperaments else None
    temperament = _by_id(temperaments, temperament_id) if temperament_id else default
    if temperament_id and not temperament:
        raise ValueError(f"unknown temperament {temperament_id}")
    seed = seed if seed is not None else random.randrange(1 << 30)
    state = {
        "id": "mock_" + uuid.uuid4().hex[:12],
        "round_id": round_id, "mode": mode, "seed": seed,
        "company": company, "temperament": temperament,
        "queue": expand_flow(round_id, personas, questions, random.Random(seed)),
        "position": 0, "phase": "questions", "current": None,
        "turns": [], "scores": [], "error_counts": {}, "retired_gaps": [], "repeat_errors": [],
        "stories_used": {}, "asked_followups": [], "events_fired": [], "rule_violations": [],
        "deescalated": False, "extra_question_used": False, "candidate_questions": 0,
        "rounds_meta": [{"id": r.get("id"), "label": r.get("label")} for r in personas.get("rounds") or []],
    }
    return state, _advance(state, lib)


# ---------- answering ----------

def _rng(state):
    return random.Random(f"{state['seed']}:{len(state['turns'])}")


def _turn(state, say, kind, **extra):
    turn = {"role": "interviewer", "say": say.strip(), "kind": kind, "silence_before_s": 0,
            "interrupt_after_s": None, "cut_off_s": None, "event": None, **extra}
    state["turns"].append(turn)
    return turn


def _say(state, instruction, fallback):
    company, temperament = state.get("company") or {}, state.get("temperament") or {}
    persona = (f"Company: {company.get('name', 'a company')}. Values: {', '.join(company.get('values') or [])}. "
               f"Probing style: {company.get('probing_style', '')}. Temperament: {temperament.get('behaviour', '')}")
    try:
        return ask_llm(f"{INTERVIEWER_RULES}\n{persona}\n\n{instruction}", max_tokens=200, retries=1).strip() or fallback
    except LLMError as error:
        logger.warning("interviewer line fell back to plain text: %s", error)
        return fallback


def gaps(text, question, seconds=None, mode="A", company=None):
    """Triggers that apply to the answer so far, gap triggers first (followups.yaml trigger names)."""
    found = []
    i_count = len(re.findall(r"\b(i|my|me|i'm|i've|i'd)\b", text, re.I))
    we_count = len(re.findall(r"\b(we|our|us|we're|we've)\b", text, re.I))
    if i_count == 0 or we_count > 2 * i_count:
        found.append("missing_ownership")
    if not NUMBER.search(text) and not NUMBER_WORDS.search(text):
        found.append("missing_number")
    if not SIGNALS["result"].search(text):
        found.append("missing_result")
    story_question = question.get("type") in STORY_TYPES
    if story_question and not SIGNALS["tradeoff"].search(text):
        found.append("missing_tradeoff")
    if story_question and not SIGNALS["resistance"].search(text):
        found.append("missing_resistance")
    if len(text.split()) < 40 or (SIGNALS["generic"].search(text) and "missing_number" in found):
        found.append("vague")
    if story_question and not SIGNALS["influence"].search(text):
        found.append("ic_level_answer")
    if question.get("type") == "failure":
        found.append("failure_answer")
    if seconds and seconds > CUT_OFF_S:
        found.append("over_90s")
    found += [f"lp:{lp}" for lp in question.get("lp") or []] + (["lp:any"] if question.get("lp") else [])
    if company:
        found.append(f"company:{company['id']}")
    if mode == "C":
        found.append("mode:C")
    return found + ["always"]


def _bank_question(state, lib, triggers):
    banks = lib["followups"]["banks"]
    allowed = set((state.get("company") or {}).get("followup_banks") or [])
    used_here = (state.get("current") or {}).get("triggers", [])
    for trigger in triggers:
        if trigger in state["retired_gaps"] or trigger in used_here:
            continue
        for bank in banks:
            company_bank = bank["trigger"].startswith("company:")
            if bank["trigger"] != trigger or (allowed and company_bank and bank["id"] not in allowed):
                continue
            unused = [q for q in bank["questions"] if q not in state["asked_followups"]]
            if unused:
                state["asked_followups"].append(unused[0])
                used_here.append(trigger)
                return trigger, bank["id"], unused[0]
    return None


def _story_for(text, stories):
    words = set(re.findall(r"[a-z]{5,}", text.lower()))
    best, best_hits = None, 0
    for story in stories.get("stories") or []:
        source = " ".join([stories["facts"].get(f, {}).get("text", "") for f in story.get("facts") or []
                           if isinstance(f, str)] + [str(story.get(k) or "") for k in ("title", "my_part", "punchline")])
        hits = len(words & set(re.findall(r"[a-z]{5,}", source.lower())))
        if hits > best_hits:
            best, best_hits = story["id"], hits
    return best if best_hits >= 3 else None


def _wrong_claim(text, rng):
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text) if NUMBER.search(s)]
    if not sentences:
        return None
    sentence = rng.choice(sentences)
    match = NUMBER.search(sentence)
    true = match.group(0)
    doubled = Decimal(true.replace(",", "")) * 2 or Decimal(2)
    wrong = format(doubled.normalize(), "f")
    claim = sentence[: match.start()] + wrong + sentence[match.end():]
    return true, wrong, f"Just so I have it right: {claim.rstrip('.!?')}?"


def _event_turn(state, lib, event, answer_text):
    eid, how = event["id"], event.get("how", "")
    if "silence" in eid:
        trigger = _bank_question(state, lib, ["always"])
        say = trigger[2] if trigger else "Go on."
        return _turn(state, say, "event", event=eid, silence_before_s=6)
    if "wrong" in eid:
        claim = _wrong_claim(answer_text, _rng(state))
        if claim:
            return _turn(state, claim[2], "event", event=eid, expected={"true": claim[0], "said": claim[1]})
        return None
    if "connection" in eid or "drop" in eid:
        return _turn(state, "Sorry, you cut out for a moment. Where were you?", "event", event=eid)
    return _turn(state, _say(state, f"Pressure event '{event['label']}': {how}\nCandidate's last answer: {answer_text}",
                             event["label"]), "event", event=eid)


def _pick_event(state, lib):
    mode_rank = MODES.index(state["mode"])
    if state["deescalated"] or _rng(state).random() >= EVENT_CHANCE[state["mode"]]:
        return None
    events = [e for e in lib["personas"]["pressure_events"] if MODES.index(e.get("min_mode", "A")) <= mode_rank]
    fresh = [e for e in events if e["id"] not in state["events_fired"]] or events
    return _rng(state).choice(fresh) if fresh else None


def _finish_question(state, lib, me):
    current = state["current"]
    text = " ".join(current["answers"])
    question = _by_id(library._questions(lib["questions"])[0], current["question_id"]) or {}
    remaining = [g for g in gaps(text, question) if g in CORE_GAPS]
    score = max(1, 5 - len(remaining))
    state["scores"].append({"question_id": current["question_id"], "score": score, "gaps": remaining})
    for gap in remaining:
        state["error_counts"][gap] = state["error_counts"].get(gap, 0) + 1
        if state["error_counts"][gap] == 3:
            state["retired_gaps"].append(gap)
            state["repeat_errors"].append({"gap": gap, "question_ids": [s["question_id"] for s in state["scores"]
                                                                        if gap in s["gaps"]]})
            logger.info("mock %s: %s three times; logged, no more follow-ups for it", state["id"], gap)
    story = _story_for(text, me.get("stories") or {})
    if story:
        state["stories_used"].setdefault(story, []).append(current["question_id"])
    scores = [s["score"] for s in state["scores"]]
    if len(scores) >= 3 and scores[2] < scores[0] and not state["deescalated"]:
        state["deescalated"] = True
        logger.info("mock %s: regression (question 3 < question 1); de-escalating", state["id"])
    state["current"] = None


def _ask_question(state, lib, item, lead=""):
    questions = library._questions(lib["questions"])[0]
    question = _by_id(questions, item["id"])
    text = _rng(state).choice([question["text"], *(question.get("variants") or [])])
    if not any(t.get("kind") == "question" for t in state["turns"]):
        round_label = next((r.get("label") for r in state.get("rounds_meta") or [] if r.get("id") == state["round_id"]),
                           state["round_id"].replace("_", " "))
        lead = (f"Hi, thanks for making the time today. I'll be running your {round_label.lower()}. "
                f"Let's get started. {lead}").strip()
    hint = None
    if state["mode"] == "A":
        hint = {"type": question["type"].replace("_", " "), "tip": TYPE_TIPS.get(question["type"], TYPE_TIPS["default"]),
                "tests_for": question.get("tests_for") or []}
    event = _pick_event(state, lib)
    state["current"] = {"question_id": question["id"], "answers": [], "followups": 0, "triggers": [],
                        "event": event["id"] if event else None}
    extra = {}
    if event and ("interrupt" in event["id"] or "cut" in event["id"]):
        state["events_fired"].append(event["id"])
        state["current"]["event"] = None
        key = "interrupt_after_s" if "interrupt" in event["id"] else "cut_off_s"
        extra = {key: 20 if key == "interrupt_after_s" else CUT_OFF_S, "event": event["id"]}
    if hint:
        extra["hint"] = hint
    extra["question_text"] = text
    return _turn(state, f"{lead} {text}", "question", question_id=question["id"], **extra)


def _strong_finish_question(state, lib, me):
    asked = {s["question_id"] for s in state["scores"]}
    story_answers = {a for s in (me.get("stories") or {}).get("stories") or [] for a in s.get("answers") or []}
    pool = [q for q in library._questions(lib["questions"])[0] if q["id"] not in asked]
    pool.sort(key=lambda q: (q["id"] not in story_answers, bool(q.get("hard"))))
    return pool[0] if pool else None


def _advance(state, lib, me=None, lead=""):
    lines = [lead] if lead else []
    while state["position"] < len(state["queue"]):
        item = state["queue"][state["position"]]
        state["position"] += 1
        if item["kind"] == "instruction":
            # Free-text flow entries ("behavioural x4 from the JD map") are the library author's notes on how the
            # round is filled, not lines to say. Spoken through the model they became a second, invented question.
            continue
        elif item["kind"] == "round":
            lines.append(f"Next: the {item['label']} part.")
        elif _by_id(library._questions(lib["questions"])[0], item["id"]):
            if (_by_id(library._questions(lib["questions"])[0], item["id"]) or {}).get("type") == "closing":
                continue  # the end of every mock already asks for their questions and a closing statement
            return _ask_question(state, lib, item, " ".join(lines))
        else:
            logger.warning("mock %s: question %s is no longer in the library; skipped", state["id"], item["id"])
    me = me if me is not None else _load_me()
    last = state["scores"][-1]["score"] if state["scores"] else 5
    if last < 4 and not state["extra_question_used"]:
        question = _strong_finish_question(state, lib, me)
        if question:
            state["extra_question_used"] = True
            return _ask_question(state, lib, {"id": question["id"]}, " ".join(lines + ["One more before we finish."]))
    state["phase"] = "candidate_questions"
    return _turn(state, " ".join(lines + ["That's all from my side. Do you have any questions for me?"]),
                 "candidate_questions")


def _load_me():
    try:
        return library.load_me()
    except library.LibraryError as error:
        logger.warning("stories not loaded for the mock: %s", error.errors[:3])
        return {}


def answer(state, text, seconds=None, pre_answer_silence_s=None, lib=None):
    """Record the candidate's reply and return the interviewer's next turn."""
    if state["phase"] == "done":
        raise ValueError("this mock is finished")
    lib = lib or library.load_library()
    state["turns"].append({"role": "candidate", "say": text, "seconds": seconds,
                           "pre_answer_silence_s": pre_answer_silence_s})
    if state["phase"] == "candidate_questions":
        if NO_QUESTIONS.match(text) or state["candidate_questions"] >= 3:
            state["phase"] = "closing"
            return _turn(state, "Before we wrap up, is there anything you'd like to add? A closing statement?",
                         "closing")
        state["candidate_questions"] += 1
        reply = _say(state, f"The candidate asks: {text}\nAnswer realistically and briefly as this interviewer, "
                            "then ask if they have anything else.", "Good question. Anything else?")
        return _turn(state, reply, "answer")
    if state["phase"] == "closing":
        state["phase"] = "done"
        return _turn(state, "Thank you, that's everything from me. We'll be in touch.", "end")

    current, me = state["current"], None
    if state["mode"] == "B" and pre_answer_silence_s is not None and pre_answer_silence_s > ANSWER_RULE_S:
        state["rule_violations"].append({"question_id": current["question_id"], "rule": "3s_answer",
                                         "seconds": pre_answer_silence_s})
    current["answers"].append(text)
    joined = " ".join(current["answers"])
    question = _by_id(library._questions(lib["questions"])[0], current["question_id"]) or {}
    lead = "Let me stop you there." if seconds and seconds > CUT_OFF_S else ""
    limit = 1 if state["deescalated"] else MAX_FOLLOWUPS

    if current["followups"] < limit:
        if current.get("event"):
            event = _by_id(lib["personas"]["pressure_events"], current["event"])
            current["event"] = None
            turn = _event_turn(state, lib, event, joined) if event else None
            if turn:
                state["events_fired"].append(event["id"])
                current["followups"] += 1
                return turn
        triggers = gaps(joined, question, seconds, state["mode"], state.get("company"))
        gap_triggers = [t for t in triggers if t in GAP_TRIGGERS]
        me = _load_me()
        story = _story_for(joined, me.get("stories") or {}) if state["mode"] == "C" else None
        if story and state["stories_used"].get(story) and current["followups"] == 0:
            current["followups"] += 1
            return _turn(state, f"{lead} You've told me about that one already. Do you have a different example?",
                         "probe", question_id=current["question_id"])
        if gap_triggers or current["followups"] == 0:
            found = _bank_question(state, lib, gap_triggers if current["followups"] else triggers)
            if found:
                current["followups"] += 1
                return _turn(state, f"{lead} {found[2]}", "followup", question_id=current["question_id"],
                             trigger=found[0], bank=found[1])
            if "vague" in gap_triggers:
                probe = next((p for p in PROBES if p not in state["asked_followups"]), None)
                if probe:
                    state["asked_followups"].append(probe)
                    current["followups"] += 1
                    return _turn(state, f"{lead} {probe}", "probe", question_id=current["question_id"])
    me = me if me is not None else _load_me()
    _finish_question(state, lib, me)
    return _advance(state, lib, me, lead)


def summary(state):
    return {key: state.get(key) for key in ("id", "round_id", "mode", "phase", "scores", "stories_used", "repeat_errors",
                                            "events_fired", "rule_violations", "deescalated", "ended_early")}
