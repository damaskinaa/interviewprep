import json
from datetime import datetime, timezone
import logging as _logging
import os
import re
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

from nailit.guards import why_company_is_generic
from nailit.llm import MODEL_STRONG, ask_json, json_dumps
from nailit.prep import research_config
from nailit.prep.common import (
    STAGE_QUALITY_INSTRUCTION,
    as_list,
    log,
    normalize_text,
    report_progress,
    submit_with_context,
    trim_text,
    write_module_json,
)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

def source_host(url):
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "")
    except Exception:
        return ""


def classify_source(company_name, url, title, content, provided_type=""):
    provided_type = normalize_text(provided_type)
    type_map = {
        "official_company_source": "Official company source",
        "directional_reddit": "Reddit directional theme",
        "directional_blind": "Blind directional theme",
        "directional_indeed": "Indeed directional theme",
        "directional_blog": "Blog directional theme",
        "directional_prep": "Public prep or candidate experience",
        "youtube_source": "YouTube public theme",
    }
    if provided_type in type_map:
        return type_map[provided_type]

    company_name = company_name or ""
    company_slug = re.sub(r"[^a-z0-9]+", "", company_name.lower())
    host = source_host(url)
    title_l = (title or "").lower()
    url_l = (url or "").lower()
    content_l = (content or "").lower()
    if not url or url in {"tavily_answer", "search_summary"}:
        return "Search summary"
    if company_slug and company_slug in re.sub(r"[^a-z0-9]+", "", host):
        return "Official company source"
    if "youtube.com" in host or "youtu.be" in host:
        return "YouTube public theme"
    if "reddit.com" in host:
        return "Reddit directional theme"
    if "blind.app" in host or "teamblind.com" in host:
        return "Blind directional theme"
    public_domains = ["medium.com", "substack.com", "prepfully.com", "igotanoffer.com", "levels.fyi", "interviewquery.com", "tryexponent.com", "gogotechy.com", "interviewkickstart.com"]
    if any(domain in host for domain in public_domains):
        return "Public prep or candidate experience"
    if "interview" in title_l or "interview" in content_l:
        return "High signal public source"
    if "hiring" in content_l or "careers" in url_l:
        return "High signal public source"
    return "Weak or background source"


def source_score(source_type, content):
    length = len(content or "")
    if source_type == "Official company source":
        return 5
    if source_type == "High signal public source":
        return 4
    if source_type in {"Public prep or candidate experience", "YouTube public theme", "Reddit directional theme", "Glassdoor directional theme", "Blind directional theme", "Blog directional theme"}:
        return 3
    if source_type == "Search summary":
        return 2
    if length > 500:
        return 2
    return 1


def canonical_source_key(url):
    url = normalize_text(url).lower()
    url = re.sub(r"\?.*$", "", url)
    url = re.sub(r"#.*$", "", url)
    url = url.rstrip("/")
    return url


BLOCKED_HOSTS = ("linkedin.com", "glassdoor.")


def is_blocked_source(url):
    """LinkedIn and Glassdoor are never scraped or fetched."""
    host = source_host(url)
    return any(blocked in host for blocked in BLOCKED_HOSTS)


def fetch_date():
    return datetime.now(timezone.utc).date().isoformat()


def source_record(source, index):
    content = normalize_text(source.get("content", ""))
    return {
        "id": f"S{index}",
        "title": source.get("title", ""),
        "url": source.get("url", ""),
        "source_type": source.get("source_type", ""),
        "confidence": source.get("source_confidence", ""),
        "query": source.get("query", ""),
        "fetched_at": source.get("fetched_at", ""),
        "excerpt": trim_text(content, 650),
    }


def company_domain_hint(company_name):
    name = normalize_text(company_name).lower()
    known = {
        "google": "google.com",
        "alphabet": "abc.xyz",
        "meta": "metacareers.com",
        "facebook": "metacareers.com",
        "amazon": "amazon.jobs",
        "stripe": "stripe.com",
        "canva": "canva.com",
        "atlassian": "atlassian.com",
        "hubspot": "hubspot.com",
        "openai": "openai.com",
        "notion": "notion.so",
        "datadog": "datadoghq.com",
    }
    for key, domain in known.items():
        if key in name:
            return domain
    slug = re.sub(r"[^a-z0-9]+", "", name)
    return f"{slug}.com" if slug else ""


