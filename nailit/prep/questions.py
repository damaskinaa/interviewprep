import re

from nailit.guards import (
    ANSWER_BANNED_OPENINGS,
    answer_word_failures_from_strategy,
    first_sentence,
    starts_with_banned_opening,
    strip_hallucinated_metrics,
    why_company_is_generic,
)
from nailit.llm import MODEL_FAST, MODEL_STRONG, ask_json, ask_llm, json_dumps, log_cost_total, start_cost_log
from nailit.prep import apps
from nailit.prep.common import (
    SESSION_MODULES,
    STAGE_QUALITY_INSTRUCTION,
    _current_progress_log,
    _current_results,
    as_list,
    count_words,
    jd_signal_texts,
    log,
    markdown_list,
    module_artifact_path,
    normalize_text,
    read_module_artifact,
    report_progress,
    safe_path_part,
    trim_text,
    write_module_json,
    write_module_markdown,
)
from nailit.prep.me import (
    candidate_bridge_summary,
    run_candidate_profile_module,
    run_gap_map_module,
)
from nailit.prep.research import (
    company_signal_text,
    discover_interview_rounds,
    has_specific_company_signal,
    run_all_rounds_research,
    run_company_intelligence_module,
    run_role_intelligence_module,
)


def replace_first_sentence(answer, new_opening):
    answer = normalize_text(answer)
    new_opening = normalize_text(new_opening).rstrip(".") + "."
    match = re.search(r"(.+?[.!?])(\s|$)", answer)
    if not match:
        return normalize_text(f"{new_opening} {answer}")
    return normalize_text(new_opening + " " + answer[match.end():])


def repair_answer_opening(question, answer, assigned_story, session, candidate_profile):
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Rewrite only the opening sentence for this interview answer. Return one sentence only.

Company: {session["company_name"]}
Role: {session["role_name"]}
Question: {question}
Assigned story: {assigned_story}

Candidate profile:
{trim_text(json_dumps(candidate_profile), 8000)}

Current first sentence:
{first_sentence(answer)}

Allowed opening patterns:
- The specific stake or problem first: The backlog across three regions had reached a point where...
- The decision first: When the metric showed 77 percent I did not accept the calculation...
- The constraint first: With no direct authority over regional leads and a 34 percent backlog gap...
- The result first: We cut response time by one hour per case. Here is how...

Never start with:
{", ".join(ANSWER_BANNED_OPENINGS)}

Use a specific metric or constraint from the assigned story if available. Do not invent facts.
"""
    opening = ask_llm(prompt, model=MODEL_FAST, max_tokens=180, retries=1).strip()
    if not opening or starts_with_banned_opening(opening):
        opening = "The operating problem was specific, measurable, and important enough to require a structured response."
    return replace_first_sentence(answer, opening)


def ensure_modular_answer(question, answer, assigned_story, session, candidate_profile, gap_map):
    answer = normalize_text(answer)
    lowered = answer.lower()
    bad_open = starts_with_banned_opening(answer)
    bad_close = lowered.endswith("aligning with expectations") or lowered.endswith("the key takeaway for you is")
    if 200 <= count_words(answer) <= 260 and not bad_open and not bad_close:
        return answer
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Rewrite this answer for an elite interview strategy pack.

Company: {session["company_name"]}
Role: {session["role_name"]}
Question: {question}
Assigned story: {assigned_story}

Candidate profile:
{trim_text(json_dumps(candidate_profile), 12000)}

Gap map:
{trim_text(json_dumps(gap_map), 10000)}

Current answer:
{answer}

Rules:
Write 200 to 250 words.
Each answer must open differently. Open with one of these patterns:
- The specific stake or problem first.
- The decision first.
- The constraint first.
- The result first.
Do not open with: While my manager was away, In my previous role, In my role as, Recognizing the need, I identified that, I faced a situation.
Use only real candidate evidence from candidate_profile and gap_map.
End with the business result or proof of fit.
Do not end with "aligning with expectations" or "the key takeaway for you is".
Do not invent employers, titles, industries, credentials, domain experience, stories, outcomes, or metrics.
Return only the answer text.
"""
    rewritten = ask_llm(prompt, model=MODEL_STRONG, max_tokens=1400, retries=1).strip()
    candidate_answer = rewritten if count_words(rewritten) >= count_words(answer) else answer
    candidate_answer = re.sub(r"^in my previous role,?\s*", "The stake was clear: ", candidate_answer, flags=re.I)
    candidate_answer = re.sub(r"^in my role as [^,.]+,?\s*", "The stake was clear: ", candidate_answer, flags=re.I)
    if count_words(candidate_answer) < 180:
        bridge = (
            f" The reason this matters for {session['role_name']} is that the role requires the same operating pattern: "
            "diagnose the real constraint, align stakeholders around evidence, make the process measurable, and protect adoption after the change. "
            "I would be careful not to overclaim direct domain ownership; the proof is that I have already delivered measurable process improvement, "
            "risk reduction, stakeholder alignment, and operating discipline with real metrics from my own work. "
            "That is the business result I would bring into the interview: evidence-led execution that improves quality, speed, and trust without inventing experience I have not had."
        )
        candidate_answer = normalize_text(candidate_answer + bridge)
    if starts_with_banned_opening(candidate_answer):
        candidate_answer = repair_answer_opening(question, candidate_answer, assigned_story, session, candidate_profile)
    return candidate_answer


