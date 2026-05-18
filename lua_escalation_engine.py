from agent_v2 import ask_llm


def build_escalation_challenge(
    company,
    role,
    focus_area,
    previous_answer,
    score,
):
    level = "retry"

    if score >= 8:
        level = "executive_pressure"
    elif score >= 5:
        level = "harder_followup"

    prompt = f"""
You are Lua, an elite FAANG interview simulator.

Create the next escalation challenge.

Company:
{company}

Role:
{role}

Focus area:
{focus_area}

Previous answer:
{previous_answer}

Score:
{score}

Escalation level:
{level}

Return only valid JSON:

{{
  "status": "escalation_ready",
  "level": "",
  "interviewer_style": "",
  "challenge_question": "",
  "why_this_is_harder": "",
  "what_is_being_tested": [],
  "target_answer_traits": [],
  "red_flags": []
}}

Rules:
1. retry = same topic but simpler repair
2. harder_followup = deeper ambiguity, prioritization, conflict, tradeoff
3. executive_pressure = boardroom pressure, metrics scrutiny, leadership tension
4. Questions must sound realistic and senior
5. Never repeat the original question
"""

    try:
        import json
        raw = ask_llm(prompt)
        return json.loads(raw)
    except Exception:
        return {
            "status": "escalation_ready",
            "level": level,
            "interviewer_style": "direct",
            "challenge_question": "What would you do differently if this happened again under tighter executive pressure?",
            "why_this_is_harder": "The challenge adds ambiguity and leadership pressure.",
            "what_is_being_tested": [
                "ownership",
                "clarity",
                "executive communication"
            ],
            "target_answer_traits": [
                "specific",
                "calm",
                "metrics driven"
            ],
            "red_flags": [
                "rambling",
                "vagueness",
                "defensiveness"
            ]
        }
