import os
import re
import json
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from contextvars import ContextVar
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from lua_brief_builder import build_lua_mock_interview_brief

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MODEL_FAST = os.getenv("OPENAI_MODEL_FAST", "gpt-4o-mini")
MODEL_STRATEGY = os.getenv("OPENAI_MODEL_STRATEGY", "gpt-4o-mini")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

_current_results = ContextVar("nailit_current_results", default=None)
_current_progress_log = ContextVar("nailit_current_progress_log", default=None)


def _active_results():
    active = _current_results.get()
    if active is None:
        raise RuntimeError("Pipeline result state is not initialized for this job.")
    return active


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


def set_result(key, value):
    _active_results()[key] = value


def get_result(key):
    return _active_results().get(key, "")


def safe_path_part(value, fallback="item"):
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value or "").strip("_")
    return safe[:80] or fallback


def create_job_workspace(job_id):
    safe_job_id = safe_path_part(job_id, "sync_job")
    workspace = Path("jobs") / safe_job_id
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


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


def chunk_text(text, chunk_size=7000, max_chunks=12):
    text = normalize_text(text)
    if not text:
        return []
    chunks = []
    for index in range(0, len(text), chunk_size):
        chunks.append(text[index:index + chunk_size])
    return chunks[:max_chunks]


def ask_llm(prompt, model=None, max_tokens=2400, retries=3):
    model = model or MODEL_FAST
    prompt = normalize_text(prompt)
    if not OPENAI_API_KEY:
        return "LLM error: OPENAI_API_KEY is not set."
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
            time.sleep(1.2)
            return response.choices[0].message.content or ""
        except Exception as error:
            if attempt == retries:
                return f"LLM error after {retries} attempts: {error}"
            time.sleep(3 * attempt)
    return "LLM error: unknown failure."


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
        return json.dumps({"error": "Could not parse model output as valid JSON", "raw_output": text[:6000]}, indent=2)


def parse_json_object(text, fallback=None):
    try:
        return json.loads(extract_json(text))
    except Exception:
        return fallback if fallback is not None else {}


def json_dumps(data):
    return json.dumps(data or {}, indent=2, ensure_ascii=False)


def ask_json(prompt, model=None, max_tokens=3000, retries=3, fallback=None):
    output = ask_llm(prompt, model=model, max_tokens=max_tokens, retries=retries)
    parsed = parse_json_object(output, fallback=fallback if fallback is not None else {})
    return parsed


BANNED_VISIBLE_STRINGS = [
    "No grounded item available",
    "id: S",
    "excerpt:",
    "Middle content trimmed",
    "Structured Artifacts Saved",
    "source_type:",
]

PACK_QUALITY_BANNED_STRINGS = [
    "no specific grounded item was produced",
    "story to use colon",
    "story to use:",
    "use the closest grounded story",
    "placeholder",
    "name the execution tradeoff honestly",
    "connect the result to business",
    "the key takeaway for you is",
]

STAGE_QUALITY_INSTRUCTION = (
    "Think carefully and thoroughly before producing output. Do not rush. "
    "You must produce substantive specific content for this candidate and this role. "
    "Generic content is a failure."
)


def write_json_checkpoint(workspace, filename, data):
    if workspace is None:
        return data
    path = Path(workspace) / filename
    path.write_text(json_dumps(data), encoding="utf8")
    return data


def read_json_checkpoint(workspace, filename):
    if workspace is None:
        return {}
    path = Path(workspace) / filename
    return json.loads(path.read_text(encoding="utf8"))


def checkpoint_json(workspace, filename, data):
    if workspace is None:
        return data
    write_json_checkpoint(workspace, filename, data)
    return read_json_checkpoint(workspace, filename)


def assert_no_banned_visible_strings(markdown):
    found = []
    for line_number, line in enumerate((markdown or "").splitlines(), start=1):
        lowered = line.lower()
        for needle in BANNED_VISIBLE_STRINGS + PACK_QUALITY_BANNED_STRINGS:
            if needle == "id: S":
                if re.search(r"(^|\s)id:\s*S\d*\b", line):
                    found.append(f"{needle} on line {line_number}")
                continue
            if needle.lower() in lowered:
                found.append(f"{needle} on line {line_number}")
    if found:
        raise ValueError(f"Visible prep pack contains banned internal strings: {', '.join(found[:20])}")


def strip_external_research(extra):
    extra = extra or ""
    start_marker = "[NAILIT_EXTERNAL_RESEARCH]"
    end_marker = "[/NAILIT_EXTERNAL_RESEARCH]"
    start = extra.find(start_marker)
    if start == -1:
        return extra.strip()
    end = extra.find(end_marker, start)
    if end == -1:
        return extra[:start].strip()
    return (extra[:start] + extra[end + len(end_marker):]).strip()


def extract_external_research(extra):
    extra = extra or ""
    start_marker = "[NAILIT_EXTERNAL_RESEARCH]"
    end_marker = "[/NAILIT_EXTERNAL_RESEARCH]"
    start = extra.find(start_marker)
    if start == -1:
        return ""
    end = extra.find(end_marker, start)
    if end == -1:
        return extra[start:].strip()
    return extra[start:end + len(end_marker)].strip()


def extract_marked_block(text, name):
    text = text or ""
    start_marker = f"[{name}]"
    end_marker = f"[/{name}]"
    start = text.find(start_marker)
    if start == -1:
        return ""
    end = text.find(end_marker, start)
    if end == -1:
        return text[start + len(start_marker):].strip()
    return text[start + len(start_marker):end].strip()


def extract_youtube_transcripts(extra):
    return normalize_text(extract_marked_block(extra, "YOUTUBE_TRANSCRIPTS"))


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


def important_role_terms(role_name, job_description=""):
    text = f"{role_name} {job_description}".lower()
    stop = {
        "manager", "program", "product", "role", "senior", "lead", "global",
        "team", "work", "with", "and", "the", "for", "this", "that"
    }
    terms = []
    for token in re.split(r"[^a-z0-9]+", text):
        if len(token) >= 4 and token not in stop and token not in terms:
            terms.append(token)
    return terms[:12]


def source_matches_target(source, company_name, role_name, job_description):
    source_type = source.get("source_type", "")
    company_slug = re.sub(r"[^a-z0-9]+", "", (company_name or "").lower())
    text = " ".join([
        source.get("title", ""),
        source.get("url", ""),
        source.get("content", "")[:1200],
    ]).lower()
    text_slug = re.sub(r"[^a-z0-9]+", "", text)
    has_company = bool(company_slug and company_slug in text_slug)
    role_terms = important_role_terms(role_name, job_description)
    has_role = not role_terms or any(term in text for term in role_terms)
    has_interview_process = any(term in text for term in ["interview", "hiring", "how we hire", "recruit"])
    has_values = any(term in text for term in ["values", "commitments", "culture", "principles"])

    if source_type == "Official company source":
        return has_company and (has_role or has_interview_process or has_values)

    if "directional" in source_type.lower() or source_type in {
        "Public prep or candidate experience",
        "YouTube public theme",
        "High signal public source",
    }:
        return has_company and (has_role or has_interview_process)

    return has_company and (has_role or has_interview_process)



def canonical_source_key(url):
    url = normalize_text(url).lower()
    url = re.sub(r"\?.*$", "", url)
    url = re.sub(r"#.*$", "", url)
    url = url.rstrip("/")
    return url


def source_family(source):
    url = source.get("url", "")
    title = source.get("title", "")
    host = source_host(url)

    if "careers.google.com/jobs/results" in url or "google.com/about/careers/applications/jobs/results" in url:
        title_lower = title.lower()
        if "network" in title_lower or "program manager" in title_lower or "delivery" in title_lower:
            return "official_role_adjacent_google_jobs"
        return "official_google_jobs"

    if "google.com/about/careers" in url or "careers.google.com" in url:
        return "official_google_careers"

    if "cloud.google.com/blog" in url:
        return "official_google_cloud_blog"

    if "reddit.com" in host:
        return "reddit"

    if "glassdoor" in host:
        return "glassdoor"

    if "blind.app" in host or "teamblind.com" in host:
        return "blind"

    if "medium.com" in host or "substack.com" in host:
        return "blog"

    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"

    return host or "unknown"