def generate_additional_round_questions(session, round_item, needed, company_intelligence, role_intelligence, candidate_profile, gap_map):
    if needed <= 0:
        return []
    round_name = round_item.get("round_name", "Interview round") if isinstance(round_item, dict) else "Interview round"
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

The interview_strategy module produced too few questions for one round. Generate exactly {needed} additional questions for this round.

Company: {session["company_name"]}
Role: {session["role_name"]}
Round: {round_name}

Round context:
{trim_text(json_dumps(round_item), 5000)}

company_intelligence.json:
{trim_text(json_dumps(company_intelligence), 9000)}

role_intelligence.json:
{trim_text(json_dumps(role_intelligence), 9000)}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 10000)}

gap_map.json:
{trim_text(json_dumps(gap_map), 9000)}

Return valid JSON only:
{{"questions": [{{"question": "", "what_it_is_really_testing": "", "assigned_story": "", "danger_to_avoid": "", "complete_written_answer": "", "delivery_notes": ""}}]}}

Rules:
Each question must be specific and serious.
Each answer must be 200 to 250 words and use only real candidate evidence.
Each answer must open with the problem, decision, constraint, or result. Do not use banned openings.
If the JD does not provide enough signal, generate the question from company_intelligence directional themes and write "Likely based on public patterns" inside what_it_is_really_testing.
Do not invent candidate employers, titles, industries, credentials, domain experience, stories, outcomes, or metrics.
"""
    data = ask_json(prompt, model=MODEL_STRONG, max_tokens=5500, retries=1, fallback={"questions": []})
    rows = []
    for item in as_list(data.get("questions"))[:needed]:
        if not isinstance(item, dict):
            continue
        item["complete_written_answer"] = ensure_modular_answer(
            item.get("question", ""),
            item.get("complete_written_answer", ""),
            item.get("assigned_story", ""),
            session,
            candidate_profile,
            gap_map,
        )
        rows.append(item)
    return rows


def insufficient_why_company_answer(company_intelligence, company_name="the company", candidate_profile=None):
    # Use whatever signals exist to produce a minimal candidate-appropriate answer
    signals = as_list(company_intelligence.get("official_company_signals"))[:2]
    themes = as_list(company_intelligence.get("directional_themes"))[:2]
    best = signals + themes
    signal_text = "; ".join(
        company_signal_text(s) for s in best if company_signal_text(s)
    ) or f"the {company_name} approach to this domain"
    bridge = candidate_bridge_summary(candidate_profile) if candidate_profile else "operations leadership and measurable delivery"
    return (
        f"What draws me to {company_name} is the specific way this role connects to {signal_text}. "
        f"That is different from a generic product or operations role because the work requires someone who can both understand the domain deeply and build the operating discipline around it. "
        f"My bridge is {bridge}. "
        f"What I want to learn at {company_name} is how the team translates those principles into product decisions at scale — "
        f"that combination of domain knowledge and execution rigour is why this role is compelling."
    )


def repair_why_company_answer(strategy, session, company_intelligence, candidate_profile):
    current = strategy.get("why_this_company_answer", "")
    company_name = session.get("company_name", "the company")
    if not has_specific_company_signal(company_intelligence):
        return insufficient_why_company_answer(company_intelligence, company_name, candidate_profile)
    if current and not why_company_is_generic(current):
        return current
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Rewrite why_this_company_answer only. Return the full answer as plain text.

Company: {session["company_name"]}
Role: {session["role_name"]}

company_intelligence.json:
{trim_text(json_dumps(company_intelligence), 12000)}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 12000)}

Required structure:
1. One specific thing about this company's approach to this domain that is different from other companies, sourced from company_intelligence official_company_signals or directional_themes.
2. One specific thing about this role that connects to the candidate's real evidence from candidate_profile.
3. One honest statement about what the candidate wants to learn or build that this role enables.

Rules:
Do not write generic phrases like "is a leader in innovation" or "I admire the culture."
Use the actual company name ({session["company_name"]}) and actual role name ({session["role_name"]}) throughout.
If specific signals are limited, build the answer from what IS available rather than stating research is insufficient.
Never output internal status text or the phrase "research insufficient."
"""
    answer = ask_llm(prompt, model=MODEL_STRONG, max_tokens=1200, retries=1).strip()
    if why_company_is_generic(answer) or not answer:
        answer = insufficient_why_company_answer(company_intelligence, session.get("company_name", "the company"), candidate_profile)
    return answer


