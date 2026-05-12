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


def get_relevant_coach_memory(session_id, query, limit=8):
    items = load_memory(session_id, limit=80)

    if not items:
        return {
            "status": "found",
            "session_id": session_id,
            "query": query,
            "relevant_memory": [],
            "memory_text": "",
        }

    packed = []
    for i, item in enumerate(items):
        packed.append({
            "id": i,
            "title": item.get("title", ""),
            "summary": item.get("summary", ""),
            "tags": item.get("tags", []),
            "content_preview": item.get("content", "")[:1200],
            "created_at": item.get("created_at", ""),
        })

    prompt = f"""
You are selecting the most relevant memory for an elite interview coach.

Query:
{query}

Memory items:
{json.dumps(packed, ensure_ascii=False)[:18000]}

Pick the most relevant items only.
Prefer memory that directly improves the current interview question, company style, answer structure, voice coaching, or scoring.
Return only valid JSON.

Schema:
{{
  "status": "ranked",
  "selected_ids": [],
  "reasoning_summary": "",
  "relevance_notes": []
}}
"""
    raw = ask_llm(prompt, max_tokens=1200, retries=3)
    parsed = safe_json(raw)

    selected_ids = parsed.get("selected_ids", [])
    selected = []
    for idx in selected_ids:
        try:
            idx = int(idx)
            if 0 <= idx < len(items):
                selected.append(items[idx])
        except Exception:
            pass

    selected = selected[:limit]

    blocks = []
    for item in selected:
        blocks.append(
            f"TITLE: {item['title']}\n"
            f"TAGS: {', '.join(item['tags'])}\n"
            f"SUMMARY: {item['summary']}\n"
            f"CONTENT: {item['content'][:3000]}"
        )

    return {
        "status": "found",
        "session_id": session_id,
        "query": query,
        "reasoning_summary": parsed.get("reasoning_summary", ""),
        "relevance_notes": parsed.get("relevance_notes", []),
        "relevant_memory": selected,
        "memory_text": "\n\n".join(blocks),
    }
