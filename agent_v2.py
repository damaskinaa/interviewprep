import os
import re
import json
import logging as _logging
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
import research_config

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

EDITORIAL_BANNED_STRINGS = [
    "The context was",
    "The result squared",
    "This proves my fit",
    "This aligns with Google expectations",
    "The result I would lead with is",
    "Use the official company signals above",
    "This section needs more specific evidence",
    "because the fastest fix would not have lasted unless the mechanism changed",
    "that is the kind of disciplined program management I can bring while learning the construction workforce domain fast",
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
                if re.search(r"(^|\s)id:\s*S\d*\b", line, flags=re.I):
                    found.append(f"{needle} on line {line_number}")
                continue
            if needle.lower() in lowered:
                found.append(f"{needle} on line {line_number}")
    if found:
        raise ValueError(f"Visible prep pack contains banned internal strings: {', '.join(found[:20])}")


def assert_no_editorial_banned_strings(markdown):
    found = []
    text = markdown or ""
    lowered = text.lower()
    for needle in EDITORIAL_BANNED_STRINGS:
        if needle.lower() in lowered:
            found.append(needle)
    copied_question_pattern = re.compile(r"I have not directly owned(?:\s+\S+){9,}", flags=re.I)
    if copied_question_pattern.search(text):
        found.append("I have not directly owned followed by a copied question")
    if found:
        raise ValueError(f"Visible prep pack failed editorial quality gate: {', '.join(found[:20])}")


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


def extract_reported_questions(extra):
    """Pull the REPORTED_QUESTIONS block Vercel extracted from Glassdoor/Blind/Reddit/LinkedIn/Indeed."""
    block = extract_marked_block(extra or "", "REPORTED_QUESTIONS")
    return block.strip() if block else ""


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


def extract_metrics(text):
    text = normalize_text(text)
    patterns = [
        r"\b\d+(?:\.\d+)?\s?%",
        r"\b\d+(?:\.\d+)?\s?(?:hours?|days?|weeks?|months?|years?)\b",
        r"\b\d+(?:\.\d+)?\s?(?:SLAs?|cases?|regions?|team members?|people|FTEs?)\b",
    ]
    metrics = []
    for pattern in patterns:
        metrics.extend(re.findall(pattern, text, flags=re.I))
    seen = set()
    unique = []
    for metric in metrics:
        key = metric.lower()
        if key not in seen:
            seen.add(key)
            unique.append(metric)
    return unique[:8]


def clean_story_title(text, fallback):
    text = normalize_text(text)
    text = re.sub(r"^(grounded stories|candidate's own prepared answers and stories)\s*:\s*", "", text, flags=re.I)
    text = re.sub(r"^(story\s*\d+)\s*[:.-]\s*", "", text, flags=re.I)
    text = text.strip(" .:-")
    if not text:
        return fallback
    words = text.split()
    title = " ".join(words[:12])
    return title[:90].strip(" .:-") or fallback


def story_id_from_title(title, index):
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_text(title).lower()).strip("_")
    return f"S{index:02d}_{slug[:48] or 'story'}"


def candidate_story(index, title, source, trigger_phrase="", situation="", decision="", actions=None, metrics=None, result="", result_squared="", competencies=None, usable_for_questions=None, forbidden_expansions=None):
    title = normalize_text(title) or f"Candidate story {index}"
    metrics = as_list(metrics)
    story = {
        "story_id": story_id_from_title(title, index),
        "title": title,
        "story_name": title,
        "source": source,
        "trigger_phrase": normalize_text(trigger_phrase),
        "situation": normalize_text(situation or trigger_phrase or title),
        "decision": normalize_text(decision),
        "actions": [normalize_text(action) for action in as_list(actions) if normalize_text(action)],
        "metrics": metrics,
        "metrics_provided": metrics,
        "result": normalize_text(result),
        "result_squared": normalize_text(result_squared),
        "competencies": [normalize_text(item) for item in as_list(competencies) if normalize_text(item)],
        "usable_for_questions": [normalize_text(item) for item in as_list(usable_for_questions) if normalize_text(item)],
        "forbidden_expansions": [normalize_text(item) for item in as_list(forbidden_expansions) if normalize_text(item)],
    }
    if not story["result"] and metrics:
        story["result"] = "Result is supported by the attached metric; prepare the exact business outcome before using this story."
    if not story["forbidden_expansions"]:
        story["forbidden_expansions"] = default_forbidden_claims()
    return story


def default_forbidden_claims():
    return [
        "No direct construction workforce development ownership unless the CV or answer bank proves it.",
        "No electrical or piping trade expertise unless the CV or answer bank proves it.",
        "No data center construction delivery ownership unless the CV or answer bank proves it.",
        "No vocational, apprenticeship, or trade school partnership ownership unless the CV or answer bank proves it.",
        "No contractor management unless the CV or answer bank proves it.",
        "No fake employers, titles, industries, credentials, or impossible seniority.",
        "No Google employment or internal Google authority unless the CV proves it.",
        "No invented metrics, projects, teams, domains, or outcomes.",
    ]


def extract_bible_trigger_phrases(text):
    text = normalize_text(text)
    triggers = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        sentence = normalize_text(sentence)
        lowered = sentence.lower()
        if not sentence:
            continue
        if any(term in lowered for term in ["do not", "don't", "never", "avoid", "forbidden", "must not", "should not", "no direct"]):
            triggers.append(sentence)
        elif any(term in lowered for term in ["result first", "decision", "tradeoff", "punchline", "result squared", "metric", "top 1"]):
            triggers.append(sentence)
    seen = set()
    unique = []
    for item in triggers:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:12]


def answer_style_rules_from_bible(guidance, answer_bank):
    extracted = extract_bible_trigger_phrases(f"{guidance}\n{answer_bank}")
    rules = extracted[:]
    defaults = [
        "Use only real candidate evidence from the CV and answer bank.",
        "Open with the result, stake, decision, or constraint rather than a generic job-title phrase.",
        "Name the decision the candidate personally made and why it mattered.",
        "Name the tradeoff, resistance, ambiguity, or risk in the story.",
        "Attach only metrics that appear in the CV or answer bank.",
        "End with the business result, proof of fit, or interviewer takeaway.",
        "Use transferable language when direct domain experience is not proven.",
        "State boundaries clearly instead of inventing direct domain ownership.",
    ]
    for rule in defaults:
        if len(rules) >= 8:
            break
        if rule.lower() not in {item.lower() for item in rules}:
            rules.append(rule)
    return rules[:10]


def split_answer_bank_stories(answer_bank):
    answer_bank = normalize_text(answer_bank)
    if not answer_bank:
        return []
    matches = list(re.finditer(r"(?:^|\n)\s*(story\s*\d+\s*[:.-])", answer_bank, flags=re.I))
    if not matches:
        cleaned = re.sub(r"^candidate's own prepared answers and stories\s*:\s*", "", answer_bank, flags=re.I)
        grounded_match = re.search(r"grounded stories\s*:\s*(.*)", cleaned, flags=re.I | re.S)
        if grounded_match:
            cleaned = grounded_match.group(1)
        cleaned = re.split(r"\bdo not claim\b|\bnever claim\b|\bforbidden\b", cleaned, flags=re.I)[0]
        blocks = [block.strip(" .") for block in re.split(r";|\n\s*\n+", cleaned) if len(block.strip()) >= 20]
    else:
        blocks = []
        for index, match in enumerate(matches):
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(answer_bank)
            blocks.append(answer_bank[start:end].strip())
    stories = []
    for index, block in enumerate(blocks, start=1):
        block = normalize_text(block)
        if not block:
            continue
        story_name = clean_story_title(block, f"Answer bank story {index}")
        sentences = re.split(r"(?<=[.!?])\s+", block)
        stories.append(candidate_story(
            index=index,
            title=story_name,
            source="answer_bank",
            trigger_phrase=block,
            situation=normalize_text(sentences[0])[:500],
            decision="Prepare the specific decision made in this answer-bank story before using it live.",
            actions=[normalize_text(sentence) for sentence in sentences[1:5] if normalize_text(sentence)] or [block],
            metrics=extract_metrics(block),
            result=normalize_text(sentences[-1])[:500],
            result_squared="Prepare how this result changed quality, speed, stakeholder trust, or operating discipline.",
            competencies=infer_story_competencies(block),
            usable_for_questions=infer_story_question_uses(block),
            forbidden_expansions=default_forbidden_claims(),
        ))
    return stories