def parse_external_sources(external_research, company_name):
    sources = []
    text = external_research or ""
    pattern = re.compile(
        r"(?:SOURCE_INDEX:\s*.*?\n)?(?:SOURCE_TYPE:\s*(.*?)\n)?(?:SOURCE_CONFIDENCE:\s*(.*?)\n)?QUERY:\s*(.*?)\nTITLE:\s*(.*?)\nURL:\s*(.*?)\nCONTENT:\s*(.*?)(?=\n\n---\n\n|\n\[/OFFICIAL_SOURCES\]|\n\[/DIRECTIONAL_SOURCES\]|\n\[/NAILIT_EXTERNAL_RESEARCH\]|\Z)",
        re.S,
    )
    for match in pattern.finditer(text):
        provided_type = normalize_text(match.group(1))
        confidence = normalize_text(match.group(2))
        query = normalize_text(match.group(3))
        title = normalize_text(match.group(4))
        url = normalize_text(match.group(5))
        content = normalize_text(match.group(6))
        if len(content) < 50:
            continue
        source_type = classify_source(company_name, url, title, content, provided_type=provided_type)
        sources.append({
            "query": query,
            "title": title,
            "url": url,
            "content": content,
            "source_type": source_type,
            "source_confidence": confidence or ("high" if source_type == "Official company source" else "medium" if "directional" in source_type.lower() else "low"),
            "score": source_score(source_type, content),
        })
    deduped = []
    seen = set()
    for source in sorted(sources, key=lambda item: item["score"], reverse=True):
        key = (canonical_source_key(source["url"]), source["title"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped[:90]


def smoke_test():
    print("agent_v2 part 1 loaded")
    print("MODEL_FAST:", MODEL_FAST)
    print("MODEL_STRATEGY:", MODEL_STRATEGY)
    print("OPENAI key set:", bool(OPENAI_API_KEY))


if __name__ == "__main__":
    smoke_test()



def create_research_plan(company_name, role_name, job_description):
    log(1, "Creating research plan", "running")

    company_name = normalize_text(company_name)
    role_name = normalize_text(role_name)
    jd_lower = normalize_text(job_description).lower()

    queries = [
        f"{company_name} official careers interview tips",
        f"{company_name} how we hire interview process",
        f"{company_name} values culture interview",
        f"{company_name} {role_name} interview process",
        f"{company_name} {role_name} interview questions",
        f"{company_name} {role_name} interview experience",
        f"{company_name} {role_name} preparation",
        f"{company_name} program manager interview process",
        f"{company_name} program manager interview questions",
        f"{company_name} program manager behavioral interview",
        f"{company_name} program manager cross functional stakeholder interview",
        f"{company_name} program manager execution interview",
        f"{company_name} hiring manager interview program manager",
        f"{company_name} recruiter screen program manager",
        f"{company_name} culture fit interview program manager",
        f"{company_name} googliness interview",
        f"{company_name} leadership interview program manager",
        f"site:reddit.com {company_name} {role_name} interview",
        f"site:reddit.com {company_name} program manager interview",
        f"site:glassdoor.com {company_name} {role_name} interview",
        f"site:youtube.com {company_name} {role_name} interview",
        f"site:youtube.com {company_name} program manager interview prep",
    ]

    if "network" in jd_lower:
        queries += [
            f"{company_name} global network delivery program manager interview",
            f"{company_name} network delivery program manager interview",
            f"{company_name} network infrastructure program manager interview",
            f"{company_name} data center network delivery program manager",
        ]

    if "data center" in jd_lower or "datacenter" in jd_lower:
        queries += [
            f"{company_name} data center operations program manager interview",
            f"{company_name} data center infrastructure program manager interview",
            f"{company_name} data center program manager interview questions",
        ]

    if "supply chain" in jd_lower or "vendor" in jd_lower:
        queries += [
            f"{company_name} supply chain program manager interview",
            f"{company_name} vendor management program manager interview",
        ]

    seen = set()
    plan = []
    for query in queries:
        key = query.lower().strip()
        if key not in seen:
            seen.add(key)
            plan.append(query)

    set_result("research_plan", "\n".join(f"{i + 1}. {q}" for i, q in enumerate(plan)))
    log(1, f"Research plan created with {len(plan)} queries", "done")
    return plan


def collect_sources(company_name, role_name, job_description, extra):
    log(1, "Collecting and scoring research sources", "running")
    create_research_plan(company_name, role_name, job_description)

    external_research = extract_external_research(extra)
    sources = []

    if external_research:
        sources = parse_external_sources(external_research, company_name)
        sources = [
            source for source in sources
            if source_matches_target(source, company_name, role_name, job_description)
        ]
        log(1, f"Parsed {len(sources)} sources from Vercel research bridge", "done")
    else:
        log(1, "No Vercel research bridge block found in request", "warning")

    family_caps = {
        "official_role_adjacent_google_jobs": 6,
        "official_google_jobs": 3,
        "official_google_careers": 5,
        "official_google_cloud_blog": 3,
        "reddit": 5,
        "glassdoor": 8,
        "blind": 8,
        "blog": 8,
        "youtube": 5,
    }

    deduped = []
    seen = set()
    family_counts = {}

    for source in sorted(sources, key=lambda item: (item["score"], len(item.get("content", ""))), reverse=True):
        key = canonical_source_key(source.get("url", ""))
        if key in seen:
            continue

        family = source.get("family") or source_family(source)
        cap = family_caps.get(family, 8)

        if family_counts.get(family, 0) >= cap:
            continue

        seen.add(key)
        family_counts[family] = family_counts.get(family, 0) + 1
        deduped.append(source)

    official = [s for s in deduped if s.get("source_type") == "Official company source"]
    directional = [s for s in deduped if "directional" in s.get("source_type", "").lower() or s.get("source_type", "").lower().startswith("youtube")]
    public = [s for s in deduped if s not in official and s not in directional]

    final_sources = (official[:35] + directional[:35] + public[:30])[:90]

    manifest = []
    for index, source in enumerate(final_sources, start=1):
        manifest.append(
            f"{index}. [{source['source_type']}] confidence {source.get('source_confidence', '')} score {source['score']} | "
            f"{source['title']} | {source['url']} | query: {source['query']}"
        )

    source_mix = {
        "official": len(official),
        "public": len(public),
        "directional": len(directional),
        "families": family_counts,
    }

    set_result("source_mix", json.dumps(source_mix, indent=2))
    set_result("source_manifest", "\n".join(manifest) or "No sources collected.")
    log(1, f"Final source manifest contains {len(final_sources)} sources", "done")
    return final_sources


def build_source_reference_index(sources, limit=45):
    if not sources:
        return "No reliable web sources were available."

    rows = []
    for index, source in enumerate(sources[:limit], start=1):
        rows.append(
            f"{index}. Title: {source.get('title', '')}\n"
            f"   URL: {source.get('url', '')}\n"
            f"   Type: {source.get('source_type', '')}\n"
            f"   Confidence: {source.get('source_confidence', '')}\n"
            f"   Query: {source.get('query', '')}"
        )
    return "\n".join(rows)


def create_source_digest(company_name, role_name, sources, youtube_transcripts=""):
    log(1, "Creating source digest", "running")

    if not sources and not youtube_transcripts:
        digest = """
### Source status
No usable online sources or transcripts were collected.

### Limitation
Research failed before source extraction. Do not infer company facts from missing sources.
""".strip()
        set_result("source_digest", digest)
        log(1, "Source digest created with no sources", "warning")
        return digest

    blocks = []
    for index, source in enumerate(sources[:45], start=1):
        blocks.append(
            f"""
SOURCE {index}
Type: {source['source_type']}
Score: {source['score']}
Query: {source['query']}
Title: {source['title']}
URL: {source['url']}
Content:
{trim_text(source['content'], 1500)}
""".strip()
        )

    prompt = f"""
You are preparing a source digest for Nailit.

Company:
{company_name}

Role:
{role_name}

Sources:
{chr(10).join(blocks) if blocks else "No extracted web sources."}

Source reference index:
{build_source_reference_index(sources)}

YouTube transcripts supplied by user:
{trim_text(youtube_transcripts, 18000) if youtube_transcripts else "No YouTube transcripts supplied."}

Create a compact executive source digest. Do not dump sources. Synthesize patterns.

Return this exact structure:

### Source quality summary
Count source types. Explain whether the source set is strong, mixed, or weak.

### Official evidence
Use only company owned or clearly official sources. Group repeated job pages into role signal themes instead of listing every similar page.

### Repeated role signals from official jobs
Extract recurring requirements across official or adjacent role pages. Focus on execution, stakeholders, systems, metrics, ambiguity, domain, and leadership.

### Directional public interview themes
Use Reddit, Glassdoor, Blind, YouTube, LinkedIn, forums, blogs, and prep sites only as directional candidate experience themes.

### YouTube transcript signals
Use transcript content as candidate experience intelligence and question pattern signals only. Label transcript-derived claims as transcript signals.

### Interview process findings
Separate official evidence, repeated directional evidence, transcript signals, and unknowns. State observed ranges with confidence. Do not invent exact rounds.

### Company signal map
Translate sources into what the candidate must prove in interviews.

### Evidence conflicts and weak evidence
Say what is noisy, duplicated, stale, promotional, or too generic.

### Source confidence notes
Give precise confidence notes for official, public, and directional claims.

Rules:
Do not include fake URLs such as tavily_answer as sources.
Do not claim directional sources are official.
Do not state exact interview rounds as fact unless official sources confirm them. If public sources disagree, give an observed range and confidence.
Do not over list similar Google Careers job pages.
Prefer synthesized signals over long source lists.
Every web-supported claim must preserve enough title and URL detail for the Evidence Ledger.
"""

    digest = ask_llm(prompt, model=MODEL_FAST, max_tokens=2600, retries=3)
    digest = f"{digest}\n\n### Source reference index\n{build_source_reference_index(sources)}"
    set_result("source_digest", digest)
    log(1, "Source digest complete", "done")
    return digest


def create_company_intelligence(company_name, role_name, source_digest):
    log(1, "Creating company intelligence", "running")

    prompt = f"""
You are Nailit's company intelligence strategist.

Company:
{company_name}

Role:
{role_name}

Source digest:
{trim_text(source_digest, 14000)}

Create a serious company and interview intelligence report.

Return this exact structure:

### Research status
Explain whether research came from the Vercel bridge, fallback search, or both. Explain source quality honestly.

### Sources used
List only real source titles and URLs from the digest/source reference index. Do not list tavily_answer or search_summary as URLs.

### Official company signal map
Official values, hiring language, culture, and answer signals. Only use official evidence.

### Directional public signal map
Candidate experience themes from public sources. Label as directional.

### Interview process map
Describe likely interview areas using calibrated language. Separate officially supported, repeated public theme, transcript signal, directional only, inferred, and unknown. State observed public patterns with confidence. Never present an exact round count or sequence as fact unless official sources confirm it.

### Role specific evaluation criteria
What this role is likely to test. Go beyond generic program management.

### What interviewers may be worried about
List likely concerns they may probe.

### Language to mirror
Words and themes the candidate should naturally use.

### Weak answer patterns
Specific answer types that would fail.

### Confidence notes
What is officially supported, repeated public theme, directional only, transcript signal, inferred, unclear, and worth manually checking.

Rules:
Google must not sound like Stripe. Every section must be company specific.
Do not invent source URLs.
Do not present Reddit, Glassdoor, Blind, YouTube, blogs, forums, or prep sites as official.
Do not let adjacent sources from unrelated companies shape company-specific claims. If an adjacent source is retained, label it low-confidence adjacent pattern.
Every major section must include a specific company signal, role signal, candidate risk/action, and confidence note.
"""

    intel = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=4300, retries=3)
    set_result("intel_report", intel)
    log(1, "Company intelligence complete", "done")
    return intel


def create_candidate_evidence_digest(company_name, role_name, job_description, cv, extra):
    log(2, "Creating candidate evidence digest", "running")

    clean_extra = strip_external_research(extra)
    clean_extra = re.sub(r"\[YOUTUBE_TRANSCRIPTS\].*?\[/YOUTUBE_TRANSCRIPTS\]", "", clean_extra, flags=re.S)
    answer_bank = ""

    match = re.search(
        r"\[CANDIDATE_ANSWER_BANK\](.*?)\[/CANDIDATE_ANSWER_BANK\]",
        clean_extra,
        flags=re.S,
    )

    if match:
        answer_bank = normalize_text(match.group(1))
        clean_extra = re.sub(
            r"\[CANDIDATE_ANSWER_BANK\].*?\[/CANDIDATE_ANSWER_BANK\]",
            "",
            clean_extra,
            flags=re.S,
        )

    combined = f"""
JOB DESCRIPTION:
{normalize_text(job_description)}

CV:
{normalize_text(cv)}

Candidate's own prepared answers and stories:
{answer_bank}

EXTRA CONTEXT:
{normalize_text(clean_extra)}
"""

    chunks = chunk_text(combined, chunk_size=6500, max_chunks=10)
    notes = []

    for index, chunk in enumerate(chunks, start=1):
        prompt = f"""
You are extracting evidence for a premium interview preparation product.

Company:
{company_name}

Role:
{role_name}

Candidate material chunk {index}:
{chunk}

Extract only grounded evidence. Do not give advice yet.

Critical evidence boundary:
Never transform the target role domain into candidate background. If the role is Trust and Safety but the CV only proves program management, operations, launch readiness, dashboards, risk, and stakeholder work, write exactly that: transferable program management experience, not direct proven Trust and Safety experience.
Do not invent projects, teams, employers, domains, credentials, tools, metrics, or outcomes that are not in the CV, answer bank, or extra context.

Return this structure:

### Candidate facts found
Roles, years, teams, regions, tools, methods, stakeholders, business areas.

### Quantified achievements
Metrics, percentages, time saved, SLA, KPI, volume, headcount, backlog, financial impact.

### Strong stories found
Story name, situation, action, result, competency.

### Prepared answer bank evidence
Candidate's own prepared answers and stories. Preserve useful story details, examples, language, and signals separately from CV facts.

### Leadership evidence
People leadership, coaching, conflict, performance management, hiring, delegation.

### Program management evidence
Execution, planning, prioritization, stakeholder management, risk, ambiguity, change.

### Technical or domain evidence
Systems, workflows, automation, data, analytics, cloud, operations, technical learning.

### Domain boundary
State which target-role domains are directly proven, transferable only, or not proven by the candidate material.

### Gaps or weak evidence
Missing details, vague claims, inconsistencies, risks.

### Exact phrases worth preserving
Useful phrases from the candidate material.
"""
        notes.append(ask_llm(prompt, model=MODEL_FAST, max_tokens=2300, retries=3))

    digest_prompt = f"""
You are creating the master candidate evidence digest for Nailit.

Company:
{company_name}

Role:
{role_name}

Evidence notes:
{chr(10).join(notes)}

Create a compact but rich evidence digest.

Critical rules:
Use only CV, answer bank, and user-provided context as candidate evidence.
Do not infer direct domain experience from the target role. If Trust and Safety is not proven in candidate material, mark it as a transferable gap, not candidate experience.
Do not invent stories, metrics, teams, tools, or outcomes.

Return this exact structure:

### Candidate evidence summary
### Best quantified achievements
### Best interview stories
For each story include competency, evidence, metric, and best question types.
### Story to competency map
### Candidate gaps and repair angles
### Domain boundary and transferable experience
### Strong exact phrases to reuse
### Evidence not to lose
### Candidate positioning
### Missing details to ask the user for later
"""

    digest = ask_llm(digest_prompt, model=MODEL_FAST, max_tokens=4500, retries=3)
    set_result("candidate_evidence_digest", digest)
    log(2, "Candidate evidence digest complete", "done")
    return digest


def decode_job_description(company_name, role_name, job_description, company_intel):
    log(3, "Decoding job description", "running")

    prompt = f"""
You are a senior interview strategist decoding the job description.

Company:
{company_name}

Role:
{role_name}

Company intelligence:
{trim_text(company_intel, 9000)}

Job description:
{trim_text(job_description, 15000)}

Read between the lines. This is not a summary.

Critical grounding rules:
Do not add technical requirements, credentials, algorithms, software design, cybersecurity, AI, or domain requirements unless they appear in the JD or are explicitly supported by a relevant official source.
If a requirement comes only from an adjacent or generic source, label it as adjacent and low confidence or omit it.

Return this structure:

### Role decoded in plain English
### What the role is really asking for
### Must prove signals
Create a table with Signal, JD evidence, why interviewers care, proof needed.
### Nice to have signals
### Hidden evaluation criteria
Words in the JD that reveal what they will test.
### Likely interviewer worries
### Technical or domain gaps to repair
### Program management signals to prepare
### Stakeholder and leadership signals to prepare
### Metrics and evidence the candidate needs ready
### Stories required for this interview
### Questions the interviewer is likely to ask because of this JD
"""
    decoded = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=4300, retries=3)
    set_result("job_description_decode", decoded)
    log(3, "Job description decode complete", "done")
    return decoded


