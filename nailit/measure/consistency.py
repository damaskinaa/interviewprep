"""Consistency checks in code: numbers said vs stories.md facts, numbers across answers, CV vs facts, story reuse."""
import re

# id -> default label/severity; a library consistency check with the same id overrides label and severity
CHECKS = {
    "number_not_in_facts": ("Number not in stories.md", "fail"),
    "unconfirmed_fact": ("Number from an unconfirmed fact", "warn"),
    "conflicting_numbers": ("Different numbers for the same thing", "fail"),
    "cv_number_missing": ("CV number missing from stories.md", "warn"),
    "story_reused": ("Story used twice in one loop", "warn"),
}
WORDS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "fifty": 50, "hundred": 100}
NUMBER = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?|" + "|".join(WORDS) + r")(?![\w])", re.I)
STOP = {"of", "the", "a", "an", "to", "and", "or", "per", "in", "on", "at", "about", "around", "roughly", "my", "our",
        "from", "by", "with", "than", "more", "less", "over", "under", "nearly", "almost", "some", "i", "we"}
SECTION_SKIP = {"People"}  # colleague names, not facts


def _value(token):
    token = token.lower().replace(",", "")
    return float(WORDS[token]) if token in WORDS else float(token)


def _noun(word):
    word = re.sub(r"[^a-z%]", "", word.lower())
    return "percent" if word in ("%", "percent", "per") else word[:-1] if word.endswith("s") and len(word) > 3 else word


def numbers(text):
    """[(value, thing)] for each number; `thing` is the noun after it, or before 'of' ("team of 4")."""
    out = []
    for match in NUMBER.finditer(text or ""):
        value = _value(match.group(1))
        if 1900 <= value <= 2100 and float(value).is_integer():
            continue  # a year
        after = [w for w in re.findall(r"[A-Za-z%]+", text[match.end():match.end() + 40]) if w.lower() not in STOP]
        before = re.findall(r"[A-Za-z]+", text[max(0, match.start() - 30):match.start()])
        thing = ""
        if after and text[match.end():match.end() + 1] == "%":
            thing = "percent"
        elif len(before) >= 2 and before[-1].lower() == "of" and before[-2].lower() not in STOP:
            thing = _noun(before[-2])
        elif after:
            thing = _noun(after[0])
        out.append((value, thing))
    return out


def _fact_values(me):
    values = {}
    for fid, fact in ((me.get("stories") or {}).get("facts") or {}).items():
        for value, _ in numbers(fact["text"]):
            values.setdefault(value, []).append((fid, fact["status"]))
    return values


def _hit(check_id, overrides, **extra):
    label, severity = CHECKS[check_id]
    library_check = overrides.get(check_id) or {}
    return {"kind": "consistency", "id": check_id, "label": library_check.get("label", label),
            "severity": library_check.get("severity", severity), **extra}


def check(answers, me, lib=None, cv_text="", stories_used=None):
    """answers: [{"text", "question_id"?}] from one mock or loop. Returns consistency hits."""
    overrides = {c["id"]: c for c in ((lib or {}).get("detectors") or {}).get("consistency_checks") or []}
    facts = _fact_values(me)
    hits, seen = [], {}
    for index, answer in enumerate(answers):
        for value, thing in numbers(answer.get("text")):
            where = {"answer": index, "question_id": answer.get("question_id"), "number": value, "thing": thing}
            sources = facts.get(value)
            if not sources:
                hits.append(_hit("number_not_in_facts", overrides, **where))
            elif all(status != "confirmed" for _, status in sources):
                hits.append(_hit("unconfirmed_fact", overrides, facts=[f for f, _ in sources], **where))
            if thing and thing != "percent":
                seen.setdefault(thing, {}).setdefault(index, set()).add(value)
    for thing, by_answer in seen.items():
        # "from 9 to 3" in one answer and "3" in another agree; only answers with no value in common conflict
        pairs = [(a, b) for a in by_answer for b in by_answer if a < b and not by_answer[a] & by_answer[b]]
        if pairs:
            hits.append(_hit("conflicting_numbers", overrides, thing=thing,
                             said={str(i): sorted(v) for i, v in by_answer.items()}))
    profile = (me.get("profile") or {}).get("sections") or {}
    cv = "\n".join([cv_text or ""] + [text for name, text in profile.items() if name not in SECTION_SKIP])
    for value, thing in numbers(cv):
        if value not in facts:
            hits.append(_hit("cv_number_missing", overrides, number=value, thing=thing))
    for story, questions in (stories_used or {}).items():
        if len(questions) > 1:
            hits.append(_hit("story_reused", overrides, story=story, question_ids=questions))
    return hits


def library_warnings(detectors):
    """check-library: consistency checks the engine has no code for (they are shown but never computed)."""
    return [f"detectors.yaml: consistency check {c['id']} has no engine implementation (known: {', '.join(CHECKS)})"
            for c in detectors.get("consistency_checks") or [] if c["id"] not in CHECKS]
