import os
import re
import json
import logging as _logging
import time
import urllib.request
import urllib.error
import contextvars
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from contextvars import ContextVar
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
import research_config

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MODEL_FAST = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
MODEL_STRATEGY = os.getenv("OPENAI_MODEL_STRATEGY", "gpt-4o-mini")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

_current_results = ContextVar("nailit_current_results", default=None)
_current_progress_log = ContextVar("nailit_current_progress_log", default=None)


def _active_progress_log():
    active = _current_progress_log.get()
    if active is None:
        raise RuntimeError("Pipeline progress state is not initialized for this job.")
    return active


def log(stage, message, status="running"):
    event = {
        "time": datetime.now().isoformat(),
        "stage": stage,
        "message": message,
        "status": status,
    }
    _active_progress_log().append(event)
    print(f"[Stage {stage}] {message}")


def report_progress(progress_callback, stage, progress):
    if progress_callback:
        progress_callback(stage, progress)


def submit_with_context(executor, fn, *args):
    """Submit to a thread pool while keeping this job's ContextVar state (results/progress log)."""
    return executor.submit(contextvars.copy_context().run, fn, *args)


def safe_path_part(value, fallback="item"):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "").strip("_")
    return safe[:80] or fallback


def normalize_text(text):
    text = text or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def trim_text(text, max_chars):
    text = normalize_text(text)
    if len(text) <= max_chars:
        return text
    head_len = int(max_chars * 0.62)
    tail_len = max_chars - head_len
    return text[:head_len] + "\n\n[Middle content trimmed after evidence extraction to stay within model limits.]\n\n" + text[-tail_len:]


class LLMError(RuntimeError):
    """Raised when the LLM call cannot produce output, so failures never leak into artifacts as text."""


def ask_llm(prompt, model=None, max_tokens=2400, retries=3):
    model = model or MODEL_FAST
    prompt = normalize_text(prompt)
    if not OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY is not set.")
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are Nailit, a premium private interview strategist. "
                            "You are evidence led, specific, practical, honest, and direct. "
                            "Do not invent facts. Separate official evidence from directional public themes. "
                            "Use candidate evidence whenever available."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.25,
                max_tokens=max_tokens,
                timeout=150,
            )
            return response.choices[0].message.content or ""
        except Exception as error:
            last_error = error
            if attempt < retries:
                time.sleep(3 * attempt)
    raise LLMError(f"LLM call failed after {retries} attempts: {last_error}")


JSON_PARSE_ERROR = "Could not parse model output as valid JSON"
JSON_PARSE_ERROR_KEY = "__nailit_parse_error__"


def extract_json(text):
    text = text or "{}"
    cleaned = text.strip()
    cleaned = re.sub(r"^```json", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"^```", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        cleaned = cleaned[first:last + 1]
    try:
        parsed = json.loads(cleaned)
        return json.dumps(parsed, indent=2)
    except Exception:
        return json.dumps({JSON_PARSE_ERROR_KEY: True, "error": JSON_PARSE_ERROR, "raw_output": text[:6000]}, indent=2)


def parse_json_object(text, fallback=None):
    fallback = fallback if fallback is not None else {}
    try:
        parsed = json.loads(extract_json(text))
    except Exception:
        return fallback
    if isinstance(parsed, dict) and parsed.get(JSON_PARSE_ERROR_KEY) is True:
        return fallback
    return parsed


def json_dumps(data):
    return json.dumps(data or {}, indent=2, ensure_ascii=False)


def ask_json(prompt, model=None, max_tokens=3000, retries=3, fallback=None):
    output = ask_llm(prompt, model=model, max_tokens=max_tokens, retries=retries)
    parsed = parse_json_object(output, fallback=fallback if fallback is not None else {})
    return parsed


STAGE_QUALITY_INSTRUCTION = (
    "Think carefully and thoroughly before producing output. Do not rush. "
    "You must produce substantive specific content for this candidate and this role. "
    "Generic content is a failure."
)


def source_host(url):
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "")
    except Exception:
        return ""


