import json
import re
from pathlib import Path

from agent_v2 import MODEL_STRATEGY, ask_json, json_dumps, normalize_text, safe_path_part, trim_text


ANSWER_LABELS = [
    "Option A safest",
    "Option B strongest stretch",
    "Option C bold top 1 percent",
]


def _word_count(text):
    return len(re.findall(r"\b\w+\b", text or ""))


def _candidate_profile_path(session_id):
    return Path("jobs") / safe_path_part(session_id, "session") / "candidate_profile" / "candidate_profile.json"


def read_candidate_profile(session_id):
    path = _candidate_profile_path(session_id)
    if not path.exists():
        raise FileNotFoundError("candidate_profile.json not found for this session. Run Candidate Profile first.")
    return json.loads(path.read_text(encoding="utf8"))


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _story_lookup(candidate_profile, assigned_story_id, assigned_story_title):
    stories = [story for story in _as_list((candidate_profile or {}).get("story_inventory")) if isinstance(story, dict)]
    assigned_story_id = normalize_text(assigned_story_id)
    assigned_story_title = normalize_text(assigned_story_title).lower()
    for story in stories:
        if normalize_text(story.get("story_id")) == assigned_story_id and assigned_story_id:
            return story
    for story in stories:
        title = normalize_text(story.get("title") or story.get("story_name")).lower()
        if title and assigned_story_title and title == assigned_story_title:
            return story
    return None


def _normalize_answer_option(option, label):
    option = option if isinstance(option, dict) else {}
    full_answer = normalize_text(option.get("full_answer"))
    return {
        "label": label,
        "full_answer": full_answer,
        "why_it_wins": normalize_text(option.get("why_it_wins")) or "It gives a clear, grounded answer while protecting the candidate from overclaiming.",
        "metric_used": normalize_text(option.get("metric_used")) or "No metric used unless grounded in the candidate evidence.",
        "tradeoff_shown": normalize_text(option.get("tradeoff_shown")) or "Balances ambition with honest boundaries.",
        "delivery_notes": normalize_text(option.get("delivery_notes")) or "Calm pace, direct tone, emphasize the decision and result.",
    }


def _fallback_answer(question, label, candidate_profile, assigned_story):
    stories = _as_list((candidate_profile or {}).get("story_inventory"))
    story = assigned_story or (stories[0] if stories and isinstance(stories[0], dict) else {})
    title = normalize_text(story.get("title") or "the strongest grounded operations story")
    result = normalize_text(story.get("result")) or "a measurable operating improvement"
    metrics = ", ".join(_as_list(story.get("metrics") or story.get("metrics_provided"))) or "the verified operating metric"
    answer = (
        f"Fallback/manual review required: this answer was assembled from grounded candidate evidence because generated options were unavailable or outside quality bounds. "
        f"The stake I would open with is that this question is really about turning an unclear operating constraint into an accountable plan. "
        f"The closest evidence I would use is {title}, because it shows the candidate working inside a real operating problem rather than speaking theoretically. "
        f"The decision was to make the issue visible, clarify ownership, and create a repeatable rhythm so the team could act on facts instead of assumptions. "
        f"The specific actions were to map the constraint, align the people closest to the work, use the available data carefully, and keep the follow-through visible until the result changed. "
        f"The metric I would use is {metrics}, but only if it is tied directly to the story and not inflated. "
        f"The tradeoff is that this is transferable evidence, not permission to claim employers, industries, credentials, or domain ownership that the candidate does not have. "
        f"For this question, I would translate the story into the role by explaining how the same operating pattern applies: understand the constraint, build trust with stakeholders, define the metric, and reduce execution risk. "
        f"The business result was {result}, which is the proof that the candidate can turn ambiguity into measurable program execution."
    )
    return {
        "label": label,
        "full_answer": answer,
        "why_it_wins": "It is honest about boundaries and still gives a concrete operating story.",
        "metric_used": metrics,
        "tradeoff_shown": "Transferable evidence versus unsupported domain ownership.",
        "delivery_notes": "Use a steady pace, pause after the boundary, and emphasize the operating decision and measurable result.",
    }


def normalize_answer_options(data, question, candidate_profile, assigned_story):
    options = data.get("answers") if isinstance(data, dict) else []
    options = [item for item in _as_list(options) if isinstance(item, dict)]
    normalized = []
    for index, label in enumerate(ANSWER_LABELS):
        item = _normalize_answer_option(options[index] if index < len(options) else {}, label)
        words = _word_count(item["full_answer"])
        if words < 160 or words > 240:
            item = _fallback_answer(question, label, candidate_profile, assigned_story)
        normalized.append(item)
    return {"answers": normalized}


def generate_answer_options(session, payload):
    session_id = session["session_id"]
    candidate_profile = read_candidate_profile(session_id)
    question = normalize_text(payload.get("question"))
    if not question:
        raise ValueError("question is required")

    assigned_story = _story_lookup(
        candidate_profile,
        payload.get("assigned_story_id", ""),
        payload.get("assigned_story_title", ""),
    )

    prompt = f"""
You are Nailit Answer Generator, an elite interview answer strategist.

Generate exactly 3 answer options for one interview question.

Company: {payload.get("company_name") or session.get("company_name")}
Role: {payload.get("role_name") or session.get("role_name")}
Round: {payload.get("round_name") or "Unknown"}
Question: {question}
Assigned story id: {payload.get("assigned_story_id") or ""}
Assigned story title: {payload.get("assigned_story_title") or ""}

Answer rule:
You may invent realistic story detail, process, and metrics within the candidate's real career lane.
Never invent employers, industries, titles, credentials, degrees, direct domain ownership, or impossible seniority.
Do not claim direct construction, contractor, trade school, electrical, piping, data center, finance, healthcare, or other domain experience unless candidate_profile proves it.
If stretching, stretch the operating scenario and process, not the candidate's background.

Each full_answer must be 180 to 220 words.
Natural spoken tone.
Open with the situation, stake, decision, or constraint. Never open with "In my previous role" or "In my role as".
End with the business result or proof of fit. Never end with template language, coaching notes, or "this aligns with expectations".
No validator language. Do not say "result squared", "proof of fit", "story to use", or "key takeaway".

Use candidate_profile as the source of truth:
{trim_text(json_dumps(candidate_profile), 16000)}

Raw CV:
{trim_text(session.get("raw_cv", ""), 9000)}

Raw answer bank:
{trim_text(session.get("raw_answer_bank", ""), 9000)}

Return valid JSON only:
{{
  "answers": [
    {{
      "label": "Option A safest",
      "full_answer": "",
      "why_it_wins": "",
      "metric_used": "",
      "tradeoff_shown": "",
      "delivery_notes": ""
    }},
    {{
      "label": "Option B strongest stretch",
      "full_answer": "",
      "why_it_wins": "",
      "metric_used": "",
      "tradeoff_shown": "",
      "delivery_notes": ""
    }},
    {{
      "label": "Option C bold top 1 percent",
      "full_answer": "",
      "why_it_wins": "",
      "metric_used": "",
      "tradeoff_shown": "",
      "delivery_notes": ""
    }}
  ]
}}
"""
    data = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=4200, retries=2, fallback={"answers": []})
    result = normalize_answer_options(data, question, candidate_profile, assigned_story)
    return {
        "session_id": session_id,
        "question": question,
        "round_name": payload.get("round_name", ""),
        **result,
    }
