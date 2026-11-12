"""The competency map: every harvested question is assigned to one of about 40 competencies.

You can't rehearse 2,874 questions, and you don't need to: interviewers test a few dozen competencies in many
wordings. This maps each question to the competency it tests, then reports coverage: how much of what gets asked
(weighted by how many sources ask it) lands on a competency the deck already has a card for.

    uv run python -m nailit.answers.competencies            # classify (cached) and print the coverage report
"""
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml

from nailit.answers.generate import DECK, HELPER, ML

DATA = Path(__file__).resolve().parent / "data" / "competencies.yaml"
MAP = ML / "harvest" / "question_map.json"
SPECIAL = {"off_topic": "not for a non-coding operations / programme role (coding, system design, networking), or not an "
                        "interview question at all (a heading, advice to candidates, a question about interviewing)",
           "other": "a real interview question for these roles that fits none of the competencies"}


def load():
    data = yaml.safe_load(DATA.read_text())
    return data["competencies"], data["groups"]


def _prompt(comps, batch):
    lines = [f"{c['id']}: {c['name']} — {c['tests']}. e.g. {c['examples'][0]}" for c in comps]
    lines += [f"{k}: {v}" for k, v in SPECIAL.items()]
    numbered = "\n".join(f"{i}. {q}" for i, q in enumerate(batch))
    return ("Interview questions for senior operations, service delivery and programme management roles are listed below. "
            "Assign each to the ONE competency it mainly tests.\n\nCompetencies:\n" + "\n".join(lines) +
            f"\n\nQuestions:\n{numbered}\n\nReply JSON {{\"map\": {{\"0\": \"competency_id\", \"1\": \"...\"}}}} with every "
            "question number as a key and only ids from the list as values.")


def classify(questions, comps):
    from nailit.answers import ai
    known = json.loads(MAP.read_text()) if MAP.exists() else {}
    todo = [q for q in questions if q not in known]
    valid = {c["id"] for c in comps} | set(SPECIAL)
    batches = [todo[i:i + 40] for i in range(0, len(todo), 40)]

    def run(batch):
        for _ in range(2):
            reply = (ai.chat(HELPER, _prompt(comps, batch), json_mode=True) or {}).get("map") or {}
            found = {batch[int(k)]: v for k, v in reply.items() if str(k).isdigit() and int(k) < len(batch) and v in valid}
            if len(found) >= len(batch) * 0.9:
                return found
        return found

    with ThreadPoolExecutor(8) as pool:
        for n, found in enumerate(pool.map(run, batches), 1):
            known.update(found)
            MAP.write_text(json.dumps(known, indent=0, ensure_ascii=False))
            print(f"  classified batch {n}/{len(batches)}", flush=True)
    return known


def report(canon, mapping, comps, groups, deck_cards):
    deck_qs = {}
    for card in deck_cards:
        for q in [card["question"], *(card.get("variants") or [])]:
            deck_qs[q.lower()] = card
    by, unmapped = {c["id"]: {"freq": 0, "n": 0, "cards": set(), "top": []} for c in comps}, 0
    special = {k: {"freq": 0, "n": 0, "top": []} for k in SPECIAL}
    for item in canon:
        cid = mapping.get(item["question"])
        if not cid:
            unmapped += 1
            continue
        bucket = by.get(cid) or special[cid]
        bucket["freq"] += item["frequency"]
        bucket["n"] += 1
        if len(bucket["top"]) < 3:
            bucket["top"].append(item["question"])
    for card in deck_cards:
        cid = mapping.get(card["question"])
        if cid in by:
            by[cid]["cards"].add(card["question"])
    asked = sum(b["freq"] for b in by.values()) + special["other"]["freq"]
    covered = sum(b["freq"] for b in by.values() if b["cards"])
    out = [f"questions mapped: {len(canon) - unmapped} of {len(canon)}",
           f"off-topic (coding, system design, not a question): {special['off_topic']['n']} questions",
           f"fit no competency ('other'): {special['other']['n']} questions, {special['other']['freq']} mentions",
           f"coverage: {covered / asked:.0%} of everything asked (by mentions) lands on a competency with a deck card", ""]
    for gid, gname in groups.items():
        out.append(f"## {gname}")
        for c in comps:
            if c["group"] != gid:
                continue
            b = by[c["id"]]
            flag = "" if b["cards"] else "   ← NO CARD"
            out.append(f"  {c['name'][:46]:46} {b['freq']:5} mentions · {b['n']:4} wordings · {len(b['cards']):2} cards{flag}")
    out += ["", "## Examples that fit no competency"] + [f"  {q}" for q in special["other"]["top"]]
    return "\n".join(out), by


def main():
    from nailit.config import load_secrets
    load_secrets()
    comps, groups = load()
    canon = json.loads((ML / "harvest" / "canonical.json").read_text())
    deck = json.loads(DECK.read_text())["cards"] if DECK.exists() else []
    questions = list(dict.fromkeys([c["question"] for c in canon] + [c["question"] for c in deck]))
    mapping = classify(questions, comps)
    text, _ = report(canon, mapping, comps, groups, deck)
    (ML / "harvest" / "coverage.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main()