def classify_source(company_name, url, title, content, provided_type=""):
    provided_type = normalize_text(provided_type)
    type_map = {
        "official_company_source": "Official company source",
        "directional_glassdoor": "Glassdoor directional theme",
        "directional_reddit": "Reddit directional theme",
        "directional_blind": "Blind directional theme",
        "directional_linkedin": "LinkedIn directional theme",
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
    if company_name.lower() == "google" and ("google.com" in host or "abc.xyz" in host):
        return "Official company source"
    if "youtube.com" in host or "youtu.be" in host:
        return "YouTube public theme"
    if "reddit.com" in host:
        return "Reddit directional theme"
    if "glassdoor." in host:
        return "Glassdoor directional theme"
    if "blind.app" in host or "teamblind.com" in host:
        return "Blind directional theme"
    public_domains = ["linkedin.com", "medium.com", "substack.com", "prepfully.com", "igotanoffer.com", "levels.fyi", "interviewquery.com", "tryexponent.com", "gogotechy.com", "interviewkickstart.com"]
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


if __name__ == "__main__":
    smoke_test()


def source_record(source, index):
    content = normalize_text(source.get("content", ""))
    return {
        "id": f"S{index}",
        "title": source.get("title", ""),
        "url": source.get("url", ""),
        "source_type": source.get("source_type", ""),
        "confidence": source.get("source_confidence", ""),
        "query": source.get("query", ""),
        "excerpt": trim_text(content, 650),
    }


def jd_signal_texts(jd_analysis):
    rows = []
    for key in ["must_prove_signals", "jd_signals", "top_responsibilities", "dangerous_gaps", "hidden_expectations"]:
        for item in as_list((jd_analysis or {}).get(key)):
            if isinstance(item, dict):
                text = item.get("signal") or item.get("responsibility") or item.get("gap") or item.get("expectation") or item.get("risk") or item.get("question") or item.get("jd_anchor")
            else:
                text = item
            text = normalize_text(text)
            if text and text not in rows:
                rows.append(text)
    return rows


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


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def count_words(text):
    return len(re.findall(r"\b\w+\b", text or ""))


SESSION_MODULES = {
    "company_intelligence",
    "role_intelligence",
    "candidate_profile",
    "gap_map",
    "interview_strategy",
    "prep_pack",
}


def session_workspace(session_id, module_name=None):
    base = Path("jobs") / safe_path_part(session_id, "session")
    if module_name:
        base = base / safe_path_part(module_name, "module")
    base.mkdir(parents=True, exist_ok=True)
    return base


def module_artifact_path(session_id, module_name):
    filename = "prep_pack.md" if module_name == "prep_pack" else f"{module_name}.json"
    return session_workspace(session_id, module_name) / filename


def read_module_artifact(session_id, module_name):
    path = module_artifact_path(session_id, module_name)
    if not path.exists():
        raise FileNotFoundError(f"Required module artifact missing: {module_name}")
    if path.suffix == ".md":
        return path.read_text(encoding="utf8")
    content = path.read_text(encoding="utf8")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        raise ValueError(f"Artifact '{module_name}' is corrupted or unreadable")


def write_module_json(session_id, module_name, data):
    path = module_artifact_path(session_id, module_name)
    path.write_text(json_dumps(data), encoding="utf8")
    return path


def write_module_markdown(session_id, module_name, markdown):
    path = module_artifact_path(session_id, module_name)
    path.write_text(markdown, encoding="utf8")
    return path


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
    except urllib.error.HTTPError as e:
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
                if not url:
                    continue
                rows.append({
                    "title": item.get("title", ""),
                    "url": url,
                    "content": item.get("content", "") or item.get("snippet", ""),
                    "query": query,
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
    urls = urls[:20]
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
        # Glassdoor
        f'site:glassdoor.com "{c}" "{r}" interview questions',
        f'site:glassdoor.com "{c}" interview experience 2024 2025',
        f'site:glassdoor.com "{c}" interview rounds process',
        # Blind
        f'site:teamblind.com "{c}" interview process',
        f'site:teamblind.com "{c}" "{r}" interview',
        # Reddit
        f'site:reddit.com "{c}" "{r}" interview questions asked',
        f'site:reddit.com "{c}" interview experience 2024 2025',
        f'site:reddit.com "{c}" behavioral interview',
        # LinkedIn / Indeed
        f'site:linkedin.com/interview-questions "{c}" "{r}"',
        f'site:indeed.com "{c}" "{r}" interview questions',
        # Round-specific
        f'"{c}" behavioral interview STAR method questions',
        f'"{c}" googliness OR "culture fit" interview questions',
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


# ── ROUND DISCOVERY ──────────────────────────────────────────────────────────

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


# ── PER-ROUND DEEP RESEARCH ──────────────────────────────────────────────────

def build_round_queries(company, role, round_name, round_type, what_it_tests):
    """Generate 20 targeted search queries for a specific interview round."""
    c, r = company.strip(), role.strip()
    rn = round_name.strip()
    focus = what_it_tests[:80] if what_it_tests else rn

    base = [
        # Community — real questions reported for this exact round
        f'site:glassdoor.com "{c}" "{rn}" interview questions',
        f'site:glassdoor.com "{c}" "{r}" {rn} interview',
        f'site:teamblind.com "{c}" "{rn}" interview',
        f'site:reddit.com "{c}" "{rn}" interview questions asked',
        f'site:reddit.com "{c}" {rn} interview what they ask',
        f'site:linkedin.com/interview-questions "{c}" {rn}',
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

    community_types = {"Glassdoor directional theme", "Reddit directional theme",
                       "Blind directional theme", "LinkedIn directional theme",
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
    path = module_artifact_path(session_id, "company_intelligence")
    if path.exists() and time.time() - path.stat().st_mtime < 24 * 60 * 60:
        report_progress(progress_callback, "Company intelligence cache hit", 100)
        return json.loads(path.read_text(encoding="utf8"))
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
    result = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=6500, retries=2, fallback={})
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
    result = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=6500, retries=2, fallback={})
    write_module_json(session["session_id"], "role_intelligence", result)
    report_progress(progress_callback, "Role intelligence complete", 100)
    return result


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
    result = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=7600, retries=2, fallback={})
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
    result = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=7600, retries=2, fallback={})
    write_module_json(session_id, "gap_map", result)
    report_progress(progress_callback, "Gap map complete", 100)
    return result


ANSWER_BANNED_OPENINGS = [
    "while my manager was away",
    "in my previous role",
    "in my role as",
    "recognizing the need",
    "i identified that",
    "i faced a situation",
]

WHY_COMPANY_GENERIC_PHRASES = [
    "leader in innovation",
    "google is a leader in innovation",
    "i admire google's culture",
    "i admire google’s culture",
    "dynamic environment",
    "culture of innovation",
    "commitment to innovation",
    "innovation and excellence",
    "innovative practices",
    "collaboration across various teams",
    "enhancing employee experience",
]


def first_sentence(text):
    text = normalize_text(text)
    match = re.search(r"(.+?[.!?])(\s|$)", text)
    return match.group(1).strip() if match else text.split("\n", 1)[0].strip()


def starts_with_banned_opening(answer):
    opening = first_sentence(answer).lower()
    return any(opening.startswith(phrase) for phrase in ANSWER_BANNED_OPENINGS)


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
    rewritten = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=1400, retries=1).strip()
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
    data = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=5500, retries=1, fallback={"questions": []})
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


