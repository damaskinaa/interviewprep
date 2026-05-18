from agent_v2 import ask_llm


def build_pressure_response(company, role, focus_area, spoken_attempt, score=0):
    try:
        score = float(score)
    except Exception:
        score = 0

    pressure_level = "medium"
    if score <= 3:
        pressure_level = "high"
    elif score >= 7:
        pressure_level = "executive"

    prompt = f"""
You are Lua, acting as a realistic senior interviewer.

Company: {company}
Role: {role}
Focus area: {focus_area}
Candidate answer: {spoken_attempt}
Score: {score}
Pressure level: {pressure_level}

Return only valid JSON:
{{
  "status": "pressure_ready",
  "pressure_level": "",
  "interruption": "",
  "pushback_question": "",
  "what_you_are_testing": [],
  "candidate_repair_instruction": "",
  "red_flags": []
}}

Rules:
1. interruption should be short and natural
2. pushback must challenge vagueness, lack of metrics, weak ownership, or unclear tradeoff
3. sound like a real interviewer, not a tutor
4. do not be rude
5. make the candidate answer under pressure
"""

    try:
        import json
        raw = ask_llm(prompt)
        return json.loads(raw)
    except Exception:
        return {
            "status": "pressure_ready",
            "pressure_level": pressure_level,
            "interruption": "Let me stop you there for a second.",
            "pushback_question": "What exactly was your ownership, and what measurable change prevented this from happening again?",
            "what_you_are_testing": ["ownership", "specificity", "metrics", "pressure clarity"],
            "candidate_repair_instruction": "Answer in 30 seconds with root cause, action, and proof.",
            "red_flags": ["vague answer", "no metric", "no clear ownership"]
        }