def story_key(story):
    if not isinstance(story, dict):
        return ""
    name = normalize_text(story.get("title") or story.get("story_name", "")).lower()
    raw = normalize_text(story.get("trigger_phrase") or story.get("situation") or story.get("result") or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", name or raw[:120]).strip()


def infer_story_competencies(text):
    lowered = normalize_text(text).lower()
    competencies = []
    checks = [
        ("stakeholder" in lowered or "launch readiness" in lowered or "handover" in lowered, "Stakeholder management"),
        ("dashboard" in lowered or "metric" in lowered or "kpi" in lowered or "sla" in lowered, "Metrics discipline"),
        ("automation" in lowered or "workflow" in lowered or "sop" in lowered or "process" in lowered, "Process improvement"),
        ("quality" in lowered or "qa" in lowered, "Quality management"),
        ("mentor" in lowered or "coach" in lowered or "training" in lowered or "onboarding" in lowered, "People development"),
        ("risk" in lowered or "escalation" in lowered, "Risk management"),
        ("backlog" in lowered or "response" in lowered, "Operational execution"),
        ("staff" in lowered or "resource" in lowered or "team of 10" in lowered, "Workforce management"),
    ]
    for condition, label in checks:
        if condition and label not in competencies:
            competencies.append(label)
    return competencies or ["Program management"]


def infer_story_question_uses(text):
    lowered = normalize_text(text).lower()
    uses = []
    checks = [
        ("backlog" in lowered or "handover" in lowered, "cross-regional execution and stakeholder alignment"),
        ("dashboard" in lowered or "metric" in lowered or "kpi" in lowered, "metrics, reporting, and workforce readiness tracking"),
        ("launch readiness" in lowered or "operating rhythm" in lowered, "launch readiness, operating cadence, and risk management"),
        ("automation" in lowered or "workflow" in lowered or "queue" in lowered, "process improvement and automation"),
        ("sop" in lowered or "escalation" in lowered, "SOPs, escalation paths, and operational control"),
        ("mentor" in lowered or "coach" in lowered or "training" in lowered, "training, onboarding, coaching, and knowledge transfer"),
        ("quality" in lowered or "qa" in lowered, "quality management and team performance"),
        ("team of 10" in lowered or "support specialists" in lowered, "team leadership and resource coordination"),
    ]
    for condition, label in checks:
        if condition and label not in uses:
            uses.append(label)
    return uses or ["behavioral interview evidence"]


def metric_present(text, *needles):
    text = normalize_text(text)
    return [needle for needle in needles if needle.lower() in text.lower()]


def add_candidate_story(stories, title, source, trigger, situation, decision, actions, metrics, result, result_squared, competencies, uses):
    stories.append(candidate_story(
        index=len(stories) + 1,
        title=title,
        source=source,
        trigger_phrase=trigger,
        situation=situation,
        decision=decision,
        actions=actions,
        metrics=metrics,
        result=result,
        result_squared=result_squared,
        competencies=competencies,
        usable_for_questions=uses,
        forbidden_expansions=default_forbidden_claims(),
    ))


def deterministic_candidate_stories(cv, answer_bank):
    full = normalize_text(f"{cv}\n{answer_bank}")
    lowered = full.lower()
    stories = []

    if "backlog" in lowered and ("34%" in lowered or "handover" in lowered):
        add_candidate_story(
            stories,
            "Backlog reduction story",
            "combined" if "backlog" in answer_bank.lower() else "CV",
            "backlog reduction; cross-regional handover; 34%",
            "Backlog and cross-region handover issues were affecting operational delivery.",
            "Create a clearer cross-regional operating mechanism rather than treating the issue as isolated queue volume.",
            ["Coordinated across regions or stakeholders.", "Improved handover visibility and accountability.", "Used operating rhythm discipline to reduce backlog."],
            metric_present(full, "34%"),
            "Reduced backlog by 34%." if "34%" in lowered else "Improved backlog visibility and operating discipline.",
            "Shows the candidate can translate ambiguous operating gaps into measurable delivery improvement.",
            ["Stakeholder management", "Operational execution", "Global handovers"],
            ["stakeholder alignment", "cross-functional operations", "delivery risk caused by coordination gaps"],
        )

    if any(term in lowered for term in ["queue routing", "40 weekly hours", "40 hours", "workflow automation", "saved 40"]):
        add_candidate_story(
            stories,
            "Queue routing redesign story",
            "combined" if any(term in answer_bank.lower() for term in ["40 weekly", "workflow automation", "queue"]) else "CV",
            "queue routing; workflow automation; 40 weekly hours",
            "Manual routing or workflow friction was consuming team capacity.",
            "Redesign the routing or workflow mechanism so work moved with less manual effort.",
            ["Mapped the workflow constraint.", "Changed routing, automation, or operating steps.", "Freed capacity for higher-value work."],
            metric_present(full, "40 weekly hours", "40 hours", "one hour"),
            "Saved 40 weekly hours through workflow automation." if "40" in lowered else "Improved workflow speed and team capacity.",
            "Shows the candidate can build scalable mechanisms instead of one-off fixes.",
            ["Process improvement", "Automation", "Resource allocation"],
            ["process improvement", "resource allocation", "repeatable operating mechanisms"],
        )

    if "77%" in lowered and "93%" in lowered:
        add_candidate_story(
            stories,
            "Metric calculation error story",
            "CV",
            "response time from 77% to 93%; SLA metric improvement",
            "A key response-time or SLA metric was not accurately reflecting performance.",
            "Interrogate the metric instead of accepting the dashboard at face value.",
            ["Reviewed the metric logic.", "Identified the calculation or visibility issue.", "Corrected reporting so decisions were based on reliable data."],
            metric_present(full, "77%", "93%"),
            "Improved response-time visibility or performance from 77% to 93%.",
            "Shows the candidate can protect decision quality through data integrity.",
            ["Metrics discipline", "Data integrity", "Risk management"],
            ["workforce readiness metrics", "data integrity", "executive reporting"],
        )

    if "team of 10" in lowered or "14%" in lowered or "qa" in lowered or "quality" in lowered:
        add_candidate_story(
            stories,
            "Team leadership and QA improvement story",
            "CV",
            "team of 10; QA scorecards; 14% quality improvement",
            "A support team needed stronger operating cadence and quality discipline.",
            "Use team rhythms and QA mechanisms to improve performance without inventing domain experience.",
            ["Led support specialists.", "Built or used QA scorecards.", "Reinforced operating cadence and performance expectations."],
            metric_present(full, "14%", "team of 10"),
            "Improved quality by 14%." if "14%" in lowered else "Improved team operating discipline.",
            "Shows the candidate can improve team capability and execution quality.",
            ["Team leadership", "Quality management", "Operating cadence"],
            ["people management", "quality improvement", "team operating rhythms"],
        )

    if any(term in lowered for term in ["mentor", "coaching", "coached", "performance improvements", "support specialists"]):
        add_candidate_story(
            stories,
            "People development story",
            "combined" if "mentor" in answer_bank.lower() or "coaching" in answer_bank.lower() else "CV",
            "mentored support specialists; quality and performance improvements",
            "Support specialists needed coaching, quality support, or performance improvement.",
            "Invest in targeted coaching and knowledge transfer rather than only escalating performance gaps.",
            ["Mentored or coached specialists.", "Used quality feedback and performance routines.", "Helped improve team capability."],
            metric_present(full, "14%"),
            "Improved quality, performance, or specialist capability using coaching and operating discipline.",
            "Shows the candidate can build capability in people, not only manage tasks.",
            ["People development", "Coaching", "Training"],
            ["training", "mentorship", "buddy programs", "team development"],
        )

    if "stakeholder" in lowered or "meta" in lowered:
        add_candidate_story(
            stories,
            "Stakeholder influence story",
            "CV",
            "stakeholder communication; Meta account; cross-functional process improvement",
            "Operational work required communication across stakeholders in the Meta support environment.",
            "Create clear communication, escalation, and visibility so stakeholders could act on the same facts.",
            ["Coordinated stakeholder updates.", "Managed escalation paths.", "Translated operational issues into clear status and actions."],
            [],
            "Improved stakeholder visibility and operating alignment.",
            "Shows the candidate can influence without relying only on formal authority.",
            ["Stakeholder communication", "Influence", "Escalation management"],
            ["contractor alignment", "partner communication", "senior stakeholder updates"],
        )

    if any(term in lowered for term in ["training coordination", "onboarding", "playbook", "knowledge transfer", "sop"]):
        add_candidate_story(
            stories,
            "Training onboarding and SOP knowledge transfer story",
            "combined" if any(term in answer_bank.lower() for term in ["sop", "training", "knowledge"]) else "CV",
            "training coordination; SOPs; knowledge transfer",
            "The team needed repeatable ways to transfer knowledge and standardize execution.",
            "Turn knowledge into SOPs, training coordination, or repeatable team practices.",
            ["Improved SOPs or knowledge practices.", "Supported training coordination.", "Reduced reliance on informal knowledge sharing."],
            [],
            "Created stronger process consistency and knowledge transfer.",
            "Shows the candidate can build repeatable capability mechanisms.",
            ["Training", "Onboarding", "Knowledge transfer", "SOPs"],
            ["training labs", "upskilling modules", "operating mechanisms"],
        )

    if "launch readiness" in lowered or "operating rhythm" in lowered or "risk tracking" in lowered:
        add_candidate_story(
            stories,
            "Launch readiness and operating rhythm story",
            "combined" if "launch readiness" in answer_bank.lower() else "CV",
            "launch readiness; operating rhythms; risk tracking",
            "A launch or operational program needed readiness, rhythm, and risk visibility.",
            "Create an operating rhythm that made readiness, risks, and owners visible before delivery issues escalated.",
            ["Coordinated launch readiness.", "Tracked risks and owners.", "Used dashboards or routines to maintain execution visibility."],
            [],
            "Improved readiness visibility and reduced execution ambiguity.",
            "Shows the candidate can manage delivery risk through operating cadence.",
            ["Launch readiness", "Risk management", "Program operating rhythm"],
            ["delivery risk", "senior stakeholder status", "program governance"],
        )

    if any(term in lowered for term in ["team of 10", "staffing", "resource", "workforce", "attrition", "hiring"]):
        add_candidate_story(
            stories,
            "Workforce management and resource allocation story",
            "CV",
            "team of 10 support specialists; resource and capacity management",
            "The candidate operated through a team and had to manage capacity, quality, and work allocation.",
            "Use team-capacity evidence honestly as a transferable foundation, without claiming construction workforce ownership.",
            ["Led a team of support specialists.", "Managed operating capacity and performance.", "Balanced quality, backlog, and response-time needs."],
            metric_present(full, "team of 10", "34%", "40 weekly hours", "14%"),
            "Improved team capacity, quality, or operational throughput using measurable operating discipline.",
            "Shows the closest truthful bridge to workforce planning and resource allocation.",
            ["Workforce management", "Resource allocation", "Team operations"],
            ["workforce readiness", "resource allocation", "labor constraint translation"],
        )

    if any(term in lowered for term in ["survey", "customer satisfaction", "csat", "satisfaction"]):
        add_candidate_story(
            stories,
            "Survey or customer satisfaction visibility story",
            "combined",
            "survey or customer satisfaction visibility",
            "Customer or stakeholder satisfaction needed better visibility.",
            "Use feedback data to identify operating issues and prioritize improvements.",
            ["Tracked satisfaction signals.", "Connected feedback to process changes.", "Used visibility to guide action."],
            extract_metrics(full),
            "Improved visibility into customer or stakeholder experience.",
            "Shows the candidate can connect operating metrics to experience outcomes.",
            ["Customer experience", "Survey analysis", "Metrics"],
            ["employee or partner experience metrics", "voice-of-customer analysis"],
        )

    return stories


def canonicalize_story(story, index):
    if not isinstance(story, dict):
        story = {"title": short_item(story)}
    return candidate_story(
        index=index,
        title=story.get("title") or story.get("story_name") or f"Candidate story {index}",
        source=story.get("source") or "CV",
        trigger_phrase=story.get("trigger_phrase") or story.get("situation") or story.get("title") or story.get("story_name") or "",
        situation=story.get("situation") or story.get("title") or story.get("story_name") or "",
        decision=story.get("decision") or story.get("candidate_decision") or "",
        actions=story.get("actions") or story.get("candidate_actions") or [],
        metrics=story.get("metrics") if "metrics" in story else story.get("metrics_provided"),
        result=story.get("result") or story.get("business_result") or "",
        result_squared=story.get("result_squared") or "",
        competencies=story.get("competencies") or [],
        usable_for_questions=story.get("usable_for_questions") or [],
        forbidden_expansions=story.get("forbidden_expansions") or default_forbidden_claims(),
    )


def merge_story_inventory(profile, cv, answer_bank):
    inventory = []
    seen = set()
    for story in deterministic_candidate_stories(cv, answer_bank):
        key = story_key(story)
        if key and key not in seen:
            inventory.append(story)
            seen.add(key)
    for story in as_list(profile.get("story_inventory")):
        if not isinstance(story, dict):
            continue
        canonical = canonicalize_story(story, len(inventory) + 1)
        key = story_key(canonical)
        if key and key not in seen:
            inventory.append(canonical)
            seen.add(key)
    for story in split_answer_bank_stories(answer_bank):
        key = story_key(story)
        if key and key not in seen:
            inventory.append(story)
            seen.add(key)
    for index, story in enumerate(inventory, start=1):
        story["story_id"] = story_id_from_title(story.get("title") or story.get("story_name"), index)
    profile["story_inventory"] = inventory
    return profile


def normalize_forbidden_claims(existing, cv, answer_bank, guidance):
    claims = [normalize_text(item) for item in as_list(existing) if normalize_text(item)]
    for phrase in extract_bible_trigger_phrases(f"{guidance}\n{answer_bank}"):
        lowered = phrase.lower()
        if any(term in lowered for term in ["do not", "don't", "never", "avoid", "forbidden", "must not", "should not", "no direct"]):
            claims.append(phrase)
    claims.extend(default_forbidden_claims())
    seen = set()
    unique = []
    for claim in claims:
        key = claim.lower()
        if key not in seen:
            seen.add(key)
            unique.append(claim)
    return unique[:14]


def normalize_answer_style_rules(existing, guidance, answer_bank):
    rules = [normalize_text(item) for item in as_list(existing) if normalize_text(item)]
    rules.extend(answer_style_rules_from_bible(guidance, answer_bank))
    seen = set()
    unique = []
    for rule in rules:
        key = rule.lower()
        if key not in seen:
            seen.add(key)
            unique.append(rule)
    return unique[:12]


def candidate_sources_are_rich(cv, answer_bank):
    text = normalize_text(f"{cv}\n{answer_bank}").lower()
    cues = [
        "backlog", "dashboard", "launch readiness", "stakeholder", "automation", "mentor",
        "training", "onboarding", "sop", "response time", "77%", "93%", "40", "14%", "team of 10",
    ]
    return sum(1 for cue in cues if cue in text) >= 6


def answer_bank_story_count(profile):
    count = 0
    for story in as_list(profile.get("story_inventory")):
        if isinstance(story, dict) and "answer_bank" in normalize_text(story.get("source")).lower():
            count += 1
    return count


def validate_candidate_profile(profile, cv, answer_bank, guidance):
    issues = []
    stories = [story for story in as_list(profile.get("story_inventory")) if isinstance(story, dict)]
    if candidate_sources_are_rich(cv, answer_bank) and len(stories) < 8:
        issues.append(f"story_inventory has fewer than 8 stories: {len(stories)}")
    if normalize_text(answer_bank) and answer_bank_story_count(profile) < 3:
        issues.append(f"answer_bank story extraction has fewer than 3 stories: {answer_bank_story_count(profile)}")
    if len(as_list(profile.get("forbidden_claims"))) < 8:
        issues.append("forbidden_claims missing or fewer than 8 items")
    if len(as_list(profile.get("answer_style_rules_from_bible"))) < 6:
        issues.append("answer_style_rules_from_bible missing or fewer than 6 items")
    for index, story in enumerate(stories, start=1):
        title = normalize_text(story.get("title") or story.get("story_name"))
        result = normalize_text(story.get("result"))
        source = normalize_text(story.get("source"))
        metrics = as_list(story.get("metrics") if "metrics" in story else story.get("metrics_provided"))
        if not source:
            issues.append(f"story {index} has no source")
        if metrics and (not title or not result):
            issues.append(f"story {index} has metrics but no title/result")
        if not as_list(story.get("forbidden_expansions")):
            issues.append(f"story {index} missing forbidden_expansions")
    return sorted(set(issues))


def candidate_profile_prompt(cv, answer_bank, guidance, strict=False):
    strict_instruction = """
Strict retry instruction:
Extract every distinct story separately. Do not collapse semicolon-separated answer-bank stories into one item. If a story appears in both CV and answer bank, preserve the full story once with source "combined".
""" if strict else ""
    return f"""
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
  "identity": "",
  "positioning_statement": "",
  "hard_evidence": [{{"claim": "", "basis": "CV | answer_bank | interview_bible", "metrics": []}}],
  "story_inventory": [{{
    "story_id": "",
    "title": "",
    "source": "CV | answer_bank | interview_bible | combined",
    "trigger_phrase": "",
    "situation": "",
    "decision": "",
    "actions": [],
    "metrics": [],
    "result": "",
    "result_squared": "",
    "competencies": [],
    "usable_for_questions": [],
    "forbidden_expansions": []
  }}],
  "candidate_strengths": [],
  "candidate_risks": [{{"risk": "", "why_it_matters": "", "repair_strategy": ""}}],
  "transferable_bridges": [{{"candidate_evidence": "", "maps_to_jd_signal": "", "bridge_language": "", "what_not_to_claim": ""}}],
  "forbidden_claims": [],
  "answer_style_rules_from_bible": [],
  "missing_story_gaps": []
}}

Rules:
Use only CV, Interview Bible / Strategy Guide, and answer bank.
Never infer target-role domain experience.
Never invent stories, employers, titles, industries, credentials, metrics, or outcomes.
Do not merge distinct stories just because they share a competency.
Every metric from CV or answer bank must attach to the correct story.
Every story must include forbidden_expansions.
forbidden_claims must include unsupported domain, trade, data center construction, vocational partnership, contractor management, fake employer, fake title, fake credential, and impossible seniority boundaries.
answer_style_rules_from_bible must preserve Interview Bible / Strategy Guide trigger phrases when present.
If a detail is missing, put it in missing_story_gaps and candidate_risks.
Populate transferable_bridges from real candidate evidence only.
{strict_instruction}
"""


def create_candidate_profile(cv, extra):
    log(2, "Stage 1 candidate extraction engine", "running")
    answer_bank, _company_context, guidance = extract_answer_bank_and_guidance(extra)
    profile = ask_json(candidate_profile_prompt(cv, answer_bank, guidance), model=MODEL_FAST, max_tokens=6200, fallback={})
    profile = normalize_candidate_profile(profile, cv=cv, answer_bank=answer_bank, guidance=guidance)
    issues = validate_candidate_profile(profile, cv, answer_bank, guidance)
    if issues:
        log(2, f"Candidate profile validation failed; retrying stricter extraction: {', '.join(issues[:5])}", "warning")
        profile = ask_json(candidate_profile_prompt(cv, answer_bank, guidance, strict=True), model=MODEL_STRATEGY, max_tokens=7600, fallback={})
        profile = normalize_candidate_profile(profile, cv=cv, answer_bank=answer_bank, guidance=guidance)
        issues = validate_candidate_profile(profile, cv, answer_bank, guidance)
    if issues:
        raise ValueError("candidate_profile failed story coverage validation. " + "; ".join(issues[:8]))
    set_result("candidate_profile_json", json_dumps(profile))
    set_result("candidate_evidence_digest", json_dumps(profile))
    log(2, "Candidate profile JSON complete", "done")
    return profile


def normalize_candidate_profile(profile, cv="", answer_bank="", guidance=""):
    profile = profile if isinstance(profile, dict) else {}
    identity = profile.get("identity")
    if isinstance(identity, dict):
        profile["identity_details"] = identity
        roles = ", ".join(as_list(identity.get("current_or_recent_roles")))
        domains = ", ".join(as_list(identity.get("industries_or_domains_proven")))
        profile["identity"] = normalize_text(f"{roles}. Proven domains: {domains}.") or "Candidate identity extracted from CV."
    else:
        profile["identity"] = normalize_text(identity) or "Operations and program management candidate with evidence from CV and answer bank."
    profile.setdefault("positioning_statement", "")
    profile.setdefault("hard_evidence", [])
    profile.setdefault("story_inventory", [])
    profile.setdefault("candidate_strengths", profile.get("core_strengths", []))
    profile.setdefault("candidate_risks", [])
    profile.setdefault("transferable_bridges", [])
    profile.setdefault("forbidden_claims", [])
    profile.setdefault("answer_style_rules_from_bible", [])
    profile.setdefault("missing_story_gaps", profile.get("story_gaps", []))
    profile["core_strengths"] = as_list(profile.get("candidate_strengths") or profile.get("core_strengths"))
    profile["story_gaps"] = as_list(profile.get("missing_story_gaps") or profile.get("story_gaps"))
    profile["leadership_themes"] = as_list(profile.get("leadership_themes"))
    profile["communication_style"] = as_list(profile.get("communication_style"))
    profile["top_proof_points"] = as_list(profile.get("top_proof_points"))

    profile = merge_story_inventory(profile, cv, answer_bank)
    profile["forbidden_claims"] = normalize_forbidden_claims(profile.get("forbidden_claims"), cv, answer_bank, guidance)
    profile["answer_style_rules_from_bible"] = normalize_answer_style_rules(profile.get("answer_style_rules_from_bible"), guidance, answer_bank)

    if not profile["positioning_statement"]:
        profile["positioning_statement"] = (
            "Position as a program and operations leader with transferable evidence in stakeholder alignment, "
            "metrics discipline, operating rhythms, quality improvement, team leadership, and process improvement. "
            "Do not claim direct data center construction workforce ownership unless the CV or answer bank proves it."
        )

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
    if not profile["core_strengths"]:
        profile["core_strengths"] = sorted({competency for story in profile["story_inventory"] for competency in as_list(story.get("competencies"))})[:8]
    profile["candidate_strengths"] = profile["core_strengths"]
    if not profile["top_proof_points"]:
        proof_points = []
        for story in profile["story_inventory"]:
            metrics = ", ".join(as_list(story.get("metrics")))
            if metrics:
                proof_points.append(f"{story.get('title')}: {metrics}")
        profile["top_proof_points"] = proof_points[:8]
    if not profile["story_gaps"]:
        profile["story_gaps"] = [
            "Direct data center construction workforce development story.",
            "Electrical, mechanical, piping, or skilled-trade labor-market story.",
            "Vocational, apprenticeship, trade school, or contractor partnership story.",
        ]
    profile["missing_story_gaps"] = profile["story_gaps"]
    return profile


WRONG_JD_DOMAIN_TERMS = [
    "supply chain",
    "order management",
    "erp",
    "sap",
    "o9",
    "fulfillment",
    "cloud capacity",
    "software engineering",
    "leetcode",
    "data structures",
    "algorithms",
]


JD_STOP_WORDS = {
    "the", "and", "for", "with", "from", "that", "this", "role", "will", "you", "are",
    "have", "has", "into", "across", "within", "about", "your", "their", "they", "them",
    "program", "manager", "google", "lead", "manage", "work", "team", "teams",
}


def content_terms(text):
    return {
        token for token in re.split(r"[^a-z0-9]+", normalize_text(text).lower())
        if len(token) >= 4 and token not in JD_STOP_WORDS
    }


def raw_jd_anchor_phrases(job_description):
    text = normalize_text(job_description)
    candidates = []
    for chunk in re.split(r"(?<=[.!?])\s+|\n+|;", text):
        chunk = normalize_text(chunk)
        if len(chunk.split()) >= 5:
            candidates.append(chunk)
        for subchunk in re.split(r",\s+", chunk):
            subchunk = normalize_text(subchunk)
            if len(subchunk.split()) >= 5:
                candidates.append(subchunk)
    anchors = []
    seen = set()
    for candidate in candidates:
        key = candidate.lower()
        if key not in seen:
            seen.add(key)
            anchors.append(candidate)
    return anchors[:12]


def derive_role_domain(role_name, job_description):
    text = f"{role_name} {job_description}".lower()
    if "data center" in text and "construction" in text and "workforce" in text:
        return "Data Center Construction Workforce Development"
    if "people operations" in text:
        return "People Operations"
    if "trust and safety" in text:
        return "Trust and Safety"
    if "lean six sigma" in text or "process improvement" in text:
        return "Process Improvement / Operational Excellence"
    role = normalize_text(role_name)
    return role or "Program Management"


def derive_top_responsibilities_from_jd(job_description):
    anchors = raw_jd_anchor_phrases(job_description)
    responsibilities = []
    for anchor in anchors:
        lower = anchor.lower()
        if any(term in lower for term in [
            "owns", "including", "aligning", "building", "tracking", "reducing",
            "coordinating", "communicating", "lead", "manage", "strategy", "program",
        ]):
            responsibilities.append(anchor)
    if len(responsibilities) < 5:
        responsibilities.extend(anchor for anchor in anchors if anchor not in responsibilities)
    return responsibilities[:8]


def derive_must_prove_from_jd(job_description):
    anchors = raw_jd_anchor_phrases(job_description)
    text = normalize_text(job_description).lower()
    signals = []

    def add(signal, evidence, why):
        if evidence:
            signals.append({"signal": signal, "jd_evidence": evidence, "why_it_matters": why})

    for anchor in anchors:
        lower = anchor.lower()
        if "trade gap" in lower or "labor market" in lower:
            add("Can diagnose critical trade and labor-market gaps", anchor, "The role depends on identifying workforce constraints before they become delivery risks.")
        elif "general contractor" in lower or "trade partner" in lower or "community college" in lower or "trade school" in lower:
            add("Can align external partners and internal delivery teams", anchor, "The role requires influence across organizations that do not report directly to the program manager.")
        elif "training" in lower or "mentorship" in lower or "upskilling" in lower or "buddy" in lower:
            add("Can build repeatable workforce development mechanisms", anchor, "The JD points to scalable capability-building rather than one-off coordination.")
        elif "metrics" in lower or "tracking" in lower:
            add("Can define and monitor workforce readiness metrics", anchor, "The program has to prove progress with evidence, not activity reporting alone.")
        elif "delivery risk" in lower or "labor constraints" in lower or "mitigation" in lower:
            add("Can translate workforce constraints into delivery-risk mitigation plans", anchor, "The business impact is construction delivery risk, so the candidate must connect workforce work to execution outcomes.")
        elif "senior" in lower or "communicating" in lower or "status" in lower:
            add("Can communicate program status, risks, and mitigations to senior stakeholders", anchor, "Senior stakeholders need clear escalation, options, and evidence-backed recommendations.")

    if "cross-functional" in text:
        add("Can connect cross-functional teams around a shared workforce plan", next((a for a in anchors if "cross-functional" in a.lower()), anchors[0] if anchors else ""), "Cross-functional alignment is implied by the number of partner groups in the JD.")
    if "data center" in text and len(signals) < 5:
        add("Can operate in a data center construction delivery context", anchors[0] if anchors else normalize_text(job_description)[:300], "The role is anchored in data center construction delivery, so domain translation matters.")

    seen = set()
    unique = []
    for item in signals:
        key = item["signal"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:8]


def derive_hidden_expectations_from_jd(job_description, top_responsibilities=None, must_prove_signals=None):
    text = normalize_text(job_description).lower()
    expectations = []
    if any(term in text for term in ["general contractors", "trade partners", "community colleges", "trade schools", "workforce boards", "cross-functional"]):
        expectations.append("Can align internal teams, external contractors, and education partners without direct authority.")
    if any(term in text for term in ["training", "mentorship", "buddy", "upskilling", "scale"]):
        expectations.append("Can build repeatable operating mechanisms, not one-off training activities.")
    if any(term in text for term in ["metrics", "tracking", "data"]):
        expectations.append("Can define workforce pipeline metrics, monitor adoption, and adjust based on evidence.")
    if any(term in text for term in ["electrical", "mechanical", "piping", "trade gaps", "labor markets"]):
        expectations.append("Can understand regional workforce constraints and translate them into practical program plans.")
    if any(term in text for term in ["delivery risk", "labor constraints", "mitigation"]):
        expectations.append("Can connect workforce development work directly to data center delivery-risk reduction.")
    if any(term in text for term in ["senior stakeholders", "program status", "risks"]):
        expectations.append("Can communicate status, tradeoffs, risks, and mitigation plans clearly to senior stakeholders.")
    if len(expectations) < 5:
        for item in as_list(top_responsibilities) + as_list(must_prove_signals):
            text_item = short_item(item)
            if text_item:
                expectations.append(f"Can turn this JD requirement into a practical operating rhythm: {text_item}")
            if len(expectations) >= 5:
                break
    return expectations[:8]


def derive_dangerous_gaps_from_jd(job_description):
    text = normalize_text(job_description).lower()
    gaps = []
    checks = [
        ("data center construction" in text or "construction delivery" in text, "direct data center construction workforce development experience"),
        ("electrical" in text or "piping" in text or "mechanical" in text, "electrical, mechanical, and piping trades familiarity"),
        ("trade school" in text or "community college" in text or "workforce board" in text, "vocational training, workforce board, or apprenticeship partnership ownership"),
        ("general contractor" in text or "trade partner" in text, "contractor and trade partner alignment experience"),
        ("mentorship" in text or "buddy" in text or "training" in text or "upskilling" in text, "on-site mentorship, buddy programming, or upskilling module ownership"),
        ("data center" in text, "data center delivery environment exposure"),
        ("safety" in text or "construction" in text, "craft labor safety standards familiarity"),
        ("metrics" in text or "tracking" in text, "workforce readiness metrics and adoption tracking experience"),
        ("senior stakeholder" in text or "communicating" in text, "senior stakeholder risk communication in a construction delivery context"),
    ]
    for condition, label in checks:
        if condition:
            gaps.append(label)
    if len(gaps) < 5:
        gaps.extend([
            "direct ownership of this role's exact operating environment",
            "partner ecosystem depth specific to this JD",
            "domain vocabulary and constraints specific to this JD",
            "evidence of scaling the exact program mechanisms named in the JD",
            "senior-level communication around the risks named in the JD",
        ])
    seen = set()
    unique = []
    for gap in gaps:
        key = gap.lower()
        if key not in seen:
            seen.add(key)
            unique.append(gap)
    return unique[:8]


def derive_scenario_questions_from_jd(job_description):
    anchors = raw_jd_anchor_phrases(job_description)
    signals = derive_must_prove_from_jd(job_description)
    questions = []
    for signal in signals:
        anchor = signal.get("jd_evidence", "")
        questions.append({
            "question": f"Tell me about a time you proved you could {signal.get('signal', '').lower()}.",
            "jd_anchor": anchor,
            "why_this_question_matters": signal.get("why_it_matters", ""),
        })
    for anchor in anchors:
        if len(questions) >= 10:
            break
        questions.append({
            "question": f"How would you approach this responsibility from the JD: {anchor[:180]}?",
            "jd_anchor": anchor,
            "why_this_question_matters": "This tests whether the candidate can translate a stated JD requirement into a practical program plan.",
        })
    return questions[:10]


def jd_analysis_prompt(job_description, role_name="", strict=False):
    strict_rules = """
Extra strict retry rules:
Use only exact wording or clearly implied wording from the submitted JD.
If you cannot prove a responsibility from the raw JD, omit it.
Do not use company search results, source manifests, Tavily research, or general knowledge.
""" if strict else ""
    return f"""
{STAGE_QUALITY_INSTRUCTION}

Analyze the submitted job description only. Do not use candidate information, company research, source manifests, Tavily results, company search results, or assumptions outside the JD.

Submitted role name:
{normalize_text(role_name) or "Not supplied."}

Job description:
{trim_text(job_description, 20000)}

Raw JD anchor phrases you must preserve:
{json_dumps(raw_jd_anchor_phrases(job_description))}

Return valid JSON only with this exact top-level structure:
{{
  "submitted_role_name": "{normalize_text(role_name)}",
  "extracted_role_title": "",
  "role_domain": "",
  "top_responsibilities": [],
  "must_prove_signals": [{{"signal": "", "jd_evidence": "", "why_it_matters": ""}}],
  "hidden_expectations": [],
  "dangerous_gaps": [],
  "scenario_question_seeds": [{{"question": "", "jd_anchor": "", "why_this_question_matters": ""}}],
  "raw_jd_anchor_phrases": [],
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
top_responsibilities must be copied from or tightly paraphrased from the raw JD.
raw_jd_anchor_phrases must contain exact phrases from the submitted JD.
Wrong-domain terms are forbidden unless they appear verbatim in the submitted JD: {", ".join(WRONG_JD_DOMAIN_TERMS)}.
{strict_rules}
"""


def validate_jd_target_lock(analysis, role_name, job_description):
    analysis = analysis if isinstance(analysis, dict) else {}
    jd_text = normalize_text(job_description).lower()
    role_text = normalize_text(role_name).lower()
    issues = []
    serialized = json_dumps(analysis).lower()

    if not normalize_text(analysis.get("submitted_role_name")):
        issues.append("submitted_role_name missing")
    if not normalize_text(analysis.get("extracted_role_title")):
        issues.append("extracted_role_title missing")
    if not normalize_text(analysis.get("role_domain")):
        issues.append("role_domain missing")

    for term in WRONG_JD_DOMAIN_TERMS:
        if term in serialized and term not in jd_text:
            issues.append(f"wrong domain term not in submitted JD: {term}")

    extracted_title = normalize_text(analysis.get("extracted_role_title", "")).lower()
    role_domain = normalize_text(analysis.get("role_domain", "")).lower()
    role_tokens = [token for token in re.split(r"[^a-z0-9]+", role_text) if len(token) >= 4 and token not in {"google"}]
    if role_tokens and extracted_title:
        missing_role_tokens = [token for token in role_tokens if token not in extracted_title and token not in role_domain and token not in jd_text]
        if missing_role_tokens:
            issues.append(f"extracted role title/domain missed submitted role tokens: {', '.join(missing_role_tokens)}")

    if "people operations" in jd_text and "people" not in f"{extracted_title} {role_domain}":
        issues.append("role_domain missed People Operations anchor from submitted JD")

    jd_terms = content_terms(job_description)
    for responsibility in as_list(analysis.get("top_responsibilities")):
        text = short_item(responsibility)
        resp_terms = content_terms(text)
        if resp_terms and len(resp_terms.intersection(jd_terms)) < 2:
            issues.append(f"top responsibility not grounded in submitted JD: {text[:120]}")
        for term in WRONG_JD_DOMAIN_TERMS:
            if term in text.lower() and term not in jd_text:
                issues.append(f"top responsibility contains wrong-domain term: {term}")

    anchors = as_list(analysis.get("raw_jd_anchor_phrases"))
    if len(anchors) < 8:
        issues.append("raw_jd_anchor_phrases has fewer than 8 items")
    for anchor in anchors[:10]:
        anchor_text = normalize_text(anchor).lower()
        if anchor_text and anchor_text not in jd_text:
            issues.append(f"raw JD anchor phrase not found in submitted JD: {anchor_text[:120]}")

    required_counts = {
        "top_responsibilities": 5,
        "must_prove_signals": 5,
        "hidden_expectations": 5,
        "dangerous_gaps": 5,
        "scenario_question_seeds": 8,
    }
    for key, minimum in required_counts.items():
        if len(as_list(analysis.get(key))) < minimum:
            issues.append(f"{key} has fewer than {minimum} items")

    return sorted(set(issues))


def normalize_jd_analysis(analysis, role_name, job_description):
    analysis = analysis if isinstance(analysis, dict) else {}
    analysis["submitted_role_name"] = normalize_text(analysis.get("submitted_role_name") or role_name)
    analysis["extracted_role_title"] = normalize_text(analysis.get("extracted_role_title") or role_name)
    analysis["role_domain"] = normalize_text(analysis.get("role_domain") or derive_role_domain(role_name, job_description))
    anchors = raw_jd_anchor_phrases(job_description)
    if len(as_list(analysis.get("raw_jd_anchor_phrases"))) < 8:
        analysis["raw_jd_anchor_phrases"] = anchors[:10]
    if not isinstance(analysis.get("must_prove_signals"), list):
        analysis["must_prove_signals"] = as_list(analysis.get("jd_signals"))
    if not isinstance(analysis.get("jd_signals"), list):
        analysis["jd_signals"] = as_list(analysis.get("must_prove_signals"))
    for key in [
        "top_responsibilities",
        "must_prove_signals",
        "hidden_expectations",
        "dangerous_gaps",
        "scenario_question_seeds",
        "likely_interviewer_concerns",
        "required_competencies",
        "likely_behavioral_themes",
        "technical_expectations",
        "success_profile",
        "failure_profile",
        "jd_signals",
    ]:
        if not isinstance(analysis.get(key), list):
            analysis[key] = []

    if len(analysis["top_responsibilities"]) < 5:
        merged = analysis["top_responsibilities"] + [
            item for item in derive_top_responsibilities_from_jd(job_description)
            if item not in analysis["top_responsibilities"]
        ]
        analysis["top_responsibilities"] = merged[:8]

    if len(analysis["must_prove_signals"]) < 5:
        existing_signals = {short_item(item).lower() for item in analysis["must_prove_signals"]}
        for item in derive_must_prove_from_jd(job_description):
            if short_item(item).lower() not in existing_signals:
                analysis["must_prove_signals"].append(item)
                existing_signals.add(short_item(item).lower())
        for responsibility in analysis["top_responsibilities"]:
            if len(analysis["must_prove_signals"]) >= 5:
                break
            signal = {
                "signal": f"Can execute this JD responsibility: {short_item(responsibility)[:160]}",
                "jd_evidence": short_item(responsibility),
                "why_it_matters": "This is a stated responsibility in the submitted JD and must be proven with a relevant candidate story.",
            }
            key = short_item(signal).lower()
            if key not in existing_signals:
                analysis["must_prove_signals"].append(signal)
                existing_signals.add(key)
        analysis["must_prove_signals"] = analysis["must_prove_signals"][:8]

    if len(analysis["jd_signals"]) < 5:
        analysis["jd_signals"] = analysis["must_prove_signals"][:8]

    if len(analysis["hidden_expectations"]) < 5:
        existing = {short_item(item).lower() for item in analysis["hidden_expectations"]}
        for item in derive_hidden_expectations_from_jd(job_description, analysis["top_responsibilities"], analysis["must_prove_signals"]):
            if short_item(item).lower() not in existing:
                analysis["hidden_expectations"].append(item)
                existing.add(short_item(item).lower())
        analysis["hidden_expectations"] = analysis["hidden_expectations"][:8]

    if len(analysis["dangerous_gaps"]) < 5:
        existing = {short_item(item).lower() for item in analysis["dangerous_gaps"]}
        for item in derive_dangerous_gaps_from_jd(job_description):
            if short_item(item).lower() not in existing:
                analysis["dangerous_gaps"].append(item)
                existing.add(short_item(item).lower())
        analysis["dangerous_gaps"] = analysis["dangerous_gaps"][:8]

    if len(analysis["scenario_question_seeds"]) < 8:
        existing = {short_item(item).lower() for item in analysis["scenario_question_seeds"]}
        for item in derive_scenario_questions_from_jd(job_description):
            if short_item(item).lower() not in existing:
                analysis["scenario_question_seeds"].append(item)
                existing.add(short_item(item).lower())
        analysis["scenario_question_seeds"] = analysis["scenario_question_seeds"][:10]

    return analysis


def create_jd_analysis_json(job_description, role_name=""):
    log(3, "Stage 2 JD analysis engine", "running")
    analysis = ask_json(jd_analysis_prompt(job_description, role_name), model=MODEL_FAST, max_tokens=5200, fallback={})
    analysis = normalize_jd_analysis(analysis, role_name, job_description)
    issues = validate_jd_target_lock(analysis, role_name, job_description)
    if issues:
        log(3, f"JD target lock failed; retrying stricter analysis: {', '.join(issues[:5])}", "warning")
        analysis = ask_json(jd_analysis_prompt(job_description, role_name, strict=True), model=MODEL_STRATEGY, max_tokens=5200, fallback={})
        analysis = normalize_jd_analysis(analysis, role_name, job_description)
        issues = validate_jd_target_lock(analysis, role_name, job_description)
    if issues:
        raise ValueError("JD analysis failed target lock. " + "; ".join(issues[:8]))
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
  "strength_matches": [{{"jd_signal": "", "candidate_evidence": "", "story_to_use": "", "metric_to_use": "", "why_it_matters": "", "how_to_say_it": ""}}],
  "dangerous_gaps": [{{"gap": "", "why_it_matters": "", "honest_bridge": "", "story_to_pivot_to": "", "do_not_say": ""}}],
  "repair_scripts": [{{"risk_question": "", "verbatim_repair_answer": "", "bridge_story": "", "proof_point": "", "forbidden_claim": ""}}],
  "story_assignments": [{{"question_theme": "", "assigned_story_id": "", "assigned_story_title": "", "why_this_story": "", "metric_to_use": "", "tradeoff_to_show": ""}}],
  "pressure_responses": [{{"pressure_probe": "", "strong_response": "", "boundary_to_hold": ""}}]
}}