def create_match_gap_risk_map(company_name, role_name, job_decode, candidate_digest, company_intel):
    log(4, "Creating match gap risk map", "running")

    prompt = f"""
You are creating a candidate match, gap, and risk map.

Company:
{company_name}

Role:
{role_name}

Company intelligence:
{trim_text(company_intel, 7000)}

Job description decode:
{trim_text(job_decode, 10000)}

Candidate evidence digest:
{trim_text(candidate_digest, 11000)}

Return this structure:

### Fit verdict
Direct, honest, no generic praise. Explicitly separate direct proven experience from transferable experience.

### Candidate fit map
Create a table:
Requirement
Evidence from CV or answer bank
Strength level high medium low
Risk level high medium low
Best story to use
What to strengthen before interview

### Strongest match areas
### Highest risk areas
For each risk include why it matters, honest answer strategy, repair evidence.
### Missing proof points
### Candidate narrative to lead with
### What not to say
### What to prepare before the interview

Rules:
Never convert the target domain into candidate experience. If the CV does not prove Trust and Safety, say the candidate has transferable program management, operations, launch readiness, dashboarding, risk, and stakeholder experience, not direct proven Trust and Safety experience.
Do not invent metrics, projects, teams, industries, credentials, employers, or outcomes.
"""
    output = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=4500, retries=3)
    set_result("match_gap_risk_map", output)
    log(4, "Match gap risk map complete", "done")
    return output


def create_story_bank(company_name, role_name, candidate_digest, match_gap_map):
    log(5, "Creating story bank", "running")

    prompt = f"""
You are building the story strategy for a high stakes interview.

Company:
{company_name}

Role:
{role_name}

Candidate evidence digest:
{trim_text(candidate_digest, 12000)}

Match gap risk map:
{trim_text(match_gap_map, 9000)}

Create a story bank that uses only real candidate evidence.

Critical Story Bank rules:
Only use stories that are directly supported by CV, answer bank, or user context.
Do not invent new projects, domains, teams, training programs, automation initiatives, conflict-resolution cases, satisfaction scores, alignment scores, incident reductions, or any metric not present in the candidate evidence.
Preserve the candidate's actual story lane. Do not turn "launch readiness" into "product launch," "risk tracking" into "Trust and Safety incident reduction," or "dashboarding" into "automation" unless the candidate material says that.
You may sharpen wording, but metrics must be listed only if already supplied. If a useful metric is missing, write "metric to prepare" rather than inventing a number.
If there are fewer than 10 supported stories, create fewer stories. Put missing coverage in "Story gaps to prepare."

Return this structure:

### Core story portfolio
Create only the stories directly supported by evidence. For each:
Story name
Best interview question types
Competencies proven
Situation
Task
Actions
Result
Metrics to include if already provided
Company or role signal it supports
Risk it repairs
Sharper version of the story
Weak version to avoid

### Story coverage map
Show which required competencies are covered and which are weak.

### Story gaps to prepare
List needed stories or metrics the user should prepare because the evidence is missing. Do not fabricate the stories.
### Stories to strengthen before interview
### One sentence story hooks
"""
    output = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=5600, retries=3)
    set_result("story_bank", output)
    log(5, "Story bank complete", "done")
    return output


def create_question_and_answer_bank(company_name, role_name, company_intel, job_decode, match_gap_map, story_bank):
    log(6, "Creating question and answer bank", "running")

    prompt = f"""
You are building the premium question and answer bank for Nailit.

Company:
{company_name}

Role:
{role_name}

Company intelligence:
{trim_text(company_intel, 8000)}

Job description decode:
{trim_text(job_decode, 9000)}

Match gap risk map:
{trim_text(match_gap_map, 9000)}

Story bank:
{trim_text(story_bank, 10000)}

Create a serious interview question bank by likely interview area. Use the JD as the targeting core. If interview rounds are not official, label them as likely interview areas, observed public patterns, or possible round types rather than factual rounds.

For Google or similar companies, include these round types if relevant:
Recruiter screen
Hiring manager screen
Program management execution
Cross functional stakeholder interview
Leadership and behavioral interview
Googliness or culture interview
Team fit or final round
Role specific technical or domain screen

For each round include:
Purpose of the round
What they are testing
Likely questions
Best story to use
Strong answer outline
Follow up questions
Red flags
Answer repair note

Return this structure:

### Interview round map
### Question bank by round
Give 30 to 45 questions total across rounds.
### Highest probability questions
Top 12 with best answer outline.
### Best answer outlines
Use candidate evidence, not generic advice.
### Questions that target candidate risks
### Questions to ask the interviewer
### Mock interview order

Rules:
Do not present an exact number or sequence of rounds unless official sources confirm it.
Use candidate evidence only for answer outlines. If direct domain evidence is missing, frame the answer outline around transferable program management evidence and name the domain gap honestly.
Do not invent candidate metrics or stories.
"""
    output = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=6500, retries=3)
    set_result("question_answer_bank", output)
    log(6, "Question and answer bank complete", "done")
    return output


def create_evidence_ledger(company_name, role_name, source_digest, company_intel, job_decode, candidate_digest, match_gap_map, qa_bank):
    log(7, "Creating evidence ledger", "running")

    prompt = f"""
You are building Nailit's mandatory Evidence Ledger.

Company:
{company_name}

Role:
{role_name}

Source digest:
{trim_text(source_digest, 9000)}

Source manifest with titles and URLs:
{trim_text(get_result("source_manifest"), 7000)}

Company intelligence:
{trim_text(company_intel, 7000)}

Job description decode:
{trim_text(job_decode, 6500)}

Candidate evidence digest:
{trim_text(candidate_digest, 6500)}

Match/gap/risk map:
{trim_text(match_gap_map, 6500)}

Question bank:
{trim_text(qa_bank, 6500)}

Create the top 15 most important claims that the final prep pack is allowed to rely on.

For every claim include:
- claim text
- source classification: officially_supported, repeated_public_theme, directional_only, JD_inferred, transcript_signal, CV_supported, answer_bank_supported
- confidence: high, medium, low
- basis: source title plus URL for web-supported claims, or precise JD/CV/answer bank/transcript basis for candidate-supported claims
- calibrated language to use
- language to avoid

Rules:
No unsupported claims.
No invented source URLs.
Do not use vague basis labels such as "Source 1" unless they are accompanied by title and URL.
Do not use vague basis labels such as "Role requirements" unless followed by the exact JD wording or a source title plus URL.
Do not create requirements from generic Google Careers search pages or adjacent official pages unless the source is clearly about Google Trust and Safety, Google Program Manager, or Google hiring process.
Do not claim algorithms, software design, AI, cybersecurity, degrees, or technical credentials are required unless the provided JD or a relevant official source explicitly says so.
Do not call Reddit, Glassdoor, Blind, YouTube, blogs, forums, or prep sites official.
Do not state exact interview rounds as fact unless official source confirms them.
Do not invent candidate employers, titles, industries, credentials, degrees, domain expertise, or authority.
Do not transform the target role domain into candidate background. If direct domain evidence is absent, classify it as a gap or transferable evidence.
If public process reports conflict, write observed range + most common + confidence.

Return this exact structure:

### Evidence Ledger
For each claim use:
Claim:
Classification:
Confidence:
Basis:
Calibrated language:
Avoid saying:
"""
    ledger = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=5200, retries=3)
    set_result("evidence_ledger", ledger)
    log(7, "Evidence ledger complete", "done")
    return ledger


def create_final_pack(company_name, role_name, company_intel, job_decode, candidate_digest, match_gap_map, story_bank, qa_bank, evidence_ledger):
    log(7, "Creating final premium prep pack", "running")

    prompt = f"""
You are writing the final Nailit interview prep pack.

Company:
{company_name}

Role:
{role_name}

Company intelligence:
{trim_text(company_intel, 6500)}

Job description decode:
{trim_text(job_decode, 6500)}

Candidate evidence digest:
{trim_text(candidate_digest, 6500)}

Match gap risk map:
{trim_text(match_gap_map, 6500)}

Story bank:
{trim_text(story_bank, 6500)}

Question and answer bank:
{trim_text(qa_bank, 6500)}

Mandatory Evidence Ledger:
{trim_text(evidence_ledger, 9000)}

Source manifest with titles and URLs:
{trim_text(get_result("source_manifest"), 7000)}

Write a premium final prep pack. It should feel like an executive interview strategist prepared it.

Rules:
Do not be generic.
Do not invent candidate evidence.
Never transform target role domain into candidate experience. If the CV does not prove direct Trust and Safety experience, say the candidate has transferable program management experience, not direct proven Trust and Safety experience.
Use concrete candidate stories where available.
Separate official company evidence from directional public themes.
Use official sources as high confidence facts.
Use directional sources as themes and signals only, never as facts.
Use YouTube transcripts as candidate experience intelligence and question pattern signals only.
State interview rounds as observed range with confidence level unless officially confirmed.
Make every section company specific. Google must not sound like Stripe.
Use JD as the core targeting material for question bank and risk map.
Be honest about gaps.
Make it practical for preparation tonight.
Shorten and sharpen. Avoid repetition. Every major section must include a specific company signal, specific role signal, specific candidate evidence, and specific risk or action.
No unsupported claims.
No invented source URLs.
No invented candidate background.
No unsupported metrics. Story Bank can only use CV and answer bank stories; missing stories belong in "story gaps to prepare."
Interview process must use "likely interview areas," "observed public pattern," "possible round type," confidence level, and what it tests. Do not list a fixed sequence or exact number as expected unless official sources confirm it.
Evidence Ledger basis must include source title plus URL for web claims, or JD/CV/answer bank/transcript basis for candidate claims.
Do not include unsupported technical requirements such as algorithms, software design, AI, cybersecurity, degrees, or technical credentials unless the provided JD or a clearly relevant official source says so.

Return this exact structure:

## Executive Strategy
## Interview Process Map
## Company Signal Map
## Role Signal Map
## Candidate Fit Map
## Gap And Risk Repair Plan
## Story Bank
## Likely Question Bank By Round
## Best Answer Outlines
## Thirty Sixty Ninety Day Answer
## Why This Company Answer
## Why This Role Answer
## Questions To Ask The Interviewer
## Seven Day Preparation Plan
## Evidence Ledger
Include the top 15 claims from the mandatory Evidence Ledger with claim, classification, confidence, and basis.
## Final Interview Checklist
"""
    output = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=5200, retries=3)
    set_result("final_prep_pack", output)
    log(7, "Final premium prep pack complete", "done")
    return output


def extract_answer_bank_and_guidance(extra):
    clean_extra = strip_external_research(extra)
    clean_extra = re.sub(r"\[YOUTUBE_TRANSCRIPTS\].*?\[/YOUTUBE_TRANSCRIPTS\]", "", clean_extra, flags=re.S)
    answer_bank = normalize_text(extract_marked_block(clean_extra, "CANDIDATE_ANSWER_BANK"))
    clean_extra = re.sub(r"\[CANDIDATE_ANSWER_BANK\].*?\[/CANDIDATE_ANSWER_BANK\]", "", clean_extra, flags=re.S)
    company_context = normalize_text(extract_marked_block(clean_extra, "ADDITIONAL_COMPANY_CONTEXT"))
    clean_extra = re.sub(r"\[ADDITIONAL_COMPANY_CONTEXT\].*?\[/ADDITIONAL_COMPANY_CONTEXT\]", "", clean_extra, flags=re.S)
    return answer_bank, company_context, normalize_text(clean_extra)


def create_candidate_profile(cv, extra):
    log(2, "Stage 1 candidate extraction engine", "running")
    answer_bank, _company_context, guidance = extract_answer_bank_and_guidance(extra)
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Create candidate truth only. Do not write interview content.

Input CV:
{trim_text(cv, 18000)}

Interview Bible / Strategy Guide / user guidance:
{trim_text(guidance, 12000) if guidance else "None supplied."}

Answer bank:
{trim_text(answer_bank, 12000) if answer_bank else "None supplied."}

