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

WRITER = os.getenv("NAILIT_ANSWER_WRITER") or "claude-opus-5-5"     # final polish of the winner + follow-ups only
DRAFTER = os.getenv("NAILIT_DRAFTER") or "claude-sonnet-5-5"         # candidate drafts
JUDGES = [m.strip() for m in (os.getenv("NAILIT_JUDGES") or "claude-sonnet-5-5").split(",")]
HELPER = os.getenv("NAILIT_HELPER") or "claude-haiku-5-5"            # story pick, key moves (small structured tasks)
DEFAULT_CAP_USD = 38.0
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
         "(about 75-90 seconds) for behavioural questions, 80-140 words for direct questions. No headings, no markup. "
         "It must sound like a real person talking, never like a checklist: do NOT restate or echo the question in the "
         "first sentence; NEVER name the structure out loud (forbidden: 'the trade-off was', 'the named trade-off', "
         "'the result of the result', 'the lesson I learned', 'the key insight', 'in terms of', 'to summarise', 'STAR'). "
         "Show the trade-off and the knock-on effect in natural words ('I could have X, but…', 'which meant…').")
TELLS = re.compile(r"(trade-off was|named trade-off|result of (that|the) result|the lesson (i learned|is)|key insight|"
                   r"to summari[sz]e|in terms of|STAR|situation was|task was|action i took)", re.I)
JUDGE_RUBRIC = ("Judge as a Bar Raiser and hiring committee would. Prefer: answer first; specific, attributable actions; "
                "decision and trade-off; numbers with context; resistance or difficulty named; result of the result; "
                "specific lesson; sounds natural when spoken; would survive follow-ups ('what would you do differently?', "
                "'where is the number?', 'how big was it?'). Penalise: generic claims, self-praise adjectives, 'we' for "
                "decisions, context-first openings, rambling, clichés. Do NOT prefer an answer because it is longer.")


ROLE_SETTINGS = {"writer": ("medium", True), "drafter": ("medium", True), "judge": ("low", False), "helper": ("low", False)}


def chat(model, prompt, json_mode=False, retries=3, role="drafter"):
    from nailit.answers import ai
    effort, thinking = ROLE_SETTINGS[role]
    return ai.chat(model, prompt, json_mode=json_mode, effort=effort, thinking=thinking, retries=retries)


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
    pick = chat(HELPER, f"{PERSONA}\n\nStory bank:\n{bank}\n\nInterview question: {item['question']}\n\n"
                        "Which two stories answer this best (or 'none' if it is a direct question that needs no story, "
                        "e.g. 'why this company')? Reply JSON {\"best\":\"M..|none\",\"second\":\"M..|none\",\"type\":"
                        "\"behavioural|motivation|failure|weakness|strength|situational|planning|opening|hard_skills|"
                        "closing|negotiation|self_assessment|presentation\"}", json_mode=True, role="helper") or {}
    cands = []
    for slot, story_id in (("A", pick.get("best")), ("B", pick.get("second"))):
        story = stories.get(story_id or "", "")
        strategy = ("Re-aim this story at the exact question: change the first sentence so it answers the question literally, "
                    "stretch the stage the question tests, tie the lesson to it. Keep every fact and number identical."
                    if story else "Answer directly (no story needed); be specific to an operations/programme leader.")
        if slot == "B" and not story:
            strategy = "Use a different structure from a typical answer: Statement-Explanation-Illustration, compressed and sharp."
        text = chat(DRAFTER, f"{PERSONA}\n\n{STYLE}\n\nQuestion: {item['question']}\n\n{strategy}\n\nStory to use:\n{story or '(none)'}")
        echo = text and text.lower().startswith(" ".join(item["question"].lower().split()[3:7])[:25])
        if text and (TELLS.search(text) or echo):
            text = chat(DRAFTER, f"Rewrite this interview answer so it sounds like natural speech. Remove any phrase that names "
                                f"the answer's structure ({TELLS.pattern}) and don't open by echoing the question; open with "
                                f"the decision or result. Keep every fact and number.\n\nQuestion: {item['question']}\n\n{text}") or text
        if text:
            cands.append({"slot": slot, "story": story_id if story else None, "text": text, "origin": "generated"})
    for q, answer in existing.items():
        if q.lower()[:60] == item["question"].lower()[:60]:
            cands.append({"slot": "E", "story": None, "text": answer, "origin": "model_level"})
    for sample in item.get("_samples", [])[:1]:  # the best-matching real answer; more adds judge calls, rarely a winner
        cands.append({"slot": "R", "story": None, "text": sample["answer"][:2500], "origin": "harvested:" + sample["source"],
                      "verdict": sample.get("verdict", "")})
    return pick.get("type"), cands


