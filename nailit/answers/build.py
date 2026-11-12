"""Deck builder v5: cards by competency, written and judged against the rubric, with gates that code enforces.

For each core competency it picks the distinct angles interviewers use, assigns model stories so they are spread
across the deck, writes two drafts with the competency's own rubric rule in the prompt, has two judges give
rule-by-rule verdicts, polishes the winner, then runs the gates:
  numbers    every number must come from the story or the persona (one repair, then the card is flagged)
  tells      no sentence that names the answer's structure
  endings    lesson sentences rotate their shape, so answers don't all close with the same formula
  rule score the finished answer is scored by the calibrated scorer; under 8 gets one repair

    uv run python -m nailit.answers.build --plan            # show the plan (cheap: angle and story calls only)
    uv run python -m nailit.answers.build --only failure,weakness,why_company   # build some competencies
    uv run python -m nailit.answers.build                   # build every core competency (resumes)

Output: ~/NailIt/library/model_level/deck.json (generation 2 cards replace older cards of the same competency).
"""
import argparse
import json
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor


from nailit import guards, scoring
from nailit.answers import competencies as comp_mod
from nailit.answers.generate import (DECK, DRAFTER, ML, PERSONA, TELLS, WRITER, attach_samples, chat, direct_rule,
                                     key_moves, story_bank)

PLAN = ML / "harvest" / "plan_v5.json"
SECOND_JUDGE = "tx:z-ai/glm-5.3"
PERSONA_FACTS = (" Fixed persona facts, the same in every answer: eight years in service delivery and operations; "
                 "current scope three team leads and about 40 specialists across EMEA, NA and APAC.")
SPOKEN = ("Write it exactly as it would be said aloud by a calm, senior candidate: plain spoken English, short sentences, "
          "no buzzwords, no self-praise adjectives, no headings or markup. Never name the structure out loud (no "
          "'the trade-off was', 'the result of the result', 'the lesson I learned', 'the key insight', 'to summarise'). "
          "Do not open by repeating the question. Show the trade-off in natural words ('I could have …, but …').")
# How the closing habit sentence starts; rotated per card so the deck doesn't end every answer the same way.
ENDINGS = ["Start the last sentence with 'Now I'", "Start the last sentence with 'That's why I'",
           "End on a present-tense habit with no time marker at the start (for example 'I open every review with …')",
           "Start the last sentence with 'These days'", "Start the last sentence with 'I still'",
           "Start the last sentence with 'It changed how I'", "Start the last sentence with 'Ever since,'",
           "End with what you do before anything else in the same situation ('The first thing I do in …')"]
COMPANIES = {
    "amazon": {"name": "Amazon", "language": "Leadership Principles: Customer Obsession, Ownership, Deliver Results, Dive Deep",
               "fact": "Andy Jassy's April 2026 shareholder letter puts delivery speed at the centre of the next phase: more than "
                       "85 same-day fulfilment centres in the US"},
    "aws": {"name": "AWS", "language": "Leadership Principles; operational excellence; customers' trust in reliability",
            "fact": "AWS has said demand for capacity is running ahead of what it can supply through 2026, and that it plans to "
                    "double its power capacity by the end of 2027"},
    "google": {"name": "Google", "language": "Googleyness, comfort with ambiguity, data-led decisions",
               "fact": "Google reported cutting the unit cost of serving Gemini by 78% over 2025 through efficiency work, while "
                       "Cloud demand is outrunning its capacity"},
    "meta": {"name": "Meta", "language": "move fast, focus on impact, be direct",
             "fact": "Meta's AI tools for businesses were handling about 10 million conversations a week by spring 2026, while "
                     "advertising remains its main growth engine and efficiency is a stated priority"},
    "pfizer": {"name": "Pfizer", "language": "Pfizer's values: Courage, Excellence, Equity, Joy; patients first",
               "fact": "Pfizer is on track for about 7.2 billion dollars of net cost savings by the end of 2026, with manufacturing "
                       "optimisation and scaling AI across the business among its named priorities"},
}
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "eighteen": 18,
         "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
