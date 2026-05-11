import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DOCTRINE_DIR = BASE_DIR / "doctrine" / "generated"

RULES_PATH = DOCTRINE_DIR / "doctrine_rules.json"
CHUNKS_PATH = DOCTRINE_DIR / "doctrine_chunks.json"
FULL_TEXT_PATH = DOCTRINE_DIR / "doctrine_full_text.json"


def load_doctrine():
    return {
        "rules": json.loads(RULES_PATH.read_text(encoding="utf8")),
        "chunks": json.loads(CHUNKS_PATH.read_text(encoding="utf8")),
        "full_text": json.loads(FULL_TEXT_PATH.read_text(encoding="utf8")),
    }


def tokenize(text):
    return set(re.findall(r"[a-zA-Z0-9%]+", text.lower()))


def retrieve_doctrine(query, limit=10):
    doctrine = load_doctrine()
    query_tokens = tokenize(query)

    scored = []

    for chunk in doctrine["chunks"]:
        chunk_text = f"{chunk.get('heading', '')} {chunk.get('text', '')}"
        chunk_tokens = tokenize(chunk_text)

        score = len(query_tokens & chunk_tokens)

        important_terms = [
            "failure",
            "ownership",
            "tradeoff",
            "trade",
            "result",
            "squared",
            "stakeholder",
            "influence",
            "authority",
            "metric",
            "data",
            "technical",
            "programme",
            "program",
            "google",
            "hero",
            "crossroads",
            "delivery",
            "risk",
            "freeze",
            "coaching",
            "story",
            "trigger",
        ]

        lower_chunk = chunk_text.lower()
        lower_query = query.lower()

        for term in important_terms:
            if term in lower_query and term in lower_chunk:
                score += 4

        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)

    return {
        "doctrine_version": doctrine["rules"].get("version", "nailit_doctrine_v1"),
        "full_doctrine_available": True,
        "hard_rules": doctrine["rules"].get("hard_rules", []),
        "retrieved_chunks": [chunk for _, chunk in scored[:limit]],
    }


def build_lua_doctrine_brief(query):
    retrieved = retrieve_doctrine(query, limit=10)

    return {
        "doctrine_version": retrieved["doctrine_version"],
        "full_doctrine_available": True,
        "hard_rules": retrieved["hard_rules"],
        "retrieved_doctrine_chunks": retrieved["retrieved_chunks"],
        "lua_behavior_contract": {
            "must_score_every_answer_against_doctrine": True,
            "must_enforce_result_first": True,
            "must_enforce_i_language_for_owned_work": True,
            "must_enforce_tradeoff": True,
            "must_enforce_result_squared": True,
            "must_detect_generic_answers": True,
            "must_detect_invented_metrics": True,
            "must_use_trigger_phrases_for_story_retrieval": True,
            "must_adapt_followups_to_weakest_signal": True,
            "must_preserve_partner_frame": True,
        },
    }


if __name__ == "__main__":
    test = build_lua_doctrine_brief(
        "failure ownership stakeholder tradeoff result squared"
    )
    print("VERSION", test["doctrine_version"])
    print("RULES", len(test["hard_rules"]))
    print("CHUNKS", len(test["retrieved_doctrine_chunks"]))
    for chunk in test["retrieved_doctrine_chunks"][:3]:
        print(chunk["chunk_id"], chunk["heading"])

