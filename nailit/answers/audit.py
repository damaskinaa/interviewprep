"""Audit the rehearsal deck against the gates: invented numbers, structure tells, formula endings, rule scores, coverage.

    uv run python -m nailit.answers.audit
"""
import collections
import json
import re
import statistics

from nailit.answers import build, competencies
from nailit.answers.generate import DECK, PERSONA, TELLS, story_bank


def last_sentence(text):
    return re.split(r"(?<=[.!?])\s+", text.strip())[-1]


def report(cards):
    stories, comps = story_bank(), competencies.load()[0]
    out = []
    for label, group in (("rebuilt (rule-driven)", [c for c in cards if c.get("generation") == 2]),
                         ("older", [c for c in cards if c.get("generation") != 2])):
        if not group:
            continue
        numbers = [c for c in group if c.get("story") in stories and build.invented(
            c["answer"], stories[c["story"]], PERSONA + build.PERSONA_FACTS,
            build.COMPANIES.get(c.get("company") or "", {}).get("fact", ""))]
        endings = collections.Counter(" ".join(last_sentence(c["answer"]).split()[:2]) for c in group)
        words = [len(c["answer"].split()) for c in group]
        quality = [c["quality"] for c in group if c.get("quality") is not None]
        out += [f"## {label}: {len(group)} cards",
                f"- numbers not found in the story: {len(numbers)} cards" + "".join(f"\n    {c['question'][:60]}" for c in numbers[:6]),
                f"- answers that name their own structure: {sum(bool(TELLS.search(c['answer'])) for c in group)}",
                f"- most common closing-sentence opening: “{endings.most_common(1)[0][0]}” in {endings.most_common(1)[0][1]} of {len(group)}",
                f"- fewer than 3 follow-ups: {sum(len(c.get('followups') or []) < 3 for c in group)}",
                f"- length in words: median {statistics.median(words):.0f}, range {min(words)}–{max(words)}"]
        if quality:
            out.append(f"- rule score (0–10): mean {statistics.mean(quality):.1f}, lowest {min(quality)}; under 8: "
                       f"{sum(q < 8 for q in quality)}")
        used = collections.Counter(c.get("story") for c in group if c.get("story"))
        if used:
            out.append(f"- most-used story: {used.most_common(1)[0][0]} in {used.most_common(1)[0][1]} cards; {len(used)} stories in use")
    core = [c for c in comps if c.get("core")]
    have = {c.get("competency") for c in cards if c.get("generation") == 2}
    out += ["## coverage", f"- core competencies with a rebuilt card: {sum(c['id'] in have for c in core)} of {len(core)}",
            "- still missing: " + (", ".join(c["name"] for c in core if c["id"] not in have) or "none")]
    return "\n".join(out)


if __name__ == "__main__":
    print(report(json.loads(DECK.read_text())["cards"]))
