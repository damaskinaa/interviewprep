import json
from agent_v2 import ask_llm, trim_text
from doctrine_runtime import build_lua_doctrine_brief
from lua_memory_store import memory_text
from lua_memory_engine import get_relevant_coach_memory


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

This is CV-plausible elite answer mode.

The candidate wants top 1 percent winning interview answers inspired by:
1. elite public interview patterns,
2. the company and role research in the Nailit pack,
3. the candidate's actual career lane, CV, answer bank, and stored coach memory.

You may invent the specific story, process, tradeoffs, and metrics, but only inside a realistic boundary for someone with this candidate's roles, seniority, skills, and plausible responsibilities.

Do not invent employers, job titles, industries, credentials, domains, tools, authority level, or career history that the candidate could not credibly claim.
Do not move the candidate into finance, engineering, cloud, sales, legal, or another domain unless their CV or memory supports it.
Do not create impossible scale, budget, headcount, revenue, or executive authority.

The answers must be as strong as possible while still sounding like this person could have said them.

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
2. Give exactly three top 1 percent answers.
3. Make every answer CV-plausible, role-realistic, company-targeted, and senior.
4. You may invent realistic metrics when they fit the candidate's role and project type.
5. Explain the winning process behind the answer: diagnosis, operating rhythm, stakeholder control, tradeoff, execution, measurement, result.
6. Use stored coach memory when it is relevant.
7. If stored memory conflicts with the request, prefer the most specific and recent memory.
8. If memory improves an answer, make that visible in why_it_works.
9. Do not quote memory blindly. Convert it into elite answer strategy.
10. Use elite interview patterns from public candidate examples, hiring guides, company style, STAR, Hero Journey, result first, tradeoff, result squared, and senior tone.
11. Each answer must include why it works, realistic metrics used, structure, tone notes, and plausibility risk.
12. Do not say these are verified personal facts. Say they are elite CV-plausible practice answers.
13. Return only valid JSON.

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
      "label": "safest elite realistic answer",
      "answer": "",
      "why_it_works": "",
      "metrics_used": [],
      "winning_process": [],
      "structure_used": [
        "result first",
        "STAR",
        "Hero Journey",
        "tradeoff",
        "result squared"
      ],
      "tone_notes": "",
      "seniority_markers": [],
      "plausibility_boundary": "",
      "risk": "Elite CV-plausible practice answer, not a verified personal fact"
    }},
    {{
      "option_id": "B",
      "label": "strongest realistic stretch",
      "answer": "",
      "why_it_works": "",
      "metrics_used": [],
      "winning_process": [],
      "structure_used": [],
      "tone_notes": "",
      "seniority_markers": [],
      "plausibility_boundary": "",
      "risk": "Elite CV-plausible practice answer, not a verified personal fact"
    }},
    {{
      "option_id": "C",
      "label": "bold top 1 percent answer",
      "answer": "",
      "why_it_works": "",
      "metrics_used": [],
      "winning_process": [],
      "structure_used": [],
      "tone_notes": "",
      "seniority_markers": [],
      "plausibility_boundary": "",
      "risk": "Elite CV-plausible practice answer, not a verified personal fact"
    }}
  ],
  "coach_instruction": "Pick A, B, or C. Then we will train it until it sounds natural."
}}
"""

    raw = ask_llm(prompt, max_tokens=4200, retries=3)
    data = safe_json(raw)
    data.setdefault("status", "benchmark_ready")
    data.setdefault("mode", "benchmark_learning")
    for option in data.get("answer_options", []) or []:
        option.setdefault("metrics_used", [])
        option.setdefault("winning_process", [])
        option.setdefault("plausibility_boundary", "")
        option.setdefault("risk", "Elite CV-plausible practice answer, not a verified personal fact")
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
Preserve the selected answer's realistic metrics and winning process.
The chunks should help the candidate sound natural, not memorized.
If the answer includes invented-but-plausible metrics, train them as interview practice metrics and keep them believable.

Return only valid JSON.
The memorisation_chunks array must contain exactly 5 chunks.
Do not merge chunks. Do not return fewer than 5 chunks.

Return only valid JSON.

memory_used must contain at least one item whenever relevant coach memory exists.

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
  "metric_and_process_notes": [],
  "first_drill": "",
  "instruction": "Read the opening out loud first. Say done when finished."
}}
"""
    raw = ask_llm(prompt, max_tokens=2500, retries=3)
    data = safe_json(raw)
    data.setdefault("metric_and_process_notes", [])
    return data


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

    memory_query = f"{chunk_name} interview practice feedback delivery scoring"
    relevant_memory = get_relevant_coach_memory(session_id, memory_query, limit=5)
    relevant_memory_text = relevant_memory.get("memory_text", "")
    relevant_memory_items = relevant_memory.get("relevant_memory", [])

    prompt = f"""
You are an elite interview delivery coach.

Selected benchmark answer:
{json.dumps(selected_answer, ensure_ascii=False)[:9000]}

Chunk being practised:
{chunk_name}

User spoken attempt:
{spoken_attempt}

Relevant coach memory:
{relevant_memory_text[:9000]}

Relevant memory count:
{len(relevant_memory_items)}

Score hard against meaning, structure, seniority, confidence, pace, tone, filler words, rambling, realistic metrics, winning process, result first, STAR, Hero Journey, and the relevant coach memory above.

The selected answer may contain invented-but-CV-plausible story details and metrics. Do not punish the user because the metric is invented. Punish only if it sounds unrealistic for the candidate's role, too inflated, inconsistent, vague, or disconnected from the process.

The standard is top 1 percent interview delivery: specific, senior, believable, company-relevant, and natural.

If relevant memory influenced scoring:
1. Add it into memory_used
2. Explain exactly how the answer violated or matched the memory
3. Mention the specific missing executive behavior
4. Never leave memory_used empty when relevant memory exists

If relevant memory influenced scoring:
1. Add it into memory_used
2. Explain exactly how the answer violated or matched the memory
3. Mention the specific missing executive behavior
4. Never leave memory_used empty when relevant memory exists

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
  "plausibility_feedback": [],
  "memory_used": [
    {{
      "memory_title": "",
      "how_it_was_applied": ""
    }}
  ],
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
    data.setdefault("plausibility_feedback", [])
    return data