WORD_NUMBER = re.compile(r"\b(" + "|".join(WORDS) + r")(?:[- ](one|two|three|four|five|six|seven|eight|nine))?\b"
                         r"(\s+per\s*cent|\s+percent)?", re.I)
GENERIC = {"1", "2", "3", "30", "60", "90", "100", "100%"}  # ordinals, 30-60-90 plans, "100%": not claims


def digits(text):
    """Number words as digits, so 'forty specialists' and '40 specialists' are the same fact to the gate."""
    def swap(m):
        value = WORDS[m.group(1).lower()] + (WORDS[m.group(2).lower()] if m.group(2) else 0)
        return f"{value}%" if m.group(3) else str(value)
    return WORD_NUMBER.sub(swap, text or "")


def invented(text, *sources):
    found = guards.invented_numbers(digits(text), *(digits(s) for s in sources))
    return [n for n in found if n.strip() not in GENERIC]


# ---------- plan: angles per competency, stories spread across the deck ----------

def target_angles(mentions):
    return 4 if mentions >= 150 else 3 if mentions >= 80 else 2 if mentions >= 40 else 1


def angles(comp, items, k, existing=()):
    """The k distinct angles interviewers use for this competency, each with the wordings that belong to it."""
    listing = "\n".join(f"{i}. ({q['frequency']}) {q['question']}" for i, q in enumerate(items[:140]))
    reply = chat(DRAFTER, f"Competency: {comp['name']} — tests: {comp['tests']}.\nBelow are interview questions for it, with how "
                          f"many sources ask each.\n{listing}\n\n" +
                          ("These angles already have a card; do not pick them or rewordings of them, and leave their "
                           "wordings unassigned:\n" + "\n".join("- " + e for e in existing) + "\n\n" if existing else "") +
                          f"Pick the {k} most important DISTINCT angles: questions that need a "
                          "genuinely different answer from each other, not rewordings. Prefer the most-asked. Then assign every "
                          "listed question number to the angle it is closest to.\nReply JSON {\"angles\": [{\"question\": "
                          "\"the canonical wording, exactly as listed\", \"members\": [numbers]}]}", json_mode=True) or {}
    out = []
    for a in (reply.get("angles") or [])[:k]:
        members = [items[i] for i in a.get("members") or [] if isinstance(i, int) and i < len(items)]
        lead = next((q for q in items if q["question"] == a.get("question")), members[0] if members else None)
        if lead:
            out.append({"question": lead["question"],
                        "variants": [m["question"] for m in members if m["question"] != lead["question"]],
                        "frequency": sum(m["frequency"] for m in members) or lead["frequency"]})
    out = [a for n, a in enumerate(out) if (n == 0 and not existing) or a["frequency"] >= 8]  # a rare angle isn't worth a card
    out = [a for a in out if a["question"] not in existing]
    if existing:
        return out
    return out or [{"question": items[0]["question"], "variants": [q["question"] for q in items[1:40]],
                    "frequency": sum(q["frequency"] for q in items)}]


