from agent_v2 import ask_llm
from lua_mastery_store import get_mastery


def _fallback_drill(session_id, item, weakest, last_feedback):
    return {
        "status": "drill_ready",
        "session_id": session_id,
        "question_key": item.get("question_key"),
        "attempt_count": item.get("attempt_count"),
        "best_score": item.get("best_score"),
        "move_on_allowed": item.get("move_on_allowed"),
        "target_weak_point": weakest,
        "drill_instruction": f"Redo only the part of your answer that fixes this weakness: {weakest}",
        "retry_script": f"The issue was not just that I missed the deadline. The root cause was {weakest}. I created a clearer operating system, aligned stakeholders earlier, and tracked proof that the same failure would not repeat.",
        "delivery_note": "Say it slowly, own the failure directly, and end with proof.",
        "pass_criteria": [
            "Names the root cause",
            "Shows a permanent system change",
            "Includes measurable proof",
            "Sounds calm and accountable",
            "Avoids vague phrases like we fixed it later",
        ],
        "last_score": item.get("last_score"),
        "memory_used": item.get("memory_used", []),
        "last_feedback_summary": {
            "what_was_missing": last_feedback.get("what_was_missing", []),
            "next_best_action": last_feedback.get("next_best_action", ""),
        },
    }


def build_retry_drill(session_id, question_key=None):
    mastery = get_mastery(session_id, question_key)
    items = mastery.get("mastery", [])

    if not items:
        return {
            "status": "no_mastery_found",
            "session_id": session_id,
            "message": "No practice mastery found yet. Complete a practice turn first.",
        }

    item = items[0]
    weak_points = item.get("weak_points", [])
    last_feedback = item.get("last_feedback", {})
    memory_used = item.get("memory_used", [])

    weakest = weak_points[0] if weak_points else "make the answer more specific and senior"

    prompt = f"""
You are Lua, an elite interview practice coach.

Create a focused retry drill from this weak point:
{weakest}

Last score:
{item.get("last_score")}

Best score:
{item.get("best_score")}

Weak points:
{weak_points}

Memory used:
{memory_used}

Last feedback:
{last_feedback}

Return only valid JSON with this exact shape:
{{
  "status": "drill_ready",
  "target_weak_point": "",
  "why_this_matters": "",
  "drill_instruction": "",
  "retry_script": "",
  "delivery_note": "",
  "pass_criteria": [],
  "avoid": [],
  "upgrade_phrase": ""
}}

Rules:
1. The retry_script must be 30 to 45 seconds spoken aloud.
2. Make it specific, senior, and natural.
3. Fix only the target weak point.
4. Include ownership, action, and proof.
5. Do not invent fake numbers unless clearly framed as placeholders.
"""

    try:
        raw = ask_llm(prompt)
        import json
        parsed = json.loads(raw)
        parsed["session_id"] = session_id
        parsed["question_key"] = item.get("question_key")
        parsed["attempt_count"] = item.get("attempt_count")
        parsed["best_score"] = item.get("best_score")
        parsed["move_on_allowed"] = item.get("move_on_allowed")
        parsed["last_score"] = item.get("last_score")
        parsed["memory_used"] = memory_used
        return parsed
    except Exception:
        return _fallback_drill(session_id, item, weakest, last_feedback)