Rules:
Do not invent candidate evidence.
If direct domain proof is missing, call it transferable or missing.
Populate every array. Empty arrays are invalid.
"""
    gap_map = ask_json(prompt, model=MODEL_STRATEGY, max_tokens=4200, fallback={})
    gap_map = normalize_gap_map(gap_map, candidate_profile, jd_analysis)
    gap_issues = validate_gap_map(gap_map)
    if gap_issues:
        raise ValueError("gap_map failed quality validation. " + "; ".join(gap_issues[:8]))
    set_result("gap_map_json", json_dumps(gap_map))
    set_result("match_gap_risk_map", json_dumps(gap_map))
    log(4, "Gap map JSON complete", "done")
    return gap_map


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


def story_result_text(story):
    return normalize_text((story or {}).get("result") or (story or {}).get("result_squared") or "Grounded operating improvement from candidate evidence.")


def story_actions_text(story):
    actions = as_list((story or {}).get("actions"))
    return "; ".join(normalize_text(item) for item in actions[:3] if normalize_text(item)) or normalize_text((story or {}).get("decision")) or "Clarified the problem, aligned stakeholders, and made the work measurable."


def normalize_gap_map(gap_map, candidate_profile, jd_analysis):
    gap_map = gap_map if isinstance(gap_map, dict) else {}
    stories, _by_id = story_lookup(candidate_profile)
    signals = jd_signal_texts(jd_analysis)
    forbidden_claims = as_list((candidate_profile or {}).get("forbidden_claims")) or [
        "Do not claim direct construction workforce development ownership unless the CV proves it.",
        "Do not claim electrical or piping trade expertise unless the CV proves it.",
        "Do not claim data center construction delivery ownership unless the CV proves it.",
    ]

    strength_matches = []
    counts = {}
    for signal in signals:
        if len(strength_matches) >= 8:
            break
        story = choose_story_for_question(signal, stories, counts)
        if story is None and stories:
            story = stories[len(strength_matches) % len(stories)]
        if story:
            counts[story_id(story)] = counts.get(story_id(story), 0) + 1
        strength_matches.append({
            "jd_signal": signal,
            "candidate_evidence": story_result_text(story) if story else "No direct story; use a story gap honestly.",
            "story_to_use": story_title(story) if story else "Story gap to prepare",
            "metric_to_use": story_metric_text(story) if story else "No direct metric.",
            "why_it_matters": "This is a core interview signal because the role turns workforce constraints into delivery-risk decisions.",
            "how_to_say_it": (
                f"I would connect this to {story_title(story)}: {story_actions_text(story)}"
                if story else
                "I would state the domain gap directly and bridge to the closest verified operating evidence."
            ),
        })

    gap_labels = [
        "Direct construction workforce development ownership",
        "Electrical and piping trade-gap expertise",
        "Data center construction delivery environment exposure",
        "Contractor and vendor alignment in construction settings",
        "Trade school, community college, or workforce-board partnership ownership",
        "Training labs, upskilling modules, mentorship, or buddy programming at craft-labor scale",
        "Workforce readiness metrics for skilled-trades pipeline health",
        "Senior stakeholder communication about labor constraints and delivery risk",
    ]
    for item in as_list((jd_analysis or {}).get("dangerous_gaps")):
        text = normalize_text(item.get("gap") if isinstance(item, dict) else item)
        if text and text not in gap_labels:
            gap_labels.append(text)

    dangerous_gaps = []
    for index, gap in enumerate(gap_labels[:10]):
        story = choose_story_for_question(gap, stories, {}) if stories else None
        dangerous_gaps.append({
            "gap": gap,
            "why_it_matters": "An interviewer may test whether the candidate understands this domain deeply enough to protect data center delivery.",
            "honest_bridge": f"I have not directly owned {gap.lower()}, but my closest transferable evidence is {story_title(story) if story else 'operations leadership, metrics discipline, and stakeholder alignment'}.",
            "story_to_pivot_to": story_title(story) if story else "Story gap to prepare",
            "do_not_say": forbidden_claims[index % len(forbidden_claims)],
        })

    repair_scripts = []
    for item in dangerous_gaps[:10]:
        repair_scripts.append({
            "risk_question": f"What if the interviewer probes your gap in {item['gap']}?",
            "verbatim_repair_answer": (
                f"I want to be precise about the boundary: I have not directly owned {item['gap'].lower()}. "
                f"The strongest transferable evidence I have is {item['story_to_pivot_to']}, where I had to make an operating problem measurable, align people around a mechanism, and protect the outcome through follow-through. "
                "I would use that foundation carefully in this role: learn the construction workforce domain fast, ask better questions of contractors and workforce partners, and build the operating rhythm that makes risk visible before it affects delivery."
            ),
            "bridge_story": item["story_to_pivot_to"],
            "proof_point": "Transferable operating discipline: metrics, stakeholder alignment, training/SOPs, quality, backlog, SLA/KPI, and handover control.",
            "forbidden_claim": item["do_not_say"],
        })

    story_themes = [
        "regional workforce shortages",
        "electrical and piping trade gaps",
        "contractor and vendor alignment",
        "trade school partnerships",
        "training labs and upskilling modules",
        "mentorship and buddy programming",
        "craft labor support and readiness",
        "peer-to-peer safety standards",
        "data center delivery risk",
        "stakeholder conflict",
        "pipeline metrics and dashboarding",
        "senior stakeholder communication",
    ]
    story_assignments = []
    counts = {}
    for theme in story_themes:
        story = choose_story_for_question(theme, stories, counts)
        if story:
            counts[story_id(story)] = counts.get(story_id(story), 0) + 1
        story_assignments.append({
            "question_theme": theme,
            "assigned_story_id": story_id(story) if story else "story_gap",
            "assigned_story_title": story_title(story) if story else "Story gap to prepare",
            "why_this_story": "This is the closest verified story for the question theme without inventing construction-domain ownership.",
            "metric_to_use": story_metric_text(story) if story else "No direct metric; prepare a truthful metric if one exists.",
            "tradeoff_to_show": "Show the transferable operating pattern while holding the boundary on direct construction, trade, contractor, and data center ownership.",
        })

    pressure_responses = []
    for item in dangerous_gaps[:6]:
        pressure_responses.append({
            "pressure_probe": f"But you have not done {item['gap'].lower()} directly. Why should we trust you in this role?",
            "strong_response": (
                f"That is fair, and I would not ask you to treat {item['gap'].lower()} as proven domain experience. "
                f"What I can prove is the operating pattern behind the role: {item['story_to_pivot_to']} shows that I can diagnose a constraint, make it measurable, align stakeholders, and sustain a process change. "
                "For this role, I would pair that with fast domain learning from construction delivery teams, contractors, and workforce partners so the program decisions are grounded in the right expertise."
            ),
            "boundary_to_hold": item["do_not_say"],
        })

    gap_map["strength_matches"] = strength_matches[:10]
    gap_map["dangerous_gaps"] = dangerous_gaps[:10]
    gap_map["repair_scripts"] = repair_scripts[:10]
    gap_map["story_assignments"] = story_assignments[:12]
    gap_map["pressure_responses"] = pressure_responses[:8]
    gap_map["missing_areas"] = [item["gap"] for item in dangerous_gaps]
    gap_map["transferable_experiences"] = [
        {"candidate_evidence": item["candidate_evidence"], "maps_to": item["jd_signal"], "boundary": "Transferable, not direct construction-domain proof."}
        for item in strength_matches[:8]
    ]
    gap_map["high_risk_areas"] = [
        {"risk": item["gap"], "why_it_matters": item["why_it_matters"], "evidence_gap": item["do_not_say"]}
        for item in dangerous_gaps[:8]
    ]
    gap_map["repair_strategies"] = [
        {"risk": item["risk_question"], "strategy": item["verbatim_repair_answer"], "prep_action": item["bridge_story"]}
        for item in repair_scripts[:8]
    ]
    return gap_map


def validate_gap_map(gap_map):
    required = {
        "strength_matches": 8,
        "dangerous_gaps": 8,
        "repair_scripts": 8,
        "story_assignments": 10,
        "pressure_responses": 6,
    }
    issues = []
    for key, minimum in required.items():
        count = len(as_list((gap_map or {}).get(key)))
        if count < minimum:
            issues.append(f"{key} has {count}, expected at least {minimum}")
    return issues


def create_interview_strategy_json(candidate_profile, jd_analysis, gap_map, research, reported_questions=""):
    log(5, "Stage 5 interview strategist engine", "running")

    reported_block = ""
    if reported_questions and reported_questions.strip():
        reported_block = f"""
