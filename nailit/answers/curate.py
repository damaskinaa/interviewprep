"""Clean the rehearsal deck: drop off-target cards, fold near-duplicate questions into one card.

Decisions live in data/curation.json (reviewed by hand): "drop" lists questions that don't belong in a non-coding
ops / programme deck (system design, networking, questions about interviewing itself, fragments); "merge" maps a
duplicate question to the card it folds into. A folded card's question becomes a variant of the kept card, and its
answer is kept under "merged" so nothing is lost. A backup of the deck is written first.

    uv run python -m nailit.answers.curate            # apply
    uv run python -m nailit.answers.curate --check    # report only
"""
import argparse
import json
import re
import shutil
import time
from pathlib import Path

from nailit.answers.generate import DECK

CURATION = Path(__file__).resolve().parent / "data" / "curation.json"

# Questions that never belong in this deck, whatever the harvest finds (used by the generator too).
OFF_TOPIC = re.compile(
    r"\bdesign (a|an) .*(system|service|shortener)|url shorten|\btcp\b|\budp\b|\bhttp\b|\bdns\b|load balanc|"
    r"\bbig[- ]o\b|linked list|binary tree|leetcode|\bsql query\b|"
    r"behaviou?ral interview questions|interview questions\?|prepare for .*interview|hiring strategy|"
    r"^why is .* (important|crucial)|^how important is ", re.I)


def is_fragment(question):
    """Headings and stubs scraped as questions ('Tight Deadlines', 'Tell me about a time when...')."""
    q = question.strip()
    return q.endswith("...") or q.endswith("…") or (len(q.split()) <= 4 and not q.endswith("?") and not
                                                    re.match(r"(tell|describe|walk|give|share|explain|how|why|what)\b", q, re.I))


def apply(deck, rules):
    by_q = {c["question"]: c for c in deck["cards"]}
    dropped = [q for q in rules["drop"] if by_q.pop(q, None)]
    merged = 0
    for child, parent in rules["merge"].items():
        if child in by_q and parent in by_q:
            c, p = by_q.pop(child), by_q[parent]
            p["variants"] = list(dict.fromkeys((p.get("variants") or []) + [child] + (c.get("variants") or [])))
            p.setdefault("merged", []).append({"question": child, "answer": c["answer"], "story": c.get("story")})
            p["frequency"] = (p.get("frequency") or 1) + (c.get("frequency") or 1)
            merged += 1
    auto = [q for q in list(by_q) if OFF_TOPIC.search(q) or is_fragment(q)]
    for q in auto:
        by_q.pop(q)
    deck["cards"] = sorted(by_q.values(), key=lambda c: -(c.get("frequency") or 1))
    return dropped + auto, merged


def main():
    parser = argparse.ArgumentParser(description="Clean the rehearsal deck")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    deck = json.loads(DECK.read_text())
    before = len(deck["cards"])
    dropped, merged = apply(deck, json.loads(CURATION.read_text()))
    print(f"{before} cards → {len(deck['cards'])}: dropped {len(dropped)}, folded {merged} duplicates into variants")
    for q in dropped:
        print("  dropped:", q)
    if not args.check:
        backup = DECK.with_name(f"deck_before_curate_{time.strftime('%Y%m%d_%H%M')}.json")
        shutil.copy(DECK, backup)
        DECK.write_text(json.dumps(deck, indent=1))
        print(f"saved; backup → {backup.name}")


if __name__ == "__main__":
    main()