def repair_why_role_answer(strategy, session, role_intelligence, candidate_profile):
    current = normalize_text(strategy.get("why_this_role_answer", ""))
    if current and count_words(current) >= 80:
        return current
    company_name = session.get("company_name", "the company")
    role_name = session.get("role_name", "this role")
    must_prove = jd_signal_texts(role_intelligence)[:4]
    bridge = candidate_bridge_summary(candidate_profile)
    positioning = normalize_text((candidate_profile or {}).get("positioning_statement", ""))
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Write why_this_role_answer only. Return plain text, 80–120 words, first-person, spoken.

Company: {company_name}
Role: {role_name}

JD signals that define the role:
{chr(10).join(f"- {s}" for s in must_prove) if must_prove else "- See role_intelligence below."}

Candidate positioning:
{positioning or bridge}

Required structure (three sentences, no headers):
1. One specific reason this role makes sense given the candidate's actual background — name the real evidence.
2. One JD requirement the candidate can genuinely meet, with a real story or outcome from the CV.
3. One honest statement about what the candidate wants to develop or learn in this specific role.

Rules:
- Do not use generic phrases like "passionate about," "excited to join," or "aligns with my values."
- Do not mention "data center construction," "Google People Operations," or any domain not present in the actual JD.
- Do not invent metrics or experience not in the candidate's documents.
- Reference the actual role name ({role_name}) and company name ({company_name}).