REPORTED QUESTIONS FROM COMMUNITY SOURCES (Glassdoor, Blind, Reddit, LinkedIn, Indeed):
These are literal questions that real candidates reported being asked at this company.
RULES:
- Include ALL of these questions in top_10_likely_questions or top_10_dangerous_questions where they fit.
- These take priority over AI-inferred questions. Do not drop them.
- Label each one with research_signal: "reported by candidates on [source type]"
- Questions reported multiple times across sources are HIGH PROBABILITY — flag them.
- Assign each reported question to the correct interview round based on question type and context.

{trim_text(reported_questions, 3500)}
"""

    prompt = f"""
{reported_block}
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
Read the question carefully before writing the answer. The question is asking about a specific angle: risk escalation, stakeholder conflict, metrics design, training adoption, or capability building. Use the assigned story to answer that specific angle. Do not write the same answer structure for every question that shares a story. Vary the opening, the decision emphasis, and the result based on what the question is actually testing.
If the question tests metrics design, lead with the metric problem and the diagnostic decision.
If the question tests stakeholder conflict, lead with the misaligned incentives and how shared data resolved them.
If the question tests training adoption, lead with the behavior change and the mechanism that made it stick.
If the question tests risk escalation, lead with the moment the risk became visible and what you did before others agreed it was a problem.
When assigned_story_id is story_gap, open the answer with a natural honest bridge that does not repeat the question text. Use one of these patterns:
Name the specific operating evidence that is closest: "The closest transferable evidence I have for this is the backlog handover work, because..."
Name the gap honestly then bridge immediately: "I have not built a contractor partnership directly. The operating pattern I would apply is..."
State the approach: "My first move would be to get the constraint visible before prescribing a solution. The way I have done that is..."
Never copy the question into the answer. Never start with "I have not directly owned" followed by the question text.
Never use the phrases "The context was", "because the fastest fix would not have lasted unless the mechanism changed", or "that is the kind of disciplined program management I can bring while learning the construction workforce domain fast".
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
    strategy = normalize_interview_strategy(strategy, research=research, candidate_profile=candidate_profile, jd_analysis=jd_analysis)
    outline_issues = validate_best_answer_outlines(strategy, candidate_profile)
    if outline_issues:
        raise ValueError("interview_strategy best_answer_outlines assignment failed. " + "; ".join(outline_issues[:8]))
    set_result("interview_strategy_json", json_dumps(strategy))
    log(5, "Interview strategy JSON complete", "done")
    return strategy


STRATEGY_BANNED_OPENINGS = [
    "in my previous role",
    "in my role as",
    "i identified that",
    "i faced a situation",
    "recognizing the need",
    "while my manager was away",
]


def strategy_answer_has_banned_opening(answer):
    opening = normalize_text(answer).lower()
    return any(opening.startswith(item) for item in STRATEGY_BANNED_OPENINGS)


def story_title(story):
    return normalize_text(story.get("title") or story.get("story_name") or "Candidate story") if isinstance(story, dict) else ""


def story_id(story):
    return normalize_text(story.get("story_id") or story_id_from_title(story_title(story), 1)) if isinstance(story, dict) else ""


def story_lookup(candidate_profile):
    stories = [story for story in as_list((candidate_profile or {}).get("story_inventory")) if isinstance(story, dict)]
    by_id = {story_id(story): story for story in stories if story_id(story)}
    return stories, by_id


def story_assignment_keywords(question):
    text = normalize_text(question).lower()
    buckets = []
    checks = [
        (["stakeholder", "cross-functional", "cross functional", "regional", "handover", "partner", "alignment"], ["backlog", "handover", "stakeholder", "regional", "cross"]),
        (["process", "redesign", "efficiency", "workflow", "automation", "improvement"], ["queue", "workflow", "automation", "40", "process"]),
        (["metric", "dashboard", "data", "root cause", "integrity", "measure"], ["metric", "dashboard", "77", "93", "data", "sla"]),
        (["leadership", "team performance", "operating cadence", "quality", "qa"], ["team leadership", "quality", "qa", "14", "cadence"]),
        (["mentor", "mentorship", "buddy", "coaching", "knowledge transfer", "team growth"], ["people development", "mentor", "coach", "training"]),
        (["training", "onboarding", "upskilling", "sop", "repeatable"], ["training", "onboarding", "sop", "knowledge", "upskilling"]),
        (["workforce", "capacity", "staffing", "resource", "labor"], ["workforce", "resource", "capacity", "team of 10"]),
        (["launch", "readiness", "risk", "escalation", "delivery"], ["launch", "readiness", "risk", "operating rhythm", "escalation"]),
    ]
    for question_terms, story_terms in checks:
        if any(term in text for term in question_terms):
            buckets.extend(story_terms)
    return buckets


def direct_domain_question(question):
    text = normalize_text(question).lower()
    direct_terms = [
        "critical trade gap", "electrical", "piping", "mechanical", "trade school",
        "apprenticeship", "contractor", "data center construction", "construction workforce",
    ]
    transferable_terms = ["stakeholder", "metric", "risk", "process", "training", "resource", "alignment", "readiness"]
    return any(term in text for term in direct_terms) and not any(term in text for term in transferable_terms)


def choose_story_for_question(question, stories, counts):
    if direct_domain_question(question):
        return None
    keywords = story_assignment_keywords(question)
    best_story = None
    best_score = 0
    for story in stories:
        if counts.get(story_id(story), 0) >= 2 and len(stories) >= 5:
            continue
        haystack = " ".join([
            story_title(story),
            normalize_text(story.get("trigger_phrase")),
            " ".join(as_list(story.get("competencies"))),
            " ".join(as_list(story.get("usable_for_questions"))),
        ]).lower()
        score = sum(1 for keyword in keywords if keyword and keyword in haystack)
        if score > best_score:
            best_score = score
            best_story = story
    if best_story:
        return best_story
    for story in stories:
        if counts.get(story_id(story), 0) < 2 or len(stories) < 5:
            return story
    return None


QUESTION_ROUNDS = [
    "Recruiter",
    "Hiring Manager",
    "Program Management Execution",
    "Stakeholder / Partner Alignment",
    "Leadership / Behavioral",
    "Googleyness / Culture",
]


ROLE_SPECIFIC_TERMS = [
    "workforce", "electrical", "piping", "trade", "contractor", "vendor",
    "trade school", "training lab", "mentorship", "buddy", "craft labor",
    "safety", "data center", "delivery risk", "pipeline", "regional",
]


def role_specific_question_count(questions):
    count = 0
    for item in as_list(questions):
        text = normalize_text(item.get("question") if isinstance(item, dict) else item).lower()
        if any(term in text for term in ROLE_SPECIFIC_TERMS):
            count += 1
    return count


def assigned_story_for_question(question, candidate_profile, counts):
    stories, by_id = story_lookup(candidate_profile)
    story = choose_story_for_question(question, stories, counts)
    if story:
        sid = story_id(story)
        counts[sid] = counts.get(sid, 0) + 1
        return sid, story_title(story), story
    return "story_gap", "Story gap to prepare", None


def question_item(question, round_name, what_it_tests, jd_signal, candidate_risk_or_bridge, answer_strategy, candidate_profile, counts):
    sid, title, story = assigned_story_for_question(question, candidate_profile, counts)
    return {
        "question": question,
        "round": round_name,
        "what_it_tests": what_it_tests,
        "jd_signal": jd_signal,
        "candidate_risk_or_bridge": candidate_risk_or_bridge,
        "candidate_gap": candidate_risk_or_bridge,
        "research_signal": "Google data center workforce development signals and public hiring process signals; directional unless officially supported.",
        "assigned_story_id": sid,
        "assigned_story_title": title,
        "answer_strategy": answer_strategy,
    }