def make_plan(only=None, legacy=False):
    """Angles for every competency (extending what an earlier run planned, never redoing it), then stories."""
    comps, _ = comp_mod.load()
    canon = json.loads((ML / "harvest" / "canonical.json").read_text())
    mapping = json.loads(comp_mod.MAP.read_text())
    plan = json.loads(PLAN.read_text()) if PLAN.exists() else {}
    todo = [c for c in comps if not only or c["id"] in only]

    def one(comp):
        items = sorted((q for q in canon if mapping.get(q["question"]) == comp["id"]), key=lambda q: -q["frequency"])
        mentions = sum(q["frequency"] for q in items)
        have = plan.get(comp["id"]) or []
        if comp.get("per_company"):
            if have:
                return comp["id"], []
            generic = {"question": "Why do you want to work here?", "variants": [q["question"] for q in items[:40]],
                       "frequency": mentions}
            return comp["id"], [generic] + [{"question": f"Why {c['name']}?", "variants": [], "frequency": mentions,
                                             "company": cid} for cid, c in COMPANIES.items()]
        missing = target_angles(mentions) - len(have)
        if missing <= 0 or not items:
            return comp["id"], []
        return comp["id"], angles(comp, items, missing, tuple(a["question"] for a in have))

    with ThreadPoolExecutor(6) as pool:
        for cid, found in pool.map(one, todo):
            if found:
                plan[cid] = (plan.get(cid) or []) + found
                PLAN.write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    if legacy and DECK.exists():  # older cards no new angle covers are rebuilt through the same pipeline, as they stand
        planned = {a["question"] for found in plan.values() for a in found}
        covered = planned | {v for found in plan.values() for a in found for v in a.get("variants") or []}
        ids = {c["id"] for c in comps}
        for old in json.loads(DECK.read_text())["cards"]:
            if old.get("generation") != 2 and old["question"] not in covered and old.get("competency") in ids:
                plan.setdefault(old["competency"], []).append({"question": old["question"], "variants": old.get("variants") or [],
                                                               "frequency": old.get("frequency", 1), "legacy": True})
        PLAN.write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    need = [{**a, "competency": cid} for cid, found in plan.items() for a in found if "stories" not in a]
    if need:
        used = {}
        for found in plan.values():
            for a in found:
                for sid in (a.get("stories") or [])[:1]:
                    used[sid] = used.get(sid, 0) + 1
        by_id = {c["id"]: c for c in comps}
        for start in range(0, len(need), 45):
            batch = need[start:start + 45]
            assign_stories(batch, by_id, used)
            for card in batch:
                for a in plan[card["competency"]]:
                    if a["question"] == card["question"]:
                        a["stories"] = card["stories"]
                for sid in card["stories"][:1]:
                    used[sid] = used.get(sid, 0) + 1
        PLAN.write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    return [{**a, "competency": cid} for cid, found in plan.items() for a in found if not only or cid in only]


def assign_stories(cards, comps, used=None):
    """One call assigns stories to every card at once, so no story carries half the deck."""
    stories = story_bank()
    bank = "\n".join(f"[{k}] " + re.sub(r"\s+", " ", v)[:380] for k, v in stories.items())
    listing = "\n".join(f"{i}. [{comps[c['competency']]['name']}] {c['question']}" for i, c in enumerate(cards))
    reply = chat(WRITER, f"{PERSONA}\n\nStory bank:\n{bank}\n\nInterview questions, by number:\n{listing}\n\n"
                         + (f"Stories already used elsewhere in the deck (times as first choice): {used}. Prefer stories used "
                            "less.\n\n" if used else "") +
                         "For each question choose the story that answers it best and a different second choice. Spread the "
                         "stories: no story may be the first choice for more than 4 questions, so that a candidate who is asked "
                         "five questions in a row tells five different stories. Use \"none\" only for questions that need no "
                         "story at all (why this company, salary, your questions for them).\n"
                         "Reply JSON {\"0\": [\"M..\", \"M..\"], \"1\": [...]} with every question number.",
                 json_mode=True, role="writer") or {}
    for i, card in enumerate(cards):
        picks = [s for s in reply.get(str(i)) or [] if s in stories]
        card["stories"] = picks[:2]


# ---------- one card ----------

def rules_text(card):
    chosen, all_rules = scoring.rule_set(card), scoring.rules()
    return chosen, "\n".join(f"- {all_rules.get(rid) or scoring.SHORT.get(rid, rid)}" for rid in chosen)


