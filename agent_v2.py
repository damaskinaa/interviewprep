import os
import re
import json
import time
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
"""

    digest = ask_llm(prompt, model=MODEL_FAST, max_tokens=2600, retries=3)
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
List only real source titles and URLs from the digest. Do not list tavily_answer or search_summary as URLs.

### Official company signal map
Official values, hiring language, culture, and answer signals. Only use official evidence.

### Directional public signal map
Candidate experience themes from public sources. Label as directional.

### Interview process map
Describe likely stages using calibrated language. Separate officially supported, repeated public theme, transcript signal, directional only, inferred, and unknown. State observed ranges with confidence. Never state exact rounds as fact unless official sources confirm them.

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

Return this exact structure:

### Candidate evidence summary
### Best quantified achievements
### Best interview stories
For each story include competency, evidence, metric, and best question types.
### Story to competency map
### Candidate gaps and repair angles
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
Direct, honest, no generic praise.

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

Return this structure:

### Core story portfolio
Create 10 to 14 stories. For each:
Story name
Best interview question types
Competencies proven
Situation
Task
Actions
Result
Metrics to include
Company or role signal it supports
Risk it repairs
Sharper version of the story
Weak version to avoid

### Story coverage map
Show which required competencies are covered and which are weak.

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

Create a serious interview question bank by likely round. Use the JD as the targeting core. If interview rounds are not official, label them as likely/observed/directional rather than factual.

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
- basis: source titles/URLs where available, or JD/CV/answer bank/transcript basis
- calibrated language to use
- language to avoid

Rules:
No unsupported claims.
No invented source URLs.
Do not call Reddit, Glassdoor, Blind, YouTube, blogs, forums, or prep sites official.
Do not state exact interview rounds as fact unless official source confirms them.
Do not invent candidate employers, titles, industries, credentials, degrees, domain expertise, or authority.
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

Write a premium final prep pack. It should feel like an executive interview strategist prepared it.

Rules:
Do not be generic.
Do not invent candidate evidence.
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
Make it detailed but readable.
No unsupported claims.
No invented source URLs.
No invented candidate background.

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

def run_full_pipeline(company_name, role_name, job_description, cv, extra, progress_callback=None):
    log(0, "Starting full Nailit pipeline", "running")
    report_progress(progress_callback, "Job created", 1)

    # Stage 1 — Research
    report_progress(progress_callback, "Official company site and careers pages", 8)
    sources = collect_sources(company_name, role_name, job_description, extra)
    youtube_transcripts = extract_youtube_transcripts(extra)
    report_progress(progress_callback, "Company values, culture, leadership principles", 16)
    source_digest = create_source_digest(company_name, role_name, sources, youtube_transcripts=youtube_transcripts)
    report_progress(progress_callback, "Interview process and likely rounds", 24)
    report_progress(progress_callback, "Role specific public signals", 32)
    report_progress(progress_callback, "Directional themes only", 40)
    report_progress(progress_callback, "Role signal synthesis", 48)
    company_intel = create_company_intelligence(company_name, role_name, source_digest)

    # Stage 2 — Candidate
    report_progress(progress_callback, "Candidate evidence digest using CV, answer bank, company context", 58)
    candidate_digest = create_candidate_evidence_digest(
        company_name,
        role_name,
        job_description,
        cv,
        extra,
    )

    # Stage 3 — Strategy
    report_progress(progress_callback, "JD decode", 66)
    job_decode = decode_job_description(
        company_name,
        role_name,
        job_description,
        company_intel,
    )

    report_progress(progress_callback, "Match gap risk", 74)
    match_map = create_match_gap_risk_map(
        company_name,
        role_name,
        job_decode,
        candidate_digest,
        company_intel,
    )

    report_progress(progress_callback, "Story bank", 82)
    story_bank = create_story_bank(
        company_name,
        role_name,
        candidate_digest,
        match_map,
    )

    report_progress(progress_callback, "Question bank by round", 90)
    qa_bank = create_question_and_answer_bank(
        company_name,
        role_name,
        company_intel,
        job_decode,
        match_map,
        story_bank,
    )

    report_progress(progress_callback, "Evidence ledger", 94)
    evidence_ledger = create_evidence_ledger(
        company_name,
        role_name,
        source_digest,
        company_intel,
        job_decode,
        candidate_digest,
        match_map,
        qa_bank,
    )

    report_progress(progress_callback, "Final prep pack", 96)
    final_pack = create_final_pack(
        company_name,
        role_name,
        company_intel,
        job_decode,
        candidate_digest,
        match_map,
        story_bank,
        qa_bank,
        evidence_ledger,
    )

    lua_brief = build_lua_mock_interview_brief(
        company_name,
        role_name,
        company_intel,
        job_decode,
        candidate_digest,
        match_map,
        story_bank,
        qa_bank,
    )

    log(0, "Pipeline complete", "done")
    report_progress(progress_callback, "Final prep pack complete", 100)

    return {
        "HAS_FAILED": "RESEARCH STATUS: FAILED" in source_digest,
        "HAS_BRIDGE": "Vercel" in source_digest or "external" in source_digest.lower(),
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
        )

        markdown = f"""# Interview Prep Pack

Company: {company_name}

Role: {role_name}

Generated: {timestamp}

Job ID: {safe_job_id}

## Research Plan

{get_result("research_plan")}

## Source Manifest

{get_result("source_manifest")}

## Company Intelligence

{get_result("intel_report")}

## Candidate Evidence Digest

{get_result("candidate_evidence_digest")}

## Job Description Decode

{get_result("job_description_decode")}

## Match Gap Risk Map

{get_result("match_gap_risk_map")}

## Story Bank

{get_result("story_bank")}

## Question And Answer Bank

{get_result("question_answer_bank")}

## Evidence Ledger

{get_result("evidence_ledger")}

## Final Prep Pack

{get_result("final_prep_pack")}
"""

        files = {
            "research_plan.txt": get_result("research_plan"),
            "source_manifest.txt": get_result("source_manifest"),
            "source_mix.json": get_result("source_mix"),
            "source_digest.txt": get_result("source_digest"),
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
