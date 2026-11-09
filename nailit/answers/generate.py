"""Model answers for the rehearsal deck: write candidates, rank them in a two-judge tournament, keep the winner.

Every answer is told by the same practice-only model candidate and built on the shared model story bank
(library/model_level/02 and 04), so the facts never contradict each other across questions. Candidates:
  A  the best-fitting model story, re-aimed at the exact question (hook, stretched stage, lesson);
  B  a second strategy (a different story, or a SEI / compressed structure);
  C  harvested real sample answers for the same question (from harvest/sample_answers.json), when any exist.
Two judges compare every pair in both orders (position bias), shorter answers are not penalised (verbosity bias).

    uv run python -m nailit.answers.generate --limit 40          # top questions by frequency
    uv run python -m nailit.answers.generate --questions library  # the library's own question bank

Output: ~/NailIt/library/model_level/deck.json (practice only: these numbers must never be used as yours).
"""
import argparse
import itertools
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nailit import library
from nailit.llm import parse_json_object

WRITER = os.getenv("NAILIT_ANSWER_WRITER") or "gpt-5.5"
JUDGES = [m.strip() for m in (os.getenv("NAILIT_JUDGES") or "gpt-5.4-mini,gpt-5-mini").split(",")]
ML = library.home() / "library" / "model_level"
DECK = ML / "deck.json"

PERSONA = ("PRACTICE-ONLY MODEL CANDIDATE: a Senior Operations / Service Delivery Manager at a vendor running "
           "partner support for a global tech platform; three team leads and about 40 specialists across EMEA, NA and "
           "APAC; owns SLAs, quarterly business reviews and the escalation path to the client's engineering teams; "
           "Six Sigma trained; no coding background. Numbers are fictional and must stay consistent with the story bank.")
STYLE = ("Write the answer exactly as spoken in an interview by a top-1% candidate: result or answer in the first "
         "sentence; at most two sentences of context; 'I' for decisions; one named trade-off or rejected option; "
         "one number with a baseline or timeframe; the result of the result; a specific lesson ('Since then, I...'); "
         "plain spoken English, no buzzwords, no self-praise adjectives, no 'we' for my decisions; 150-210 words "
         "(about 75-90 seconds) for behavioural questions, 80-140 words for direct questions. No headings, no markup.")
JUDGE_RUBRIC = ("Judge as a Bar Raiser and hiring committee would. Prefer: answer first; specific, attributable actions; "
                "decision and trade-off; numbers with context; resistance or difficulty named; result of the result; "
                "specific lesson; sounds natural when spoken; would survive follow-ups ('what would you do differently?', "
                "'where is the number?', 'how big was it?'). Penalise: generic claims, self-praise adjectives, 'we' for "
                "decisions, context-first openings, rambling, clichés. Do NOT prefer an answer because it is longer.")


def _client():
    from openai import OpenAI
    return OpenAI()


USAGE = {}


def chat(model, prompt, json_mode=False, retries=3):
    for attempt in range(retries):
        try:
            kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
            resp = _client().chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], **kwargs)
            u = USAGE.setdefault(model, [0, 0])
            u[0] += resp.usage.prompt_tokens
            u[1] += resp.usage.completion_tokens
            text = resp.choices[0].message.content or ""
            return parse_json_object(text, {}) if json_mode else text.strip()
        except Exception:  # noqa: BLE001 - retry with backoff, then give up on this call
            time.sleep(3 * (attempt + 1))
    return {} if json_mode else ""


def story_bank():
    """M-stories as {id: text}, from the model-level files."""
    stories = {}
    for name in ("02_model_stories_SDM_SOM.md", "04_model_stories_extra.md"):
        path = ML / name
        if not path.exists():
            continue
        for block in re.split(r"\n## ", path.read_text()):
            m = re.match(r"(M\d+)\s*·\s*(.+)", block)
            if m:
                stories[m.group(1)] = block.split("\n## How to")[0][:3500]
    return stories


def role_answers():
    """Existing TPM / Head of Ops model answers as {question: answer} (candidates, not winners)."""
    found = {}
    for name in ("06_model_TPM.md", "07_model_HeadOfOps.md"):
        path = ML / name
        if not path.exists():
            continue
        for block in re.split(r"\n## ", path.read_text()):
            m = re.match(r"[TH]\d+\s*·\s*\"?(.+?)\"?\s*(?:→.*)?\n", block)
            quote = "\n".join(l[1:].strip() for l in block.splitlines() if l.startswith(">"))
            if m and quote:
                found[m.group(1).strip().strip('"')] = re.sub(r"[▼‖]", "", quote).strip()
    return found