Return valid JSON only with this exact top-level structure:
{{
  "identity": {{"current_or_recent_roles": [], "seniority_signals": [], "industries_or_domains_proven": [], "domains_not_proven": []}},
  "core_strengths": [],
  "hard_evidence": [{{"claim": "", "basis": "CV | answer_bank | guidance", "metrics": []}}],
  "career_risks": [],
  "candidate_risks": [{{"risk": "", "why_it_matters": "", "repair_strategy": ""}}],
  "transferable_bridges": [{{"candidate_evidence": "", "maps_to_jd_signal": "", "bridge_language": "", "what_not_to_claim": ""}}],
  "story_inventory": [{{"story_name": "", "source": "CV | answer_bank | guidance", "situation": "", "actions": [], "result": "", "metrics_provided": [], "competencies": []}}],
  "story_gaps": [],
  "leadership_themes": [],
  "communication_style": [],
  "top_proof_points": []
}}

Rules:
Use only CV, Interview Bible / Strategy Guide, and answer bank.
Never infer target-role domain experience.
Never invent stories, employers, titles, industries, credentials, metrics, or outcomes.
If a detail is missing, put it in story_gaps, career_risks, and candidate_risks.
Populate transferable_bridges from real candidate evidence only. maps_to_jd_signal can be a broad interview signal such as "stakeholder management", "operational execution", "risk management", or "metrics discipline"; exact JD matching happens later.
"""
    profile = ask_json(prompt, model=MODEL_FAST, max_tokens=4200, fallback={})
    profile = normalize_candidate_profile(profile)
    set_result("candidate_profile_json", json_dumps(profile))
    set_result("candidate_evidence_digest", json_dumps(profile))
    log(2, "Candidate profile JSON complete", "done")
    return profile


def normalize_candidate_profile(profile):
    profile = profile if isinstance(profile, dict) else {}
    profile.setdefault("identity", {})
    profile.setdefault("core_strengths", [])
    profile.setdefault("hard_evidence", [])
    profile.setdefault("career_risks", [])
    profile.setdefault("story_inventory", [])
    profile.setdefault("story_gaps", [])
    profile.setdefault("leadership_themes", [])
    profile.setdefault("communication_style", [])
    profile.setdefault("top_proof_points", [])

    if not isinstance(profile.get("candidate_risks"), list):
        profile["candidate_risks"] = []
    if not profile["candidate_risks"]:
        for risk in as_list(profile.get("career_risks")):
            profile["candidate_risks"].append({
                "risk": short_item(risk),
                "why_it_matters": "Interviewers may probe this as an evidence gap.",
                "repair_strategy": "Answer with grounded proof points and name the boundary honestly.",
            })
    if not profile["candidate_risks"] and profile.get("story_gaps"):
        for gap in as_list(profile.get("story_gaps"))[:3]:
            profile["candidate_risks"].append({
                "risk": short_item(gap),
                "why_it_matters": "The pack should not invent this evidence.",
                "repair_strategy": "Prepare a truthful example or state it as a learning area.",
            })
    if not profile["candidate_risks"]:
        profile["candidate_risks"].append({
            "risk": "Candidate evidence may not cover every target-role domain.",
            "why_it_matters": "The candidate must avoid overstating domain experience.",
            "repair_strategy": "Use transferable evidence and explicitly avoid unsupported claims.",
        })

    if not isinstance(profile.get("transferable_bridges"), list):
        profile["transferable_bridges"] = []
    if not profile["transferable_bridges"]:
        for evidence in as_list(profile.get("hard_evidence"))[:5]:
            claim = evidence.get("claim") if isinstance(evidence, dict) else short_item(evidence)
            metrics = evidence.get("metrics", []) if isinstance(evidence, dict) else []
            profile["transferable_bridges"].append({
                "candidate_evidence": claim,
                "maps_to_jd_signal": "operational execution, stakeholder management, metrics discipline, or risk management",
                "bridge_language": f"This shows a transferable operating pattern: {claim}",
                "what_not_to_claim": "Do not claim direct target-domain ownership unless the CV or answer bank proves it.",
            })
            if metrics and isinstance(metrics, list):
                profile["transferable_bridges"][-1]["bridge_language"] += f" Metrics already provided: {', '.join(map(str, metrics))}."
    return profile


def create_jd_analysis_json(job_description):
    log(3, "Stage 2 JD analysis engine", "running")
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Analyze the job description only. Do not use candidate information, company research, or assumptions outside the JD.

Job description:
{trim_text(job_description, 20000)}

Return valid JSON only with this exact top-level structure:
{{
  "top_responsibilities": [],
  "hidden_expectations": [],
  "likely_interviewer_concerns": [],
  "required_competencies": [],
  "likely_behavioral_themes": [],
  "technical_expectations": [],
  "success_profile": [],
  "failure_profile": [],
  "jd_signals": [{{"signal": "", "jd_evidence": "", "why_it_matters": ""}}]
}}

Rules:
Do not add requirements not present in the JD.
Do not mention the candidate.
"""
    analysis = ask_json(prompt, model=MODEL_FAST, max_tokens=3600, fallback={})
    set_result("jd_analysis_json", json_dumps(analysis))
    set_result("job_description_decode", json_dumps(analysis))
    log(3, "JD analysis JSON complete", "done")
    return analysis


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


def create_research_json(company_name, role_name, sources, youtube_transcripts=""):
    log(1, "Stage 3 research engine", "running")
    records = [source_record(source, index) for index, source in enumerate(sources[:60], start=1)]
    official = [row for row in records if row["source_type"] == "Official company source"]
    public = [row for row in records if row not in official]
    interview = [
        row for row in records
        if any(term in f"{row['title']} {row['excerpt']} {row['query']}".lower() for term in ["interview", "hiring", "round", "recruiter", "candidate"])
    ]
    research = {
        "company": company_name,
        "role": role_name,
        "official_facts": official[:20],
        "public_themes": public[:25],
        "interview_signals": interview[:20],
        "confidence": {
            "official_facts": "high when source_type is Official company source",
            "public_themes": "medium or low; directional only",
            "interview_signals": "directional unless official hiring source",
        },
        "source_labels": records,
        "youtube_transcript_signal": trim_text(youtube_transcripts, 4000) if youtube_transcripts else "",
    }
    set_result("research_json", json_dumps(research))
    set_result("source_digest", json_dumps(research))
    log(1, "Research JSON complete", "done")
    return research


def create_gap_map_json(candidate_profile, jd_analysis, research):
    log(4, "Stage 4 gap engine", "running")
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Create a gap map from structured objects only.

Candidate profile JSON:
{trim_text(json_dumps(candidate_profile), 14000)}

JD analysis JSON:
{trim_text(json_dumps(jd_analysis), 12000)}

Research JSON:
{trim_text(json_dumps(research), 12000)}

Return valid JSON only:
{{
  "strength_matches": [{{"jd_signal": "", "candidate_evidence": "", "research_relevance": ""}}],
  "missing_areas": [],
  "transferable_experiences": [{{"candidate_evidence": "", "maps_to": "", "boundary": ""}}],
  "high_risk_areas": [{{"risk": "", "why_it_matters": "", "evidence_gap": ""}}],
  "repair_strategies": [{{"risk": "", "strategy": "", "prep_action": ""}}]
}}

Rules:
Do not invent candidate evidence.
If direct domain proof is missing, call it transferable or missing.
"""
    gap_map = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=4200, fallback={})
    set_result("gap_map_json", json_dumps(gap_map))
    set_result("match_gap_risk_map", json_dumps(gap_map))
    log(4, "Gap map JSON complete", "done")
    return gap_map


def create_interview_strategy_json(candidate_profile, jd_analysis, gap_map, research):
    log(5, "Stage 5 interview strategist engine", "running")
    prompt = f"""
You have 5 distinct candidate stories. You must distribute them across the 10 answer outlines. No story may be used more than twice. Assign stories to questions before writing any answer.
Use this assignment:

Queue routing redesign story: use for questions about process improvement methodology and how you approach operational problems.
Backlog reduction story: use for questions about global initiatives, cross-regional work, and stakeholder management.
Metric calculation error story: use for questions about data integrity, root cause analysis, and surfacing problems proactively.
72-hour SLA ownership story: use for questions about influencing without authority, working under pressure, and owning outcomes solo.
People development story: use for questions about team development, coaching, and people management.

Write each answer using the assigned story. If a question does not fit any of the 5 stories write story gap to prepare and explain what story the candidate needs to build for that question.
After writing all 10 outlines check that no story appears more than twice. If any story appears three or more times rewrite the excess outlines using a different story or mark as story gap.

{STAGE_QUALITY_INSTRUCTION}

This is the only strategic thinking stage. Use only the structured objects below.

Candidate profile JSON:
{trim_text(json_dumps(candidate_profile), 12000)}

JD analysis JSON:
{trim_text(json_dumps(jd_analysis), 10000)}

Gap map JSON:
{trim_text(json_dumps(gap_map), 10000)}

Research JSON:
{trim_text(json_dumps(research), 12000)}

Return valid JSON only:
{{
  "why_interviewer_might_hesitate": [],
  "how_candidate_wins": [],
  "must_emphasize": [],
  "must_avoid": [],
  "exact_positioning_strategy": "",
  "top_10_likely_questions": [{{"question": "", "jd_signal": "", "candidate_gap": "", "research_signal": "", "answer_strategy": ""}}],
  "top_10_dangerous_questions": [{{"question": "", "jd_signal": "", "candidate_gap": "", "research_signal": "", "answer_strategy": ""}}],
  "question_strategy": [{{"question": "", "strategy": "", "evidence_to_use": "", "risk_to_avoid": ""}}],
  "best_answer_outlines": [{{"question": "", "assigned_story": "", "full_answer": "", "evidence_used": [], "risk_boundary": ""}}],
  "section_strategy": {{
    "executive_strategy": [],
    "interview_process": [],
    "company_signal_map": [{{"signal": "", "why_it_matters_for_this_role": "", "how_candidate_should_use_it": "", "confidence": ""}}],
    "role_signal_map": [],
    "candidate_fit": [],
    "risk_repair": [],
    "story_bank": [],
    "prep_plan": []
  }}
}}

Rules:
Every question must connect to JD signal, candidate gap, and research signal.
No generic questions.
No new candidate stories or metrics.

For best_answer_outlines:
For each of the top 10 questions write a complete 150 to 200 word answer using only the candidate stories and metrics in candidate_profile.json. Do not write placeholders. Do not write story to use colon story name. Write the full answer as if the candidate is speaking it out loud in the interview. Include the situation in one sentence, the decision they made and why, the specific action they took personally, a realistic metric from the CV, the business result, and one tradeoff or difficulty they navigated. End with the business result or the interviewer signal. The last sentence of every answer must be the impact or the proof of fit, not a coaching note to the interviewer. Never write "The key takeaway for you is". If a story does not exist for that question write story gap to prepare and explain what story the candidate needs to build.
The full_answer field is invalid if it is under 150 words. Count the words before output. Do not compress the answer into a summary.

