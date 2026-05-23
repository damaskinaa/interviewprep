import json
import re
from openai import OpenAI
from agent_v2 import ask_llm, trim_text
from doctrine_runtime import build_lua_doctrine_brief


CONTINUATION_PHRASES = {
    "mm",
    "um",
    "uh",
    "one sec",
    "let me think",
    "hold on",
    "wait",
    "i am still answering",
    "i'm still answering",
    "and also",
    "because",
    "so",
    "the reason is",
}


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def should_wait_for_more(candidate_answer):
    text = normalize(candidate_answer)

    if not text:
        return True

    if text in CONTINUATION_PHRASES:
        return True

    if any(text.endswith(phrase) for phrase in CONTINUATION_PHRASES):
        return True

    if text.endswith(("and", "because", "so", "but", "then", "also")):
        return True

    if len(text.split()) < 12 and text.endswith(("mm", "um", "uh")):
        return True

    return False


def classify_question(question, candidate_answer):
    text = normalize(question + " " + candidate_answer)

    if any(word in text for word in ["fail", "mistake", "missed", "wrong", "deadline"]):
        return "failure"
    if any(word in text for word in ["stakeholder", "influence", "buy in", "disagree", "conflict"]):
        return "influence_or_conflict"
    if any(word in text for word in ["data", "metric", "kpi", "analytics", "measure"]):
        return "data_or_metric"
    if any(word in text for word in ["coach", "performance", "underperform", "delegate", "hiring", "team"]):
        return "people_leadership"
    if any(word in text for word in ["process", "improve", "sla", "workflow", "backlog", "operations"]):
        return "process_improvement"
    if any(word in text for word in ["technical", "system", "cloud", "automation", "infrastructure"]):
        return "technical_program_management"

    return "general_behavioral"



def scrub_unconfirmed_numbers(value):
    if isinstance(value, dict):
        return {k: scrub_unconfirmed_numbers(v) for k, v in value.items()}

    if isinstance(value, list):
        return [scrub_unconfirmed_numbers(v) for v in value]

    if not isinstance(value, str):
        return value

    value = re.sub(r"\b\d+%\b", "[needs confirmation]", value)
    value = re.sub(r"\b\d+\s*percent\b", "[needs confirmation]", value, flags=re.I)

    return value


def build_lua_coach_response(
    company,
    role,
    question,
    candidate_answer,
    lua_brief,
    conversation_history=None,
    voice_notes="",
):
    conversation_history = conversation_history or []

    if should_wait_for_more(candidate_answer):
        return {
            "status": "listening",
            "message": "I am still listening. Finish your answer, then say done or feedback.",
            "should_respond": False,
        }

    question_type = classify_question(question, candidate_answer)

    doctrine_query = f"""
    company {company}
    role {role}
    question type {question_type}
    question {question}
    answer {candidate_answer}
    result first ownership tradeoff result squared specificity evidence integrity voice tone follow up
    """

    doctrine = build_lua_doctrine_brief(doctrine_query)

    prompt = f"""
You are Lua Live Coach v2, an elite interview coach.

You must coach the candidate using the Nailit doctrine and the Lua brief.

Company:
{company}

Role:
{role}

Question type:
{question_type}

Current question:
{question}

Candidate answer:
{candidate_answer}

Voice notes:
{voice_notes}

Lua brief:
{trim_text(json.dumps(lua_brief, ensure_ascii=False), 14000)}

Doctrine:
{trim_text(json.dumps(doctrine, ensure_ascii=False), 16000)}

Conversation history:
{trim_text(json.dumps(conversation_history, ensure_ascii=False), 7000)}

Your job:
1. Score the answer strictly.
2. Identify which doctrine rules were followed or broken.
3. Explain what made the answer weak or strong.
4. Give a better structure.
5. Give three top 1 percent answer versions that are CV-plausible, role-realistic, company-targeted, and as strong as possible.
6. You may invent realistic metrics, timelines, stakes, and process details when they fit the candidate's actual career lane, role history, seniority, and plausible responsibilities.
7. Never invent employers, job titles, industries, credentials, domains, tools, authority level, or career history that the candidate could not credibly claim.
8. Never move the candidate into finance, engineering, cloud, sales, legal, or another domain unless the CV, answer, memory, or Lua brief supports it.
9. Give voice and tone coaching.
10. Ask one adaptive follow up question.
11. In the three answer versions, make the process make sense: context, stakes, diagnosis, action, tradeoff, stakeholder management, measurement, result.
12. Keep metrics realistic for the work described. Prefer believable operational, delivery, quality, SLA, cycle time, adoption, escalation, risk, or throughput metrics over inflated revenue or headcount claims.
13. Do not move on if the answer is below 8.5 unless the user asks to move on.

Return only valid JSON with this exact schema:

{{
  "status": "coaching",
  "should_respond": true,
  "question_type": "",
  "score_out_of_10": 0,
  "verdict": "",
  "what_worked": [],
  "what_was_weak": [],
  "doctrine_rules_followed": [],
  "doctrine_rules_broken": [],
  "missing_evidence": [],
  "plausibility_boundary": [],
  "better_structure": [],
  "top_1_percent_answers": {{
    "safe_strong": "",
    "elite_concise": "",
    "pressure_proof": ""
  }},
  "voice_and_delivery_coaching": {{
    "pace": "",
    "tone": "",
    "confidence": "",
    "words_to_remove": [],
    "sentence_to_practise": ""
  }},
  "next_drill": "",
  "adaptive_follow_up_question": "",
  "move_on_allowed": false
}}
"""

    raw = ask_llm(prompt, max_tokens=3500, retries=3)

    cleaned = raw.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
        parsed.setdefault("status", "coaching")
        parsed.setdefault("should_respond", True)
        parsed.setdefault("question_type", question_type)
        parsed.setdefault("move_on_allowed", False)
        parsed.setdefault("missing_evidence", [])
        parsed.setdefault("plausibility_boundary", [])
        parsed.setdefault("next_drill", "")
        parsed.setdefault("adaptive_follow_up_question", "")
        return parsed
    except Exception:
        return {
            "status": "coaching",
            "should_respond": True,
            "question_type": question_type,
            "score_out_of_10": None,
            "verdict": "Coach response could not be parsed as JSON.",
            "raw_response": raw,
            "move_on_allowed": False,
        }


if __name__ == "__main__":
    demo = build_lua_coach_response(
        company="Google",
        role="Program Manager",
        question="Tell me about a time you failed.",
        candidate_answer="I missed a deadline because the team was busy, but we fixed it later.",
        lua_brief={},
    )
    print(json.dumps(demo, indent=2, ensure_ascii=False)[:5000])