def questions(source, limit):
    if source == "library":
        lib = library.load_library()
        qs = library._questions(lib["questions"])[0]
        return [{"question": q["text"], "variants": q.get("variants") or [], "frequency": 1, "type": q.get("type"),
                 "hard": q.get("hard"), "roles": q.get("rounds") or [], "id": q["id"]} for q in qs][:limit]
    canon = json.loads((ML / "harvest" / "canonical.json").read_text())
    return canon[:limit]


def write_candidates(item, stories, existing):
    bank = "\n".join(f"[{k}] " + re.sub(r"\s+", " ", v)[:420] for k, v in stories.items())
    pick = chat(JUDGES[0], f"{PERSONA}\n\nStory bank:\n{bank}\n\nInterview question: {item['question']}\n\n"
                        "Which two stories answer this best (or 'none' if it is a direct question that needs no story, "
                        "e.g. 'why this company')? Reply JSON {\"best\":\"M..|none\",\"second\":\"M..|none\",\"type\":"
                        "\"behavioural|motivation|failure|weakness|strength|situational|planning|opening|hard_skills|"
                        "closing|negotiation|self_assessment|presentation\"}", json_mode=True) or {}
    cands = []
    for slot, story_id in (("A", pick.get("best")), ("B", pick.get("second"))):
        story = stories.get(story_id or "", "")
        strategy = ("Re-aim this story at the exact question: change the first sentence so it answers the question literally, "
                    "stretch the stage the question tests, tie the lesson to it. Keep every fact and number identical."
                    if story else "Answer directly (no story needed); be specific to an operations/programme leader.")
        if slot == "B" and not story:
            strategy = "Use a different structure from a typical answer: Statement-Explanation-Illustration, compressed and sharp."
        text = chat(WRITER, f"{PERSONA}\n\n{STYLE}\n\nQuestion: {item['question']}\n\n{strategy}\n\nStory to use:\n{story or '(none)'}")
        if text:
            cands.append({"slot": slot, "story": story_id if story else None, "text": text, "origin": "generated"})
    for q, answer in existing.items():
        if q.lower()[:60] == item["question"].lower()[:60]:
            cands.append({"slot": "E", "story": None, "text": answer, "origin": "model_level"})
    for sample in item.get("_samples", [])[:2]:
        cands.append({"slot": "R", "story": None, "text": sample["answer"][:2500], "origin": "harvested:" + sample["source"],
                      "verdict": sample.get("verdict", "")})
    return pick.get("type"), cands


def judge_pair(question, a, b, judge):
    data = chat(judge, f"{JUDGE_RUBRIC}\n\nQuestion: {question}\n\nAnswer 1:\n{a}\n\nAnswer 2:\n{b}\n\n"
                       "Which answer would more likely get a Strong Hire? Reply JSON {\"winner\":1|2,\"why\":\"one sentence\"}",
                json_mode=True) or {}
    return data.get("winner"), data.get("why", "")


def tournament(question, cands):
    wins = {i: 0 for i in range(len(cands))}
    reasons = {i: [] for i in range(len(cands))}
    for i, j in itertools.combinations(range(len(cands)), 2):
        for judge in JUDGES:
            for first, second in ((i, j), (j, i)):
                w, why = judge_pair(question, cands[first]["text"], cands[second]["text"], judge)
                if w in (1, 2):
                    winner = first if w == 1 else second
                    wins[winner] += 1
                    reasons[winner].append(why)
    order = sorted(wins, key=lambda k: -wins[k])
    total = max(1, (len(cands) - 1) * 2 * len(JUDGES))
    return [{**cands[k], "wins": wins[k], "win_rate": round(wins[k] / total, 2), "reasons": reasons[k][:3]} for k in order]


