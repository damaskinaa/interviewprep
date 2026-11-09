

from nailit.llm import MODEL_STRONG, ask_json, json_dumps
from nailit.prep.common import (
    STAGE_QUALITY_INSTRUCTION,
    as_list,
    normalize_text,
    read_module_artifact,
    report_progress,
    trim_text,
    write_module_json,
)


def story_metric_text(story):
    metrics = as_list((story or {}).get("metrics") or (story or {}).get("metrics_provided"))
    return ", ".join(normalize_text(item) for item in metrics if normalize_text(item)) or "Use only verified metrics from this story."


def story_title(story):
    return normalize_text(story.get("title") or story.get("story_name") or "Candidate story") if isinstance(story, dict) else ""


def candidate_bridge_summary(candidate_profile):
    strengths = []
    for story in as_list((candidate_profile or {}).get("story_inventory")):
        if not isinstance(story, dict):
            continue
        title = story_title(story)
        metrics = story_metric_text(story)
        if title:
            strengths.append(f"{title} ({metrics})")
        if len(strengths) >= 4:
            break
    return "; ".join(strengths) or "operations leadership, metrics discipline, stakeholder alignment, training/SOPs, and risk visibility"


def run_candidate_profile_module(session, progress_callback=None):
    role_intelligence = read_module_artifact(session["session_id"], "role_intelligence")
    report_progress(progress_callback, "Candidate evidence extraction", 25)
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Create candidate_profile.json. Use raw CV and raw answer bank as truth. Use role_intelligence only to map evidence to role signals.

Role intelligence:
{trim_text(json_dumps(role_intelligence), 12000)}

Raw CV:
{trim_text(session.get("raw_cv"), 22000)}

Raw answer bank:
{trim_text(session.get("raw_answer_bank"), 18000) or "None supplied."}

Return valid JSON only:
{{
  "positioning_statement": "",
  "confirmed_evidence": [{{"claim": "", "specific_metric_or_outcome": "", "story": "", "jd_signal": ""}}],
  "story_inventory": [{{"story_name": "", "situation": "", "candidate_decision": "", "candidate_actions": [], "metric": "", "business_result": "", "jd_signal": "", "interview_round_fit": ""}}],
  "transferable_bridges": [{{"danger_zone": "", "bridge_language": "", "candidate_evidence": "", "what_not_to_claim": ""}}],
  "forbidden_claims": [{{"claim": "", "why_forbidden": ""}}],
  "story_gaps": [{{"question": "", "why_it_matters": "", "story_to_build": "", "required_elements": []}}]
}}

Rules:
Never invent employers, titles, industries, credentials, direct domain experience, stories, outcomes, or metrics.
If the candidate has transferable evidence but not direct domain evidence, say that honestly in positioning_statement.
transferable_bridges must be actual words the candidate can say.
"""
    result = ask_json(prompt, model=MODEL_STRONG, max_tokens=7600, retries=2, fallback={})
    write_module_json(session["session_id"], "candidate_profile", result)
    report_progress(progress_callback, "Candidate profile complete", 100)
    return result


def run_gap_map_module(session, progress_callback=None):
    session_id = session["session_id"]
    role_intelligence = read_module_artifact(session_id, "role_intelligence")
    candidate_profile = read_module_artifact(session_id, "candidate_profile")
    company_intelligence = read_module_artifact(session_id, "company_intelligence")
    report_progress(progress_callback, "Gap and repair mapping", 35)
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Create gap_map.json from artifacts only.

role_intelligence.json:
{trim_text(json_dumps(role_intelligence), 12000)}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 16000)}

company_intelligence.json:
{trim_text(json_dumps(company_intelligence), 14000)}

Return valid JSON only:
{{
  "strength_matches": [{{"must_prove_signal": "", "candidate_evidence": "", "story_to_use": "", "metric_to_mention": ""}}],
  "dangerous_gaps": [{{"gap": "", "why_it_will_come_up": "", "repair_script": "", "what_not_to_say": ""}}],
  "repair_scripts": [{{"gap": "", "script": "", "evidence_boundary": ""}}],
  "story_assignments": [{{"question": "", "assigned_story": "", "why_this_story": "", "story_gap_text": ""}}],
  "pressure_responses": [{{"gap": "", "interviewer_pushback": "", "candidate_response": ""}}]
}}

Rules:
repair_scripts and pressure_responses must be verbatim candidate words, not advice.
No story may be assigned more than twice. Use story gap where evidence is missing.
"""
    result = ask_json(prompt, model=MODEL_STRONG, max_tokens=7600, retries=2, fallback={})
    write_module_json(session_id, "gap_map", result)
    report_progress(progress_callback, "Gap map complete", 100)
    return result
