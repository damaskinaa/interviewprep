from pathlib import Path
import json
import re

ROOT = Path(__file__).parent
GENERATED = ROOT / "doctrine" / "generated"

CHUNKS_PATH = GENERATED / "doctrine_chunks.json"
RULES_PATH = GENERATED / "doctrine_rules.json"
FULL_TEXT_PATH = GENERATED / "doctrine_full_text.json"


def load_doctrine():
    return {
        "chunks": json.loads(CHUNKS_PATH.read_text(encoding="utf8")),
        "rules": json.loads(RULES_PATH.read_text(encoding="utf8")),
        "full_text": json.loads(FULL_TEXT_PATH.read_text(encoding="utf8")),
    }


def tokenize(text):
    return set(re.findall(r"[a-zA-Z0-9%]+", text.lower()))


def retrieve_doctrine(query, limit=8):
    doctrine = load_doctrine()
    q = tokenize(query)

    scored = []
    for chunk in doctrine["chunks"]:
        tokens = tokenize(chunk["heading"] + " " + chunk["text"])
        score = len(q & tokens)

        bonus_terms = [
            "result",
            "tradeoff",
            "failure",
            "stakeholder",
            "metric",
            "influence",
            "authority",
            "technical",
            "programme",
            "google",
            "hero",
            "crossroads",
            "ownership",
        ]

        for term in bonus_terms:
            if term in query.lower() and term in chunk["text"].lower():
                score += 4

        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    return {
        "doctrine_version": doctrine["rules"]["version"],
        "hard_rules": doctrine["rules"]["hard_rules"],
        "retrieved_chunks": [item for _, item in scored[:limit]],
        "full_doctrine_available": True,
    }


if __name__ == "__main__":
    result = retrieve_doctrine("failure answer ownership result squared tradeoff", limit=5)
    print(json.dumps(result, indent=2, ensure_ascii=False)[:4000])