def brief(card, comp, story, index):
    """Everything a writer needs for this card: what is tested, the rules, the facts allowed, the length."""
    chosen, rules = rules_text(card)
    is_story = "R1.4" in chosen
    company = COMPANIES.get(card.get("company") or "")
    parts = [PERSONA + PERSONA_FACTS, f"Question: {card['question']}",
             f"What the interviewer is testing: {comp['tests']}.",
             "Rules this answer must satisfy (from the candidate's coaching manuals):\n" + rules, SPOKEN]
    if company:
        parts.append(f"The company is {company['name']}. Open with THEIR need, using this real, recent fact: {company['fact']}. "
                     f"Say it as something you noticed, in one sentence. Then your proof in two or three sentences, then one "
                     f"sentence on who you are. Use the company's own language where it fits naturally: {company['language']}. "
                     "Do not flatter the company or praise its mission.")
    elif card["competency"] == "why_company":
        parts.append("No company is named, so write the reusable shell: sentence one states the kind of need this employer has "
                     "(mark the place for a company fact with the words 'I noticed that' and a typical example), then proof, "
                     "then who you are.")
    special = direct_rule(card["question"])
    if special:
        parts.append("Specific instructions for this question: " + special)
    if is_story:
        parts.append(f"Length: 150 to 200 words (75 to 90 seconds spoken). {ENDINGS[index % len(ENDINGS)]}; never use the "
                     "words 'Since then'.")
    elif card["competency"] == "tmay":
        parts.append("Length: 150 to 190 words (60 to 80 seconds). End on why this role is the next step, not on a lesson.")
    elif not special:
        parts.append("Length: 90 to 140 words. No formula ending.")
    parts.append("Facts: use ONLY facts and numbers from the persona above and the story below. Never invent a number, a "
                 "duration, a company or a product. If you need a figure the story does not give, say it without a figure.")
    for sample in (card.get("_samples") or [])[:2]:
        parts.append("A real answer to this question published by a coach or interviewer"
                     + (f" (their verdict: {sample['verdict'][:160]})" if sample.get("verdict") else "") +
                     ". Learn what it does well; do NOT copy its facts, numbers or wording:\n" + sample["answer"][:1400])
    parts.append("Story to use:\n" + (story or "(no story: answer directly from the persona)"))
    return "\n\n".join(parts)


def judge(card, text):
    """Rule-by-rule verdicts from two judges of different families; the mean quality ranks the drafts."""
    results = []
    for model, timeout in ((None, 40), (SECOND_JUDGE, 240)):
        try:
            results.append(_score(card, text, model, timeout))
        except Exception:  # noqa: BLE001 - one judge failing must not lose the card
            continue
    if not results:
        return 0.0, []
    failed = {}
    for r in results:
        for rule in r["rules"]:
            if rule["verdict"] != "pass":
                failed[rule["id"]] = f"{rule['name']} ({rule['verdict']})"
    return sum(r["quality"] for r in results) / len(results), list(failed.values())


def _score(card, text, model, timeout):
    return scoring.score({**card, "answer": "", "moves": []}, text, level=2, judge=model, timeout=timeout)


def gate_numbers(card, text, story):
    extra = invented(text, story or "", PERSONA + PERSONA_FACTS, COMPANIES.get(card.get("company") or "", {}).get("fact", ""),
                     direct_rule(card["question"]) or "")
    if not extra:
        return text, []
    fixed = chat(DRAFTER, "This spoken interview answer contains numbers that are not in its source story: "
                          f"{extra}. Rewrite only the sentences that contain them so they state the same point with a number "
                          "from the story, or with no number. Change nothing else.\n\nStory:\n" + (story or "(none)") +
                          "\n\nAnswer:\n" + text) or text
    return fixed, invented(fixed, story or "", PERSONA + PERSONA_FACTS,
                           COMPANIES.get(card.get("company") or "", {}).get("fact", ""), direct_rule(card["question"]) or "")


