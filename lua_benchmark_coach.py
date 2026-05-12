import json
from agent_v2 import ask_llm, trim_text
from doctrine_runtime import build_lua_doctrine_brief
from lua_memory_store import memory_text


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
    stored_memory = memory_text(session_id, limit=20)

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

Uploaded memory from request:
{trim_text(uploaded_memory, 9000)}

Stored coach memory for this session:
{trim_text(stored_memory, 9000)}

Doctrine:
{json.dumps(doctrine, ensure_ascii=False)[:9000]}

Rules:
1. Pick one high probability interview question.
2. Give exactly three top 1 percent benchmark answers.
3. Do not limit answers to the candidate CV.
4. Use stored coach memory when it is relevant.
5. If stored memory conflicts with the request, prefer the most specific and recent memory.
6. If memory improves an answer, make that visible in why_it_works.
7. Do not quote memory blindly. Convert it into elite answer strategy.
8. Use elite interview patterns from public candidate examples, hiring guides, company style, STAR, Hero Journey, result first, tradeoff, result squared, and senior tone.
9. Each answer must include why it works, metrics used, structure, tone notes, and risk.
10. Make answers specific, senior, and memorable.
11. Do not say these are the candidate's real facts.
12. Return only valid JSON.

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


def build_benchmark_practice_feedback(
    session_id,
    selected_answer,
    spoken_attempt,
    chunk_name="full_answer",
    is_final=True,
):
    if not is_final:
        return {
            "status": "saved_listening",
            "should_respond": False,
            "session_id": session_id,
        }

    prompt = f"""
You are an elite interview delivery coach.

Selected benchmark answer:
{json.dumps(selected_answer, ensure_ascii=False)[:9000]}

Chunk being practised:
{chunk_name}

User spoken attempt:
{spoken_attempt}

Score hard against meaning, structure, seniority, confidence, pace, tone, filler words, rambling, metrics, result first, STAR, and Hero Journey.

Do not move on unless score is 8.5 or higher.
Return only valid JSON.

Schema:
{{
  "status": "practice_feedback",
  "session_id": "{session_id}",
  "should_respond": true,
  "score_out_of_10": 0,
  "move_on_allowed": false,
  "verdict": "",
  "what_matched": [],
  "what_was_missing": [],
  "wording_feedback": [],
  "voice_feedback": {{
    "pace": "",
    "tone": "",
    "confidence": "",
    "filler_words": [],
    "seniority": ""
  }},
  "improved_version": "",
  "one_sentence_to_repeat": "",
  "next_instruction": ""
}}
"""
    raw = ask_llm(prompt, max_tokens=2800, retries=3)
    data = safe_json(raw)
    data.setdefault("status", "practice_feedback")
    data.setdefault("session_id", session_id)
    data.setdefault("should_respond", True)
    data.setdefault("move_on_allowed", False)
    return data
