"""Does the rehearsal scorer tell strong attempts from weak ones? Builds test attempts from deck cards and checks the scores.

For each sampled card it scores six attempts whose rank is known in advance:
  model      the model answer word for word                      expect 9-10
  paraphrase the same content in different words                 expect 8-10
  runner_up  a different decent answer to the same question      expect 4-8
  weak       same story told badly: context first, "we", no numbers, no result, rambling   expect <= 5
  off_topic  a strong answer to a different question             expect <= 3
  fragment   one vague sentence                                  expect <= 2
A scorer that can't keep this order isn't measuring anything. Each attempt is scored twice to measure wobble.

    uv run python -m nailit.answers.calibrate --cards 4
"""
import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

EXPECT = {"model": (9, 10), "paraphrase": (8, 10), "runner_up": (4, 8), "weak": (0, 5), "off_topic": (0, 3), "fragment": (0, 2)}


def attempts_for(card, other, ai, writer):
    para = ai.chat(writer, "Rewrite this spoken interview answer in different words and sentence order, as another person "
                           "would naturally say it. Keep every fact, number, decision and the lesson. Same length.\n\n" + card["answer"])
    weak = ai.chat(writer, "Rewrite this interview answer as a nervous, weak candidate would say it: start with long background, "
                           "say 'we' for every decision, remove every number and the result, no trade-off, no lesson, add hedges "
                           "('kind of', 'I think', 'basically'), ramble. About the same length.\n\n" + card["answer"])
    return {"model": card["answer"], "paraphrase": para, "runner_up": card.get("runner_up") or "", "weak": weak,
            "off_topic": other["answer"], "fragment": "I think I usually handle that well by communicating with the team."}


def main():
    from nailit import rehearse
    from nailit.answers import ai, generate
    from nailit.config import load_secrets
    load_secrets()
    parser = argparse.ArgumentParser()
    parser.add_argument("--cards", type=int, default=4)
    parser.add_argument("--out", default="")
    parser.add_argument("--scorer", default="", help="model to test as the scorer (default: the app's scorer)")
    parser.add_argument("--attempts", default="", help="JSON file of attempts saved by an earlier run (same test for every scorer)")
    parser.add_argument("--save-attempts", default="")
    args = parser.parse_args()
    if args.scorer:
        rehearse.SCORER = args.scorer
    deck = [c for c in rehearse.load_deck()["cards"] if c.get("runner_up") and c.get("type") == "behavioural"]
    step = max(1, len(deck) // args.cards)
    sample = deck[::step][: args.cards]
    jobs, saved = [], json.load(open(args.attempts)) if args.attempts else {}
    by_q = {c["question"]: c for c in rehearse.load_deck()["cards"]}
    if saved:
        sample = [by_q[q] for q in saved if q in by_q]
    for i, card in enumerate(sample):
        other = deck[(i * step + step // 2 + 7) % len(deck)]
        made = saved.get(card["question"]) or attempts_for(card, other, ai, generate.DRAFTER)
        saved[card["question"]] = made
        for kind, text in made.items():
            if text:
                jobs += [(card, kind, text, run) for run in (1, 2)]
    if args.save_attempts:
        json.dump(saved, open(args.save_attempts, "w"), indent=1)
    times = []

    def score(job):
        card, kind, text, run = job
        try:
            started = time.time()
            value = rehearse._score(card, text, None, 0, log=False)["score"]
            times.append(time.time() - started)
            return card["question"], kind, run, value
        except Exception as error:  # noqa: BLE001
            return card["question"], kind, run, f"ERROR {error}"

    with ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(score, jobs))
    by_kind, fails, wobble = {}, [], []
    for question, kind, run, value in rows:
        by_kind.setdefault(kind, []).append(value)
    for (question, kind) in dict.fromkeys((q, k) for q, k, _, _ in rows):
        pair = [v for q, k, _, v in rows if (q, k) == (question, kind) and isinstance(v, int)]
        if len(pair) == 2:
            wobble.append(abs(pair[0] - pair[1]))
        lo, hi = EXPECT[kind]
        if any(isinstance(v, int) and not lo <= v <= hi for v in pair) or len(pair) < 2:
            fails.append((kind, pair, question[:60]))
    print(f"scorer: {rehearse.SCORER} · {len(sample)} cards · {len(rows)} scored attempts")
    for kind, (lo, hi) in EXPECT.items():
        values = [v for v in by_kind.get(kind, []) if isinstance(v, int)]
        if values:
            print(f"  {kind:10} expect {lo}-{hi:<2}  got {sorted(values)}  mean {statistics.mean(values):.1f}")
    print(f"  wobble between two runs of the same attempt: mean {statistics.mean(wobble):.2f}, max {max(wobble)}")
    if times:
        print(f"  seconds per score: median {statistics.median(times):.1f}, slowest {max(times):.1f}")
    print(f"  out of range: {len(fails)} of {len(set((q, k) for q, k, _, _ in rows))}")
    for kind, pair, question in fails:
        print(f"    ✗ {kind:10} {pair}  {question}")
    if args.out:
        json.dump(rows, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
