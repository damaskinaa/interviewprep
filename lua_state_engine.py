def build_interview_state(events):
    practice_turns = [
        e for e in events
        if e.get("event_type") == "practice_turn"
    ]

    scores = []
    weak_points = []
    memory_hits = 0

    for event in practice_turns:
        feedback = event.get("payload", {}).get("feedback", {})

        score = feedback.get("score_out_of_10")
        if isinstance(score, (int, float)):
            scores.append(float(score))

        weak_points.extend(
            feedback.get("weak_points", [])
        )

        memory_hits += len(
            feedback.get("memory_used", [])
        )

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0

    trend = "stable"

    if len(scores) >= 2:
        if scores[-1] > scores[0]:
            trend = "improving"
        elif scores[-1] < scores[0]:
            trend = "declining"

    top_weaknesses = weak_points[:5]

    executive_ready = (
        avg_score >= 8
        and trend != "declining"
    )

    return {
        "status": "state_ready",
        "attempts": len(practice_turns),
        "average_score": avg_score,
        "score_trend": trend,
        "top_weaknesses": top_weaknesses,
        "memory_hits": memory_hits,
        "executive_ready": executive_ready
    }