def tavily_post(endpoint, payload, timeout=20):
    if not TAVILY_API_KEY:
        return {}
    data = json.dumps(payload).encode("utf8")
    req = urllib.request.Request(
        f"https://api.tavily.com/{endpoint}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TAVILY_API_KEY}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf8", errors="replace"))
    except urllib.error.HTTPError:
        raise  # let caller handle HTTP errors (e.g. 429)
    except Exception:
        return {}


def tavily_with_retry(query):
    """
    Call tavily_search with 429 rate-limit retry logic.
    Attempt 1 → on 429 wait 2s → Attempt 2 → on 429 wait 5s → Attempt 3 → log and return [].
    Never raises. Never crashes.
    """
    cfg = research_config.get_config()
    search_depth = cfg.get("search_depth", "basic")
    wait_schedule = [2, 5]  # seconds to wait before attempt 2, then attempt 3

    for attempt, wait in enumerate([-1] + wait_schedule):
        if wait >= 0:
            time.sleep(wait)
        try:
            if not TAVILY_API_KEY:
                return []
            data_bytes = json.dumps({
                "query": query,
                "search_depth": search_depth,
                "max_results": 8,
                "include_answer": False,
                "include_raw_content": False,
            }).encode("utf8")
            req = urllib.request.Request(
                "https://api.tavily.com/search",
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {TAVILY_API_KEY}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as res:
                parsed = json.loads(res.read().decode("utf8", errors="replace"))
            rows = []
            for item in parsed.get("results", []) if isinstance(parsed, dict) else []:
                url = item.get("url", "")
                if not url or is_blocked_source(url):
                    continue
                rows.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "content": item.get("content", "") or item.get("snippet", ""),
                    "query": query,
                    "fetched_at": fetch_date(),
                })
            return rows
        except urllib.error.HTTPError as e:
            if e.code == 429:
                if attempt < len(wait_schedule):
                    continue  # will sleep on next iteration
                # Third attempt also 429 — give up
                _logging.warning("tavily_with_retry: 429 on all 3 attempts for query=%r", query[:80])
                return []
            # Non-429 HTTP error — log and return empty
            _logging.warning("tavily_with_retry: HTTP %s for query=%r", e.code, query[:80])
            return []
        except Exception as exc:
            _logging.warning("tavily_with_retry: exception for query=%r — %s", query[:80], exc)
            return []
    return []


def tavily_search(query):
    """Thin wrapper — kept for backward compatibility with collect_company_research."""
    return tavily_with_retry(query)


def tavily_extract(urls):
    if not urls:
        return []
    # Tavily extract API rejects batches larger than 20 URLs
    urls = [url for url in urls if not is_blocked_source(url)][:20]
    try:
        data = tavily_post(
            "extract",
            {"urls": urls, "extract_depth": "basic"},
            timeout=20,
        )
    except Exception as exc:
        _logging.warning("tavily_extract: failed — %s", exc)
        return []
    rows = []
    for item in data.get("results", []) if isinstance(data, dict) else []:
        content = item.get("raw_content", "") or item.get("content", "")
        if content:
            rows.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "content": trim_text(content, 5000),
                "fetched_at": fetch_date(),
            })
    return rows


