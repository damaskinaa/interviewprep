from pathlib import Path
import json
from doctrine_runtime import build_lua_doctrine_brief


def build_lua_mock_interview_brief(
    company_name,
    role_name,
    company_intel,
    job_decode,
    candidate_digest,
    match_gap_map,
    story_bank,
    qa_bank,
):
    doctrine_query = f"""
    Company: {company_name}
    Role: {role_name}
    failure ownership stakeholder influence tradeoff result squared
    program management ambiguity risk metrics data technical leadership
    story bank trigger phrases coaching follow up pressure mock interview
    """

    doctrine = build_lua_doctrine_brief(doctrine_query)

    brief = {
        "brief_type": "nailit_lua_mock_interview_brief",
        "version": "nailit_lua_v1",
        "company": company_name,
        "role": role_name,
        "doctrine": doctrine,
        "candidate_strategy": {
            "company_intelligence": company_intel,
            "job_description_decode": job_decode,
            "candidate_evidence_digest": candidate_digest,
            "match_gap_risk_map": match_gap_map,
            "story_bank": story_bank,
            "question_answer_bank": qa_bank,
        },
        "lua_operating_rules": [
            "Ask one question at a time.",
            "Score every candidate answer against the doctrine hard rules.",
            "Do not accept vague answers.",
            "Force result first if the answer starts with long context.",
            "Force I language when candidate owns the work.",
            "Force tradeoff clarity when judgment is being tested.",
            "Force result squared when a metric is mentioned.",
            "Challenge invented or unsupported metrics.",
            "Ask adaptive follow ups based on the weakest signal.",
            "Use pressure realistically but do not become hostile.",
            "After feedback, give a stronger answer model using only candidate evidence.",
            "Preserve partner frame and calm executive tone.",
        ],
        "scoring_dimensions": [
            "clarity",
            "specificity",
            "ownership",
            "tradeoff_judgment",
            "result_squared",
            "role_relevance",
            "company_alignment",
            "composure",
            "senior_signal",
            "evidence_integrity",
        ],
    }

    return json.dumps(brief, indent=2, ensure_ascii=False)



SESSION_BRIEF_MODULES = [
    "company_intelligence",
    "role_intelligence",
    "candidate_profile",
    "gap_map",
    "interview_strategy",
]


def build_session_lua_brief(session_id, jobs_root="jobs", max_chars_per_module=6000):
    """Collect the session's completed module artifacts so Lua coaches with real candidate context."""
    from agent_v2 import safe_path_part, trim_text

    base = Path(jobs_root) / safe_path_part(session_id, "session")
    brief = {"brief_type": "nailit_session_lua_brief", "session_id": session_id, "modules": {}}
    for module_name in SESSION_BRIEF_MODULES:
        path = base / module_name / f"{module_name}.json"
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf8"))
        except (OSError, json.JSONDecodeError):
            continue
        brief["modules"][module_name] = trim_text(
            json.dumps(data, ensure_ascii=False), max_chars_per_module
        )
    return brief


if __name__ == "__main__":
    print(
        build_lua_mock_interview_brief(
            "Google",
            "Program Manager",
            "company intel",
            "job decode",
            "candidate digest",
            "match gap map",
            "story bank",
            "question bank",
        )[:3000]
    )