role_intelligence.json:
{trim_text(json_dumps(role_intelligence), 8000)}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 8000)}
"""
    answer = ask_llm(prompt, model=MODEL_STRONG, max_tokens=400, retries=1).strip()
    if not answer or count_words(answer) < 40:
        # Deterministic fallback using real data
        jd_anchor = must_prove[0] if must_prove else f"the core requirements of the {role_name} role"
        answer = (
            f"This role makes sense because the {role_name} position at {company_name} maps directly "
            f"to the kind of work I have already done: {bridge}. "
            f"The JD requirement I can meet most immediately is {jd_anchor}, which my evidence already demonstrates. "
            f"What I want to develop here is a deeper understanding of how {company_name} approaches this domain at scale — "
            f"the operating patterns, the stakeholder dynamics, and the product decisions that would be new to me."
        )
    return answer


def normalize_modular_strategy(strategy, session, company_intelligence, role_intelligence, candidate_profile, gap_map):
    strategy = strategy if isinstance(strategy, dict) else {}
    if not isinstance(strategy.get("questions_by_round"), list):
        strategy["questions_by_round"] = []
    existing_rounds = {
        normalize_text(item.get("round_name", "")).lower()
        for item in as_list(strategy.get("questions_by_round"))
        if isinstance(item, dict)
    }
    for round_plan in as_list(strategy.get("round_by_round_plan")):
        if not isinstance(round_plan, dict):
            continue
        round_name = normalize_text(round_plan.get("round_name", ""))
        if not round_name:
            continue
        key = round_name.lower()
        if key not in existing_rounds:
            strategy["questions_by_round"].append({"round_name": round_name, "questions": []})
            existing_rounds.add(key)
    for round_item in as_list(strategy.get("questions_by_round")):
        if not isinstance(round_item, dict):
            continue
        questions = as_list(round_item.get("questions"))[:15]
        if len(questions) < 6:
            questions.extend(generate_additional_round_questions(
                session,
                round_item,
                8 - len(questions),
                company_intelligence,
                role_intelligence,
                candidate_profile,
                gap_map,
            ))
        round_item["questions"] = questions[:15]
        for item in as_list(round_item.get("questions")):
            if not isinstance(item, dict):
                continue
            item["complete_written_answer"] = ensure_modular_answer(
                item.get("question", ""),
                item.get("complete_written_answer", ""),
                item.get("assigned_story", ""),
                session,
                candidate_profile,
                gap_map,
            )
            if starts_with_banned_opening(item["complete_written_answer"]):
                item["complete_written_answer"] = repair_answer_opening(
                    item.get("question", ""),
                    item["complete_written_answer"],
                    item.get("assigned_story", ""),
                    session,
                    candidate_profile,
                )
            # Strip any metrics that don't appear in the candidate's own documents
            cleaned, hallucinated = strip_hallucinated_metrics(
                item["complete_written_answer"],
                session.get("raw_cv", ""),
                session.get("raw_answer_bank", ""),
            )
            if hallucinated:
                log(3, f"Stripped hallucinated metrics from answer '{item.get('question','')[:60]}': {hallucinated}", "warn")
            item["complete_written_answer"] = cleaned
    strategy["why_this_company_answer"] = repair_why_company_answer(strategy, session, company_intelligence, candidate_profile)
    strategy["why_this_role_answer"] = repair_why_role_answer(strategy, session, role_intelligence, candidate_profile)
    return strategy


def run_interview_strategy_module(session, progress_callback=None):
    session_id = session["session_id"]
    company_name = session["company_name"]
    role_name = session["role_name"]

    # ── DEPENDENCY CHECK ─────────────────────────────────────────────────────
    # Each upstream artifact must exist, be non-empty, and contain at least 3
    # keys before the strategy module is allowed to start.  Failing early with
    # a clear message prevents silent bad output from incomplete artifacts.
    _required = [
        ("role_intelligence",  "role_intelligence module must complete before interview_strategy can run"),
        ("candidate_profile",  "candidate_profile module must complete before interview_strategy can run"),
        ("gap_map",            "gap_map module must complete before interview_strategy can run"),
    ]
    for module_name, error_message in _required:
        try:
            artifact = read_module_artifact(session_id, module_name)
        except FileNotFoundError:
            raise ValueError(error_message)
        if not isinstance(artifact, dict) or len(artifact) < 3:
            raise ValueError(
                f"{error_message} (artifact '{module_name}' is empty or incomplete — "
                f"found {len(artifact) if isinstance(artifact, dict) else 0} keys, need at least 3)"
            )
    # ── END DEPENDENCY CHECK ─────────────────────────────────────────────────

    company_intelligence = read_module_artifact(session_id, "company_intelligence")
    role_intelligence = read_module_artifact(session_id, "role_intelligence")
    candidate_profile = read_module_artifact(session_id, "candidate_profile")
    gap_map = read_module_artifact(session_id, "gap_map")

    # ── PHASE 1: Round discovery ──────────────────────────────────────────────
    report_progress(progress_callback, "Discovering interview rounds", 8)
    rounds = discover_interview_rounds(company_intelligence, role_intelligence, company_name, role_name)
    log(5, f"Discovered {len(rounds)} interview rounds: {[r['round_name'] for r in rounds]}", "done")

    # ── PHASE 2: Per-round deep research (parallel, all on Daytona) ───────────
    report_progress(progress_callback, f"Deep research: {len(rounds)} rounds in parallel", 15)
    per_round_research = run_all_rounds_research(company_name, role_name, rounds)

    # Build a compact per-round brief for the strategy prompt
    round_research_brief = []
    for rr in per_round_research:
        rname = rr.get("round_name", "Unknown")
        qs = rr.get("reported_questions", [])
        srcs = rr.get("sources", [])
        reported_q_text = "\n".join(f"  - {q['question']} [{q.get('source_type','')}]" for q in qs[:20]) if qs else "  No community-reported questions found."
        source_summary = f"{len(srcs)} sources ({len([s for s in srcs if 'glassdoor' in s.get('url','').lower()])} Glassdoor, {len([s for s in srcs if 'reddit' in s.get('url','').lower()])} Reddit, {len([s for s in srcs if 'blind' in s.get('url','').lower()])} Blind)"
        round_research_brief.append(
            f"### {rname}\n"
            f"Sources: {source_summary}\n"
            f"Reported questions (real candidates reported these):\n{reported_q_text}"
        )

    round_research_block = "\n\n".join(round_research_brief)
    report_progress(progress_callback, "Executive strategy and round plan", 45)
    # Pull real candidate stories from candidate_profile for dynamic story assignment
    story_names = [
        normalize_text(s.get("story_name", "")) for s in as_list(candidate_profile.get("story_inventory"))
        if isinstance(s, dict) and normalize_text(s.get("story_name", ""))
    ]
    story_list_text = "\n".join(f"- {s}" for s in story_names[:8]) if story_names else "- No stories extracted yet. Use gap_map transferable_bridges."

    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

This is the most important module. Produce interview_strategy.json for this exact candidate and role.

Company: {company_name}
Role: {role_name}

=== PER-ROUND RESEARCH (real data scraped from Glassdoor, Blind, Reddit, LinkedIn, Indeed per round) ===
RULES:
1. The reported questions below are REAL — actual candidates reported being asked these at {company_name}.
2. Each reported question MUST appear in questions_by_round for its correct round. Do not drop them.
3. Questions reported by multiple sources are HIGH PROBABILITY — flag them.
4. After placing all reported questions, fill remaining slots with high-probability inferred questions.
5. Target 8–15 questions per round. Do not cap at 6.

{trim_text(round_research_block, 10000)}

=== CANDIDATE STORIES (use ONLY these — do not invent new stories) ===
{story_list_text}

Raw JD:
{trim_text(session.get("raw_jd"), 10000)}

Raw CV:
{trim_text(session.get("raw_cv"), 10000)}

Raw answer bank:
{trim_text(session.get("raw_answer_bank"), 8000) or "None supplied."}

company_intelligence.json:
{trim_text(json_dumps(company_intelligence), 10000)}

role_intelligence.json:
{trim_text(json_dumps(role_intelligence), 8000)}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 14000)}

gap_map.json:
{trim_text(json_dumps(gap_map), 12000)}

Return valid JSON only with this exact structure:
{{
  "executive_win_strategy": "",
  "round_by_round_plan": [{{"round_name": "", "what_this_round_tests": "", "likely_interviewer": "", "what_they_are_evaluating": "", "stories_to_use": [], "gaps_to_expect": [], "repair_scripts": [], "success_looks_like": "", "failure_looks_like": "", "specific_preparation_actions": []}}],
  "questions_by_round": [{{"round_name": "", "questions": [{{"question": "", "what_it_is_really_testing": "", "assigned_story": "", "danger_to_avoid": "", "complete_written_answer": "", "delivery_notes": "", "source": "reported by candidates | jd-inferred | company-values | inferred"}}]}}],
  "top_10_likely_questions": [{{"question": "", "jd_signal": "", "research_signal": "", "answer_strategy": ""}}],
  "top_10_dangerous_questions": [{{"question": "", "jd_signal": "", "research_signal": "", "answer_strategy": ""}}],
  "dangerous_questions": [{{"question": "", "script": "", "why_it_is_dangerous": ""}}],
  "pressure_followups": [{{"dangerous_question": "", "interviewer_followup": "", "candidate_response": ""}}],
  "do_not_say": [{{"item": "", "reason": ""}}],
  "why_this_company_answer": "",
  "why_this_role_answer": "",
  "thirty_sixty_ninety": {{"30_days": [], "60_days": [], "90_days": []}},
  "questions_to_ask": [],
  "seven_day_plan": [{{"day": "", "actions": []}}]
}}

Requirements:
executive_win_strategy must be at least 400 words.
Each round must have minimum 8 questions. Place all reported questions first. Fill remaining with inferred. Do not cap at 6.
Each complete_written_answer must be 200 to 250 words.
Each answer must open differently.
Ban these opening phrases across all answers in the same pack:
- While my manager was away
- In my previous role
- In my role as
- Recognizing the need
- I identified that
- I faced a situation
Each answer must open with one of these patterns instead:
- The specific stake or problem first: [describe the operational problem using only evidence from the candidate's CV]
- The decision first: [name the decision the candidate made, using only real facts from the CV]
- The constraint first: [name a real constraint from the candidate's experience, using only facts from the CV]
- The result first: [state a real result from the candidate's CV, then explain how it was achieved]
Each answer must end with the business result or proof of fit. Never end with "aligning with expectations" or "the key takeaway for you is".
METRIC RULE: Every specific number, percentage, time measurement, or dollar figure used in any answer MUST appear literally in the raw CV or raw answer bank text provided above. Do not invent any number. If no real metric exists for a story, use qualitative language such as "significantly reduced," "meaningfully improved," or "substantially faster." Never fabricate a percentage, headcount, time saving, or financial figure.
dangerous_questions must contain exactly 8 items with verbatim scripts.
do_not_say must contain exactly 15 specific items.
questions_to_ask must contain exactly 8 specific questions.
why_this_company_answer must use specific signals from company_intelligence official_company_signals and directional_themes. It must not contain generic phrases.
why_this_company_answer must follow this structure:
1. One specific thing about this company's approach to this domain that is different from other companies, sourced from company_intelligence.
2. One specific thing about this role that connects to the candidate's real evidence from candidate_profile.
3. One honest statement about what the candidate wants to learn or build that this role enables.
why_this_role_answer must be at least 80 words and must reference the actual role name and actual JD signals, not generic language about "data center construction" unless the JD explicitly mentions it.
why_this_role_answer must follow this structure:
1. One specific reason this role makes sense given the candidate's background, using only CV evidence.
2. One specific JD requirement the candidate can meet, with real evidence.
3. One honest statement about what the candidate wants to learn or develop in this role.
Do not invent candidate background.
"""
    result = ask_json(prompt, model=MODEL_STRONG, max_tokens=15000, retries=2, fallback={})
    if not result:
        raise ValueError(
            "Interview strategy generation returned no usable output (model output was empty or not valid JSON). Please run it again."
        )
    report_progress(progress_callback, "Strategy answer validation", 86)
    result = normalize_modular_strategy(result, session, company_intelligence, role_intelligence, candidate_profile, gap_map)
    if not any(
        isinstance(round_item, dict) and round_item.get("questions")
        for round_item in as_list(result.get("questions_by_round"))
    ):
        raise ValueError(
            "Interview strategy generation returned no usable questions (model output was empty or not valid JSON). Please run it again."
        )
    write_module_json(session_id, "interview_strategy", result)
    apps.write_questions(session, result)
    report_progress(progress_callback, "Interview strategy complete", 100)
    return result


