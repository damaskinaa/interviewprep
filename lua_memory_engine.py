import json
from agent_v2 import ask_llm, trim_text
from lua_memory_store import save_memory, load_memory, memory_text

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
        return {"status": "error", "raw_response": text}

def add_coach_memory(session_id, title, content, scope="session", source_type="pasted_text"):
    prompt = f"""
You are organizing memory for an elite interview coach.

Extract what matters from this material.

Content:
{trim_text(content, 12000)}

Return only valid JSON:
{{
  "status": "memory_added",
  "summary": "",
  "tags": [],
  "answer_patterns": [],
  "metrics": [],
  "tone_rules": [],
  "questions_it_improves": [],
  "coach_instruction_update": ""
}}
"""
    raw = ask_llm(prompt, max_tokens=1800, retries=3)
    parsed = safe_json(raw)
    save_memory(session_id, scope, source_type, title, content, parsed.get("summary", ""), parsed.get("tags", []))
    parsed["session_id"] = session_id
    parsed["title"] = title
    parsed["scope"] = scope
    parsed["source_type"] = source_type
    return parsed

def get_coach_memory(session_id):
    return {
        "status": "found",
        "session_id": session_id,
        "memory": load_memory(session_id),
        "memory_text": memory_text(session_id),
    }