def default_likely_questions(candidate_profile):
    counts = {}
    specs = [
        ("Recruiter", "Walk me through why this Google Data Center Construction Workforce Development role makes sense for you when your background is operations rather than construction.", "Role motivation, truthful positioning, and gap awareness.", "Workforce development strategy for data center construction delivery.", "Transferable operations evidence, not direct construction ownership.", "Open with the honest bridge: operations systems, metrics, training, stakeholders, and delivery risk."),
        ("Recruiter", "Which parts of the role are strongest for you, and which parts would require the fastest learning curve?", "Self-awareness and role targeting.", "Electrical, mechanical, piping, contractor, trade-school, and workforce-board ecosystem.", "Must not pretend domain expertise.", "Name the strengths first, then the domain gaps and the learning plan."),
        ("Hiring Manager", "How would you diagnose regional workforce shortages that could put a data center delivery plan at risk?", "Structured problem diagnosis in the target domain.", "Identify critical trade gaps and labor-market constraints.", "No direct construction labor-market ownership.", "Use metrics, dashboards, stakeholder interviews, and operating rhythm as the transferable method."),
        ("Hiring Manager", "Tell me how you would build a workforce readiness dashboard for electrical and piping trade gaps.", "Metrics design and data integrity.", "Tracking workforce readiness metrics.", "Candidate has SLA/KPI evidence but not trade-pipeline metrics.", "Use the SLA metric correction and dashboarding bridge; hold the domain boundary."),
        ("Program Management Execution", "Describe a program mechanism you would use to reduce delivery risk caused by craft labor constraints.", "Program mechanism design and risk reduction.", "Reducing delivery risk caused by labor constraints.", "Must not claim past data center delivery ownership.", "Use launch readiness, backlog, and operating cadence as transferable mechanisms."),
        ("Program Management Execution", "How would you decide whether a training lab, mentorship program, or upskilling module is actually working?", "Outcome metrics, adoption, and control plans.", "Building training labs, mentorship or buddy programs, and upskilling modules.", "Candidate has training/SOP/team development bridge, not craft-labor ownership.", "Answer with training, SOP, QA, adoption, and measurable readiness."),
        ("Stakeholder / Partner Alignment", "A contractor says the labor shortage is not their problem, while internal delivery leaders say it is blocking schedule. What do you do?", "Conflict handling without direct authority.", "Aligning general contractors, trade partners, and internal construction delivery teams.", "No direct contractor management proof.", "Use stakeholder influence, backlog handovers, and neutral operating data."),
        ("Stakeholder / Partner Alignment", "How would you align community colleges, trade schools, workforce boards, contractors, and Google delivery teams around one plan?", "Partner ecosystem alignment.", "Align external partners and internal delivery teams.", "No direct trade-school partnership ownership.", "Use global handovers and cross-functional operating rhythm as the bridge."),
        ("Leadership / Behavioral", "Tell me about a time you improved team capability through coaching, training, or a repeatable playbook.", "People development and scalable capability-building.", "Mentorship, buddy programming, upskilling, and SOPs.", "Strong bridge through people development and SOPs.", "Use coaching, onboarding, playbooks, and quality improvement."),
        ("Leadership / Behavioral", "Tell me about a time you had to communicate a serious operating risk to senior stakeholders before everyone agreed it was a problem.", "Executive communication and risk escalation.", "Communicating program status, risks, and mitigation plans to senior stakeholders.", "Candidate has stakeholder communication and KPI evidence.", "Use SLA/KPI, dashboards, or launch readiness."),
        ("Googleyness / Culture", "How would you keep peer-to-peer safety standards and craft labor support from becoming a checkbox exercise?", "Judgment, culture, and sustained adoption.", "Craft labor support, mentorship, buddy programming, and safety standards.", "Safety domain is not proven; adoption discipline is transferable.", "Hold the safety-domain boundary and discuss adoption mechanisms."),
        ("Googleyness / Culture", "Give me an example of when you challenged a metric or process because the visible number was not telling the truth.", "Comfort with evidence, ambiguity, and integrity.", "Workforce readiness metrics and data tracking capabilities.", "Strong bridge through SLA metric correction.", "Use the 77% to 93% metric correction story."),
    ]
    return [
        question_item(question, round_name, test, signal, risk, strategy, candidate_profile, counts)
        for round_name, question, test, signal, risk, strategy in specs
    ]


def default_dangerous_questions(candidate_profile):
    counts = {}
    specs = [
        ("Recruiter", "You have no direct data center construction workforce development experience. Why should Google take that risk?", "Domain-gap pressure test.", "Data center construction workforce development.", "Direct domain gap.", "Give an honest boundary, then bridge to workforce-adjacent operating systems."),
        ("Hiring Manager", "How would you identify electrical and piping trade gaps if you have not worked with those trades before?", "Depth of learning plan and humility.", "Electrical and piping trade gaps.", "Electrical/piping expertise gap.", "Do not fake expertise; explain the diagnostic operating model and expert-partner approach."),
        ("Hiring Manager", "What would you say to a general contractor who disagrees with your workforce readiness assessment?", "Contractor influence and conflict.", "Contractor alignment.", "No direct contractor management claim.", "Use stakeholder influence and data-backed alignment."),
        ("Program Management Execution", "What metrics would you use to prove a training lab is reducing delivery risk rather than just training attendance?", "Outcome metrics and business linkage.", "Training labs and delivery-risk reduction.", "No craft-labor training ownership.", "Bridge from SLA/KPI discipline to readiness and adoption metrics."),
        ("Program Management Execution", "A region is six months behind building the trade pipeline. What is your first 30 days of action?", "Prioritization under delivery pressure.", "Regional workforce shortages.", "No direct labor-market plan ownership.", "Use triage, stakeholder map, data baseline, and escalation rhythm."),
        ("Stakeholder / Partner Alignment", "A trade school partner wants long-term curriculum funding, but delivery leaders need immediate labor support. How do you handle the tradeoff?", "Tradeoff reasoning across partner incentives.", "Trade school partnerships and delivery risk.", "No trade-school ownership.", "Name short-term/long-term operating mechanisms without pretending past ownership."),
        ("Stakeholder / Partner Alignment", "How would you handle a workforce board, contractor, and internal delivery team all using different definitions of readiness?", "Operating definitions and governance.", "Workforce readiness metrics.", "Metrics bridge is strong; domain definitions need learning.", "Use metric correction and dashboard governance."),
        ("Leadership / Behavioral", "Tell me about a time your process improvement created resistance and how you got adoption.", "Change adoption and influence.", "Repeatable workforce mechanisms.", "Strong bridge through SOPs, backlog, and workflow automation.", "Use SOP/process story with adoption and tradeoff."),
        ("Leadership / Behavioral", "What would you do if your mentorship or buddy program looked good in reports but craft workers said it was not useful?", "Listening, quality, and corrective action.", "Mentorship and buddy programming.", "No craft-worker experience.", "Use coaching/QA bridge and explain feedback loops."),
        ("Googleyness / Culture", "What is the strongest claim you cannot make in this interview, and how will you compensate for it?", "Integrity, self-awareness, and judgment.", "Avoid unsupported domain claims.", "Candidate must not invent construction expertise.", "State the forbidden claim clearly and bridge to verified operating evidence."),
    ]
    return [
        question_item(question, round_name, test, signal, risk, strategy, candidate_profile, counts)
        for round_name, question, test, signal, risk, strategy in specs
    ]


def normalize_strategy_questions(strategy, candidate_profile):
    likely = default_likely_questions(candidate_profile)
    dangerous = default_dangerous_questions(candidate_profile)
    strategy["top_10_likely_questions"] = likely
    strategy["top_10_dangerous_questions"] = dangerous
    return strategy


def first_company_signal(strategy, research):
    section_strategy = strategy.get("section_strategy", {}) if isinstance(strategy.get("section_strategy"), dict) else {}
    for item in as_list(section_strategy.get("company_signal_map")):
        if isinstance(item, dict):
            signal = normalize_text(item.get("signal"))
            if signal and "research insufficient" not in signal.lower():
                return signal
        else:
            text = normalize_text(item)
            if text and "research insufficient" not in text.lower():
                return text
    for item in as_list((research or {}).get("official_facts")):
        title = normalize_text(item.get("title") if isinstance(item, dict) else item)
        if "workforce" in title.lower() or "data center" in title.lower():
            return "Google has public data center workforce-development signals, so this role is about building workforce ecosystems that protect delivery, not generic program coordination."
    return "Google's public materials and the submitted JD point to workforce ecosystem building as a delivery-risk lever."


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


def build_why_company_answer(strategy, research, candidate_profile):
    company = (research or {}).get("company") or "Google"
    signal = first_company_signal(strategy, research)
    bridge = candidate_bridge_summary(candidate_profile)
    return (
        f"What draws me to {company} is that this role connects workforce development directly to data center delivery risk. "
        f"The company signal I would anchor on is this: {signal} "
        "That is different from a generic program management role because the work is not only coordinating tasks; it is building the operating system around partners, readiness metrics, training mechanisms, and risk visibility. "
        f"My bridge is not direct construction ownership, and I would be clear about that. My evidence is {bridge}. "
        "Those stories show that I can make an ambiguous operating constraint measurable, align people who do not all report to me, and sustain improvement through dashboards, SOPs, coaching, and escalation rhythms. "
        "What I want to learn at Google is the construction workforce ecosystem itself: how contractors, trade partners, education partners, and delivery teams define readiness, where the pipeline breaks, and which mechanisms actually reduce schedule risk. "
        "That combination is why Google is compelling to me: the role would let me apply proven operating discipline to a workforce problem that has real delivery impact."
    )


def build_why_role_answer(jd_analysis, candidate_profile):
    domain = normalize_text((jd_analysis or {}).get("role_domain")) or "Data Center Construction Workforce Development"
    responsibilities = jd_signal_texts(jd_analysis)[:4]
    bridge = candidate_bridge_summary(candidate_profile)
    return (
        f"This role makes sense because it sits at the intersection of {domain}, stakeholder alignment, training mechanisms, metrics, and delivery-risk management. "
        f"The JD signals I would focus on are: {'; '.join(responsibilities)}. "
        "Those responsibilities require someone who can turn an unclear operating problem into a measurable program, not just someone who can run meetings. "
        f"My strongest bridge is {bridge}. "
        "I would not claim that I already own construction workforce development, electrical or piping trades, contractor management, or trade-school partnerships. "
        "What I can credibly bring is the operating pattern behind the role: diagnose the constraint, build a rhythm around it, align stakeholders, track the right metrics, and communicate risk clearly before it becomes a delivery issue. "
        "That is why this role is attractive: it stretches me into a new domain while still using the program-management evidence I can already prove."
    )


def build_thirty_sixty_ninety_answer(jd_analysis, candidate_profile):
    bridge = candidate_bridge_summary(candidate_profile)
    return {
        "30_days": [
            "Learn the data center construction workforce ecosystem: internal delivery teams, contractors, trade partners, education partners, workforce boards, and the current definition of readiness.",
            "Map the existing risk rhythm: how labor constraints are surfaced, who owns mitigation, what metrics are trusted, and where the current dashboard or reporting gaps sit.",
            f"Use my proven bridge carefully: {bridge}. I would apply that operating discipline while learning the construction domain from the experts."
        ],
        "60_days": [
            "Build or refine a workforce readiness operating view that separates pipeline, training, mentorship, partner alignment, and delivery-risk signals.",
            "Identify the highest-risk regional trade gaps and create a practical stakeholder cadence with clear owners, escalation paths, and decision points.",
            "Pilot one repeatable mechanism, such as a readiness review, training adoption tracker, or partner alignment forum, without claiming past craft-labor ownership."
        ],
        "90_days": [
            "Show measurable improvement in visibility, decision speed, or risk mitigation for at least one workforce constraint agreed by the team.",
            "Turn the pilot into a repeatable operating mechanism with SOPs, dashboard discipline, and senior stakeholder communication.",
            "Demonstrate that I can bridge from operations leadership into construction workforce development responsibly: honest about domain learning, strong on execution, and useful to delivery teams."
        ],
    }


def answer_word_range(answer):
    return count_words(answer)


def fit_answer_word_count(answer):
    answer = normalize_text(answer)
    if answer_word_range(answer) < 180:
        answer = normalize_text(answer + " " + (
            "I would be careful not to overclaim construction, contractor, trade, or data center ownership. "
            "The strength I would emphasize is the operating pattern: I clarified the problem, made the work measurable, aligned people around the change, and protected the outcome through follow-through. "
            "That is the bridge I can bring to a Google role where workforce readiness, partner alignment, and delivery risk need disciplined program management."
        ))
    if answer_word_range(answer) > 240:
        sentences = re.split(r"(?<=[.!?])\s+", answer)
        kept = []
        for sentence in sentences:
            if answer_word_range(" ".join(kept + [sentence])) > 235:
                break
            kept.append(sentence)
        answer = normalize_text(" ".join(kept)) or answer
    return answer


def build_story_answer(question, story):
    title = story_title(story)
    metrics = ", ".join(as_list(story.get("metrics") or story.get("metrics_provided"))) or "the operating metric attached to the story"
    actions = as_list(story.get("actions"))[:3]
    competencies = ", ".join(as_list(story.get("competencies"))[:3]) or "program management and operating discipline"
    result = normalize_text(story.get("result")) or "a measurable operating improvement"
    situation = normalize_text(story.get("situation")) or title
    decision = normalize_text(story.get("decision")) or "to treat the issue as an operating-system problem rather than a one-off task"
    opening = story_answer_opening(question, story)
    action_sentence = story_action_sentence(actions)
    angle = question_angle(question)
    if angle == "metrics_design":
        angle_sentence = "For Google, I would translate that into a readiness metric only after agreeing what decision the metric should improve and which domain expert owns the definition."
        tradeoff = "The tradeoff is speed versus accuracy: a fast dashboard is dangerous if the metric drives the wrong behavior."
    elif angle == "stakeholder_conflict":
        angle_sentence = "For Google, I would use the same pattern with contractors and internal delivery teams: separate opinion from evidence, agree the readiness definition, and make the next decision explicit."
        tradeoff = "The tradeoff is that alignment can feel slower at first, but it prevents people from optimizing against different versions of the problem."
    elif angle == "training_adoption":
        angle_sentence = "For Google, I would apply that to training labs or mentorship by measuring adoption, behavior change, and whether the mechanism reduces delivery risk."
        tradeoff = "The tradeoff is activity versus impact: attendance is easy to count, but readiness is what matters."
    elif angle == "risk_escalation":
        angle_sentence = "For Google, I would use that pattern to move labor constraints from informal concern to visible delivery risk with owners, cadence, and escalation."
        tradeoff = "The tradeoff is raising risk early without overstating certainty; I would rather create visibility while the team can still act."
    elif angle == "domain_bridge":
        angle_sentence = "For Google, I would be explicit that this is transferable operating evidence, then show how I would learn the construction workforce domain from the people closest to it."
        tradeoff = "The tradeoff is credibility versus ambition: I need to stretch into the domain without pretending I have already owned it."
    else:
        angle_sentence = "For Google, I would apply the same operating discipline: clarify the constraint, make ownership visible, and create a mechanism that survives beyond one escalation."
        tradeoff = "The tradeoff is solving the immediate pressure while still fixing the operating mechanism underneath it."
    answer = (
        f"{opening} "
        f"In that example, {situation}. "
        f"The decision I made was {decision}. "
        f"{action_sentence} "
        f"The metric I would use is {metrics}, and I would connect it to the business result: {result}. "
        f"{tradeoff} "
        "I would also be clear that this was not construction workforce development, so I would not present it as trade, contractor, or data center delivery experience. "
        f"{angle_sentence} "
        f"{story_answer_closing(question, story, result)}"
    )
    if strategy_answer_has_banned_opening(answer):
        answer = "The measurable operating result is the important starting point. " + answer
    return fit_answer_word_count(answer)


def build_story_gap_answer(question, candidate_profile):
    forbidden = "; ".join(as_list((candidate_profile or {}).get("forbidden_claims"))[:3])
    angle = question_angle(question)
    if "contractor" in normalize_text(question).lower():
        opening = "I have not built a contractor partnership directly. The operating pattern I would apply is to make the constraint visible before trying to force agreement."
        bridge = "The closest transferable evidence is stakeholder alignment through backlog and handover work, where different groups needed one shared view of the operating problem."
        close = "That is the honest answer: I would bring structure, shared facts, and escalation discipline, while learning the contractor context from the experts."
    elif any(term in normalize_text(question).lower() for term in ["trade school", "community college", "workforce board"]):
        opening = "I have not owned trade-school or workforce-board partnerships directly. The bridge I would use is repeatable training, SOP, stakeholder, and adoption work."
        bridge = "The closest transferable evidence is building mechanisms that make knowledge transfer and operating expectations clearer for a team."
        close = "That shows the interviewer I can build the operating rhythm around partners without inventing education-partnership ownership."
    elif any(term in normalize_text(question).lower() for term in ["electrical", "piping", "trade gap"]):
        opening = "I have not owned electrical or piping trade planning. My first move would be to learn the constraint from domain experts and turn it into a metric the program can act on."
        bridge = "The closest transferable evidence is the SLA and dashboard work, where I challenged whether the visible number reflected the real operating issue."
        close = "That keeps the boundary honest while still showing how I would make the trade gap measurable and actionable."
    elif angle == "domain_bridge":
        opening = "The closest transferable evidence I have for this is the backlog handover work, because it shows how I handle ambiguity, ownership gaps, and delivery risk."
        bridge = "I would name the domain gap directly, then show the operating pattern I can prove: metrics, handovers, capacity visibility, stakeholder alignment, and follow-through."
        close = "The interviewer should hear both parts: no false domain claim, and a credible operating foundation for learning the domain quickly."
    else:
        opening = "My first move would be to get the constraint visible before prescribing a solution. The way I have done that is through operations work where unclear ownership and weak metrics were creating delivery risk."
        bridge = "The closest transferable evidence is making ambiguous work measurable, creating dashboards or operating rhythms, coordinating stakeholders, and using metrics to guide decisions."
        close = "That is the bridge I would use: not domain ownership, but disciplined problem diagnosis and accountable execution."
    answer = (
        f"{opening} "
        "I would be explicit about that boundary in the interview because claiming direct construction, electrical, piping, trade school, contractor, or data center delivery ownership would be inaccurate. "
        f"{bridge} "
        "The tradeoff is that transferable evidence is not the same as domain proof, so I would not present it as a finished workforce-development credential or pretend I already know the trade ecosystem. "
        "Instead, I would say that the story I still need to prepare is a truthful example of diagnosing a capacity or capability gap, aligning partners, tracking adoption, and reducing delivery risk. "
        f"What I would not say is: {forbidden or 'anything that invents unsupported direct domain ownership'}. "
        f"{close}"
    )
    return fit_answer_word_count(answer)