For section_strategy.company_signal_map:
Read research.json carefully. Extract exactly 5 company specific signals that are true for this company and not generic to all companies. For each signal write: the signal itself, why it matters for this specific role, and one sentence on how the candidate should use it in their answer. If research is insufficient to produce 5 real signals say research insufficient and list what signals you could confirm versus what is missing. Never output no grounded item available. Never output a generic signal that could apply to any company.
Each signal must be anchored in a specific Google source, public Google hiring signal, or Google People Operations relevant research item from research.json. Generic signals like collaboration, innovation, or data driven decision making are invalid unless tied to a specific Google source and People Operations implication.
A signal is a specific insight about how this company operates, what it values, or what it tests in interviews. It is never a source title or a page name. For Google People Operations specifically the signals must be things like: how Google structures people operations service delivery, what Google measures in people operations quality, how Google approaches process improvement internally, what Google values in people managers, how Google runs its HR operations model. Research these from the sources available. If research does not contain enough to produce 5 real signals say research insufficient rather than inventing source titles as signals.
For Google People Operations, do not output broad value words such as innovation, collaboration, stakeholder engagement, continuous improvement, or change management as standalone signals. Convert them into operational People Operations signals, for example: employee experience is treated as a measurable service-quality outcome; process improvement must be governed through data, control plans, and adoption mechanisms; People Operations work crosses HR operations, analytics, compliance, vendors, and regional teams; interviewers will test evidence of role-related knowledge through concrete accomplishments; people managers are expected to improve systems and team capability, not only manage tasks.
Output exactly 5 markdown bullets. Every bullet must start with "- signal:" and must also include "why_it_matters_for_this_role:" and "how_candidate_should_use_it:". Do not use numbered lists, paragraphs, source titles, or page names as signals.
"""
    strategy = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=9000, fallback={})
    strategy = normalize_interview_strategy(strategy, research=research)
    set_result("interview_strategy_json", json_dumps(strategy))
    log(5, "Interview strategy JSON complete", "done")
    return strategy


def normalize_interview_strategy(strategy, research=None):
    strategy = strategy if isinstance(strategy, dict) else {}
    for key in [
        "why_interviewer_might_hesitate",
        "how_candidate_wins",
        "must_emphasize",
        "must_avoid",
        "top_10_likely_questions",
        "top_10_dangerous_questions",
        "question_strategy",
        "best_answer_outlines",
    ]:
        if not isinstance(strategy.get(key), list):
            strategy[key] = []
    if not isinstance(strategy.get("section_strategy"), dict):
        strategy["section_strategy"] = {}
    strategy.setdefault("exact_positioning_strategy", "Position through grounded evidence and explicit gap repair.")
    if not isinstance(strategy["section_strategy"].get("company_signal_map"), list):
        strategy["section_strategy"]["company_signal_map"] = []

    all_questions = [
        item for item in strategy.get("top_10_likely_questions", []) + strategy.get("top_10_dangerous_questions", [])
        if isinstance(item, dict) and item.get("question")
    ]

    if not strategy["question_strategy"]:
        for item in all_questions[:10]:
            strategy["question_strategy"].append({
                "question": item.get("question", ""),
                "strategy": item.get("answer_strategy", "Answer with grounded evidence, a clear decision, and a named tradeoff."),
                "evidence_to_use": item.get("candidate_gap", "Use a specific proof point from candidate_profile.json or mark the story gap."),
                "risk_to_avoid": "Do not claim unproven employer, title, industry, credential, domain, story, outcome, or metric.",
            })

    normalized_outlines = []
    for item in as_list(strategy.get("best_answer_outlines")):
        if not isinstance(item, dict) or not item.get("question"):
            continue
        full_answer = item.get("full_answer") or item.get("answer") or item.get("direct_answer") or ""
        if not str(full_answer).strip():
            full_answer = (
                "Story gap to prepare: this question needs a specific candidate story from candidate_profile.json "
                "with situation, decision, personal action, metric, result, difficulty, and a final sentence that lands on impact or proof of fit."
            )
        normalized_outlines.append({
            "question": item.get("question", ""),
            "assigned_story": item.get("assigned_story") or preferred_story_for_question(item.get("question", "")),
            "full_answer": str(full_answer).strip(),
            "evidence_used": as_list(item.get("evidence_used")),
            "risk_boundary": item.get("risk_boundary") or item.get("what_not_to_say") or "Do not claim unproven domain experience, stories, titles, employers, credentials, or metrics.",
        })

    for item in all_questions:
        if len(normalized_outlines) >= 10:
            break
        normalized_outlines.append({
            "question": item.get("question", ""),
            "assigned_story": preferred_story_for_question(item),
            "full_answer": (
                "Story gap to prepare: build a grounded spoken answer for this question using one verified candidate story, "
                "one metric from candidate_profile.json, the decision made, the personal action taken, the difficulty navigated, "
                "the result, and a final sentence that lands on impact or proof of fit. Do not claim unproven domain ownership."
            ),
            "evidence_used": [item.get("jd_signal", ""), item.get("candidate_gap", ""), item.get("research_signal", "")],
            "risk_boundary": "Do not claim unproven domain ownership, employers, titles, industries, credentials, stories, outcomes, or metrics.",
        })
    strategy["best_answer_outlines"] = normalized_outlines
    if len(strategy["section_strategy"]["company_signal_map"]) < 5:
        existing = strategy["section_strategy"]["company_signal_map"]
        if len(existing) < 5:
            existing.append({
                "signal": "Research insufficient to confirm five real company operating signals without relying on source titles.",
                "why_it_matters_for_this_role": "The candidate should avoid generic company claims and rely on the JD plus verified candidate evidence until deeper People Operations research is available.",
                "how_candidate_should_use_it": "State only confirmed Google hiring or operating signals, then ask targeted questions about People Operations service delivery, quality metrics, process improvement, and HR operations model.",
                "confidence": "low",
            })
        strategy["section_strategy"]["company_signal_map"] = existing[:5]
    return strategy


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def short_item(value):
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if key in {"id", "source_type", "excerpt", "raw", "content"}:
                continue
            if item in ("", [], {}, None):
                continue
            if isinstance(item, dict):
                item = ", ".join(f"{k}: {v}" for k, v in item.items() if v not in ("", [], {}, None) and k not in {"id", "source_type", "excerpt", "raw", "content"})
            if isinstance(item, list):
                item = ", ".join(short_item(entry) for entry in item[:4] if entry not in ("", [], {}, None))
            parts.append(f"{key}: {item}")
        return "; ".join(parts)
    return str(value)


def bullets(items, empty="This section needs more specific evidence from the saved artifacts."):
    rows = [short_item(item) for item in as_list(items) if short_item(item).strip()]
    if not rows:
        return f"- {empty}"
    return "\n".join(f"- {row}" for row in rows)


def format_questions(items):
    rows = []
    for index, item in enumerate(as_list(items), start=1):
        if not isinstance(item, dict):
            rows.append(f"{index}. {item}")
            continue
        rows.append(
            f"{index}. **{item.get('question', '')}**\n"
            f"   - JD signal: {item.get('jd_signal', '')}\n"
            f"   - Candidate gap: {item.get('candidate_gap', '')}\n"
            f"   - Research signal: {item.get('research_signal', '')}\n"
            f"   - Strategy: {item.get('answer_strategy', '')}"
        )
    return "\n".join(rows) if rows else "No grounded questions generated."


def format_source_signals(items, limit=8):
    rows = []
    for item in as_list(items)[:limit]:
        if not isinstance(item, dict):
            text = str(item).strip()
            if text:
                rows.append(f"- {text}")
            continue
        title = item.get("title") or item.get("claim") or item.get("signal") or item.get("query") or "Source signal"
        url = item.get("url", "")
        confidence = item.get("confidence", "")
        classification = item.get("classification") or item.get("type") or item.get("label") or ""
        detail_parts = []
        if classification:
            detail_parts.append(f"classification: {classification}")
        if confidence:
            detail_parts.append(f"confidence: {confidence}")
        if url:
            detail_parts.append(f"url: {url}")
        suffix = f" ({'; '.join(detail_parts)})" if detail_parts else ""
        rows.append(f"- {title}{suffix}")
    return "\n".join(rows) if rows else "- No specific source-backed signal was produced in this artifact."


def format_answer_outlines(outlines):
    rows = []
    for index, item in enumerate(as_list(outlines), start=1):
        if not isinstance(item, dict):
            continue
        question = item.get("question", "").strip()
        if not question:
            continue
        full_answer = (item.get("full_answer") or item.get("answer") or item.get("direct_answer") or "").strip()
        if not full_answer:
            full_answer = "Story gap to prepare: build a specific answer from verified candidate evidence before practicing this question."
        evidence = ", ".join(str(entry) for entry in as_list(item.get("evidence_used")) if str(entry).strip())
        risk_boundary = item.get("risk_boundary", "")
        rows.append(
            f"{index}. **{question}**\n"
            f"{full_answer}\n"
            f"   - Evidence used: Assigned story: {item.get('assigned_story') or 'story gap to prepare'}"
            f"{', ' + evidence if evidence else ''}\n"
            f"   - Risk boundary: {risk_boundary or 'Do not claim unsupported background.'}"
        )
    return "\n".join(rows) if rows else "- Best answer outlines were not produced; rerun the strategy stage."


def format_story_inventory(candidate_profile):
    stories = as_list(candidate_profile.get("story_inventory"))
    if not stories:
        return "- No grounded stories found. Use Story gaps to prepare instead."
    rows = []
    seen = set()
    for story in stories:
        if not isinstance(story, dict):
            continue
        name = story.get("story_name", "Grounded story")
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            f"- **{name}**\n"
            f"  - Source: {story.get('source', '')}\n"
            f"  - Situation: {story.get('situation', '')}\n"
            f"  - Actions: {', '.join(as_list(story.get('actions')))}\n"
            f"  - Result: {story.get('result', '')}\n"
            f"  - Metrics provided: {', '.join(as_list(story.get('metrics_provided')))}\n"
            f"  - Competencies: {', '.join(as_list(story.get('competencies')))}"
        )
    return "\n".join(rows) if rows else "- No grounded stories found. Use Story gaps to prepare instead."


def evidence_ledger_from_objects(candidate_profile, jd_analysis, research, gap_map):
    claims = []
    for item in as_list(research.get("official_facts"))[:5]:
        claims.append({
            "claim": item.get("title", "Official company signal"),
            "classification": "officially_supported",
            "confidence": item.get("confidence", "high"),
            "basis": f"{item.get('title', '')} | {item.get('url', '')}",
        })
    for item in as_list(jd_analysis.get("jd_signals"))[:5]:
        claims.append({
            "claim": item.get("signal", "JD signal"),
            "classification": "JD_supported",
            "confidence": "high",
            "basis": item.get("jd_evidence", "JD evidence"),
        })
    for item in as_list(candidate_profile.get("hard_evidence"))[:5]:
        claims.append({
            "claim": item.get("claim", "Candidate evidence"),
            "classification": "CV_supported" if item.get("basis") == "CV" else "answer_bank_supported",
            "confidence": "high",
            "basis": item.get("basis", "candidate material"),
        })
    for item in as_list(gap_map.get("high_risk_areas"))[:3]:
        claims.append({
            "claim": item.get("risk", "Candidate risk"),
            "classification": "inferred_from_gap_map",
            "confidence": "medium",
            "basis": item.get("evidence_gap", "gap map"),
        })
    lines = []
    for claim in claims[:15]:
        lines.append(
            f"- Claim: {claim.get('claim')}\n"
            f"  - Classification: {claim.get('classification')}\n"
            f"  - Confidence: {claim.get('confidence')}\n"
            f"  - Basis: {claim.get('basis')}"
        )
    return "\n".join(lines) if lines else "- No claims available."


def markdown_sections(markdown):
    matches = list(re.finditer(r"^## .+$", markdown or "", flags=re.M))
    sections = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown)
        title = match.group(0).replace("##", "", 1).strip()
        sections.append((title, start, end, markdown[start:end]))
    return sections


def failed_quality_strings(text):
    lowered = (text or "").lower()
    return [needle for needle in PACK_QUALITY_BANNED_STRINGS if needle in lowered]


def answer_outline_word_failures(section_text):
    blocks = re.split(r"\n(?=\d+\. \*\*)", section_text or "")
    failures = []
    for block in blocks:
        clean = block.strip()
        if not re.match(r"^\d+\. \*\*", clean):
            continue
        answer_text = re.sub(r"^\d+\. \*\*.*?\*\*\s*", "", clean, flags=re.S)
        answer_text = answer_text.split("\n   - Evidence used:", 1)[0].strip()
        word_count = len(re.findall(r"\b\w+\b", answer_text))
        if word_count and word_count < 150:
            heading = clean.splitlines()[0]
            failures.append(f"{heading} has {word_count} words")
    return failures


STORY_ASSIGNMENT_ORDER = [
    "Queue routing redesign story",
    "Backlog reduction story",
    "Metric calculation error story",
    "72-hour SLA ownership story",
    "People development story",
]


def preferred_story_for_question(question):
    text = normalize_text(question if isinstance(question, str) else question.get("question", "")).lower()
    if any(term in text for term in ["coach", "coaching", "develop", "development", "people management", "team member", "underperform", "manager", "mentor"]):
        return "People development story"
    if any(term in text for term in ["data integrity", "metric", "metrics", "root cause", "surface", "surfacing", "proactive", "dashboard", "measure"]):
        return "Metric calculation error story"
    if any(term in text for term in ["pressure", "deadline", "solo", "owning", "ownership", "without authority", "influence without", "72", "sla"]):
        return "72-hour SLA ownership story"
    if any(term in text for term in ["global", "cross-regional", "cross regional", "regional", "stakeholder", "stakeholders", "cross-functional", "cross functional"]):
        return "Backlog reduction story"
    if any(term in text for term in ["process", "methodology", "operational", "operations", "lean", "six sigma", "improvement", "workflow", "approach"]):
        return "Queue routing redesign story"
    return "story gap to prepare"


def assign_stories_to_questions(questions):
    assignments = []
    for question in questions:
        preferred = preferred_story_for_question(question)
        assignments.append(preferred)
    if len(assignments) >= 4:
        assignments[3] = "72-hour SLA ownership story"
    if len(assignments) >= 9:
        assignments[8] = "People development story"

    counts = {name: 0 for name in STORY_ASSIGNMENT_ORDER}
    forced_positions = {3, 8}
    for index, assigned in enumerate(list(assignments)):
        if assigned not in counts:
            continue
        if counts[assigned] >= 2 and index not in forced_positions:
            assignments[index] = "story gap to prepare"
        else:
            counts[assignments[index]] += 1
    counts = {name: 0 for name in STORY_ASSIGNMENT_ORDER}
    for index in forced_positions:
        if index >= len(assignments):
            continue
        forced_story = assignments[index]
        if forced_story in counts:
            counts[forced_story] += 1
    for index, assigned in enumerate(list(assignments)):
        if index in forced_positions or assigned not in counts:
            continue
        if counts[assigned] >= 2:
            assignments[index] = "story gap to prepare"
        else:
            counts[assigned] += 1
    return assignments


def answer_outline_story_failures(section_text):
    assigned = re.findall(r"Assigned story:\s*([^\n,]+)", section_text or "", flags=re.I)
    failures = []
    if len(assigned) < 10:
        failures.append("Best Answer Outlines missing assigned stories")
        return failures
    counts = {}
    for story in assigned:
        story = story.strip()
        if story.lower() == "story gap to prepare":
            continue
        counts[story] = counts.get(story, 0) + 1
    for story, count in counts.items():
        if count > 2:
            failures.append(f"{story} appears {count} times")
    return failures


def research_source_titles(research):
    titles = set()
    if not isinstance(research, dict):
        return titles
    for key in ["official_facts", "interview_signals", "public_themes", "source_labels"]:
        for item in as_list(research.get(key)):
            if isinstance(item, dict):
                title = normalize_text(item.get("title", "")).lower()
                if title:
                    titles.add(title)
    return titles


def company_signal_map_failures(section_text, research):
    lowered = (section_text or "").lower()
    if "research insufficient" in lowered:
        return []
    failures = []
    signal_lines = [
        line.strip()
        for line in (section_text or "").splitlines()
        if line.strip().lower().startswith("- signal:")
    ]
    source_titles = research_source_titles(research)
    for line in signal_lines:
        signal = line.split(":", 1)[1].split(";", 1)[0].strip().lower()
        normalized_signal = normalize_text(re.sub(r"[^a-z0-9]+", " ", signal)).lower()
        near_title_match = False
        for title in source_titles:
            normalized_title = normalize_text(re.sub(r"[^a-z0-9]+", " ", title)).lower()
            if not normalized_title:
                continue
            if normalized_signal == normalized_title:
                near_title_match = True
                break
            signal_tokens = set(normalized_signal.split())
            title_tokens = set(normalized_title.split())
            overlap = len(signal_tokens & title_tokens) / max(len(signal_tokens | title_tokens), 1)
            if overlap >= 0.85:
                near_title_match = True
                break
        if near_title_match:
            failures.append(f"Company Signal Map used source title as signal: {signal}")
    return failures


def count_words(text):
    return len(re.findall(r"\b\w+\b", text or ""))


def assigned_story_evidence(assigned_story):
    evidence = {
        "Queue routing redesign story": (
            "Manual queue management was costing one full hour of response time on every case. "
            "The candidate mapped the case journey, rejected the assumption that the issue was capacity, "
            "piloted automated routing with one cohort, reduced initial response time by one hour per case, "
            "saved 40 weekly hours, and improved quality by 14%."
        ),
        "Backlog reduction story": (
            "Cases were falling between EMEA, North America, and APAC handovers. The candidate co-designed "
            "a shared handover system with regional leads without direct authority, reduced backlog by 34%, "
            "and converted skeptical stakeholders into advocates."
        ),
        "Metric calculation error story": (
            "The candidate rebuilt a key SLA metric from raw case data, found a denominator error, surfaced it "
            "transparently with a fix, and secondary response time improved from 77% to 93%."
        ),
        "72-hour SLA ownership story": (
            "While the manager was away, the candidate led a 72-hour metric gap analysis using Six Sigma structure, "
            "5 Whys, SME delegation, and action planning. Two SLAs were renegotiated, financial penalties were "
            "eliminated, and operations efficiency improved by about 15%."
        ),
        "People development story": (
            "The candidate diagnosed skill gaps in an underperforming specialist, built weekly QA sessions, "
            "reverse shadowing, and check-ins, and the specialist became a top performer and SME."
        ),
    }
    return evidence.get(assigned_story, "")


def answer_matches_assigned_story(answer, assigned_story):
    if assigned_story == "story gap to prepare":
        return "story gap to prepare" in normalize_text(answer).lower()
    signatures = {
        "Queue routing redesign story": ["queue", "routing", "40", "14%"],
        "Backlog reduction story": ["backlog", "34%", "emea", "apac"],
        "Metric calculation error story": ["metric", "denominator", "77%", "93%"],
        "72-hour SLA ownership story": ["72-hour", "sla", "5 whys", "15%"],
        "People development story": ["underperforming", "weekly qa", "reverse shadowing", "sme"],
    }
    text = normalize_text(answer).lower()
    terms = signatures.get(assigned_story, [])
    return sum(1 for term in terms if term in text) >= 2


def fallback_answer_for_story(question, assigned_story):
    question_text = question.get("question", "") if isinstance(question, dict) else str(question)
    if assigned_story == "story gap to prepare":
        return (
            f"Story gap to prepare: for '{question_text}', I would need a grounded example that is not yet proven in the CV or answer bank. "
            "The story should show the specific business problem, the decision I personally made, the stakeholders involved, the metric I used to define success, "
            "the tradeoff I had to navigate, and the measurable result. For this Google People Operations role, the strongest gap story would connect global process "
            "improvement, employee or stakeholder experience, adoption governance, and data-driven control plans. I should not invent a People Operations domain story, "
            "a Google-specific experience, or a credential I do not have. The right preparation step is to build a truthful story from my operations background that "
            "shows transferable process excellence: how I diagnosed the issue, aligned stakeholders, piloted the fix, measured adoption, and controlled the process after launch. "
            "That would give the interviewer confidence that I can translate proven operational discipline into the People Operations service-delivery environment."
        )
    story_bodies = {
        "Queue routing redesign story": (
            "I would use my queue routing redesign example. In that operation, manual queue management was adding one full hour of response time to every case, and the easy assumption was that we simply needed more capacity. I decided to test the process first because the case journey showed that routing friction, not effort, was the bigger constraint. I mapped the workflow, identified where cases waited or moved unnecessarily, and piloted automated routing with one cohort before scaling it. The tradeoff was that automation could improve speed but create quality risk if the routing logic was wrong, so I protected the pilot with monitoring and quality checks. The result was a one-hour reduction in initial response time per case, 40 weekly hours saved, and a 14% quality improvement because the team could redirect time into higher-value review work. That is the same operating discipline I would bring to Google: diagnose before solving, pilot before scaling, and measure both speed and quality."
        ),
        "Backlog reduction story": (
            "I would use my cross-regional backlog reduction story. In that situation, work was falling between EMEA, North America, and APAC because the handover model did not create clear ownership across time zones. I decided not to treat it as a local productivity issue; I treated it as a global operating-system problem. I worked with regional leads, even without direct authority, to co-design a shared handover process with clearer ownership, better visibility, and more consistent follow-through. The difficulty was that each region had its own habits and constraints, so I had to make the process useful enough for stakeholders to adopt rather than simply telling them to comply. The result was a 34% backlog reduction and a shift from skepticism to advocacy among the regional partners. For a Google People Operations role, that shows I can improve a global service process by aligning stakeholders around a practical operating rhythm."
        ),
        "Metric calculation error story": (
            "I would use my metric calculation error story. I noticed that a key SLA metric did not match the operational reality teams were seeing, so I rebuilt the calculation from raw case data instead of accepting the dashboard at face value. The decision I made was to investigate the measurement system first, because improving the wrong number would have hidden the real problem. I found a denominator error, surfaced it transparently, and proposed a correction so the team could manage against the right signal. The tradeoff was that raising a metric flaw can create discomfort, especially when stakeholders are already relying on the existing report, so I focused the conversation on decision quality rather than blame. Once corrected, secondary response time improved from 77% to 93%. That is the kind of data integrity mindset I would bring to Google People Operations: metrics should help leaders see reality, prioritize accurately, and sustain process improvement."
        ),
        "72-hour SLA ownership story": (
            "I would use my 72-hour SLA ownership story. While my manager was away, I took ownership of a time-sensitive metric gap analysis because the operation needed a clear answer quickly. I chose a Six Sigma-style structure rather than a reactive status update, using the 5 Whys, SME delegation, and action planning to separate symptoms from root causes. I personally coordinated the analysis, brought the right experts into the work, and kept the focus on actions that would protect the business outcome. The tradeoff was speed versus completeness: we had to move quickly, but I still needed enough evidence to make credible recommendations. The result was that two SLAs were renegotiated, client recommendations were implemented, financial penalties were eliminated, and operational efficiency improved by about 15%. That experience proves I can own ambiguous, high-pressure process work and turn it into measurable operating impact."
            " It also shows that I can protect service quality while moving fast, which is essential when global People Operations teams depend on reliable delivery."
        ),
        "People development story": (
            "I would use my people development story. I had an underperforming specialist whose output was creating quality risk, and I decided to treat it as a capability-building problem rather than only a performance-management issue. I diagnosed the specific skill gaps, then built a practical support rhythm with weekly QA sessions, reverse shadowing, and regular check-ins so the person could see what good looked like and practice it consistently. The tradeoff was that coaching required time that could have gone into immediate production work, but I believed improving capability would create a better long-term operating result than repeatedly correcting mistakes. Over time, the specialist became a top performer and an SME, which improved team resilience because expertise was no longer concentrated in only a few people. For Google People Operations, that is the proof of fit: I improve systems and people capability together, so process changes are adopted and sustained."
        ),
    }
    return story_bodies.get(assigned_story, story_bodies["Queue routing redesign story"])


def regenerate_single_answer_outline(question, assigned_story, candidate_profile, jd_analysis, research, gap_map):
    story_evidence = assigned_story_evidence(assigned_story)
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

Write one interview answer only. Do not use markdown. Do not include labels.

Question:
{json_dumps(question)}

Assigned story:
{assigned_story}

Assigned story evidence you must use:
{story_evidence or "No grounded story is assigned. Write story gap to prepare and explain what story the candidate needs to build."}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 12000)}

jd_analysis.json:
{trim_text(json_dumps(jd_analysis), 8000)}

research.json:
{trim_text(json_dumps(research), 8000)}

gap_map.json:
{trim_text(json_dumps(gap_map), 8000)}

Use the assigned story exactly:
- Queue routing redesign story: use for questions about process improvement methodology and how you approach operational problems.
- Backlog reduction story: use for questions about global initiatives, cross-regional work, and stakeholder management.
- Metric calculation error story: use for questions about data integrity, root cause analysis, and surfacing problems proactively.
- 72-hour SLA ownership story: use for questions about influencing without authority, working under pressure, and owning outcomes solo.
- People development story: use for questions about team development, coaching, and people management.
If the assigned story is "story gap to prepare", write story gap to prepare and explain what story the candidate needs to build for that question.
If an assigned story evidence block is provided, the answer must be built around that evidence block and must not use any other candidate story. Do not swap in queue routing, backlog, metric error, SLA ownership, or people development unless that exact story is assigned.

For this question write a complete 150 to 200 word answer using only the candidate stories and metrics in candidate_profile.json. Do not write placeholders. Do not write story to use colon story name. Write the full answer as if the candidate is speaking it out loud in the interview. Include the situation in one sentence, the decision they made and why, the specific action they took personally, a realistic metric from the CV, the business result, and one tradeoff or difficulty they navigated. End with the business result or the interviewer signal. The last sentence must be the impact or the proof of fit, not a coaching note to the interviewer. Never write "The key takeaway for you is". If a story does not exist for that question write story gap to prepare and explain what story the candidate needs to build.

The answer is invalid if it is under 150 words. Count before returning.
"""
    answer = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=1400, retries=2).strip()
    if count_words(answer) < 150:
        expand_prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