def why_company_is_generic(text):
    lowered = normalize_text(text).lower()
    if not lowered:
        return True
    return any(phrase in lowered for phrase in WHY_COMPANY_GENERIC_PHRASES)


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
    answer = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=1200, retries=1).strip()
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
    answer = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=400, retries=1).strip()
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
    result = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=15000, retries=2, fallback={})
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
    report_progress(progress_callback, "Interview strategy complete", 100)
    return result


def markdown_list(items):
    lines = []
    for item in as_list(items):
        if isinstance(item, dict):
            safe_parts = []
            for k, v in item.items():
                key = str(k).lower()
                if (
                    key in {"id", "excerpt", "source_type", "source_manifest"}
                    or key.endswith("_id")
                    or "source_id" in key
                    or v in ("", [], None)
                ):
                    continue
                label = str(k).replace("_", " ").strip().title()
                safe_parts.append(f"{label}: {v}")
            text = "; ".join(safe_parts)
        else:
            text = str(item)
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


def extract_source_numbers(raw_cv, raw_answer_bank):
    """Return the set of digit strings that appear literally in the candidate's own documents."""
    combined = (raw_cv or "") + " " + (raw_answer_bank or "")
    # Match standalone numbers possibly followed by % or units
    return set(re.findall(r"\b\d+(?:\.\d+)?\b", combined))


def strip_hallucinated_metrics(answer, raw_cv, raw_answer_bank):
    """
    Scan answer for number+unit patterns.  Replace any that don't appear in
    the candidate's source text with qualitative language.
    Returns (cleaned_answer, list_of_stripped_metrics).
    """
    source_numbers = extract_source_numbers(raw_cv, raw_answer_bank)
    stripped = []

    def _replace(match):
        full = match.group(0)
        digits = re.search(r"\d+(?:\.\d+)?", full)
        if not digits:
            return full
        num = digits.group(0)
        if num in source_numbers:
            return full
        # Qualitative replacements by suffix
        low = full.lower()
        stripped.append(full)
        if "%" in full or "percent" in low:
            return "significantly"
        if any(u in low for u in ("hour", "minute", "day", "week", "month")):
            return "meaningfully faster"
        if any(u in low for u in ("$", "dollar", "usd", "gbp", "€")):
            return "meaningfully"
        return "significantly"

    # Pattern: number optionally followed by %, unit words, or currency symbols.
    # Use lookahead/lookbehind instead of \b so the unit suffix is captured in the match.
    pattern = re.compile(
        r"(?<!\d)\$?\d+(?:\.\d+)?(?:\s*(?:%|percent|hours?|minutes?|days?|weeks?|months?))?(?!\d)",
        re.IGNORECASE,
    )
    cleaned = pattern.sub(_replace, answer)
    return cleaned, stripped


def answer_word_failures_from_strategy(strategy):
    failures = []
    for round_item in as_list(strategy.get("questions_by_round")):
        for item in as_list(round_item.get("questions") if isinstance(round_item, dict) else []):
            answer = item.get("complete_written_answer", "") if isinstance(item, dict) else ""
            words = count_words(answer)
            if words and words < 180:
                failures.append(item.get("question", "answer")[:120])
    return failures


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
        _current_progress_log.reset(progress_token)
        _current_results.reset(results_token)


if __name__ == "__main__":
    print("agent_v2 ready")