def key_moves(question, answer):
    data = chat(JUDGES[0], f"Question: {question}\nModel answer:\n{answer}\n\nList the 4-6 moves that make this answer strong, "
                           "each as a short checkable phrase a learner should reproduce (e.g. 'Opens with the result', "
                           "'Names the trade-off: speed vs adoption', 'Gives the number: backlog down a third in 6 weeks'). "
                           "Reply JSON {\"moves\":[\"...\"],\"hook\":\"the first sentence\"}", json_mode=True) or {}
    return data.get("moves") or [], data.get("hook") or answer.split(".")[0]


def build_card(item, stories, existing):
    qtype, cands = write_candidates(item, stories, existing)
    if not cands:
        return None
    ranked = tournament(item["question"], cands) if len(cands) > 1 else [{**cands[0], "wins": 0, "win_rate": 1.0, "reasons": []}]
    best = ranked[0]
    moves, hook = key_moves(item["question"], best["text"])
    return {"id": item.get("id") or re.sub(r"[^a-z0-9]+", "_", item["question"].lower())[:60].strip("_"),
            "question": item["question"], "variants": item.get("variants", [])[:5], "frequency": item.get("frequency", 1),
            "roles": item.get("roles", []), "companies": item.get("companies", []), "type": qtype or item.get("type"),
            "answer": best["text"], "story": best.get("story"), "origin": best["origin"], "win_rate": best["win_rate"],
            "why_it_won": best["reasons"], "moves": moves, "hook": hook,
            "runner_up": ranked[1]["text"] if len(ranked) > 1 else None, "candidates": len(cands),
            "practice_only": True}


def attach_samples(items):
    path = ML / "harvest" / "sample_answers.json"
    if not path.exists():
        return
    samples = json.loads(path.read_text())
    if not samples:
        return
    from nailit.answers.harvest import embed
    import numpy as np
    sv = np.array(embed([s["q"] for s in samples]), dtype="float32")
    qv = np.array(embed([i["question"] for i in items]), dtype="float32")
    sv /= np.linalg.norm(sv, axis=1, keepdims=True)
    qv /= np.linalg.norm(qv, axis=1, keepdims=True)
    sims = qv @ sv.T
    for index, item in enumerate(items):
        best = [int(k) for k in sims[index].argsort()[::-1][:2] if sims[index][k] > 0.85]
        item["_samples"] = [samples[k] for k in best if len(samples[k].get("answer", "")) > 200]


def merge_similar(items, existing, threshold=0.76):
    """Drop questions that mean the same as a more frequent one (or one already in the deck); keep their phrasing."""
    if not items:
        return items
    from nailit.answers.harvest import embed
    import numpy as np
    vecs = np.array(embed([i["question"] for i in items] + existing), dtype="float32")
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    kept, kept_vecs = [], [vecs[len(items) + k] for k in range(len(existing))]
    for index, item in enumerate(items):
        v = vecs[index]
        if kept_vecs and float(np.max(np.array(kept_vecs) @ v)) >= threshold:
            continue
        kept.append(item)
        kept_vecs.append(v)
    return kept


def main():
    parser = argparse.ArgumentParser(description="Build the rehearsal deck")
    parser.add_argument("--questions", default="harvest", choices=["harvest", "library"])
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--min-frequency", type=int, default=1)
    args = parser.parse_args()
    items = [q for q in questions(args.questions, 10_000) if q.get("frequency", 1) >= args.min_frequency][: args.limit * 3]
    deck = json.loads(DECK.read_text()) if DECK.exists() else {"cards": []}
    done = {c["question"].lower() for c in deck["cards"]}
    items = [i for i in items if i["question"].lower() not in done]
    items = merge_similar(items, [c["question"] for c in deck["cards"]])[: args.limit]
    attach_samples(items)
    stories, existing = story_bank(), role_answers()
    with ThreadPoolExecutor(6) as pool:
        for card in pool.map(lambda i: build_card(i, stories, existing), items):
            if card:
                deck["cards"].append(card)
                DECK.write_text(json.dumps(deck, indent=1))
                print(f"✓ ({card['frequency']}) {card['question'][:80]} · {card['candidates']} candidates · won {card['win_rate']:.0%} · {card['origin'][:40]}")
    deck["persona"] = PERSONA
    deck["built"] = time.strftime("%Y-%m-%d %H:%M")
    DECK.write_text(json.dumps(deck, indent=1))
    print(f"deck: {len(deck['cards'])} cards → {DECK}")
    print("tokens by model (input, output):", json.dumps(USAGE))


if __name__ == "__main__":
    main()
