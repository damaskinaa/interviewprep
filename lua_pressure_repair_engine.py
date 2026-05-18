from agent_v2 import ask_llm


def build_pressure_repair_feedback(
    company,
    role,
    focus_area,
    original_answer,
    pressure_question,
    repair_answer,
):
    prompt = f"""
You are Lua, a senior FAANG interviewer.

Evaluate whether the candidate recovered after pressure.

Company: {company}
Role: {role}
Focus area: {focus_area}

Original weak answer:
{original_answer}

Pressure question:
{pressure_question}

Candidate repair answer:
{repair_answer}

Return only valid JSON:
{{
  "status": "pressure_repair_feedback",
  "recovery_score": 0,
  "recovered": false,
  "pressure_outcome": "",
  "what_improved": [],
  "still_missing": [],
  "next_interviewer_move": "",
  "should_escalate": false,
  "should_relax_pressure": false
}}

Rules:
1. recovery_score is 1 to 10
2. recovered is true only if the repair is clearly stronger
3. should_escalate true if answer is still vague, defensive, or lacks proof
4. should_relax_pressure true if answer is specific, calm, and senior
5. Be strict but fair
"""

    try:
        import json
        raw = ask_llm(prompt)
        return json.loads(raw)
    except Exception:
        return {
            "status": "pressure_repair_feedback",
            "recovery_score": 4,
            "recovered": False,
            "pressure_outcome": "The repair needs more specific ownership, action, and proof.",
            "what_improved": [],
            "still_missing": ["specific action", "measurable proof", "clear ownership"],
            "next_interviewer_move": "Ask for the exact metric and system change.",
            "should_escalate": True,
            "should_relax_pressure": False,
        }
