"""Score a spoken answer against the rubric built from the manuals (library/rubric.md), rule by rule.

The old scorer asked a model for one number, and a rambling "we"-answer with no figures and no result still got
6-7 out of 10. Here the model only judges each rule (pass / partial / fail, with the words that prove it); the
score is computed in code from those verdicts, and rules that code can check itself (numbers, "we" for decisions,
hedges, length) are checked in code and can only lower a verdict, never raise it.

  quality   how well the answer follows the rules for this kind of question   (always)
  fidelity  how many of the model answer's key moves were reproduced           (Level 1 rehearsal only)
"""
import re

import yaml

from nailit import library

RULE_BLOCK = re.compile(r"^\*\*(R\d+\.\d+)\*\*\s*(.*?)(?=^\*\*R\d+\.\d+\*\*|^## |\Z)", re.S | re.M)
# Rules for answers that tell a story, with their weight in the score; the question type adds its own rule.
STORY_RULES = {"R1.1": 2, "R1.2": 1, "R1.3": 2, "R1.4": 2, "R1.5": 2, "R1.7": 1.5, "R1.8": 1.5}
DIRECT_RULES = {"R1.1": 2, "R1.11": 1}
STORY_TYPE_RULES = {"R2.1", "R2.3", "R2.4", "R2.6", "R4.10", "R4.11", "R1.5"}
SHORT = {"R1.1": "Answer first", "R1.2": "Context in two sentences or fewer", "R1.3": "“I” for your decisions",
         "R1.4": "Names the trade-off", "R1.5": "A number with a baseline or timeframe", "R1.7": "Result of the result",
         "R1.8": "A specific lesson", "R1.11": "No hedging, no inflating", "R2.1": "The story has its turning points",
         "R2.3": "Shows how you influenced", "R2.4": "Owns the failure and the fix", "R2.5": "A real weakness, already being fixed",
         "R2.6": "Says what you did NOT do", "R2.7": "30-60-90 shape", "R2.8": "Their need first, then your proof",
         "R2.9": "Clarify, options, decision", "R2.10": "A sober self-rating", "R2.12": "Method plus a real example",
         "R2.13": "A researched range, no pay history", "R4.10": "Shows the reasoning", "R4.11": "Disagrees with evidence, then commits",
         "R6.1": "Questions that show you think like the job holder", "R7.1": "Opening built for the interview"}
VALUE = {"pass": 1.0, "partial": 0.5, "fail": 0.0}
NUMBER = re.compile(r"\d|\b(two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|sixty|"
                    r"seventy|eighty|ninety|hundred|thousand|million|half|third|quarter|double|doubled|halved)\b", re.I)
WE_DECIDED = re.compile(r"\bwe (decided|chose|built|designed|created|implemented|launched|found|identified|realised|realized|"
                        r"proposed|introduced|fixed|changed|redesigned|analysed|analyzed|led|drove|agreed|picked|went with)\b", re.I)
I_DECIDED = re.compile(r"\bI (decided|chose|built|designed|created|implemented|launched|found|identified|realised|realized|"
                       r"proposed|introduced|fixed|changed|redesigned|analysed|analyzed|led|drove|rebuilt|mapped|set|told|put|"
                       r"asked|wrote|cut|moved|took|ran|made|stopped|kept|said|went|pushed|paused|escalated|negotiated)\b")

_rules = None
_comps = None


def rules():
    """{rule id: full text}, including the bullet lines under a rule (the library parser keeps only the first line)."""
    global _rules
    if _rules is None:
        path = library.home() / "library" / "rubric.md"
        text = path.read_text() if path.exists() else ""
        _rules = {m.group(1): re.sub(r"\s+", " ", re.sub(r"\(src:.*?\)", "", m.group(2))).strip()
                  for m in RULE_BLOCK.finditer(text)}
    return _rules


def competency(comp_id):
    global _comps
    if _comps is None:
        from nailit.answers.competencies import DATA
        _comps = {c["id"]: c for c in yaml.safe_load(DATA.read_text())["competencies"]}
    return _comps.get(comp_id or "")


def rule_set(card):
    """Which rules apply to this card, with weights. Story questions get the full story rules plus their type rule."""
    comp = competency(card.get("competency"))
    type_rule = (comp or {}).get("rule")
    story = type_rule in STORY_TYPE_RULES if comp else card.get("type") in ("behavioural", "failure", "situational")
    chosen = dict(STORY_RULES if story else DIRECT_RULES)
    if type_rule and type_rule in rules() and type_rule not in chosen:
        chosen[type_rule] = 2.5
    return chosen