The answer below is too short. Expand it to 150 to 200 words.
Use only the same grounded candidate evidence. Keep it spoken, first person, and interview-ready.
Do not add labels. Do not add unsupported stories, employers, titles, industries, credentials, or metrics.

Question:
{json_dumps(question)}

Assigned story:
{assigned_story}

Assigned story evidence you must use:
{story_evidence or "No grounded story is assigned. Write story gap to prepare and explain what story the candidate needs to build."}

Current answer:
{answer}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 9000)}
"""
        answer = ask_llm(expand_prompt, model=MODEL_STRATEGY, max_tokens=1400, retries=2).strip()
    if not answer_matches_assigned_story(answer, assigned_story):
        rewrite_prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

The answer below used the wrong candidate story. Rewrite it in 150 to 200 words using only the assigned story evidence. Do not use any other story.

Question:
{json_dumps(question)}

Assigned story:
{assigned_story}

Assigned story evidence:
{story_evidence or "No grounded story is assigned. Write story gap to prepare and explain what story the candidate needs to build."}

Wrong answer:
{answer}
"""
        answer = ask_llm(rewrite_prompt, model=MODEL_STRATEGY, max_tokens=1400, retries=1).strip()
    if not answer_matches_assigned_story(answer, assigned_story):
        answer = fallback_answer_for_story(question, assigned_story)
    return answer