def run_prep_pack_module(session, progress_callback=None):
    session_id = session["session_id"]
    company_intelligence = read_module_artifact(session_id, "company_intelligence")
    role_intelligence = read_module_artifact(session_id, "role_intelligence")
    candidate_profile = read_module_artifact(session_id, "candidate_profile")
    gap_map = read_module_artifact(session_id, "gap_map")
    strategy = read_module_artifact(session_id, "interview_strategy")

    # Repair why_this_company_answer and why_this_role_answer from the stored strategy
    # in case they were written before the repair functions existed or contain internal
    # status text.  This is cheap (no LLM call if the field is already good).
    strategy["why_this_company_answer"] = repair_why_company_answer(
        strategy, session, company_intelligence, candidate_profile
    )
    strategy["why_this_role_answer"] = repair_why_role_answer(
        strategy, session, role_intelligence, candidate_profile
    )

    report_progress(progress_callback, "Deterministic prep pack assembly", 45)

    answer_failures = answer_word_failures_from_strategy(strategy)
    if answer_failures:
        raise ValueError(f"Any answer under 180 words: {', '.join(answer_failures[:5])}")

    # Required-field validation before assembly
    required_fields = {
        "executive_win_strategy": "executive_win_strategy is empty",
        "why_this_company_answer": "why_this_company_answer is empty — regenerate interview_strategy",
        "why_this_role_answer": "why_this_role_answer is empty — regenerate interview_strategy",
        "round_by_round_plan": "round_by_round_plan is empty",
        "questions_by_round": "questions_by_round is empty",
    }
    missing_required = []
    for field, msg in required_fields.items():
        val = strategy.get(field)
        empty = not val or (isinstance(val, str) and count_words(val) < 20) or (isinstance(val, list) and len(val) == 0)
        if empty:
            missing_required.append(msg)
    if missing_required:
        raise ValueError("Prep pack failed required-field check: " + "; ".join(missing_required))

    round_sections = []
    for round_item in as_list(strategy.get("round_by_round_plan")):
        if not isinstance(round_item, dict):
            continue
        prep_actions = markdown_list(round_item.get("specific_preparation_actions"))
        if not prep_actions:
            prep_actions = f"- Review the JD requirements and available research to prepare focused talking points for the {round_item.get('round_name', 'interview')} round."
        round_sections.append(
            f"### {round_item.get('round_name', 'Interview round')}\n"
            f"- What it tests: {round_item.get('what_this_round_tests', '')}\n"
            f"- Who interviews: {round_item.get('likely_interviewer', '')}\n"
            f"- What they evaluate: {round_item.get('what_they_are_evaluating', '')}\n"
            f"- Preparation actions:\n{prep_actions}"
        )

    qa_sections = []
    for round_item in as_list(strategy.get("questions_by_round")):
        if not isinstance(round_item, dict):
            continue
        questions = []
        for item in as_list(round_item.get("questions")):
            if not isinstance(item, dict):
                continue
            questions.append(
                f"#### {item.get('question', '')}\n"
                f"- Really testing: {item.get('what_it_is_really_testing', '')}\n"
                f"- Assigned story: {item.get('assigned_story', '')}\n"
                f"- Danger to avoid: {item.get('danger_to_avoid', '')}\n\n"
                f"{item.get('complete_written_answer', '')}\n\n"
                f"- Delivery notes: {item.get('delivery_notes', '')}"
            )
        qa_sections.append(f"### {round_item.get('round_name', 'Interview round')}\n" + "\n\n".join(questions))

    evidence_claims = []
    for item in as_list(company_intelligence.get("official_company_signals"))[:6]:
        if isinstance(item, dict):
            evidence_claims.append(f"- Claim: {item.get('signal', '')}\n  - Source type: official company source\n  - Confidence: {item.get('confidence', '')}\n  - Basis: {item.get('basis') or item.get('source_url', '')}")
    for item in as_list(candidate_profile.get("confirmed_evidence"))[:6]:
        if isinstance(item, dict):
            evidence_claims.append(f"- Claim: {item.get('claim', '')}\n  - Source type: CV or answer bank\n  - Confidence: high when directly present in candidate documents\n  - Basis: {item.get('story', '')} {item.get('specific_metric_or_outcome', '')}")
    for item in as_list(role_intelligence.get("must_prove"))[:5]:
        if isinstance(item, dict):
            evidence_claims.append(f"- Claim: {item.get('signal', '')}\n  - Source type: JD supported\n  - Confidence: high\n  - Basis: {item.get('why_it_matters', '')}")

    markdown = f"""# Interview Prep Pack

Company: {session["company_name"]}

Role: {session["role_name"]}

Session ID: {session_id}

## EXECUTIVE WIN STRATEGY
{strategy.get("executive_win_strategy", "")}

## CANDIDATE POSITIONING
{candidate_profile.get("positioning_statement", "")}

### Forbidden Claims
{markdown_list(candidate_profile.get("forbidden_claims"))}

## INTERVIEW PROCESS INTELLIGENCE
{markdown_list(company_intelligence.get("interview_process_signals"))}

## COMPANY INTELLIGENCE
### Official Signals
{markdown_list(company_intelligence.get("official_company_signals"))}

### Directional Themes
{markdown_list(company_intelligence.get("directional_themes"))}

## INTERVIEW ROUNDS AND PREPARATION
{chr(10).join(round_sections)}

## QUESTIONS AND ANSWERS BY ROUND
{chr(10).join(qa_sections)}

## DANGEROUS QUESTIONS AND SCRIPTS
{markdown_list(strategy.get("dangerous_questions"))}

## DO NOT SAY
{markdown_list(strategy.get("do_not_say"))}

## STORY BANK
{markdown_list(candidate_profile.get("story_inventory"))}

## GAP REPAIR SCRIPTS
{markdown_list(gap_map.get("repair_scripts"))}

## WHY THIS COMPANY AND ROLE
### Why This Company
{strategy.get("why_this_company_answer", "")}

### Why This Role
{strategy.get("why_this_role_answer", "")}

## THIRTY SIXTY NINETY
{markdown_list(strategy.get("thirty_sixty_ninety", {}).get("30_days") if isinstance(strategy.get("thirty_sixty_ninety"), dict) else [])}

{markdown_list(strategy.get("thirty_sixty_ninety", {}).get("60_days") if isinstance(strategy.get("thirty_sixty_ninety"), dict) else [])}

{markdown_list(strategy.get("thirty_sixty_ninety", {}).get("90_days") if isinstance(strategy.get("thirty_sixty_ninety"), dict) else [])}

## QUESTIONS TO ASK
{markdown_list(strategy.get("questions_to_ask"))}

## SEVEN DAY PLAN
{markdown_list(strategy.get("seven_day_plan"))}

## EVIDENCE LEDGER
{chr(10).join(evidence_claims) if evidence_claims else "- Research insufficient."}
"""
    banned = [
        "This section needs more specific evidence",
        "No grounded questions generated",
        "Just a moment",
        "in my previous role as",
        "aligning with expectations",
        "the key takeaway for you is",
        "No grounded item available",
        "Research insufficient",
        "id: S",
        "excerpt:",
        "source_type:",
    ]
    lowered = markdown.lower()
    found = []
    for needle in banned:
        if needle == "id: S":
            if re.search(r"(^|\s)id:\s*S\d*\b", markdown):
                found.append(needle)
            continue
        if needle.lower() in lowered:
            found.append(needle)
    if found:
        raise ValueError(f"Prep pack failed assembly validation: {', '.join(found)}")
    path = write_module_markdown(session_id, "prep_pack", markdown.strip())
    report_progress(progress_callback, "Prep pack complete", 100)
    return {"markdown": markdown.strip(), "path": str(path)}


