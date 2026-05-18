from lua_mastery_store import get_mastery


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

    weakest = weak_points[0] if weak_points else "make the answer more specific and senior"

    return {
        "status": "drill_ready",
        "session_id": session_id,
        "question_key": item.get("question_key"),
        "attempt_count": item.get("attempt_count"),
        "best_score": item.get("best_score"),
        "move_on_allowed": item.get("move_on_allowed"),
        "target_weak_point": weakest,
        "drill_instruction": f"Redo only the part of your answer that fixes this weakness: {weakest}",
        "success_criteria": [
            "Say the answer out loud in 30 to 45 seconds",
            "Fix the target weakness directly",
            "Use one concrete action",
            "End with measurable proof",
            "Sound calm, senior, and accountable",
        ],
        "last_score": item.get("last_score"),
        "memory_used": item.get("memory_used", []),
        "last_feedback_summary": {
            "what_was_missing": last_feedback.get("what_was_missing", []),
            "next_best_action": last_feedback.get("next_best_action", ""),
        },
    }