def normalize_outline_answer_item(question, story, candidate_profile):
    if story is None:
        return {
            "question": normalize_text(question),
            "assigned_story_id": "story_gap",
            "assigned_story_title": "Story gap to prepare",
            "assigned_story": "Story gap to prepare",
            "story_source": "story_gap",
            "why_this_story": "No candidate story directly proves this domain-specific question without risking unsupported claims.",
            "complete_written_answer": build_story_gap_answer(question, candidate_profile),
            "full_answer": build_story_gap_answer(question, candidate_profile),
            "what_it_proves": "Truthful boundary-setting and transferable operating discipline.",
            "metric_to_use": "No direct metric; prepare a truthful metric if one exists.",
            "tradeoff_to_show": "Transferable evidence versus direct domain ownership.",
            "result_squared": "Shows honesty, judgment, and a plan to build the missing story.",
            "what_not_to_say": "Do not invent direct construction, electrical, piping, trade school, contractor, or data center delivery ownership.",
            "evidence_used": ["story_gap"],
            "risk_boundary": "Do not claim unsupported background.",
        }
    metrics = as_list(story.get("metrics") or story.get("metrics_provided"))
    answer = build_story_answer(question, story)
    return {
        "question": normalize_text(question),
        "assigned_story_id": story_id(story),
        "assigned_story_title": story_title(story),
        "assigned_story": story_title(story),
        "story_source": story.get("source", ""),
        "why_this_story": f"This story maps to the question through {', '.join(as_list(story.get('usable_for_questions'))[:3]) or 'transferable program evidence'}.",
        "complete_written_answer": answer,
        "full_answer": answer,
        "what_it_proves": ", ".join(as_list(story.get("competencies"))[:4]) or "Grounded candidate evidence.",
        "metric_to_use": ", ".join(metrics) if metrics else "Use only the metrics already attached to this story.",
        "tradeoff_to_show": "Name the domain boundary honestly while showing the transferable operating pattern.",
        "result_squared": story.get("result_squared") or "Explain how the result proves a repeatable operating pattern.",
        "what_not_to_say": "; ".join(as_list(story.get("forbidden_expansions"))[:3]) or "Do not claim unsupported domain ownership.",
        "evidence_used": [story_id(story), story_title(story)],
        "risk_boundary": "Do not claim unsupported background.",
    }


def normalize_best_answer_outlines(strategy, candidate_profile):
    stories, by_id = story_lookup(candidate_profile)
    questions = [
        item for item in as_list(strategy.get("top_10_likely_questions"))
        if isinstance(item, dict) and item.get("question")
    ][:10]
    if len(questions) < 8:
        for item in as_list(strategy.get("best_answer_outlines")):
            if len(questions) >= 10:
                break
            if isinstance(item, dict) and item.get("question"):
                questions.append({"question": item.get("question")})
    counts = {}
    outlines = []
    for item in questions[:10]:
        question = item.get("question", "")
        story = choose_story_for_question(question, stories, counts)
        if story is not None:
            counts[story_id(story)] = counts.get(story_id(story), 0) + 1
        outlines.append(normalize_outline_answer_item(question, story, candidate_profile))
    strategy["best_answer_outlines"] = outlines
    return strategy


def validate_best_answer_outlines(strategy, candidate_profile):
    stories, by_id = story_lookup(candidate_profile)
    outlines = as_list(strategy.get("best_answer_outlines"))
    issues = []
    if len(outlines) < 8:
        issues.append("best_answer_outlines has fewer than 8")
    counts = {}
    for index, outline in enumerate(outlines, start=1):
        if not isinstance(outline, dict):
            issues.append(f"outline {index} is not an object")
            continue
        sid = normalize_text(outline.get("assigned_story_id"))
        title = normalize_text(outline.get("assigned_story_title"))
        answer = normalize_text(outline.get("complete_written_answer") or outline.get("full_answer"))
        if not sid:
            issues.append(f"outline {index} missing assigned_story_id")
        if not title:
            issues.append(f"outline {index} missing assigned_story_title")
        if sid != "story_gap" and sid not in by_id:
            issues.append(f"outline {index} assigned_story_id not found in candidate_profile: {sid}")
        if sid != "story_gap":
            counts[sid] = counts.get(sid, 0) + 1
        words = count_words(answer)
        if words < 180:
            issues.append(f"outline {index} complete_written_answer fewer than 180 words")
        if words > 240:
            issues.append(f"outline {index} complete_written_answer more than 240 words")
        if strategy_answer_has_banned_opening(answer):
            issues.append(f"outline {index} starts with banned opening")
    if len(stories) >= 5:
        for sid, count in counts.items():
            if count > 2:
                issues.append(f"story {sid} used more than twice")
    return issues


def normalize_interview_strategy(strategy, research=None, candidate_profile=None, jd_analysis=None):
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

    strategy = normalize_strategy_questions(strategy, candidate_profile or {})

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

    strategy = normalize_best_answer_outlines(strategy, candidate_profile or {})
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
    if not normalize_text(strategy.get("exact_positioning_strategy")):
        strategy["exact_positioning_strategy"] = (
            "Position as a transferable operating-systems builder: honest about not owning data center construction workforce development directly, "
            "strong on capacity visibility, KPI discipline, stakeholder alignment, SOPs, training, handovers, launch readiness, and risk escalation."
        )
    if not strategy["why_interviewer_might_hesitate"]:
        strategy["why_interviewer_might_hesitate"] = [
            "The candidate has not directly owned data center construction workforce development.",
            "The candidate does not have proven electrical, piping, contractor, trade-school, or craft-labor domain ownership.",
            "The interviewer may worry the candidate will overtranslate general operations experience into a specialized construction workforce role.",
        ]
    if not strategy["how_candidate_wins"]:
        bridge = candidate_bridge_summary(candidate_profile or {})
        strategy["how_candidate_wins"] = [
            f"Use the strongest grounded bridge stories: {bridge}.",
            "Translate each story into the role's real operating problem: workforce visibility, partner alignment, readiness metrics, training adoption, and delivery-risk reduction.",
            "Hold the domain boundary clearly while showing a practical learning plan for contractors, trade partners, education partners, and data center delivery teams.",
        ]
    if not strategy["must_emphasize"]:
        signals = jd_signal_texts(jd_analysis or {})[:4]
        strategy["must_emphasize"] = [
            "Capacity, quality, handover, dashboard, and risk-management evidence from the real CV and answer bank.",
            "A clear operating mechanism: diagnose the constraint, define the metric, align owners, create cadence, and escalate risk early.",
            "Role-specific signals from the JD: " + ("; ".join(signals) if signals else "workforce development strategy, trade-gap diagnosis, partner alignment, training mechanisms, readiness metrics, and senior stakeholder communication."),
        ]
    if not strategy["must_avoid"]:
        strategy["must_avoid"] = [
            "Do not claim direct construction workforce development ownership.",
            "Do not claim electrical, piping, contractor, trade-school, craft-labor, or data center delivery expertise unless the CV proves it.",
            "Do not turn transferable operations stories into fake domain stories; label them as bridges.",
        ]
    strategy["why_this_company_answer"] = build_why_company_answer(strategy, research or {}, candidate_profile or {})
    strategy["why_this_role_answer"] = build_why_role_answer(jd_analysis or {}, candidate_profile or {})
    strategy["thirty_sixty_ninety"] = build_thirty_sixty_ninety_answer(jd_analysis or {}, candidate_profile or {})
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
            if key in {"id", "source_type", "excerpt", "raw", "content"} or key.endswith("_id"):
                continue
            if item in ("", [], {}, None):
                continue
            if isinstance(item, dict):
                item = ", ".join(f"{k}: {v}" for k, v in item.items() if v not in ("", [], {}, None) and k not in {"id", "source_type", "excerpt", "raw", "content"} and not k.endswith("_id"))
            if isinstance(item, list):
                item = ", ".join(short_item(entry) for entry in item[:4] if entry not in ("", [], {}, None))
            parts.append(f"{key}: {item}")
        return "; ".join(parts)
    return str(value)


def bullets(items, empty="No additional grounded items were produced for this section."):
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
            f"   - Round: {item.get('round', 'Likely interview area')}\n"
            f"   - What it tests: {item.get('what_it_tests', '')}\n"
            f"   - JD signal: {item.get('jd_signal', '')}\n"
            f"   - Candidate risk or bridge: {item.get('candidate_risk_or_bridge') or item.get('candidate_gap', '')}\n"
            f"   - Assigned story: {item.get('assigned_story_title', 'Story gap to prepare')}\n"
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
        full_answer = (item.get("complete_written_answer") or item.get("full_answer") or item.get("answer") or item.get("direct_answer") or "").strip()
        if not full_answer:
            full_answer = "Story gap to prepare: build a specific answer from verified candidate evidence before practicing this question."
        evidence = ", ".join(
            str(entry) for entry in as_list(item.get("evidence_used"))
            if str(entry).strip() and not re.match(r"^S\d", str(entry).strip())
        )
        risk_boundary = item.get("risk_boundary", "")
        story_label = item.get("assigned_story_title") or item.get("assigned_story") or "Story gap to prepare"
        rows.append(
            f"{index}. **{question}**\n"
            f"{full_answer}\n"
            f"   - Evidence used: Assigned story: {story_label}"
            f"{', ' + evidence if evidence else ''}\n"
            f"   - Why this story: {item.get('why_this_story') or 'Grounded candidate evidence.'}\n"
            f"   - Metric to use: {item.get('metric_to_use') or 'Use only verified metrics.'}\n"
            f"   - Tradeoff to show: {item.get('tradeoff_to_show') or 'Name the honest boundary.'}\n"
            f"   - Deeper impact: {item.get('result_squared') or 'Connect the result to business impact.'}\n"
            f"   - What not to say: {item.get('what_not_to_say') or 'Do not invent unsupported background.'}\n"
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
        name = story.get("title") or story.get("story_name") or "Grounded story"
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
            f"  - Metrics provided: {', '.join(as_list(story.get('metrics') or story.get('metrics_provided')))}\n"
            f"  - Competencies: {', '.join(as_list(story.get('competencies')))}"
        )
    return "\n".join(rows) if rows else "- No grounded stories found. Use Story gaps to prepare instead."


def evidence_ledger_from_objects(candidate_profile, jd_analysis, research, gap_map):
    claims = []
    seen = set()

    def add_claim(claim, classification, confidence, basis):
        claim = normalize_text(claim)
        basis = normalize_text(basis)
        if not claim or not classification or not confidence or not basis:
            return
        key = claim.lower()
        if key in seen:
            return
        seen.add(key)
        claims.append({
            "claim": claim,
            "classification": classification,
            "confidence": confidence,
            "basis": basis,
        })

    official_basis = []
    for item in as_list((research or {}).get("official_facts"))[:8]:
        if not isinstance(item, dict):
            continue
        title = normalize_text(item.get("title"))
        url = normalize_text(item.get("url"))
        if title or url:
            official_basis.append(f"{title} | {url}".strip(" |"))
    joined_official = " ; ".join(official_basis[:4]) or "official Google and submitted role materials"
    add_claim(
        "Google's posted role emphasizes workforce ecosystem building, skilled-trades pipeline readiness, and delivery-risk reduction rather than generic program coordination.",
        "officially_supported",
        "high",
        joined_official,
    )
    add_claim(
        "Google data center workforce preparation should connect partner alignment, training mechanisms, readiness metrics, and senior stakeholder risk communication.",
        "officially_supported",
        "high",
        joined_official,
    )
    add_claim(
        "Google interview preparation should treat public interview-process sources as directional unless the signal comes from official Google hiring material.",
        "directional_only",
        "medium",
        "research.json interview_signals and confidence labels",
    )

    for item in jd_signal_texts(jd_analysis)[:8]:
        add_claim(
            f"The JD explicitly tests whether the candidate can handle: {item}",
            "JD_supported",
            "high",
            "submitted job_description",
        )

    for item in as_list((candidate_profile or {}).get("hard_evidence"))[:5]:
        if not isinstance(item, dict):
            continue
        add_claim(
            item.get("claim", "Candidate has verified operating evidence."),
            "CV_supported" if item.get("basis") == "CV" else "answer_bank_supported",
            "high",
            item.get("basis", "candidate material"),
        )

    for story in as_list((candidate_profile or {}).get("story_inventory"))[:5]:
        if not isinstance(story, dict):
            continue
        metric = story_metric_text(story)
        add_claim(
            f"The candidate can credibly bridge through {story_title(story)} using {metric}.",
            "CV_supported" if story.get("source") == "CV" else "answer_bank_supported",
            "high",
            f"candidate_profile.story_inventory:{story_id(story)}",
        )

    add_claim(
        "The candidate has proven workforce-adjacent operating experience through team capacity management, resource allocation, training/onboarding, SOPs, KPI discipline, backlog reduction, and stakeholder influence, but not direct construction labor ownership.",
        "CV_supported",
        "high",
        "CV and answer_bank",
    )

    for item in as_list((gap_map or {}).get("dangerous_gaps"))[:6]:
        if not isinstance(item, dict):
            continue
        add_claim(
            f"The safest positioning on {item.get('gap')} is an honest transferable bridge, not a direct domain claim.",
            "inferred",
            "medium",
            item.get("honest_bridge") or item.get("do_not_say") or "gap_map.dangerous_gaps",
        )

    add_claim(
        "The safest interview positioning is transferable operating-system builder, not construction workforce expert.",
        "inferred",
        "high",
        "candidate_profile.forbidden_claims and gap_map.repair_scripts",
    )

    lines = []
    for claim in claims[:18]:
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
        if word_count and word_count < 180:
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
    if len(assigned) < 8:
        failures.append("Best Answer Outlines missing assigned stories")
        return failures
    counts = {}
    for story in assigned:
        story = story.strip()
        if story.lower().startswith("story gap"):
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


def source_title_claim_count(ledger_text, research):
    source_titles = research_source_titles(research)
    count = 0
    for claim in re.findall(r"^- Claim:\s*(.+)$", ledger_text or "", flags=re.M):
        normalized_claim = normalize_text(re.sub(r"[^a-z0-9]+", " ", claim)).lower()
        if not normalized_claim:
            continue
        for title in source_titles:
            normalized_title = normalize_text(re.sub(r"[^a-z0-9]+", " ", title)).lower()
            if not normalized_title:
                continue
            if normalized_claim == normalized_title:
                count += 1
                break
            claim_tokens = set(normalized_claim.split())
            title_tokens = set(normalized_title.split())
            overlap = len(claim_tokens & title_tokens) / max(len(claim_tokens | title_tokens), 1)
            if overlap >= 0.9 and len(claim_tokens) <= len(title_tokens) + 2:
                count += 1
                break
    return count


def validate_evidence_ledger(ledger_text, research):
    claims = re.findall(r"^- Claim:\s*(.+)$", ledger_text or "", flags=re.M)
    issues = []
    if len(claims) < 12:
        issues.append(f"Evidence Ledger has fewer than 12 meaningful claims: {len(claims)}")
    title_count = source_title_claim_count(ledger_text, research)
    if title_count:
        issues.append(f"Evidence Ledger has {title_count} source-title claims")
    blocks = re.split(r"\n(?=- Claim:)", ledger_text or "")
    for index, block in enumerate([item for item in blocks if item.strip()], start=1):
        if "Classification:" not in block or "Confidence:" not in block or "Basis:" not in block:
            issues.append(f"Evidence Ledger claim {index} missing classification, confidence, or basis")
    return issues


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