def collect_company_research(company_name, role_name):
    domain = company_domain_hint(company_name)
    c, r = company_name.strip(), role_name.strip()
    queries = [
        # Official
        f"{c} official interview process site:{domain}" if domain else f"{c} official interview process",
        f"{c} careers how we hire",
        f"{c} values leadership principles culture",
        f"{c} {r} job requirements 2025",
        # Blind
        f'site:teamblind.com "{c}" interview process',
        f'site:teamblind.com "{c}" "{r}" interview',
        # Reddit
        f'site:reddit.com "{c}" "{r}" interview questions asked',
        f'site:reddit.com "{c}" interview experience 2024 2025',
        f'site:reddit.com "{c}" behavioral interview',
        # Indeed
        f'site:indeed.com "{c}" "{r}" interview questions',
        # Round-specific
        f'"{c}" behavioral interview STAR method questions',
        f'"{c}" "culture fit" interview questions',
        f'"{c}" hiring manager interview questions',
        f'"{c}" cross functional stakeholder interview',
        # YouTube
        f'site:youtube.com "{c}" "{r}" interview preparation',
        f'site:youtube.com "{c}" interview questions mock',
    ]
    discovered = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_map = {submit_with_context(executor, tavily_search, query): query for query in queries}
        for future in as_completed(future_map, timeout=45):
            try:
                discovered.extend(future.result(timeout=2))
            except Exception:
                continue
    seen = set()
    unique = []
    for row in discovered:
        key = canonical_source_key(row.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        source_type = classify_source(company_name, row.get("url", ""), row.get("title", ""), row.get("content", ""))
        row["source_type"] = source_type
        row["source_confidence"] = "high" if source_type == "Official company source" else "medium" if "directional" in source_type.lower() or source_type in {"Glassdoor directional source", "Reddit directional source", "Blind directional source"} else "low"
        unique.append(row)
    unique.sort(key=lambda row: source_score(row.get("source_type", ""), row.get("content", "")), reverse=True)
    extract_urls = [
        row["url"] for row in unique[:50]
        if "youtube.com" not in row["url"].lower() and "youtu.be" not in row["url"].lower()
    ][:40]
    extracted = {canonical_source_key(row.get("url", "")): row for row in tavily_extract(extract_urls)}
    enriched = []
    for row in unique[:60]:
        key = canonical_source_key(row.get("url", ""))
        content = extracted.get(key, {}).get("content") or row.get("content", "")
        title = extracted.get(key, {}).get("title") or row.get("title", "")
        if any(blocked in normalize_text(f"{title} {content}").lower() for blocked in ["just a moment", "enable javascript", "access denied"]):
            continue
        row = dict(row)
        row["title"] = title
        row["content"] = trim_text(content, 5000)
        enriched.append(row)
    return enriched


def discover_interview_rounds(company_intelligence, role_intelligence, company_name, role_name):
    """
    Extract the confirmed/reported interview round structure from existing artifacts.
    Returns list of {round_name, round_type, what_it_tests, search_focus, confidence}.
    Used as the seed for per-round deep research.
    """
    rounds = []
    seen = set()

    def add(name, rtype, tests, focus, conf):
        key = normalize_text(name).lower()
        if key and key not in seen:
            seen.add(key)
            rounds.append({
                "round_name": name,
                "round_type": rtype,
                "what_it_tests": tests,
                "search_focus": focus,
                "confidence": conf,
            })

    # Pull from role_intelligence.interview_round_map (JD-inferred)
    for item in as_list(role_intelligence.get("interview_round_map")):
        if not isinstance(item, dict):
            continue
        name = normalize_text(item.get("round_name", ""))
        if not name:
            continue
        add(name, "jd_inferred", item.get("what_it_tests", ""), name, item.get("confidence", "inferred"))

    # Pull from company_intelligence.interview_process_signals (research-backed)
    for item in as_list(company_intelligence.get("interview_process_signals")):
        if not isinstance(item, dict):
            continue
        name = normalize_text(item.get("signal", "") or item.get("process_area", ""))
        if not name or len(name.split()) > 8:
            continue
        conf = item.get("source_type", "inferred")
        add(name, "company_intel", item.get("what_it_tests", ""), name, conf)

    # If we got nothing, fall back to standard known structure for major tech companies
    if not rounds:
        defaults = [
            ("Recruiter Screen",          "behavioral",   "Fit, motivation, comp, logistics",            "recruiter screen phone"),
            ("Hiring Manager Interview",   "behavioral",   "Leadership, execution, role fit",             "hiring manager interview questions"),
            ("Behavioral / Leadership",    "behavioral",   "STAR stories, leadership principles",         "behavioral leadership interview STAR"),
            ("Cross-functional Stakeholder","stakeholder", "Influence, alignment, conflict resolution",   "cross functional stakeholder interview"),
            ("Technical / Domain Screen",  "technical",    "Role-specific knowledge and execution",       "technical domain interview questions"),
            ("Culture / Values Fit",       "values",       "Company values alignment, googliness",        "culture fit values interview questions"),
        ]
        for name, rtype, tests, focus in defaults:
            add(name, rtype, tests, focus, "default_fallback")

    return rounds


def build_round_queries(company, role, round_name, round_type, what_it_tests):
    """Generate 20 targeted search queries for a specific interview round."""
    c, r = company.strip(), role.strip()
    rn = round_name.strip()
    focus = what_it_tests[:80] if what_it_tests else rn

    base = [
        # Community — real questions reported for this exact round
        f'site:teamblind.com "{c}" "{rn}" interview',
        f'site:reddit.com "{c}" "{rn}" interview questions asked',
        f'site:reddit.com "{c}" {rn} interview what they ask',
        f'site:indeed.com "{c}" {rn} interview questions',
        # Prep resources targeting this round
        f'"{c}" "{rn}" interview questions {r}',
        f'"{c}" {rn} interview preparation guide 2024 2025',
        f'"{c}" {rn} interview questions examples answers',
        # Behavioral / STAR targeting
        f'"{c}" {round_type} interview questions STAR method',
        f'"{c}" {focus} interview questions',
        f'{c} {rn} interview questions igotanoffer OR exponent',
        # YouTube for this round
        f'site:youtube.com "{c}" {rn} interview preparation',
        f'"{c}" {rn} interview tips mock answers',
    ]

    # Round-type specific additions
    if "behavioral" in round_type.lower() or "leadership" in round_type.lower():
        base += [
            f'"{c}" behavioral interview tell me about a time',
            f'"{c}" leadership interview STAR examples',
            f'"{c}" behavioral interview questions answers 2024',
            f'"{c}" tell me about a time {r}',
            f'"{c}" {r} behavioral interview failure conflict',
        ]
    elif "technical" in round_type.lower() or "domain" in round_type.lower():
        base += [
            f'"{c}" technical interview {r} questions',
            f'"{c}" {r} execution interview case study',
            f'"{c}" technical screen {r} preparation',
            f'"{c}" {r} technical questions metrics analytics',
            f'"{c}" {r} domain knowledge interview questions',
        ]
    elif "stakeholder" in round_type.lower() or "cross" in round_type.lower():
        base += [
            f'"{c}" stakeholder interview conflict resolution questions',
            f'"{c}" cross functional influence without authority interview',
            f'"{c}" {r} alignment prioritization interview',
            f'"{c}" stakeholder management interview STAR examples',
            f'"{c}" influencing without authority interview questions',
        ]
    elif "values" in round_type.lower() or "culture" in round_type.lower() or "googlin" in round_type.lower():
        base += [
            f'"{c}" culture interview values questions',
            f'"{c}" googliness interview questions examples',
            f'"{c}" culture fit interview what they ask',
            f'"{c}" values alignment interview questions 2024',
            f'"{c}" culture interview behavioral examples',
        ]
    else:
        base += [
            f'"{c}" {rn} interview frequently asked questions',
            f'"{c}" {rn} interview what to expect',
            f'"{c}" {rn} interview tips how to pass',
            f'"{c}" {r} {rn} common questions',
            f'"{c}" {rn} interview questions and answers',
        ]

    # Deduplicate
    seen_q = set()
    out = []
    for q in base:
        k = q.lower().strip()
        if k not in seen_q:
            seen_q.add(k)
            out.append(q)
    return out[:25]


def extract_round_reported_questions(sources):
    """
    Extract literal interview questions from community sources for a specific round.
    Matches both question-mark questions AND common imperative interview formats.
    """
    # Patterns that match real interview questions — both ? and imperative
    patterns = [
        re.compile(r'(?:^|\n|•|-|\d+[\).]\s*)([A-Z][^.!?\n]{15,200}\?)', re.M),
        re.compile(r'(?:^|\n|•|-|\d+[\).]\s*)((?:Tell|Describe|Walk|Give|Share|Explain|Talk|Think|What would|How would|What did|How did)[^.!?\n]{15,200})', re.M | re.I),
    ]
    seen = set()
    results = []

    community_types = {"Reddit directional theme", "Blind directional theme",
                       "Indeed directional theme", "Public prep or candidate experience"}

    for source in sources:
        if source.get("source_type") not in community_types:
            continue
        text = source.get("content", "") or source.get("snippet", "")
        if not text:
            continue
        for pat in patterns:
            for m in pat.finditer(text):
                q = m.group(1).strip().rstrip(".,;")
                if len(q.split()) < 5 or len(q.split()) > 50:
                    continue
                # Skip non-interview content
                if any(skip in q.lower() for skip in ["salary", "compensation", "relocation", "cookie", "privacy", "sign in", "log in", "subscribe", "click here"]):
                    continue
                key = re.sub(r'\s+', ' ', q.lower())
                if key not in seen:
                    seen.add(key)
                    results.append({"question": q, "source_url": source.get("url", ""), "source_type": source.get("source_type", "")})

    return results


def collect_per_round_research(company_name, role_name, round_name, round_type, what_it_tests):
    """
    Run targeted searches for ONE specific interview round.
    Search counts driven by research_config.get_config().
    Runs entirely on Daytona — no Vercel timeout constraint.
    """
    cfg = research_config.get_config()
    round_searches = cfg["round_searches"]
    round_extracts = cfg["round_extracts"]

    queries = build_round_queries(company_name, role_name, round_name, round_type, what_it_tests)
    queries = queries[:round_searches]
    log(5, f"Per-round research: {round_name} — {len(queries)} queries (tier={research_config.RESEARCH_TIER})", "running")

    discovered = []
    with ThreadPoolExecutor(max_workers=min(len(queries), 20)) as executor:
        future_map = {submit_with_context(executor, tavily_with_retry, q): q for q in queries}
        for future in as_completed(future_map, timeout=50):
            try:
                rows = future.result(timeout=2)
                discovered.extend(rows)
            except Exception:
                continue

    # Dedupe + classify
    seen = set()
    sources = []
    for row in discovered:
        key = canonical_source_key(row.get("url", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        source_type = classify_source(company_name, row.get("url", ""), row.get("title", ""), row.get("content", ""))
        row["source_type"] = source_type
        row["round_name"] = round_name
        sources.append(row)

    sources.sort(key=lambda s: source_score(s.get("source_type", ""), s.get("content", "")), reverse=True)

    # Extract full content — count driven by tier config
    extract_urls = [s["url"] for s in sources[:round_extracts * 10] if "youtube" not in s["url"]][:round_extracts * 5]
    extracted_map = {canonical_source_key(r.get("url", "")): r for r in tavily_extract(extract_urls)}

    enriched = []
    for s in sources[:40]:
        key = canonical_source_key(s.get("url", ""))
        full = extracted_map.get(key, {})
        s = dict(s)
        s["content"] = trim_text(full.get("content") or s.get("content", ""), 4000)
        if any(blocked in s["content"].lower() for blocked in ["just a moment", "enable javascript", "access denied"]):
            continue
        enriched.append(s)

    reported_questions = extract_round_reported_questions(enriched)
    log(5, f"Per-round research: {round_name} — {len(enriched)} sources, {len(reported_questions)} reported Qs", "done")

    return {
        "round_name": round_name,
        "round_type": round_type,
        "what_it_tests": what_it_tests,
        "sources": enriched,
        "reported_questions": reported_questions,
    }


def run_all_rounds_research(company_name, role_name, rounds):
    """
    Run per-round research for ALL rounds IN PARALLEL using ThreadPoolExecutor.
    Returns list of round_research dicts (one per round).
    """
    log(5, f"Starting per-round research for {len(rounds)} rounds", "running")
    results = []
    with ThreadPoolExecutor(max_workers=min(len(rounds), 6)) as executor:
        future_map = {
            submit_with_context(
                executor,
                collect_per_round_research,
                company_name, role_name,
                r["round_name"], r["round_type"], r["what_it_tests"],
            ): r["round_name"]
            for r in rounds
        }
        for future in as_completed(future_map, timeout=180):
            round_name = future_map[future]
            try:
                result = future.result(timeout=5)
                results.append(result)
                log(5, f"Round research done: {round_name}", "done")
            except Exception as e:
                log(5, f"Round research failed: {round_name} — {e}", "warning")
                results.append({"round_name": round_name, "sources": [], "reported_questions": []})
    return results


def run_company_intelligence_module(session, progress_callback=None):
    session_id = session["session_id"]
    report_progress(progress_callback, "Company research discovery", 15)
    sources = collect_company_research(session["company_name"], session["role_name"])
    report_progress(progress_callback, "Company signal extraction", 55)
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Build company_intelligence.json for a serious interview intelligence tool.

Company: {session["company_name"]}
Role: {session["role_name"]}

Raw JD:
{trim_text(session.get("raw_jd"), 10000)}

Company context:
{trim_text(session.get("raw_company_context"), 8000) or "None supplied."}

YouTube transcripts:
{trim_text(session.get("raw_youtube_transcripts"), 14000) or "No transcripts provided."}

Research sources:
{trim_text(json_dumps([source_record(source, i) for i, source in enumerate(sources, start=1)]), 22000)}

Return valid JSON only with this exact structure:
{{
  "official_company_signals": [{{"signal": "", "source_url": "", "confidence": "high", "basis": ""}}],
  "interview_process_signals": [{{"signal": "", "source_type": "officially confirmed | directional only | inferred", "confidence": "high | medium | low", "process_area": "", "what_it_tests": "", "rejection_signal": "", "hiring_signal": ""}}],
  "role_specific_signals": [{{"signal": "", "basis": "", "confidence": "high | medium | low"}}],
  "directional_themes": [{{"theme": "", "source_count": 0, "confidence": "medium | low", "label": "directional only"}}],
  "youtube_intelligence": {{"question_patterns": [], "success_themes": [], "failure_themes": [], "what_interviewers_look_for": [], "status": ""}},
  "gaps_in_research": []
}}

Rules:
Official company signals must be specific to this company, never generic.
Public community sources are directional only, never official.
If a field cannot be confirmed, say research insufficient and explain what is missing.
Do not invent source URLs.
Do not use page titles as claims.
"""
    result = ask_json(prompt, model=MODEL_STRONG, max_tokens=6500, retries=2, fallback={})
    known_urls = {normalize_text(source.get("url", "")) for source in sources if source.get("url")}
    for item in as_list(result.get("official_company_signals")):
        if not isinstance(item, dict):
            continue
        source_url = normalize_text(item.get("source_url", ""))
        if source_url and source_url not in known_urls:
            item["source_url"] = ""
            item["confidence"] = "medium"
            item["basis"] = (
                "Source URL was not present in the collected source manifest, so this is treated as a JD, "
                "company-context, or synthesis-supported signal rather than a proof-linked official source."
            )
    result["source_manifest"] = [
        {
            "title": source.get("title", ""),
            "url": source.get("url", ""),
            "source_type": source.get("source_type", ""),
            "confidence": source.get("source_confidence", ""),
            "fetched_at": source.get("fetched_at") or fetch_date(),
        }
        for source in sources[:40]
    ]
    write_module_json(session_id, "company_intelligence", result)
    report_progress(progress_callback, "Company intelligence complete", 100)
    return result


def run_role_intelligence_module(session, progress_callback=None):
    report_progress(progress_callback, "JD domain analysis", 20)
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Read the JD with extreme care. Use the JD only. Do not use company name, CV, answer bank, or research.

Raw JD:
{trim_text(session.get("raw_jd"), 24000)}

Return valid JSON only with this exact structure:
{{
  "role_domain": "",
  "must_prove": [{{"signal": "", "why_it_matters": "", "weak_answer": "", "strong_answer": ""}}],
  "hidden_expectations": [],
  "danger_zones": [{{"requirement": "", "why_candidates_struggle": "", "jd_basis": ""}}],
  "interview_round_map": [{{"round_name": "", "what_it_tests": "", "confidence": "inferred from JD", "jd_basis": ""}}],
  "question_seeds": [{{"question": "", "maps_to_jd_line_or_requirement": "", "competency": ""}}]
}}

Requirements:
role_domain must be the real domain in the JD text only.
must_prove must contain exactly 5 high-value role-specific signals.
question_seeds must contain exactly 20 specific questions derived directly from the JD.
"""
    result = ask_json(prompt, model=MODEL_STRONG, max_tokens=6500, retries=2, fallback={})
    write_module_json(session["session_id"], "role_intelligence", result)
    report_progress(progress_callback, "Role intelligence complete", 100)
    return result


def company_signal_text(signal):
    if isinstance(signal, dict):
        return normalize_text(signal.get("signal") or signal.get("theme") or signal.get("claim") or "")
    return normalize_text(signal)


def company_signal_has_source(signal):
    if not isinstance(signal, dict):
        return False
    return bool(normalize_text(signal.get("source_url") or signal.get("url")) or signal.get("source_count"))


def has_specific_company_signal(company_intelligence):
    signals = as_list(company_intelligence.get("official_company_signals"))
    themes = as_list(company_intelligence.get("directional_themes"))
    for item in signals + themes:
        text = company_signal_text(item)
        if len(text.split()) < 7:
            continue
        if why_company_is_generic(text):
            continue
        if company_signal_has_source(item) or isinstance(item, dict) and item.get("source_count"):
            return True
    return False