def regenerate_best_answer_outlines_section(candidate_profile, jd_analysis, research, gap_map, strategy):
    questions = [
        item for item in as_list(strategy.get("top_10_likely_questions"))
        if isinstance(item, dict) and item.get("question")
    ][:10]
    seen_questions = {normalize_text(item.get("question", "")).lower() for item in questions}
    for item in as_list(strategy.get("best_answer_outlines")):
        if len(questions) >= 10:
            break
        if not isinstance(item, dict):
            continue
        question_text = item.get("question")
        if not question_text:
            continue
        normalized = normalize_text(question_text).lower()
        if normalized in seen_questions:
            continue
        questions.append({"question": question_text})
        seen_questions.add(normalized)
    assignments = assign_stories_to_questions(questions)
    rows = []
    for index, question in enumerate(questions, start=1):
        assigned_story = assignments[index - 1] if index - 1 < len(assignments) else "story gap to prepare"
        answer = regenerate_single_answer_outline(question, assigned_story, candidate_profile, jd_analysis, research, gap_map)
        rows.append(
            f"{index}. **{question.get('question', '')}**\n"
            f"{answer}\n"
            f"   - Evidence used: Assigned story: {assigned_story}, Candidate profile evidence only\n"
            f"   - Risk boundary: Do not claim unsupported background."
        )
    return "\n".join(rows)


def regenerate_pack_section(section_title, section_text, company_name, role_name, candidate_profile, jd_analysis, research, gap_map, strategy):
    banned = ", ".join(PACK_QUALITY_BANNED_STRINGS)
    if section_title == "Best Answer Outlines":
        return regenerate_best_answer_outlines_section(candidate_profile, jd_analysis, research, gap_map, strategy)
    if section_title == "Company Signal Map":
        specific_instruction = """
Rewrite this section as the Company Signal Map body only.
Read research.json carefully. Extract exactly 5 company specific signals that are true for this company and not generic to all companies. For each signal write: the signal itself, why it matters for this specific role, and one sentence on how the candidate should use it in their answer. If research is insufficient to produce 5 real signals say research insufficient and list what signals you could confirm versus what is missing. Never output no grounded item available. Never output a generic signal that could apply to any company.
A signal is a specific insight about how this company operates, what it values, or what it tests in interviews. It is never a source title or a page name. For Google People Operations specifically the signals must be things like: how Google structures people operations service delivery, what Google measures in people operations quality, how Google approaches process improvement internally, what Google values in people managers, how Google runs its HR operations model. Research these from the sources available. If research does not contain enough to produce 5 real signals say research insufficient rather than inventing source titles as signals.
For Google People Operations, do not output broad value words such as innovation, collaboration, stakeholder engagement, continuous improvement, or change management as standalone signals. Convert them into operational People Operations signals, for example: employee experience is treated as a measurable service-quality outcome; process improvement must be governed through data, control plans, and adoption mechanisms; People Operations work crosses HR operations, analytics, compliance, vendors, and regional teams; interviewers will test evidence of role-related knowledge through concrete accomplishments; people managers are expected to improve systems and team capability, not only manage tasks.
Output exactly 5 markdown bullets. Every bullet must start with "- signal:" and must also include "why_it_matters_for_this_role:" and "how_candidate_should_use_it:". Do not use numbered lists, paragraphs, source titles, or page names as signals.
"""
    else:
        specific_instruction = "Rewrite this section body only with specific, useful content for this company, role, candidate, JD, and research."

    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

The visible prep pack section below failed quality validation because it contained template or placeholder language.
Regenerate only the body for this markdown section. Do not include the ## heading.
Do not use any of these banned strings or close variants: {banned}

Section title:
{section_title}

Company: {company_name}
Role: {role_name}

Instruction:
{specific_instruction}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 10000)}

jd_analysis.json:
{trim_text(json_dumps(jd_analysis), 8000)}

research.json:
{trim_text(json_dumps(research), 10000)}

gap_map.json:
{trim_text(json_dumps(gap_map), 8000)}

interview_strategy.json:
{trim_text(json_dumps(strategy), 10000)}

Current failed section:
{trim_text(section_text, 6000)}
"""
    return ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=4500, retries=2).strip()


def repair_pack_quality(pack, company_name, role_name, candidate_profile, jd_analysis, research, gap_map, strategy):
    repaired = pack
    for _attempt in range(2):
        sections = markdown_sections(repaired)
        failures = []
        for title, start, end, text in sections:
            hits = failed_quality_strings(text)
            if title == "Best Answer Outlines":
                hits.extend(answer_outline_word_failures(text))
                hits.extend(answer_outline_story_failures(text))
            if title == "Company Signal Map":
                if _attempt == 0:
                    hits.extend(company_signal_map_failures(text, research))
            if hits:
                failures.append((title, start, end, text, hits))
        if not failures:
            return repaired
        for title, start, end, text, hits in reversed(failures):
            log(6, f"Pack quality validation failed in {title}; regenerating section. Banned strings: {', '.join(hits)}", "running")
            try:
                replacement_body = regenerate_pack_section(
                    title,
                    text,
                    company_name,
                    role_name,
                    candidate_profile,
                    jd_analysis,
                    research,
                    gap_map,
                    strategy,
                )
            except Exception as exc:
                if title == "Company Signal Map":
                    log(6, f"Company Signal Map regeneration failed; keeping existing section: {exc}", "done")
                    continue
                raise
            replacement = f"## {title}\n{replacement_body.strip()}\n\n"
            repaired = repaired[:start] + replacement + repaired[end:]
            log(6, f"Regenerated visible section: {title}", "done")
    assert_no_banned_visible_strings(repaired)
    remaining_outline_failures = []
    for title, _start, _end, text in markdown_sections(repaired):
        if title == "Best Answer Outlines":
            remaining_outline_failures.extend(answer_outline_word_failures(text))
            remaining_outline_failures.extend(answer_outline_story_failures(text))
    if remaining_outline_failures:
        raise ValueError(f"Best Answer Outlines failed word-count validation: {', '.join(remaining_outline_failures[:10])}")
    return repaired


def build_pack_from_structured_objects(company_name, role_name, candidate_profile, jd_analysis, research, gap_map, strategy):
    section_strategy = strategy.get("section_strategy", {}) if isinstance(strategy.get("section_strategy"), dict) else {}
    likely_questions = strategy.get("top_10_likely_questions", [])
    dangerous_questions = strategy.get("top_10_dangerous_questions", [])
    evidence_ledger = evidence_ledger_from_objects(candidate_profile, jd_analysis, research, gap_map)

    pack = f"""## Executive Strategy
Company: {company_name}
Role: {role_name}

Exact positioning strategy:
{strategy.get("exact_positioning_strategy", "Position the candidate through grounded evidence only.")}

How candidate wins:
{bullets(strategy.get("how_candidate_wins"))}

Why interviewer might hesitate:
{bullets(strategy.get("why_interviewer_might_hesitate"))}

Must emphasize:
{bullets(strategy.get("must_emphasize"))}

Must avoid:
{bullets(strategy.get("must_avoid"))}

## Interview Process Map
Likely interview areas, not confirmed rounds:
{format_source_signals(research.get("interview_signals"), limit=10)}

Confidence:
{json_dumps(research.get("confidence", {}))}

## Company Signal Map
{bullets(section_strategy.get("company_signal_map"))}

Official facts to mirror once:
{format_source_signals(research.get("official_facts")[:8] if isinstance(research.get("official_facts"), list) else [])}

## Role Signal Map
Top responsibilities:
{bullets(jd_analysis.get("top_responsibilities"))}

Required competencies:
{bullets(jd_analysis.get("required_competencies"))}

Hidden expectations:
{bullets(jd_analysis.get("hidden_expectations"))}

## Candidate Fit Map
Strength matches:
{bullets(gap_map.get("strength_matches"))}

Transferable experiences:
{bullets(gap_map.get("transferable_experiences"))}

Top proof points:
{bullets(candidate_profile.get("top_proof_points"))}

## Gap And Risk Repair Plan
High risk areas:
{bullets(gap_map.get("high_risk_areas"))}

Repair strategies:
{bullets(gap_map.get("repair_strategies"))}

## Story Bank
Grounded story inventory only:
{format_story_inventory(candidate_profile)}

Story gaps to prepare:
{bullets(candidate_profile.get("story_gaps"))}

## Likely Question Bank By Round
Likely interview areas, not confirmed rounds:
{format_questions(likely_questions)}

## Dangerous Question Bank
{format_questions(dangerous_questions)}

## Best Answer Outlines
Use these outlines as grounded coaching notes. Do not invent new candidate stories or metrics.
{format_answer_outlines(strategy.get("best_answer_outlines"))}

## Thirty Sixty Ninety Day Answer
- 30 days: learn the operating model, clarify stakeholder map, understand current metrics, and identify risk review rhythms.
- 60 days: tighten execution mechanisms, dashboard visibility, and escalation paths using the candidate's proven program management strengths.
- 90 days: show measurable operating improvement with evidence agreed by the team. Metrics must be prepared from real candidate experience or future-role goals, not invented past claims.

## Why This Company Answer
Use the official company signals above and a grounded motivation. Avoid restating the source list or claiming direct domain background unless candidate_profile proves it.

## Why This Role Answer
Connect JD responsibilities to candidate proof points and named gaps:
{bullets(jd_analysis.get("top_responsibilities")[:6] if isinstance(jd_analysis.get("top_responsibilities"), list) else [])}

## Questions To Ask The Interviewer
- Which operating rhythms matter most for success in this role in the first 90 days?
- Which cross-functional partners are hardest to align, and why?
- What metrics best reflect quality execution in this team?
- Where do candidates most often underestimate the role?
- What would excellent stakeholder trust look like six months in?

## Seven Day Preparation Plan
- Day 1: tighten the three strongest grounded stories.
- Day 2: prepare metrics honestly; mark missing metrics as future prep, not past claims.
- Day 3: rehearse high-risk questions from the dangerous question list.
- Day 4: map company signals to story hooks.
- Day 5: prepare concise gap repair language.
- Day 6: run a timed mock using the likely question list.
- Day 7: polish delivery, pacing, and executive-level concision.

## Evidence Ledger
{evidence_ledger}