def code_checks(text, chosen):
    """Verdicts that code can decide without a model. These only ever lower a model verdict."""
    out = {}
    if "R1.5" in chosen and not NUMBER.search(text):
        out["R1.5"] = ("fail", "no number anywhere in the answer")
    we, i = len(WE_DECIDED.findall(text)), len(I_DECIDED.findall(text))
    if "R1.3" in chosen and we >= 2 and we > i:
        out["R1.3"] = ("fail", f"“we” made {we} of the decisions, “I” made {i}")
    return out


PROMPT = """You are assessing a spoken interview answer against a fixed rubric. Be strict and literal: a rule passes
only if the answer clearly does what the rule says, and you must quote the learner's words that prove it. No quote,
no pass. "partial" means attempted but weak (for example a number with no baseline). Judge only the learner's answer.

Question: {question}

Rules:
{rules}
{model_block}
Learner's answer (speech-to-text, so ignore spelling and punctuation):
{attempt}

Reply JSON {{"on_topic": true or false (does it answer this question at all?),
"rules": {{"<rule id>": {{"verdict": "pass|partial|fail", "evidence": "the learner's words, or '' if none"}}}},
{moves_keys}"best_line": "the learner's strongest sentence, quoted exactly",
"one_fix": "the single most valuable change for the next attempt, as a spoken-coach instruction of at most 25 words"}}"""


def score(card, text, level=1, judge=None, timeout=40):
    """Returns {score, quality, fidelity, rules[], moves_hit, moves_missed, one_fix, best_line, verdict, on_topic}."""
    from nailit.answers import ai
    from nailit.rehearse import SCORER
    chosen = rule_set(card)
    all_rules = rules()
    moves = card.get("moves") or [] if level == 1 else []
    model_block = (f"\nThe learner is rehearsing this model answer and may paraphrase it:\n{card['answer']}\n"
                   f"Key moves of the model answer: {moves}\n" if level == 1 and card.get("answer") else "")
    moves_keys = ('"moves_hit": [exact strings from the key moves that the learner reproduced], "moves_missed": [the rest],\n'
                  if moves else "")
    reply = ai.chat(judge or SCORER, PROMPT.format(
        question=card["question"], rules="\n".join(f"{rid}: {all_rules.get(rid, SHORT.get(rid, ''))}" for rid in chosen),
        model_block=model_block, attempt=text, moves_keys=moves_keys), json_mode=True, effort="low", timeout=timeout) or {}
    if not reply.get("rules"):
        raise RuntimeError("the scoring model returned no rule verdicts")
    overrides, results, total, weight = code_checks(text, chosen), [], 0.0, 0.0
    for rid, w in chosen.items():
        got = (reply["rules"].get(rid) or {})
        verdict, evidence = got.get("verdict") if got.get("verdict") in VALUE else "fail", (got.get("evidence") or "").strip()
        if verdict == "pass" and not evidence:
            verdict = "partial"  # no quote, no pass
        if rid in overrides and VALUE[overrides[rid][0]] < VALUE[verdict]:
            verdict, evidence = overrides[rid]
        results.append({"id": rid, "name": SHORT.get(rid, rid), "verdict": verdict, "evidence": evidence[:220]})
        total += w * VALUE[verdict]
        weight += w
    quality = 10 * total / weight if weight else 0.0
    hit = [m for m in reply.get("moves_hit") or [] if m in moves]
    missed = [m for m in moves if m not in hit]
    fidelity = 10 * len(hit) / len(moves) if moves else None
    raw = quality if fidelity is None else 0.6 * quality + 0.4 * fidelity
    words, on_topic = len(text.split()), reply.get("on_topic") is not False
    if not on_topic or words < 25:
        raw = min(raw, 2)
    elif words < 60 and len(chosen) > 4:
        raw = min(raw, 5)
    final = max(0, min(10, round(raw)))
    return {"score": final, "quality": round(quality, 1), "fidelity": None if fidelity is None else round(fidelity, 1),
            "rules": results, "moves_hit": hit, "moves_missed": missed, "on_topic": on_topic,
            "one_fix": reply.get("one_fix"), "best_line": reply.get("best_line"),
            "verdict": "Strong Hire" if final >= 9 else "Hire" if final >= 7 else "Lean No Hire" if final >= 5 else "No Hire"}
