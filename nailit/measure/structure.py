"""Structure checks: one LLM call per answer, judged against the rubric rules named in detectors.yaml."""
from nailit import llm

PROMPT = """You check one interview answer against rubric rules. Judge only what the answer says; do not
rewrite it or add facts.

Question type: {question_type}
Question: {question}
Answer:
\"\"\"{answer}\"\"\"

Rules:
{rules}

Return JSON: {{"checks": {{"<check id>": {{"pass": true|false, "reason": "<one short sentence quoting the answer>"}}}}}}
with one entry for every check id above."""


def applicable(checks, question_type):
    return [c for c in checks if "all" in c["applies_to"] or question_type in c["applies_to"]]


def check(lib, answer, question_type=None, question="", ask=None):
    """Failed structure checks as debrief hits; [] when no check applies (no LLM call is made then)."""
    checks = applicable(lib["detectors"]["structure_checks"], question_type)
    if not checks or not (answer or "").strip():
        return []
    rubric = {r["id"]: r["text"] for r in lib["rubric"]["rules"]}
    rules = "\n".join(f"- {c['id']} ({c['rubric_rule']}): {rubric.get(c['rubric_rule'], c['label'])}" for c in checks)
    result = (ask or llm.ask_json)(PROMPT.format(question_type=question_type or "unknown", question=question,
                                                 answer=answer, rules=rules), max_tokens=800)
    verdicts = result.get("checks") if isinstance(result, dict) else None
    verdicts = verdicts if isinstance(verdicts, dict) else {}
    hits = []
    for c in checks:
        verdict = verdicts.get(c["id"])
        if isinstance(verdict, dict) and verdict.get("pass") is False:
            hits.append({"kind": "structure", "id": c["id"], "label": c["label"], "severity": c["severity"],
                         "rubric_rule": c["rubric_rule"], "reason": str(verdict.get("reason") or "")[:300]})
    return hits