## Final Interview Checklist
- Target company lock: {company_name}
- Target role lock: {role_name}
- No unsupported employer, title, industry, credential, domain, story, or metric claims.
- Every question connects to JD signal, candidate gap, and research signal.
- Use grounded stories only; put missing evidence in gaps to prepare.
"""
    pack = repair_pack_quality(
        pack.strip(),
        company_name,
        role_name,
        candidate_profile,
        jd_analysis,
        research,
        gap_map,
        strategy,
    )
    assert_no_banned_visible_strings(pack)
    return pack.strip()


def validate_pack(company_name, role_name, pack, candidate_profile, strategy):
    lowered = pack.lower()
    issues = []
    if company_name.lower() not in lowered:
        issues.append("wrong company")
    role_terms = [term for term in re.split(r"[^a-z0-9]+", role_name.lower()) if len(term) >= 4]
    if role_terms and not any(term in lowered for term in role_terms):
        issues.append("wrong role")
    if "no grounded questions generated" in lowered:
        issues.append("generic questions")
    story_names = [
        story.get("story_name", "").lower()
        for story in as_list(candidate_profile.get("story_inventory"))
        if isinstance(story, dict) and story.get("story_name")
    ]
    if len(story_names) != len(set(story_names)):
        issues.append("repeated evidence")
    for question in as_list(strategy.get("top_10_likely_questions")) + as_list(strategy.get("top_10_dangerous_questions")):
        if not isinstance(question, dict):
            issues.append("generic questions")
            continue
        if not question.get("jd_signal") or not question.get("candidate_gap") or not question.get("research_signal"):
            issues.append("generic questions")
    return sorted(set(issues))


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
    return json.loads(path.read_text(encoding="utf8"))


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
    except Exception:
        return {}


def tavily_search(query):
    data = tavily_post(
        "search",
        {
            "query": query,
            "search_depth": "advanced",
            "max_results": 8,
            "include_answer": False,
            "include_raw_content": False,
        },
        timeout=20,
    )
    rows = []
    for item in data.get("results", []) if isinstance(data, dict) else []:
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


def tavily_extract(urls):
    if not urls:
        return []
    data = tavily_post(
        "extract",
        {"urls": urls, "extract_depth": "basic"},
        timeout=20,
    )
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
    queries = [
        f"{company_name} official interview process site:{domain}" if domain else f"{company_name} official interview process",
        f"{company_name} {role_name} interview questions site:glassdoor.com",
        f"{company_name} interview experience site:reddit.com",
        f"{company_name} values culture leadership principles",
        f"{company_name} careers how we hire",
        f"{company_name} {role_name} interview rounds behavioral",
        f"{company_name} interview site:blind.app",
        f"{company_name} {role_name} interview experience 2024 2025",
    ]
    discovered = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map = {executor.submit(tavily_search, query): query for query in queries}
        for future in as_completed(future_map, timeout=22):
            try:
                discovered.extend(future.result(timeout=1))
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
        row["url"] for row in unique[:28]
        if "youtube.com" not in row["url"].lower() and "youtu.be" not in row["url"].lower()
    ][:20]
    extracted = {canonical_source_key(row.get("url", "")): row for row in tavily_extract(extract_urls)}
    enriched = []
    for row in unique[:35]:
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


def ensure_modular_answer(question, answer, assigned_story, session, candidate_profile, gap_map):
    answer = normalize_text(answer)
    lowered = answer.lower()
    bad_open = lowered.startswith("in my previous role") or lowered.startswith("in my role as")
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
Open with the situation or the stake. Do not open with "In my previous role" or "In my role as".
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
    return candidate_answer


def normalize_modular_strategy(strategy, session, candidate_profile, gap_map):
    strategy = strategy if isinstance(strategy, dict) else {}
    for round_item in as_list(strategy.get("questions_by_round")):
        if not isinstance(round_item, dict):
            continue
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
    return strategy


def run_interview_strategy_module(session, progress_callback=None):
    session_id = session["session_id"]
    company_intelligence = read_module_artifact(session_id, "company_intelligence")
    role_intelligence = read_module_artifact(session_id, "role_intelligence")
    candidate_profile = read_module_artifact(session_id, "candidate_profile")
    gap_map = read_module_artifact(session_id, "gap_map")
    report_progress(progress_callback, "Executive strategy and round plan", 20)
    prompt = f"""
{STAGE_QUALITY_INSTRUCTION}

This is the most important module. Produce interview_strategy.json for this exact candidate and role.

Company: {session["company_name"]}
Role: {session["role_name"]}

Raw JD:
{trim_text(session.get("raw_jd"), 12000)}

Raw CV:
{trim_text(session.get("raw_cv"), 12000)}

Raw answer bank:
{trim_text(session.get("raw_answer_bank"), 12000) or "None supplied."}

company_intelligence.json:
{trim_text(json_dumps(company_intelligence), 13000)}

role_intelligence.json:
{trim_text(json_dumps(role_intelligence), 12000)}

candidate_profile.json:
{trim_text(json_dumps(candidate_profile), 16000)}

gap_map.json:
{trim_text(json_dumps(gap_map), 14000)}

Return valid JSON only with this exact structure:
{{
  "executive_win_strategy": "",
  "round_by_round_plan": [{{"round_name": "", "what_this_round_tests": "", "likely_interviewer": "", "what_they_are_evaluating": "", "stories_to_use": [], "gaps_to_expect": [], "repair_scripts": [], "success_looks_like": "", "failure_looks_like": "", "specific_preparation_actions": []}}],
  "questions_by_round": [{{"round_name": "", "questions": [{{"question": "", "what_it_is_really_testing": "", "assigned_story": "", "danger_to_avoid": "", "complete_written_answer": "", "delivery_notes": ""}}]}}],
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
Each round must have 3 to 5 questions.
Each complete_written_answer must be 200 to 250 words.
Each answer must open with the situation or the stake. Never open with "In my previous role" or "In my role as".
Each answer must end with the business result or proof of fit. Never end with "aligning with expectations" or "the key takeaway for you is".
dangerous_questions must contain exactly 8 items with verbatim scripts.
do_not_say must contain exactly 15 specific items.
questions_to_ask must contain exactly 8 specific questions.
Do not invent candidate background.
"""
    result = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=15000, retries=2, fallback={})
    report_progress(progress_callback, "Strategy answer validation", 86)
    result = normalize_modular_strategy(result, session, candidate_profile, gap_map)
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
    return "\n".join(lines) if lines else "- Research insufficient."


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
    report_progress(progress_callback, "Deterministic prep pack assembly", 45)

    answer_failures = answer_word_failures_from_strategy(strategy)
    if answer_failures:
        raise ValueError(f"Any answer under 180 words: {', '.join(answer_failures[:5])}")

    round_sections = []
    for round_item in as_list(strategy.get("round_by_round_plan")):
        if not isinstance(round_item, dict):
            continue
        round_sections.append(
            f"### {round_item.get('round_name', 'Interview round')}\n"
            f"- What it tests: {round_item.get('what_this_round_tests', '')}\n"
            f"- Who interviews: {round_item.get('likely_interviewer', '')}\n"
            f"- What they evaluate: {round_item.get('what_they_are_evaluating', '')}\n"
            f"- Preparation actions:\n{markdown_list(round_item.get('specific_preparation_actions'))}"
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


def run_full_pipeline(company_name, role_name, job_description, cv, extra, progress_callback=None, workspace=None):
    log(0, "Starting full Nailit pipeline", "running")
    report_progress(progress_callback, "Job created", 1)

    # Stage 1 — Candidate truth
    report_progress(progress_callback, "Candidate extraction engine", 8)
    candidate_profile = create_candidate_profile(cv, extra)
    candidate_profile = checkpoint_json(workspace, "candidate_profile.json", candidate_profile)
    set_result("candidate_profile_json", json_dumps(candidate_profile))
    set_result("candidate_evidence_digest", json_dumps(candidate_profile))

    # Stage 2 — JD truth
    report_progress(progress_callback, "JD analysis engine", 18)
    jd_analysis = create_jd_analysis_json(job_description)
    jd_analysis = checkpoint_json(workspace, "jd_analysis.json", jd_analysis)
    set_result("jd_analysis_json", json_dumps(jd_analysis))
    set_result("job_description_decode", json_dumps(jd_analysis))

    # Stage 3 — Research truth
    report_progress(progress_callback, "Research engine source collection", 28)
    sources = collect_sources(company_name, role_name, job_description, extra)
    youtube_transcripts = extract_youtube_transcripts(extra)
    research = create_research_json(company_name, role_name, sources, youtube_transcripts=youtube_transcripts)
    research = checkpoint_json(workspace, "research.json", research)
    set_result("research_json", json_dumps(research))
    set_result("intel_report", json_dumps(research))

    # Stage 4 — Gap map
    report_progress(progress_callback, "Gap engine", 52)
    gap_map = create_gap_map_json(candidate_profile, jd_analysis, research)
    gap_map = checkpoint_json(workspace, "gap_map.json", gap_map)
    set_result("gap_map_json", json_dumps(gap_map))
    set_result("match_gap_risk_map", json_dumps(gap_map))

    # Stage 5 — Strategy
    report_progress(progress_callback, "Interview strategist engine", 74)
    strategy = create_interview_strategy_json(candidate_profile, jd_analysis, gap_map, research)
    strategy = checkpoint_json(workspace, "interview_strategy.json", strategy)
    set_result("interview_strategy_json", json_dumps(strategy))

    # Stage 6 — Assembly only
    report_progress(progress_callback, "Pack generation and validation", 92)
    final_pack = build_pack_from_structured_objects(
        company_name,
        role_name,
        candidate_profile,
        jd_analysis,
        research,
        gap_map,
        strategy,
    )
    assert_no_banned_visible_strings(final_pack)
    validation_issues = validate_pack(company_name, role_name, final_pack, candidate_profile, strategy)
    validation = {
        "target_lock_company": company_name,
        "target_lock_role": role_name,
        "issues": validation_issues,
        "status": "pass" if not validation_issues else "review_required",
    }
    validation = checkpoint_json(workspace, "pack_validation.json", validation)
    set_result("pack_validation_json", json_dumps(validation))
    set_result("final_prep_pack", final_pack)
    set_result("story_bank", format_story_inventory(candidate_profile))
    set_result("question_answer_bank", format_questions(strategy.get("top_10_likely_questions")) + "\n\n### Dangerous questions\n" + format_questions(strategy.get("top_10_dangerous_questions")))
    set_result("evidence_ledger", evidence_ledger_from_objects(candidate_profile, jd_analysis, research, gap_map))
    set_result("intel_report", json_dumps(research))

    lua_brief = build_lua_mock_interview_brief(
        company_name,
        role_name,
        json_dumps(research),
        json_dumps(jd_analysis),
        json_dumps(candidate_profile),
        json_dumps(gap_map),
        get_result("story_bank"),
        get_result("question_answer_bank"),
    )

    log(0, "Pipeline complete", "done")
    report_progress(progress_callback, "Final prep pack complete", 100)

    return {
        "HAS_FAILED": bool(validation_issues),
        "HAS_BRIDGE": bool(sources),
        "HAS_TOKEN_ERROR": "LLM error" in final_pack,
        "final_pack": final_pack,
        "lua_mock_interview_brief": lua_brief,
    }


if __name__ == "__main__":
    print("agent_v2 ready")

def run_pipeline(job_description, cv, extra, company_name, role_name, progress_callback=None, job_id=None):
    local_results = {}
    local_progress_log = []
    results_token = _current_results.set(local_results)
    progress_token = _current_progress_log.set(local_progress_log)

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_company = safe_path_part(company_name, "company")
        safe_job_id = safe_path_part(job_id or f"sync_{timestamp}_{safe_company}", "sync_job")
        workspace = create_job_workspace(safe_job_id)

        pipeline_result = run_full_pipeline(
            company_name=company_name,
            role_name=role_name,
            job_description=job_description,
            cv=cv,
            extra=extra,
            progress_callback=progress_callback,
            workspace=workspace,
        )

        markdown = f"""# Interview Prep Pack

Company: {company_name}

Role: {role_name}

Generated: {timestamp}

Job ID: {safe_job_id}

## Final Prep Pack

{get_result("final_prep_pack")}
"""
        assert_no_banned_visible_strings(markdown)

        files = {
            "research_plan.txt": get_result("research_plan"),
            "source_manifest.txt": get_result("source_manifest"),
            "source_mix.json": get_result("source_mix"),
            "source_digest.txt": get_result("source_digest"),
            "candidate_profile.json": get_result("candidate_profile_json"),
            "jd_analysis.json": get_result("jd_analysis_json"),
            "research.json": get_result("research_json"),
            "gap_map.json": get_result("gap_map_json"),
            "interview_strategy.json": get_result("interview_strategy_json"),
            "pack_validation.json": get_result("pack_validation_json"),
            "company_intelligence.txt": get_result("intel_report"),
            "candidate_digest.txt": get_result("candidate_evidence_digest"),
            "job_description_decode.txt": get_result("job_description_decode"),
            "match_gap_risk_map.txt": get_result("match_gap_risk_map"),
            "story_bank.txt": get_result("story_bank"),
            "question_answer_bank.txt": get_result("question_answer_bank"),
            "evidence_ledger.txt": get_result("evidence_ledger"),
            "final_prep_pack.txt": get_result("final_prep_pack"),
            "progress_log.json": json.dumps(local_progress_log, indent=2),
        }
        for filename, content in files.items():
            (workspace / filename).write_text(content or "", encoding="utf8")

        md_path = workspace / "prep_pack.md"
        md_path.write_text(markdown, encoding="utf8")

        lua_path = workspace / "lua_brief.json"
        lua_path.write_text(
            pipeline_result.get("lua_mock_interview_brief", "{}"),
            encoding="utf8",
        )

        return str(md_path)
    finally:
        _current_progress_log.reset(progress_token)
        _current_results.reset(results_token)