def build_card(card, comps, stories, index):
    comp = comps[card["competency"]]
    card = {**card, "type": comp["group"]}
    picks = [s for s in card.get("stories") or [] if s in stories]
    if not picks and card["competency"] in ("why_company", "why_you", "why_role") and "M12" in stories:
        picks = ["M12"]  # the persona's fit story is the proof in every why-us answer
    picks = picks or [None]
    drafts = []
    for n, sid in enumerate((picks + picks)[:2]):
        text = chat(DRAFTER, brief(card, comp, stories.get(sid), index + n) +
                    ("\n\nThis is a second version: take a different opening and emphasis from the obvious one." if n else ""))
        if text:
            text, _ = gate_numbers(card, text, stories.get(sid))
            quality, failed = judge(card, text)
            drafts.append({"text": text, "story": sid, "quality": quality, "failed": failed})
    if not drafts:
        return None
    drafts.sort(key=lambda d: -d["quality"])
    best = drafts[0]
    story = stories.get(best["story"])
    final = chat(WRITER, brief(card, comp, story, index) + "\n\nA draft that scored best with two judges:\n" + best["text"] +
                 "\n\nRules the judges did not fully pass: " + (", ".join(best["failed"]) or "none") +
                 "\n\n1. Produce the final spoken answer: fix those rules, keep the story and every fact and number, add none.\n"
                 "2. As a Bar Raiser, ask the 3 hardest follow-ups (one 'what would you do differently', one probing the "
                 "number or how it was measured, one challenging the scope or the decision) and give the candidate's best "
                 "spoken reply to each: 30 to 60 words, consistent with the answer, no new numbers.\n"
                 "Reply JSON {\"answer\": \"...\", \"followups\": [{\"q\": \"...\", \"a\": \"...\"}]}",
                 json_mode=True, role="writer") or {}
    answer = (final.get("answer") or "").strip() or best["text"]
    answer, leftover = gate_numbers(card, answer, story)
    if TELLS.search(answer) or "Since then" in answer:
        answer = chat(DRAFTER, "Rewrite only the sentences in this spoken answer that name its own structure or start with "
                               "'Since then'. Keep every fact and number.\n\n" + answer) or answer
    result = _score(card, answer, None, 60)
    if result["quality"] < 8 and best["quality"] > result["quality"]:
        answer, result, leftover = best["text"], _score(card, best["text"], None, 60), []
    moves, hook = key_moves(card["question"], answer)
    slug = re.sub(r"[^a-z0-9]+", "_", card["question"].lower())[:60].strip("_")
    return {"id": slug, "question": card["question"], "variants": card.get("variants") or [],
            "frequency": card.get("frequency", 1), "competency": card["competency"], "company": card.get("company"),
            "type": {"opening": "opening", "close": "closing"}.get(comp["group"], "behavioural")
            if "R1.4" in scoring.rule_set(card) or comp["group"] in ("opening", "close") else "hard_skills",
            "answer": answer, "story": best["story"], "origin": "generated", "generation": 2,
            "quality": result["quality"], "rules": result["rules"], "gate_numbers": leftover,
            "win_rate": 1.0, "why_it_won": [], "candidates": len(drafts), "runner_up": drafts[1]["text"] if len(drafts) > 1 else None,
            "moves": moves, "hook": hook, "followups": (final.get("followups") or [])[:3],
            "amazon": comp.get("amazon") or [], "google": comp.get("google") or [], "practice_only": True,
            "roles": comp.get("roles") or [],
            "evidence": [{"source": s.get("source"), "verdict": (s.get("verdict") or "")[:200], "excerpt": s["answer"][:400]}
                         for s in (card.get("_samples") or [])[:2]],
            "refresh_note": ("Before a real interview, replace the company fact with one from the last 30 days."
                             if card.get("company") else None)}