def replace_markdown_section(markdown, title, body):
    pattern = re.compile(rf"^## {re.escape(title)}\s*$", flags=re.M)
    match = pattern.search(markdown or "")
    if not match:
        return markdown
    start = match.end()
    next_match = re.search(r"^## ", markdown[start:], flags=re.M)
    end = start + next_match.start() if next_match else len(markdown)
    replacement = f"## {title}\n{body.strip()}\n\n"
    return markdown[:match.start()] + replacement + markdown[end:]


def find_story(candidate_profile, terms):
    stories = [story for story in as_list((candidate_profile or {}).get("story_inventory")) if isinstance(story, dict)]
    terms = [term.lower() for term in terms]
    best = None
    best_score = -1
    for story in stories:
        haystack = " ".join([
            story_title(story),
            normalize_text(story.get("situation")),
            normalize_text(story.get("decision")),
            " ".join(as_list(story.get("actions"))),
            " ".join(as_list(story.get("competencies"))),
            " ".join(as_list(story.get("usable_for_questions"))),
        ]).lower()
        score = sum(1 for term in terms if term in haystack)
        if score > best_score:
            best = story
            best_score = score
    return best


def lead_story_set(candidate_profile):
    return [
        find_story(candidate_profile, ["backlog", "handover", "stakeholder", "regional"]),
        find_story(candidate_profile, ["queue", "workflow", "automation", "40"]),
        find_story(candidate_profile, ["metric", "dashboard", "77", "93", "sla"]),
    ]


def story_label_for_visible(story):
    return story_title(story) if story else "Bridge story to prepare"


def editorial_story_for_question(question, candidate_profile):
    text = normalize_text(question).lower()
    if any(term in text for term in ["electrical", "piping", "readiness dashboard", "metric", "pipeline metrics", "definitions of readiness"]):
        return find_story(candidate_profile, ["metric", "dashboard", "77", "93", "sla"])
    if any(term in text for term in ["contractor", "vendor", "stakeholder", "community college", "trade school", "workforce board", "external partners"]):
        return find_story(candidate_profile, ["backlog", "stakeholder", "handover", "regional"])
    if any(term in text for term in ["training lab", "mentorship", "buddy", "upskilling", "safety", "craft workers", "coaching", "playbook"]):
        return find_story(candidate_profile, ["training", "onboarding", "sop", "people development", "mentor", "coaching", "quality"])
    if any(term in text for term in ["delivery risk", "regional workforce", "labor constraints", "six months behind", "data center"]):
        return find_story(candidate_profile, ["launch", "readiness", "risk", "workforce", "resource", "backlog"])
    if any(term in text for term in ["background is operations", "strongest claim", "fastest learning curve"]):
        return find_story(candidate_profile, ["backlog", "queue", "metric", "team leadership"])
    return find_story(candidate_profile, ["backlog", "metric", "training", "stakeholder"])


def metric_sentence(story):
    metrics = [normalize_text(item) for item in as_list((story or {}).get("metrics") or (story or {}).get("metrics_provided")) if normalize_text(item)]
    if not metrics:
        return "I would not add a metric unless I can tie it back to the actual story."
    if len(metrics) == 1:
        return f"The metric I would use is {metrics[0]}, because it gives the interviewer something concrete instead of a vague claim."
    return f"The metrics I would use are {', '.join(metrics[:3])}, because they show the change was measurable rather than anecdotal."


def question_angle(question):
    text = normalize_text(question).lower()
    if any(term in text for term in ["dashboard", "metric", "measure", "readiness", "definition", "visible number"]):
        return "metrics_design"
    if any(term in text for term in ["contractor", "disagrees", "partner", "community college", "trade school", "workforce board", "alignment"]):
        return "stakeholder_conflict"
    if any(term in text for term in ["training", "mentorship", "buddy", "upskilling", "coaching", "playbook", "capability"]):
        return "training_adoption"
    if any(term in text for term in ["risk", "six months behind", "delivery", "shortage", "labor constraint", "escalation"]):
        return "risk_escalation"
    if any(term in text for term in ["background", "strongest", "learning curve", "why should google", "claim you cannot make"]):
        return "domain_bridge"
    return "program_execution"


def story_action_sentence(actions):
    actions = [normalize_text(item).rstrip(".") for item in as_list(actions) if normalize_text(item)]
    if not actions:
        return "I clarified ownership, made the work measurable, and created a repeatable follow-up rhythm."
    if len(actions) == 1:
        return f"I personally {actions[0][0].lower() + actions[0][1:] if actions[0] else actions[0]}."
    if len(actions) == 2:
        return f"I personally {actions[0][0].lower() + actions[0][1:] if actions[0] else actions[0]}, and {actions[1][0].lower() + actions[1][1:] if actions[1] else actions[1]}."
    first = actions[0][0].lower() + actions[0][1:] if actions[0] else actions[0]
    second = actions[1][0].lower() + actions[1][1:] if actions[1] else actions[1]
    third = actions[2][0].lower() + actions[2][1:] if actions[2] else actions[2]
    return f"I personally {first}, {second}, and {third}."


def story_answer_opening(question, story):
    angle = question_angle(question)
    text = normalize_text(question).lower()
    title = story_title(story).lower()
    if angle == "metrics_design":
        if "electrical" in text or "piping" in text:
            return "For an electrical and piping readiness dashboard, I would start by making sure the metric reflects the real constraint, not just what is easy to count."
        if "visible number" in text or "telling the truth" in text:
            return "The metric example I would use is the moment I challenged a visible number because it was not telling the operating truth."
        if "metric" in title or "dashboard" in title or "77" in title or "93" in title:
            return "The answer starts with data integrity: I once found that a visible SLA number was not telling the full operating truth."
        return "For a metrics question, I would start by defining what decision the metric is supposed to improve."
    if angle == "stakeholder_conflict":
        if "community college" in text or "trade school" in text or "workforce board" in text:
            return "For a partner ecosystem question, I would lead with the need for one shared plan across groups with different incentives."
        if "contractor" in text:
            return "For a contractor disagreement, I would start by moving the conversation away from blame and toward the shared delivery risk."
        if "backlog" in title or "handover" in title:
            return "The stakeholder issue I would lead with was a cross-regional backlog where different teams were seeing the problem differently."
        return "For a partner-conflict question, I would lead with shared facts before trying to force agreement."
    if angle == "training_adoption":
        if "training lab" in text or "upskilling" in text:
            return "For a training lab or upskilling question, I would focus on whether the program changes readiness rather than whether it simply runs."
        if "playbook" in text or "improved team capability" in text:
            return "For a coaching and playbook question, I would show how I turned individual performance feedback into a repeatable team mechanism."
        if "safety" in text or "buddy" in text:
            return "For a safety or buddy-program question, I would focus on adoption quality rather than a checkbox rollout."
        if "mentor" in title or "training" in title or "sop" in title or "quality" in title:
            return "For a training-adoption question, I would focus on behavior change rather than activity."
        return "For capability building, I would show how I turned informal execution into a repeatable mechanism."
    if angle == "risk_escalation":
        if "regional workforce" in text or "shortage" in text:
            return "For regional workforce shortages, I would lead with the schedule risk and then work backward to the constraint."
        if "serious operating risk" in text or "senior stakeholders" in text:
            return "For a senior-stakeholder risk question, I would lead with the moment the risk became visible before everyone agreed it was urgent."
        if "craft labor" in text or "labor constraints" in text:
            return "For craft labor constraints, I would frame the answer around the program mechanism that turns an early warning into accountable action."
        if "launch" in title or "readiness" in title or "risk" in title:
            return "The risk became important when readiness gaps were visible before the team had a clean rhythm to manage them."
        return "The moment I would emphasize is when the operating risk became visible enough that waiting would have made the problem harder."
    if angle == "domain_bridge":
        if "strongest" in text or "learning curve" in text:
            return "I would separate the answer into two parts: where my evidence is strongest and where the learning curve is real."
        if "why should google take that risk" in text:
            return "I would answer the risk question by naming the gap plainly and then showing the closest operating evidence."
        if "claim you cannot make" in text:
            return "The strongest claim I cannot make is direct construction workforce ownership, and I would say that plainly."
        return "I would answer that by being clear about the boundary first and then showing the closest operating evidence."
    if "queue" in title or "workflow" in title or "40" in title:
        return "The process example I would use is a queue-routing redesign that freed 40 weekly hours."
    if "backlog" in title:
        return "The strongest execution example I would use is the backlog handover work that reduced volume by 34%."
    return "The strongest part of this example is that it turned ambiguity into a controlled operating mechanism."


def story_answer_closing(question, story, result):
    angle = question_angle(question)
    text = normalize_text(question).lower()
    result = normalize_text(result).rstrip(".")
    if angle == "metrics_design":
        if "electrical" in text or "piping" in text:
            return f"The result was {result}, and I would use that to show Google I can make workforce-readiness metrics decision-grade before teams rely on them."
        if "visible number" in text or "telling the truth" in text:
            return f"The result was {result}, and I would land the point that I do not let a clean-looking number hide a real operating risk."
        return f"The result was {result}, and the interviewer signal is that I protect decision quality before asking teams to act on a number."
    if angle == "stakeholder_conflict":
        if "community college" in text or "trade school" in text or "workforce board" in text:
            return f"The result was {result}, and I would connect it to building one operating plan across partners without pretending I have owned that exact ecosystem before."
        if "contractor" in text:
            return f"The result was {result}, and I would close by showing that I can turn contractor disagreement into a fact-based decision path."
        return f"The result was {result}, and the point I would land is that shared visibility makes disagreement easier to turn into action."
    if angle == "training_adoption":
        if "training lab" in text or "upskilling" in text:
            return f"The result was {result}, and I would connect that to measuring whether training changes readiness rather than just counting participation."
        if "playbook" in text or "improved team capability" in text:
            return f"The result was {result}, and I would close on the proof that capability improves when coaching becomes a repeatable mechanism."
        if "safety" in text or "buddy" in text:
            return f"The result was {result}, and I would use it to show that adoption quality has to be tested through feedback, not assumed from rollout."
        return f"The result was {result}, and I would connect that to building mechanisms people actually adopt, not programs that only look good on paper."
    if angle == "risk_escalation":
        if "regional workforce" in text or "shortage" in text:
            return f"The result was {result}, and I would close by showing that I can turn a capacity signal into an action plan before it becomes schedule damage."
        if "senior stakeholders" in text or "serious operating risk" in text:
            return f"The result was {result}, and the proof is that I can communicate risk early without overstating certainty."
        return f"The result was {result}, and the proof is that I know how to surface risk early enough for leaders to make better tradeoffs."
    if angle == "domain_bridge":
        if "strongest" in text or "learning curve" in text:
            return f"The result was {result}, and that is how I would balance confidence in my operating evidence with honesty about the domain learning curve."
        if "claim you cannot make" in text:
            return f"The result was {result}, and I would use that boundary to build trust rather than weaken the answer with overclaiming."
        return f"The result was {result}, and that is the honest bridge I would bring: operating discipline first, domain learning with humility."
    return f"The result was {result}, and I would use it to show that my value is turning unclear work into accountable execution."


def editorial_opening_for_question(question, story):
    text = normalize_text(question).lower()
    if "background is operations" in text or "why should google take that risk" in text:
        return "I would be careful not to sell myself as a construction workforce expert."
    if "electrical" in text or "piping" in text:
        return "I would not pretend I already know the electrical or piping labor market."
    if "contractor" in text or "vendor" in text:
        return "I would start by separating the disagreement from the data."
    if "trade school" in text or "workforce board" in text or "community college" in text:
        return "I would treat that as a partner-alignment problem with different incentives on the table."
    if "training lab" in text or "mentorship" in text or "buddy" in text or "upskilling" in text:
        return "I would judge the program by whether it changes readiness, not by whether it looks active."
    if "regional workforce" in text or "delivery risk" in text or "labor constraints" in text:
        return "The stake I would put on the table is schedule risk."
    if story:
        title = story_title(story).lower()
        if "backlog" in title:
            return "The closest evidence I would use is the global backlog and handover work."
        if "metric" in title or "dashboard" in title:
            return "The strongest evidence I have is the metric-correction work."
        if "training" in title or "sop" in title or "mentor" in title:
            return "The closest capability-building evidence is my training, SOP, and coaching work."
    return "The way I would answer is with an honest bridge, not a domain claim."


def fit_editorial_answer(answer):
    answer = normalize_text(answer)
    if count_words(answer) < 180:
        answer = normalize_text(answer + " " + (
            "I would close by making the boundary clear: this is not the same as owning construction workforce development, but it is evidence that I can bring order to ambiguous, cross-functional work. "
            "That is the part I would want Google to see: disciplined problem diagnosis, practical stakeholder alignment, and the judgment not to overstate what I have not yet owned."
        ))
    if count_words(answer) > 240:
        sentences = re.split(r"(?<=[.!?])\s+", answer)
        kept = []
        for sentence in sentences:
            if count_words(" ".join(kept + [sentence])) > 235:
                break
            kept.append(sentence)
        answer = normalize_text(" ".join(kept)) or answer
    return answer


def editorial_answer_for_question(question, story, candidate_profile):
    if story:
        return build_story_answer(question, story)
    return build_story_gap_answer(question, candidate_profile)


def editorial_executive_strategy(company_name, role_name, candidate_profile, jd_analysis, gap_map, strategy):
    lead_stories = [story for story in lead_story_set(candidate_profile) if story]
    thesis = (
        "The candidate wins by positioning as a transferable operating-systems builder: someone who has not owned construction workforce development directly, "
        "but has repeatedly made messy operational work measurable, aligned stakeholders, improved team capability, and reduced execution risk."
    )
    objection = (
        "The biggest interviewer objection is domain credibility: Google may worry that the candidate does not understand data center construction, skilled trades, contractors, trade schools, or electrical and piping labor constraints deeply enough."
    )
    bridge = (
        "The honest bridge is to say: I have not owned that domain, but I have owned the operating pattern behind it: capacity visibility, KPI discipline, stakeholder alignment, SOPs, training, handovers, launch readiness, and risk escalation."
    )
    proof_lines = []
    for story in lead_stories[:3]:
        proof_lines.append(f"- {story_title(story)}: {story_result_text(story)}; metric to use: {story_metric_text(story)}")
    avoid = [
        "Do not imply direct construction workforce development ownership.",
        "Do not claim electrical, piping, contractor, trade-school, or data center delivery expertise.",
        "Do not answer only with generic program management; translate every story into workforce readiness, partner alignment, metrics, or delivery-risk language.",
    ]
    positioning = (
        "Positioning line to say: \"I am not coming in as a construction workforce expert; I am coming in as an operator who knows how to make constraints visible, align the right partners, and build the rhythm that turns risk into accountable execution.\""
    )
    return "\n".join([
        f"Company: {company_name}",
        f"Role: {role_name}",
        "",
        f"Winning thesis: {thesis}",
        "",
        f"Biggest interviewer objection: {objection}",
        "",
        f"Exact honest bridge: {bridge}",
        "",
        "Three proof stories to lead with:",
        *(proof_lines or ["- Prepare three grounded proof stories before the interview."]),
        "",
        "Three things to avoid:",
        *(f"- {item}" for item in avoid),
        "",
        positioning,
    ])


def editorial_gap_repair(candidate_profile):
    scripts = [
        (
            "Construction workforce gap",
            "I would be direct: I have not owned construction workforce development before. The bridge I would make is that I have managed capacity, quality, handovers, and operating risk in support operations. I would use that experience to build the workforce operating system carefully: first understand the trade constraints from contractors and delivery teams, then make the gaps measurable, assign owners, and create a cadence where risk is surfaced early."
        ),
        (
            "Electrical and piping trade gap",
            "I would not pretend to know the electrical or piping labor market on day one. My first move would be to learn the constraint from the people closest to it, then translate that input into a dashboard the program can act on. The closest story I would use is the SLA/KPI correction work, because it shows I do not accept a number until I understand whether it reflects reality."
        ),
        (
            "Contractor/vendor gap",
            "If a contractor disagreed with the workforce assessment, I would not try to win the argument by authority. I would move the conversation to shared facts: where the schedule risk is, what each side is seeing, what metric defines readiness, and what decision is needed. The backlog and handover story is the bridge because it shows I can align groups without pretending they all have the same incentives."
        ),
        (
            "Trade school/apprenticeship gap",
            "I have not owned trade-school or apprenticeship partnerships, so I would not overclaim that. The bridge is training, onboarding, SOPs, and knowledge transfer. I would frame the work as a capability-building mechanism: define the skill gap, agree what readiness looks like, build a repeatable learning path with partners, and measure whether it changes workforce availability, not just participation."
        ),
        (
            "Safety/mentorship gap",
            "For safety or buddy programming, I would be careful because craft labor safety has domain-specific standards. My bridge is people development and QA discipline: I know how to turn coaching into a repeatable rhythm, make quality visible, and create feedback loops. I would lean on safety experts for the standard and own the operating mechanism that helps people adopt it consistently."
        ),
        (
            "Data center delivery context gap",
            "I would acknowledge that I have not worked inside a data center construction delivery environment. The way I would compensate is by learning the delivery model quickly and using launch-readiness discipline: stakeholder map, risk log, operating cadence, escalation path, and dashboard. My value would be making risk visible and actionable without pretending to be the domain expert."
        ),
        (
            "Workforce metrics gap",
            "The metric bridge is one of my strongest. I have experience challenging a KPI when the number did not reflect reality, improving visibility, and using dashboards to guide decisions. For this role, I would apply that same discipline to workforce readiness: define the metric with domain experts, test whether it predicts delivery risk, and make it useful for decisions rather than just reporting."
        ),
    ]
    return "\n".join(f"- **{title}:** {body}" for title, body in scripts)


