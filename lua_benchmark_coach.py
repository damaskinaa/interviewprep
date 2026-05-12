import json
from agent_v2 import ask_llm, trim_text
from doctrine_runtime import build_lua_doctrine_brief


def safe_json(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except Exception:
        return {
            "status": "error",
            "raw_response": text,
        }


def build_benchmark_question(
    session_id,
    company,
    role,
    question_number,
    nailit_pack="",
    uploaded_memory="",
    focus_area="",
):
    doctrine_query = f"""
    elite interview benchmark answers hero journey star result first
    tradeoff metrics confidence senior communication {company} {role} {focus_area}
    """
    doctrine = build_lua_doctrine_brief(doctrine_query)

    prompt = f"""
You are an elite career coach and interview strategist.

Create ONE benchmark learning card.

This is NOT truthful CV mode.
This is benchmark learning mode.

The candidate wants top 1 percent ideal answers, invented or inspired by public interview patterns.
The answers can be hypothetical and idealized.
Clearly label them as benchmark practice answers, not verified personal experience.

Company:
{company}

Role:
{role}

Question number:
{question_number}

Focus area:
{focus_area or "choose the highest value interview signal"}

Nailit pack memory:
{trim_text(nailit_pack, 9000)}

Uploaded memory:
{trim_text(uploaded_memory, 9000)}

Doctrine:
{json.dumps(doctrine, ensure_ascii=False)[:9000]}

Rules:
1. Pick one high probability interview question.
2. Give exactly three top 1 percent benchmark answers.
3. Do not limit answers to the candidate CV.
4. Use elite interview patterns from public candidate examples, hiring guides, company style, STAR, Hero Journey, result first, tradeoff, result squared, and senior tone.
5. Each answer must include why it works, metrics used, structure, tone notes, and risk.
6. Make answers specific, senior, and memorable.
7. Do not say these are the candidate's real facts.
8. Return only valid JSON.

Schema:
{{
  "status": "benchmark_ready",
  "mode": "benchmark_learning",
  "session_id": "{session_id}",
  "company": "{company}",
  "role": "{role}",
  "question_number": {question_number},
  "question": "",
  "signal_tested": "",
  "what_interviewer_is_really_testing": "",
  "answer_options": [
    {{
      "option_id": "A",
      "label": "executive benchmark",
      "answer": "",
      "why_it_works": "",
      "metrics_used": [],
      "structure_used": [
        "result first",
        "STAR",
        "Hero Journey",
        "tradeoff",
        "result squared"
      ],
      "tone_notes": "",
      "seniority_markers": [],
      "risk": "Benchmark invented answer, not verified personal experience"
    }},
    {{
      "option_id": "B",
      "label": "concise pressure proof",
      "answer": "",
      "why_it_works": "",
      "metrics_used": [],
      "structure_used": [],
      "tone_notes": "",
      "seniority_markers": [],
      "risk": "Benchmark invented answer, not verified personal experience"
    }},
    {{
      "option_id": "C",
      "label": "story driven Hero Journey",
      "answer": "",
      "why_it_works": "",
      "metrics_used": [],
      "structure_used": [],
      "tone_notes": "",
      "seniority_markers": [],
      "risk": "Benchmark invented answer, not verified personal experience"
    }}
  ],
  "coach_instruction": "Pick A, B, or C. Then we will train it until it sounds natural."
}}
"""

    raw = ask_llm(prompt, max_tokens=4200, retries=3)
    data = safe_json(raw)
    data.setdefault("status", "benchmark_ready")
    data.setdefault("mode", "benchmark_learning")
    return data


def build_selected_answer_training_card(session_id, selected_answer, user_choice):
    prompt = f"""
You are an elite interview coach.

The user selected this benchmark answer to train.

Choice:
{user_choice}

Selected answer:
{json.dumps(selected_answer, ensure_ascii=False)[:9000]}

Break it into a practice plan.

Return only valid JSON:
{{
  "status": "training_ready",
  "session_id": "{session_id}",
  "chosen_option": "{user_choice}",
  "memorisation_chunks": [
    {{
      "chunk_name": "opening",
      "text": "",
      "why_it_matters": "",
      "delivery_note": ""
    }}
  ],
  "practice_order": [],
  "voice_targets": {{
    "pace": "",
    "tone": "",
    "confidence": "",
    "words_to_avoid": []
  }},
  "first_drill": "",
  "instruction": "Read the opening out loud first. Say done when finished."
}}
"""
    raw = ask_llm(prompt, max_tokens=2500, retries=3)
    return safe_json(raw)