def save(deck, card):
    """A generation-2 card replaces any older card with the same question; older cards of its competency are retired
    once the competency has all its new cards (done in main)."""
    same = lambda q: re.sub(r"[^a-z0-9]+", " ", q.lower()).strip()  # "…yourself." and "…yourself" are one question
    replaced = [c for c in deck["cards"] if same(c["question"]) == same(card["question"]) and c.get("company") == card.get("company")]
    deck["retired"] = (deck.get("retired") or []) + [c for c in replaced if c.get("answer") != card.get("answer")]
    deck["cards"] = [c for c in deck["cards"] if c not in replaced] + [card]
    tmp = DECK.with_name(DECK.name + ".tmp")  # write then rename: a killed build can't leave half a deck
    tmp.write_text(json.dumps(deck, indent=1, ensure_ascii=False))
    tmp.replace(DECK)


def main():
    from nailit.config import load_secrets
    load_secrets()
    parser = argparse.ArgumentParser(description="Build the deck by competency")
    parser.add_argument("--only", default="", help="comma-separated competency ids")
    parser.add_argument("--plan", action="store_true", help="show the plan and stop")
    parser.add_argument("--redo", action="store_true", help="rebuild cards that already exist as generation 2")
    parser.add_argument("--legacy", action="store_true", help="also rebuild older cards that no new angle covers")
    args = parser.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()} or None
    cards = make_plan(only, args.legacy)
    comps = {c["id"]: c for c in comp_mod.load()[0]}
    stories = story_bank()
    if args.plan:
        for c in cards:
            print(f"{c['competency']:22} {c['frequency']:4}  {c.get('stories')}  {c['question'][:80]}  (+{len(c.get('variants') or [])} wordings)")
        print(len(cards), "cards planned")
        return
    deck = json.loads(DECK.read_text()) if DECK.exists() else {"cards": []}
    backup = DECK.with_name(f"deck_before_v5_{time.strftime('%Y%m%d_%H%M')}.json")
    if DECK.exists():
        shutil.copy(DECK, backup)
    done = {c["question"] for c in deck["cards"] if c.get("generation") == 2}
    todo = [(i, c) for i, c in enumerate(cards) if args.redo or c["question"] not in done]
    print(f"{len(todo)} cards to build ({len(cards) - len(todo)} already done)", flush=True)
    attach_samples([c for _, c in todo])

    def run(job):
        index, card = job
        try:
            return card, build_card(card, comps, stories, index)
        except Exception as error:  # noqa: BLE001
            return card, f"ERROR {type(error).__name__}: {error}"

    with ThreadPoolExecutor(6) as pool:
        for card, built in pool.map(run, todo):
            if isinstance(built, dict):
                save(deck, built)
                flag = f" · numbers not in story: {built['gate_numbers']}" if built["gate_numbers"] else ""
                print(f"✓ {built['competency']:20} quality {built['quality']:4} · {built['question'][:70]}{flag}", flush=True)
            else:
                print(f"✗ {card['competency']:20} {card['question'][:60]} · {built}", flush=True)
    new = {c["question"] for c in deck["cards"] if c.get("generation") == 2}
    variants = {v for c in deck["cards"] if c.get("generation") == 2 for v in c.get("variants") or []}
    retired = [c for c in deck["cards"] if c.get("generation") != 2 and (c["question"] in variants or c["question"] in new
                                                                          or c.get("competency") == "why_company")]
    deck["retired"] = (deck.get("retired") or []) + retired  # nothing is deleted; replaced cards stay in the file
    deck["cards"] = [c for c in deck["cards"] if c not in retired]
    deck["cards"].sort(key=lambda c: (c.get("generation") != 2, -(c.get("frequency") or 1)))
    deck["built"] = time.strftime("%Y-%m-%d %H:%M")
    DECK.write_text(json.dumps(deck, indent=1, ensure_ascii=False))
    gen2 = [c for c in deck["cards"] if c.get("generation") == 2]
    print(f"deck: {len(deck['cards'])} cards ({len(gen2)} rebuilt, {len(deck['cards']) - len(gen2)} older) → {DECK}")
    print(f"backup → {backup.name}")


if __name__ == "__main__":
    main()