def editorial_questions_section(items, candidate_profile):
    rows = []
    for index, item in enumerate(as_list(items), start=1):
        if not isinstance(item, dict):
            continue
        question = item.get("question", "")
        story = editorial_story_for_question(question, candidate_profile)
        rows.append(
            f"{index}. **{question}**\n"
            f"   - Round: {item.get('round', 'Likely interview area')}\n"
            f"   - What it tests: {item.get('what_it_tests', '')}\n"
            f"   - Why it is dangerous or important: {item.get('candidate_risk_or_bridge') or item.get('candidate_gap', '')}\n"
            f"   - Best bridge story: {story_label_for_visible(story)}\n"
            f"   - Strategy: {item.get('answer_strategy', '')}"
        )
    return "\n".join(rows)


def editorial_answer_outlines(strategy, candidate_profile):
    rows = []
    for index, item in enumerate(as_list(strategy.get("best_answer_outlines"))[:10], start=1):
        if not isinstance(item, dict) or not item.get("question"):
            continue
        question = item.get("question")
        story = editorial_story_for_question(question, candidate_profile)
        answer = editorial_answer_for_question(question, story, candidate_profile)
        rows.append(
            f"{index}. **{question}**\n"
            f"{answer}\n"
            f"   - Best bridge story: {story_label_for_visible(story)}\n"
            f"   - Delivery note: Say this calmly and precisely. The strength is the operating pattern, not a claim of direct construction-domain ownership."
        )
    return "\n".join(rows)


def editorial_why_google(company_name, candidate_profile, research):
    bridge = candidate_bridge_summary(candidate_profile)
    return (
        f"Why {company_name}: what interests me is the way this role connects workforce development to real infrastructure delivery risk. "
        "From the data center workforce signals, this is not generic program coordination; it is about building the partner ecosystem, training mechanisms, readiness metrics, and operating cadence that help construction teams deliver. "
        f"My honest bridge is {bridge}. "
        "I would not claim that I already know the skilled-trades labor market or the contractor ecosystem. What I can bring is the operating discipline behind the problem: make constraints visible, align stakeholders who have different incentives, build repeatable mechanisms, and use metrics to decide where risk is increasing. "
        "Why now is simple: my strongest experience is in operations where quality, capacity, handovers, and stakeholder trust all mattered, and this role would let me apply that pattern to a higher-stakes workforce problem. "
        "That is why Google is compelling to me: the work has a clear business consequence, and it rewards someone who can be honest about the learning curve while still moving the operating system forward."
    )


def editorial_why_role(role_name, candidate_profile, jd_analysis):
    bridge = candidate_bridge_summary(candidate_profile)
    domain = normalize_text((jd_analysis or {}).get("role_domain")) or role_name
    return (
        f"Why this role: {domain} is exactly the kind of problem where my background is transferable without pretending it is identical. "
        "The JD is asking for someone who can identify workforce gaps, align contractors and education partners, build training and mentorship mechanisms, track readiness metrics, and communicate delivery risk. "
        f"My bridge is {bridge}. "
        "Those stories are not construction stories, and I would not present them that way. They are evidence that I can diagnose an operating constraint, build visibility, improve a process, coach people through adoption, and communicate risk clearly. "
        "The part of the role that stretches me is the construction workforce domain: electrical and piping trades, contractor alignment, trade-school partnerships, and data center delivery context. "
        "The part I can contribute immediately is the program discipline: turn ambiguity into a mechanism, make the work measurable, and help senior stakeholders see where the risk is before it becomes a schedule problem."
    )


def editorial_thirty_sixty_ninety(candidate_profile):
    bridge = candidate_bridge_summary(candidate_profile)
    return "\n".join([
        "30 days:",
        "- Learn the domain before prescribing solutions: delivery model, contractor roles, trade constraints, education partners, workforce boards, and the current definition of readiness.",
        "- Build the stakeholder and risk map: who sees labor constraints first, which metrics are trusted, where escalation happens, and where the current operating rhythm breaks down.",
        f"- Bring the bridge carefully: {bridge}. Use those patterns to ask better questions, not to overclaim domain expertise.",
        "",
        "60 days:",
        "- Create a practical workforce-readiness view that separates pipeline, training, mentorship, partner alignment, adoption, and delivery-risk signals.",
        "- Pick one high-risk region or trade gap and build a repeatable operating cadence with owners, decision points, and senior stakeholder visibility.",
        "- Test whether the metrics change decisions. If a dashboard does not help teams act earlier, improve the metric rather than defend the report.",
        "",
        "90 days:",
        "- Show measurable improvement in visibility, decision speed, or mitigation quality for a real workforce constraint agreed by the team.",
        "- Turn the strongest pilot into a repeatable mechanism: SOP, cadence, dashboard, escalation path, and adoption feedback loop.",
        "- Demonstrate the core promise: honest about the domain learning curve, senior in operating discipline, and useful to delivery teams because risk becomes visible sooner.",
    ])


def final_editorial_rewrite_pack(pack, company_name, role_name, candidate_profile, jd_analysis, gap_map, strategy, research):
    edited = pack
    edited = replace_markdown_section(
        edited,
        "Executive Strategy",
        editorial_executive_strategy(company_name, role_name, candidate_profile, jd_analysis, gap_map, strategy),
    )
    edited = replace_markdown_section(edited, "Gap And Risk Repair Plan", editorial_gap_repair(candidate_profile))
    edited = replace_markdown_section(edited, "Likely Question Bank By Round", editorial_questions_section(strategy.get("top_10_likely_questions"), candidate_profile))
    edited = replace_markdown_section(edited, "Dangerous Question Bank", editorial_questions_section(strategy.get("top_10_dangerous_questions"), candidate_profile))
    edited = replace_markdown_section(edited, "Best Answer Outlines", editorial_answer_outlines(strategy, candidate_profile))
    edited = replace_markdown_section(edited, "Why This Company Answer", editorial_why_google(company_name, candidate_profile, research))
    edited = replace_markdown_section(edited, "Why This Role Answer", editorial_why_role(role_name, candidate_profile, jd_analysis))
    edited = replace_markdown_section(edited, "Thirty Sixty Ninety Day Answer", editorial_thirty_sixty_ninety(candidate_profile))
    assert_no_banned_visible_strings(edited)
    assert_no_editorial_banned_strings(edited)
    return edited


def build_pack_from_structured_objects(company_name, role_name, candidate_profile, jd_analysis, research, gap_map, strategy):
    section_strategy = strategy.get("section_strategy", {}) if isinstance(strategy.get("section_strategy"), dict) else {}
    likely_questions = strategy.get("top_10_likely_questions", [])
    dangerous_questions = strategy.get("top_10_dangerous_questions", [])
    evidence_ledger = evidence_ledger_from_objects(candidate_profile, jd_analysis, research, gap_map)
    evidence_issues = validate_evidence_ledger(evidence_ledger, research)
    if evidence_issues:
        raise ValueError("Evidence Ledger failed validation. " + "; ".join(evidence_issues[:8]))
    thirty_sixty_ninety = strategy.get("thirty_sixty_ninety", {}) if isinstance(strategy.get("thirty_sixty_ninety"), dict) else {}

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
{bullets(jd_analysis.get("required_competencies") or jd_analysis.get("must_prove_signals") or jd_analysis.get("jd_signals"))}

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
Dangerous gaps:
{bullets(gap_map.get("dangerous_gaps"))}

Repair scripts:
{bullets(gap_map.get("repair_scripts"))}

Story assignments:
{bullets(gap_map.get("story_assignments"))}

Pressure responses:
{bullets(gap_map.get("pressure_responses"))}

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
30 days:
{bullets(thirty_sixty_ninety.get("30_days"))}

60 days:
{bullets(thirty_sixty_ninety.get("60_days"))}

90 days:
{bullets(thirty_sixty_ninety.get("90_days"))}

## Why This Company Answer
{strategy.get("why_this_company_answer", "")}

## Why This Role Answer
{strategy.get("why_this_role_answer", "")}

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
    pack = final_editorial_rewrite_pack(
        pack,
        company_name,
        role_name,
        candidate_profile,
        jd_analysis,
        gap_map,
        strategy,
        research,
    )
    assert_no_banned_visible_strings(pack)
    assert_no_editorial_banned_strings(pack)
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


def validate_artifacts_before_pack(role_name, job_description, extra, candidate_profile, jd_analysis, gap_map, strategy):
    issues = []
    answer_bank, _company_context, _guidance = extract_answer_bank_and_guidance(extra)

    jd_issues = validate_jd_target_lock(jd_analysis, role_name, job_description)
    issues.extend(f"JD target lock: {issue}" for issue in jd_issues)

    expected_answer_bank_stories = split_answer_bank_stories(answer_bank)
    actual_story_count = len(as_list(candidate_profile.get("story_inventory")))
    if expected_answer_bank_stories and actual_story_count < len(expected_answer_bank_stories):
        issues.append(
            f"candidate story inventory incomplete: expected at least {len(expected_answer_bank_stories)} answer-bank stories, found {actual_story_count}"
        )
    if not as_list(candidate_profile.get("story_inventory")):
        issues.append("candidate story inventory empty")

    if not as_list(jd_analysis.get("top_responsibilities")):
        issues.append("JD top_responsibilities empty")
    if not as_list(jd_analysis.get("must_prove_signals")) and not as_list(jd_analysis.get("jd_signals")):
        issues.append("JD role signals empty")

    if not normalize_text(strategy.get("exact_positioning_strategy")):
        issues.append("interview strategy exact_positioning_strategy empty")
    for key in ["why_interviewer_might_hesitate", "how_candidate_wins", "must_emphasize", "must_avoid"]:
        if not as_list(strategy.get(key)):
            issues.append(f"interview strategy {key} empty")
    if not as_list(strategy.get("top_10_dangerous_questions")):
        issues.append("interview strategy dangerous questions empty")
    if not as_list(strategy.get("top_10_likely_questions")):
        issues.append("interview strategy likely questions empty")
    if len(as_list(strategy.get("top_10_likely_questions"))) < 12:
        issues.append("interview strategy likely questions fewer than 12")
    if len(as_list(strategy.get("top_10_dangerous_questions"))) < 10:
        issues.append("interview strategy dangerous questions fewer than 10")
    if role_specific_question_count(strategy.get("top_10_likely_questions")) + role_specific_question_count(strategy.get("top_10_dangerous_questions")) < 8:
        issues.append("interview strategy has fewer than 8 role-specific scenario questions")
    for index, question in enumerate(as_list(strategy.get("top_10_likely_questions")) + as_list(strategy.get("top_10_dangerous_questions")), start=1):
        if not isinstance(question, dict):
            continue
        if not question.get("assigned_story_id") or not question.get("assigned_story_title"):
            issues.append(f"question {index} missing assigned story or story_gap")
        for field in ["round", "what_it_tests", "jd_signal", "candidate_risk_or_bridge", "answer_strategy"]:
            if not normalize_text(question.get(field)):
                issues.append(f"question {index} missing {field}")
    outline_issues = validate_best_answer_outlines(strategy, candidate_profile)
    issues.extend(f"best_answer_outlines: {issue}" for issue in outline_issues)
    issues.extend(f"gap_map: {issue}" for issue in validate_gap_map(gap_map))
    if count_words(strategy.get("why_this_company_answer", "")) < 80:
        issues.append("why_this_company_answer is not fully written")
    if count_words(strategy.get("why_this_role_answer", "")) < 80:
        issues.append("why_this_role_answer is not fully written")
    thirty = strategy.get("thirty_sixty_ninety", {}) if isinstance(strategy.get("thirty_sixty_ninety"), dict) else {}
    if sum(len(as_list(thirty.get(key))) for key in ["30_days", "60_days", "90_days"]) < 6:
        issues.append("thirty_sixty_ninety is not fully written")

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
        future_map = {executor.submit(tavily_search, query): query for query in queries}
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
        future_map = {executor.submit(tavily_with_retry, q): q for q in queries}
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
            executor.submit(
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


def insufficient_why_company_answer(company_intelligence):
    found = markdown_list(company_intelligence.get("official_company_signals") or company_intelligence.get("directional_themes"))
    return (
        "Research insufficient for specific Google People Operations signals. "
        f"Found: {found} "
        "Missing: a clearly verified, non-generic signal about Google's People Operations operating model, "
        "service delivery measures, process improvement mechanisms, or People Operations quality model that can be safely used in a Why Google answer."
    )


def repair_why_company_answer(strategy, session, company_intelligence, candidate_profile):
    current = strategy.get("why_this_company_answer", "")
    if not has_specific_company_signal(company_intelligence):
        return insufficient_why_company_answer(company_intelligence)
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
Do not write generic phrases like "Google is a leader in innovation" or "I admire Google's culture."
If company_intelligence does not have enough specific signals to write a non-generic Why Google answer, write: "Research insufficient for specific Google People Operations signals" and list what was found versus what is missing.
Never pretend a generic answer is specific.
"""
    answer = ask_llm(prompt, model=MODEL_STRATEGY, max_tokens=1200, retries=1).strip()
    if why_company_is_generic(answer):
        answer = insufficient_why_company_answer(company_intelligence)
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
    report_progress(progress_callback, "Strategy answer validation", 86)
    result = normalize_modular_strategy(result, session, company_intelligence, role_intelligence, candidate_profile, gap_map)
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
    jd_analysis = create_jd_analysis_json(job_description, role_name)
    jd_analysis = checkpoint_json(workspace, "jd_analysis.json", jd_analysis)
    set_result("jd_analysis_json", json_dumps(jd_analysis))
    set_result("job_description_decode", json_dumps(jd_analysis))

    # Stage 3 — Research truth
    report_progress(progress_callback, "Research engine source collection", 28)
    sources = collect_sources(company_name, role_name, job_description, extra)
    youtube_transcripts = extract_youtube_transcripts(extra)
    reported_questions = extract_reported_questions(extra)
    research = create_research_json(company_name, role_name, sources, youtube_transcripts=youtube_transcripts)
    research = checkpoint_json(workspace, "research.json", research)
    set_result("research_json", json_dumps(research))
    set_result("intel_report", json_dumps(research))
    if reported_questions:
        log(3, f"Reported questions extracted from community sources ({len(reported_questions)} chars)", "done")
    else:
        log(3, "No reported questions extracted from community sources", "warning")

    # Stage 4 — Gap map
    report_progress(progress_callback, "Gap engine", 52)
    gap_map = create_gap_map_json(candidate_profile, jd_analysis, research)
    gap_map = checkpoint_json(workspace, "gap_map.json", gap_map)
    set_result("gap_map_json", json_dumps(gap_map))
    set_result("match_gap_risk_map", json_dumps(gap_map))

    # Stage 5 — Strategy
    report_progress(progress_callback, "Interview strategist engine", 74)
    strategy = create_interview_strategy_json(candidate_profile, jd_analysis, gap_map, research, reported_questions=reported_questions)
    strategy = checkpoint_json(workspace, "interview_strategy.json", strategy)
    set_result("interview_strategy_json", json_dumps(strategy))

    # Stage 6 — Assembly only
    report_progress(progress_callback, "Pack generation and validation", 92)
    artifact_issues = validate_artifacts_before_pack(role_name, job_description, extra, candidate_profile, jd_analysis, gap_map, strategy)
    if artifact_issues:
        validation = {
            "target_lock_company": company_name,
            "target_lock_role": role_name,
            "issues": artifact_issues,
            "status": "failed",
        }
        validation = checkpoint_json(workspace, "pack_validation.json", validation)
        set_result("pack_validation_json", json_dumps(validation))
        raise ValueError("Prep pack artifact validation failed. " + "; ".join(artifact_issues[:8]))

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
        "status": "pass" if not validation_issues else "failed",
    }
    validation = checkpoint_json(workspace, "pack_validation.json", validation)
    set_result("pack_validation_json", json_dumps(validation))
    if validation_issues:
        raise ValueError("Prep pack validation failed. " + "; ".join(validation_issues[:8]))
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
