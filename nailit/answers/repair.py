"""Rewrite the deck's weakest cards with Claude Fable on your Claude plan, and keep a rewrite only when two
independent judges (other model families) score it higher.

    uv run python -m nailit.answers.repair            # every card whose rule score is under 8
    uv run python -m nailit.answers.repair --limit 5  # the five weakest
    uv run python -m nailit.answers.repair --dry      # show the before/after scores, change nothing

The writer never judges its own work: Fable writes, GLM and DeepSeek judge. Numbers must come from the card's story
(the same gate as the builder). The answer it replaces is kept in the deck file under "retired".
"""
import argparse
import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

from nailit import scoring
from nailit.answers.build import gate_numbers, judge, rules_text
from nailit.answers.generate import DECK, PERSONA, TELLS, key_moves, story_bank

FABLE = os.getenv("NAILIT_REPAIR_WRITER") or "claude-fable-5-2"
MARGIN = 0.5  # a rewrite must beat the old answer by this much, so judge noise alone never swaps a card

PROMPT = """{persona}

You are writing the model answer a top candidate would SAY in an interview. It will be spoken aloud and rehearsed.

Question: {question}

The answer is marked against these rules from the candidate's interview manuals:
{rules}

The current answer, which two judges marked down:
{answer}

Rules the judges did not fully pass, with what they saw:
{failed}

Source story (the only place facts and numbers may come from):
{story}

Write a better answer:
- It must pass every rule above, most of all the ones the judges marked down.
- Use only facts and numbers that appear in the source story or the candidate description. Invent nothing.
- 150 to 200 words, plain spoken English, first person, short sentences. No headings, no labels for its own structure,
  and do not start a sentence with "Since then".
- If the question is not a story question, answer it directly in the first sentence, then give the proof.

Reply JSON {{"answer": "..."}}"""


def weak_cards(deck, threshold):
    cards = [c for c in deck["cards"] if c.get("generation") == 2 and (c.get("quality") or 0) < threshold]
    return sorted(cards, key=lambda c: c.get("quality") or 0)


def rewrite(card, stories, writer=None, threshold=8.0):
    """Returns {"before", "after", "answer", "leftover"}, {"before", "remarked": True} when two judges already put the
    stored answer at the threshold (the stored mark came from one run and was noise), or None when the writer gave
    nothing usable."""
    from nailit.answers import ai
    before, failed = judge(card, card["answer"])
    if before >= threshold:
        return {"before": round(before, 1), "remarked": True}
    detail = "; ".join(f"{r['name']} ({r['verdict']}{': ' + r['evidence'][:80] if r.get('evidence') else ''})"
                       for r in card.get("rules") or [] if r["verdict"] != "pass") or ", ".join(failed) or "none recorded"
    story = stories.get(card.get("story") or "")
    reply = ai.chat(writer or FABLE, PROMPT.format(persona=PERSONA, question=card["question"], rules=rules_text(card)[1],
                                                   answer=card["answer"], failed=detail,
                                                   story=story or "(no story: answer from the candidate description)"),
                    json_mode=True, effort="high", retries=2) or {}
    answer = (reply.get("answer") or "").strip()
    if len(answer.split()) < 60 or TELLS.search(answer):
        return None
    answer, leftover = gate_numbers(card, answer, story)
    after, _ = judge(card, answer)
    return {"before": round(before, 1), "after": round(after, 1), "answer": answer, "leftover": leftover}


def accept(result):
    return bool(result) and not result.get("remarked") and not result["leftover"] and result["after"] >= result["before"] + MARGIN


def apply(deck, card, result):
    """Swap the answer in, keep the old version, refresh the fields that describe the answer."""
    deck.setdefault("retired", []).append({**card, "retired_reason": f"rewritten {time.strftime('%Y-%m-%d')}: "
                                                                     f"{result['before']} → {result['after']}"})
    final = scoring.score({**card, "answer": "", "moves": []}, result["answer"], level=2, timeout=60)
    moves, hook = key_moves(card["question"], result["answer"])
    card.update({"answer": result["answer"], "quality": final["quality"], "rules": final["rules"], "moves": moves,
                 "hook": hook, "gate_numbers": [], "writer": FABLE, "runner_up": None})


def main():
    from nailit.config import load_secrets
    load_secrets()
    parser = argparse.ArgumentParser(description="Rewrite weak cards with Fable; keep only judged improvements")
    parser.add_argument("--threshold", type=float, default=8.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()
    deck = json.loads(DECK.read_text())
    todo = weak_cards(deck, args.threshold)[: args.limit or None]
    stories = story_bank()
    print(f"{len(todo)} cards under {args.threshold}; writer {FABLE}", flush=True)
    if todo and not args.dry:
        shutil.copy(DECK, DECK.with_name(f"deck_before_repair_{time.strftime('%Y%m%d_%H%M')}.json"))

    def run(card):
        try:
            return card, rewrite(card, stories, threshold=args.threshold)
        except Exception as error:  # noqa: BLE001 - one failed card must not stop the run
            return card, {"error": str(error)[:160]}

    kept = 0
    with ThreadPoolExecutor(3) as pool:
        for card, result in pool.map(run, todo):
            if result and "error" in result:
                print(f"✗ {card['question'][:60]} · {result['error']}", flush=True)
                continue
            if result and result.get("remarked"):
                print(f"= fine as is, two judges give {result['before']} (stored {card.get('quality')}) · {card['question'][:50]}", flush=True)
                if not args.dry:
                    card.update({"quality": result["before"], "judged_by": 2})
                    DECK.write_text(json.dumps(deck, indent=1, ensure_ascii=False))
                continue
            ok = accept(result)
            note = "no usable rewrite" if not result else f"{result['before']} → {result['after']}" + (
                f" · numbers not in story {result['leftover']}" if result["leftover"] else "")
            print(f"{'✓ kept   ' if ok else '– skipped'} {note:14} · {card['question'][:64]}", flush=True)
            if ok and not args.dry:
                apply(deck, card, result)
                DECK.write_text(json.dumps(deck, indent=1, ensure_ascii=False))
                kept += 1
    print(f"{kept} of {len(todo)} cards replaced", flush=True)


if __name__ == "__main__":
    main()