def run_session_module(session, module_name, progress_callback=None):
    module_name = safe_path_part(module_name, "module")
    if module_name not in SESSION_MODULES:
        raise ValueError(f"Unknown module: {module_name}")
    local_results = {}
    local_progress_log = []
    results_token = _current_results.set(local_results)
    progress_token = _current_progress_log.set(local_progress_log)
    cost_records = start_cost_log()
    try:
        report_progress(progress_callback, f"{module_name} started", 1)
        if module_name == "company_intelligence":
            result = run_company_intelligence_module(session, progress_callback)
        elif module_name == "role_intelligence":
            result = run_role_intelligence_module(session, progress_callback)
        elif module_name == "candidate_profile":
            result = run_candidate_profile_module(session, progress_callback)
        elif module_name == "gap_map":
            result = run_gap_map_module(session, progress_callback)
        elif module_name == "interview_strategy":
            result = run_interview_strategy_module(session, progress_callback)
        elif module_name == "prep_pack":
            pack = run_prep_pack_module(session, progress_callback)
            return {
                "stage": "Prep pack complete",
                "markdown": pack["markdown"],
                "product_json": {"module_name": module_name, "session_id": session["session_id"]},
                "output_file": pack["path"],
            }
        artifact = module_artifact_path(session["session_id"], module_name)
        return {
            "stage": f"{module_name} complete",
            "markdown": "",
            "product_json": result,
            "output_file": str(artifact),
        }
    finally:
        log_cost_total(cost_records, f"{session['session_id']}/{module_name}")
        _current_progress_log.reset(progress_token)
        _current_results.reset(results_token)