def judge_pair(question, a, b, judge):
    data = chat(judge, f"{JUDGE_RUBRIC}\n\nQuestion: {question}\n\nAnswer 1:\n{a}\n\nAnswer 2:\n{b}\n\n"
                       "Which answer would more likely get a Strong Hire? Reply JSON {\"winner\":1|2,\"why\":\"one sentence\"}",
                json_mode=True, role="judge") or {}
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
    data = chat(HELPER, f"Question: {question}\nModel answer:\n{answer}\n\nList the 4-6 moves that make this answer strong, "
                           "each as a short checkable phrase a learner should reproduce (e.g. 'Opens with the result', "
                           "'Names the trade-off: speed vs adoption', 'Gives the number: backlog down a third in 6 weeks'). "
                           "Reply JSON {\"moves\":[\"...\"],\"hook\":\"the first sentence\"}", json_mode=True, role="helper") or {}
    return data.get("moves") or [], data.get("hook") or answer.split(".")[0]


def build_card(item, stories, existing):
    qtype, cands = write_candidates(item, stories, existing)
    if not cands:
        return None
    ranked = tournament(item["question"], cands) if len(cands) > 1 else [{**cands[0], "wins": 0, "win_rate": 1.0, "reasons": []}]
    best = ranked[0]
    final = chat(WRITER, f"{PERSONA}\n\n{STYLE}\n\nQuestion: {item['question']}\n\nThis answer won a judged tournament "
                         f"against {len(cands) - 1} alternatives:\n{best['text']}\n\nJudges' reasons: {best['reasons'][:2]}\n\n"
                         "1. Polish it into the final spoken answer: keep what made it win, keep the story and every fact and "
                         "number (add none), fix anything that breaks the style rules, tighten weak sentences.\n"
                         "2. As a Bar Raiser, ask the 3 hardest follow-ups (one counterfactual 'what would you do differently', "
                         "one data probe 'how did you measure / where is the number', one scope or disagreement probe), and give "
                         "the model candidate's best spoken reply to each, 30-60 words, consistent with every fact in the answer, "
                         "no new numbers unless they follow from it.\n"
                         "Reply JSON {\"answer\":\"...\",\"followups\":[{\"q\":\"...\",\"a\":\"...\"}]}",
                 json_mode=True, role="writer") or {}
    answer = (final.get("answer") or "").strip() or best["text"]
    moves, hook = key_moves(item["question"], answer)
    return {"id": item.get("id") or re.sub(r"[^a-z0-9]+", "_", item["question"].lower())[:60].strip("_"),
            "question": item["question"], "variants": item.get("variants", [])[:5], "frequency": item.get("frequency", 1),
            "roles": item.get("roles", []), "companies": item.get("companies", []),
            "type": {"behavioral": "behavioural"}.get(qtype or item.get("type"), qtype or item.get("type")),
            "answer": answer, "story": best.get("story"), "origin": best["origin"], "win_rate": best["win_rate"],
            "why_it_won": best["reasons"], "moves": moves, "hook": hook,
            "runner_up": ranked[1]["text"] if len(ranked) > 1 else None, "candidates": len(cands),
            "followups": (final.get("followups") or [])[:3], "polished_by": WRITER if final.get("answer") else None,
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
        best = [int(k) for k in sims[index].argsort()[::-1][:2] if sims[index][k] > 0.88]  # bge-small scale
        item["_samples"] = [samples[k] for k in best if len(samples[k].get("answer", "")) > 200]


def merge_similar(items, existing, threshold=0.84):  # bge-small scale (was 0.76 on OpenAI)
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


# Output tokens per call (visible text + thinking), assumed for the dry run; the live run prints measured spend.
DRY_OUT = {"writer": 2300, "drafter": 1400, "judge": 80, "helper": 250}


def dry_run(items, stories, existing, cap):
    """Run the real card logic with a fake model: exact call counts and input sizes, assumed output sizes."""
    from nailit.answers import ai
    tally = {}
    tokens = lambda text: int(len(text) / 4 * 1.3)  # chars/4, +30% for the newer Claude tokenizer (upper bound)

    def fake(model, prompt, json_mode=False, retries=3, role="drafter"):
        t = tally.setdefault((role, model), [0, 0, 0])
        t[0] += 1
        t[1] += tokens(prompt)
        t[2] += DRY_OUT[role]
        if role == "judge":
            return {"winner": 1, "why": "dry run"}
        if role == "helper":
            return {"best": next(iter(stories), "none"), "second": "none", "type": "behavioural", "moves": [], "hook": ""}
        if role == "writer":
            return {"answer": "dry run answer", "followups": []}
        return "I cut repeat contacts by a third in six weeks. " * 20

    global chat
    real, chat = chat, fake
    try:
        cards = [build_card(i, stories, existing) for i in items]
    finally:
        chat = real
    total = 0.0
    print(f"dry run: {len(items)} questions → {sum(1 for c in cards if c)} cards, "
          f"{sum(c['candidates'] for c in cards if c) / max(1, len(cards)):.1f} candidates per card")
    for (role, model), (calls, inp, out) in sorted(tally.items()):
        price = ai.PRICES.get(model, (0, 0))
        cost = (inp * price[0] + out * price[1]) / 1e6
        total += cost
        print(f"  {role:8} {model:18} {calls:5} calls  {inp:>10,} in  {out:>9,} out (assumed)  ≈ ${cost:6.2f}")
    print(f"  estimated total ≈ ${total:.2f}  (cap ${cap:.2f})")


def main():
    from nailit.config import load_secrets
    load_secrets()
    parser = argparse.ArgumentParser(description="Build the rehearsal deck")
    parser.add_argument("--questions", default="harvest", choices=["harvest", "library"])
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--min-frequency", type=int, default=1)
    parser.add_argument("--cap", type=float, default=DEFAULT_CAP_USD, help="hard spending cap in USD; the run stops there")
    parser.add_argument("--dry-run", action="store_true", help="no API calls: count calls and estimate cost")
    args = parser.parse_args()
    from nailit.answers import ai
    ai.set_cap(args.cap)
    items = [q for q in questions(args.questions, 10_000) if q.get("frequency", 1) >= args.min_frequency][: args.limit * 3]
    deck = json.loads(DECK.read_text()) if DECK.exists() else {"cards": []}
    done = {c["question"].lower() for c in deck["cards"]}
    items = [i for i in items if i["question"].lower() not in done]
    items = merge_similar(items, [c["question"] for c in deck["cards"]])[: args.limit]
    attach_samples(items)
    stories, existing = story_bank(), role_answers()
    if args.dry_run:
        return dry_run(items, stories, existing, args.cap)

    def safe(item):
        try:
            return build_card(item, stories, existing)
        except ai.BudgetExceeded:
            return "stop"

    stopped = False
    with ThreadPoolExecutor(6) as pool:
        for n, card in enumerate(pool.map(safe, items), 1):
            if card == "stop":
                if not stopped:
                    print(f"■ stopped: spending cap ${args.cap:.2f} reached")
                stopped = True
                continue
            if card:
                deck["cards"].append(card)
                DECK.write_text(json.dumps(deck, indent=1))
                print(f"✓ ({card['frequency']}) {card['question'][:80]} · {card['candidates']} candidates · won "
                      f"{card['win_rate']:.0%} · {card['origin'][:40]} · spent ${ai.spent():.2f}", flush=True)
                if n == 10:
                    print(f"  projection: ${ai.spent() / 10 * len(items):.2f} for {len(items)} cards (cap ${args.cap:.2f})", flush=True)
    deck["persona"] = PERSONA
    deck["built"] = time.strftime("%Y-%m-%d %H:%M")
    DECK.write_text(json.dumps(deck, indent=1))
    print(f"deck: {len(deck['cards'])} cards → {DECK}")
    print(ai.usage_report())


if __name__ == "__main__":
    main()
