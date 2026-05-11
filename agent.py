import os
import re
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from daytona import Daytona, DaytonaConfig
from tavily import TavilyClient
from openai import OpenAI
from lua_brief_builder import build_lua_mock_interview_brief

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DAYTONA_API_KEY = os.getenv("DAYTONA_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
tavily = TavilyClient(api_key=TAVILY_API_KEY)

daytona = None
if DAYTONA_API_KEY:
    daytona = Daytona(DaytonaConfig(api_key=DAYTONA_API_KEY))

try:
    from firecrawl import FirecrawlApp
    firecrawl = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY")) if os.getenv("FIRECRAWL_API_KEY") else None
except Exception:
    firecrawl = None

results = {}
progress_log = []

SKIP_DOMAINS = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com")

HEADERS = {
    "User-Agent": "Mozilla/5.0 Chrome Safari"
}


def log(stage, message, status="running"):
    event = {
        "time": datetime.now().isoformat(),
        "stage": stage,
        "message": message,
        "status": status,
    }
    progress_log.append(event)
    print(f"[Stage {stage}] {message}")


def set_result(key, value):
    results[key] = value


def get_result(key):
    return results.get(key, "")




def make_sandbox(stage_name):
    if os.getenv("ENABLE_CHILD_SANDBOXES", "0") != "1":
        log(0, f"Using current Daytona backend for {stage_name}. Child sandbox creation disabled.", "done")
        return None

    if not daytona:
        log(0, f"Daytona not configured. Running {stage_name} without child sandbox.", "warning")
        return None

    try:
        sandbox = daytona.create()
        log(0, f"Daytona child sandbox created for {stage_name}", "done")
        return sandbox
    except Exception as error:
        log(0, f"Could not create Daytona child sandbox for {stage_name}: {error}", "warning")
        return None

def cleanup_sandbox(sandbox):
    if not sandbox:
        return

    try:
        sandbox.delete()
    except Exception:
        try:
            daytona.remove(sandbox)
        except Exception:
            pass


def ask_llm(prompt, model="gpt-4o", retries=2):
    for attempt in range(1, retries + 1):
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a practical interview coach and product analyst. Be specific, honest, structured, and useful.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                timeout=120,
            )
            return response.choices[0].message.content or ""
        except Exception as error:
            if attempt == retries:
                return f"LLM error after {retries} attempts: {error}"
            time.sleep(2)


def extract_json(text):
    if not text:
        return "{}"

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
        return json.dumps(
            {
                "error": "Could not parse model output as valid JSON",
                "raw_output": text,
            },
            indent=2,
        )


def strip_html(html):
    text = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()


def fetch_url(url):
    if any(domain in url for domain in SKIP_DOMAINS):
        return ""

    if firecrawl:
        try:
            result = firecrawl.scrape_url(url, params={"formats": ["markdown"]})
            content = (result or {}).get("markdown", "")
            if content and len(content) > 200:
                return content[:5000]
        except Exception:
            pass

    try:
        response = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if response.ok and response.text:
            text = strip_html(response.text)
            if len(text) > 200:
                return text[:5000]
    except Exception:
        pass

    try:
        extract = tavily.extract(urls=[url])
        for item in (extract or {}).get("results", []):
            content = item.get("raw_content", "")
            if content and len(content) > 200:
                return content[:5000]
    except Exception:
        pass

    return ""






# >>> NAILIT RESEARCH HELPERS

RESEARCH_MAX_TOTAL_CHARS = 120000
RESEARCH_MAX_SOURCE_CHARS = 9000
RESEARCH_RESULT_LIMIT = 6

BLOCKED_FETCH_DOMAINS = (
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
)

def is_google(company_name):
    return company_name.strip().lower() in {"google", "google cloud", "alphabet"}

def source_key(url):
    return (url or "").split("#")[0].split("?")[0].rstrip("/").lower()

def company_seed_urls(company_name):
    if is_google(company_name):
        return [
            {
                "category": "official_company",
                "url": "https://www.google.com/about/careers/applications/how-we-hire/",
                "title": "Google Careers: How we hire",
            },
            {
                "category": "official_company",
                "url": "https://www.google.com/about/careers/applications/interview-tips",
                "title": "Google Careers: Interviewing at Google",
            },
            {
                "category": "official_company",
                "url": "https://about.google/company-info/philosophy/",
                "title": "About Google: Ten things we know to be true",
            },
            {
                "category": "official_company",
                "url": "https://about.google/company-info/commitments/",
                "title": "About Google: Commitments",
            },
        ]

    return []

def company_official_domains(company_name):
    if is_google(company_name):
        return ["google.com", "about.google", "careers.google.com", "blog.google"]

    clean = re.sub(r"[^a-z0-9]+", "", company_name.lower())
    if clean:
        return [f"{clean}.com"]

    return []

def build_research_queries(company_name, role_name):
    company = company_name.strip()
    role = role_name.strip()

    official_domains = company_official_domains(company)

    queries = [
        {
            "category": "official_company",
            "query": f"{company} official careers interview process how we hire interview tips values mission",
            "include_domains": official_domains,
        },
        {
            "category": "official_company",
            "query": f"{company} official company values principles culture hiring interview",
            "include_domains": official_domains,
        },
        {
            "category": "role_specific",
            "query": f"{company} {role} interview process questions experience",
            "include_domains": None,
        },
        {
            "category": "role_specific",
            "query": f"{company} {role} interview preparation rounds behavioral technical",
            "include_domains": None,
        },
        {
            "category": "public_candidate_experience",
            "query": f"{company} {role} interview questions Glassdoor",
            "include_domains": ["glassdoor.com", "glassdoor.co.uk", "glassdoor.ie"],
        },
        {
            "category": "public_candidate_experience",
            "query": f"site:reddit.com {company} {role} interview experience questions",
            "include_domains": ["reddit.com"],
        },
        {
            "category": "video_themes",
            "query": f"site:youtube.com {company} {role} interview preparation questions",
            "include_domains": ["youtube.com"],
        },
        {
            "category": "role_requirements",
            "query": f"{company} {role} responsibilities requirements competencies",
            "include_domains": None,
        },
    ]

    if is_google(company):
        queries.extend(
            [
                {
                    "category": "official_google",
                    "query": "site:google.com/about/careers/applications Google interview tips how we hire",
                    "include_domains": ["google.com"],
                },
                {
                    "category": "official_google",
                    "query": "site:about.google/company-info Google ten things we know to be true values",
                    "include_domains": ["about.google"],
                },
                {
                    "category": "google_program_manager",
                    "query": "Google Program Manager interview process behavioral questions stakeholder management",
                    "include_domains": None,
                },
                {
                    "category": "google_program_manager",
                    "query": "Google Program Manager interview experience process improvement stakeholder questions",
                    "include_domains": None,
                },
            ]
        )

    return queries

def tavily_search_once(query, include_domains=None, max_results=RESEARCH_RESULT_LIMIT):
    kwargs = {
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": True,
        "include_raw_content": True,
    }

    if include_domains:
        kwargs["include_domains"] = include_domains

    try:
        return tavily.search(query, **kwargs)
    except Exception as sdk_error:
        log(1, f"Tavily SDK search failed for query: {query}. Error: {sdk_error}", "warning")

    if not TAVILY_API_KEY:
        return {"results": []}

    try:
        payload = dict(kwargs)
        payload["query"] = query

        response = requests.post(
            "https://api.tavily.com/search",
            headers={
                "Authorization": f"Bearer {TAVILY_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=30,
        )

        if response.ok:
            return response.json()

        log(1, f"Tavily REST search failed {response.status_code}: {response.text[:300]}", "warning")
    except Exception as rest_error:
        log(1, f"Tavily REST search error: {rest_error}", "warning")

    return {"results": []}

def score_source(category, url):
    url_lower = (url or "").lower()

    score = 0

    if category.startswith("official"):
        score += 100

    if "google.com/about/careers" in url_lower or "about.google" in url_lower:
        score += 80

    if "glassdoor" in url_lower:
        score += 35

    if "reddit.com" in url_lower:
        score += 25

    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        score += 20

    return score

def collect_research_sources(company_name, role_name):
    sources = []
    seen = set()

    for seed in company_seed_urls(company_name):
        url = seed["url"]
        key = source_key(url)

        if key in seen:
            continue

        seen.add(key)
        content = fetch_url(url)

        if content:
            sources.append(
                {
                    "category": seed["category"],
                    "title": seed["title"],
                    "url": url,
                    "content": content[:RESEARCH_MAX_SOURCE_CHARS],
                    "score": score_source(seed["category"], url),
                }
            )
            log(1, f"Seed source loaded: {url}", "done")
        else:
            log(1, f"Seed source could not be read: {url}", "warning")

    for item in build_research_queries(company_name, role_name):
        query = item["query"]
        category = item["category"]
        include_domains = item.get("include_domains")

        log(1, f"Searching {category}: {query}")

        result = tavily_search_once(query, include_domains=include_domains)

        answer = result.get("answer") or ""
        if answer and len(answer) > 80:
            pseudo_url = f"tavily_answer:{category}:{query}"
            if pseudo_url not in seen:
                seen.add(pseudo_url)
                sources.append(
                    {
                        "category": category,
                        "title": f"Tavily answer for {query}",
                        "url": pseudo_url,
                        "content": answer[:2500],
                        "score": score_source(category, pseudo_url) + 10,
                    }
                )

        for res in result.get("results", []):
            url = res.get("url", "")
            key = source_key(url)

            if not url or key in seen:
                continue

            seen.add(key)

            title = res.get("title", "") or url
            content = res.get("raw_content") or res.get("content") or ""

            if len(content) < 700 and not any(domain in url for domain in BLOCKED_FETCH_DOMAINS):
                fetched = fetch_url(url)
                if fetched and len(fetched) > len(content):
                    content = fetched

            if not content or len(content) < 100:
                continue

            sources.append(
                {
                    "category": category,
                    "title": title,
                    "url": url,
                    "content": content[:RESEARCH_MAX_SOURCE_CHARS],
                    "score": score_source(category, url),
                }
            )

        time.sleep(0.25)

    sources.sort(key=lambda x: x.get("score", 0), reverse=True)

    return sources[:24]

def format_sources_for_prompt(sources):
    chunks = []
    total = 0

    for index, source in enumerate(sources, 1):
        content = source["content"].strip()
        chunk = f"""
SOURCE {index}
Category: {source["category"]}
Title: {source["title"]}
URL: {source["url"]}

{content}
""".strip()

        if total + len(chunk) > RESEARCH_MAX_TOTAL_CHARS:
            break

        chunks.append(chunk)
        total += len(chunk)

    return "\n\n" + ("=" * 80) + "\n\n".join(chunks)

def build_source_manifest(sources):
    rows = []
    for index, source in enumerate(sources, 1):
        rows.append(
            {
                "id": index,
                "category": source["category"],
                "title": source["title"],
                "url": source["url"],
            }
        )

    return json.dumps(rows, indent=2)

# <<< NAILIT RESEARCH HELPERS

def save_output(company, role):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_company = company.replace(" ", "_").replace("/", "_")

    json_filename = f"interview_prep_{safe_company}_{timestamp}.json"
    md_filename = f"interview_prep_{safe_company}_{timestamp}.md"
    product_json_filename = f"product_brief_{safe_company}_{timestamp}.json"
    lua_brief_filename = f"lua_brief_{safe_company}_{timestamp}.md"

    payload = {
        "company": company,
        "role": role,
        "generated_at": timestamp,
        "results": results,
        "progress_log": progress_log,
    }

    with open(json_filename, "w") as file:
        json.dump(payload, file, indent=2)

    with open(product_json_filename, "w") as file:
        file.write(get_result("product_brief"))

    with open(lua_brief_filename, "w") as file:
        file.write(get_result("lua_brief"))

    markdown = f"""
# Interview Prep Pack

Company: {company}

Role: {role}

Generated: {timestamp}

## Company Research Summary

{get_result("intel_report")}

## Role And CV Analysis

{get_result("role_cv_analysis")}

## Final Prep Pack

{get_result("final_prep_pack")}

## Mock Interview Script

{get_result("mock_interview")}

## Lua Mock Interview Brief

{get_result("lua_brief")}

## Product Ready JSON Brief

```json
{get_result("product_brief")}
```
"""

    with open(md_filename, "w") as file:
        file.write(markdown)

    print(f"\nSaved full JSON: {json_filename}")
    print(f"Saved markdown prep pack: {md_filename}")
    print(f"Saved product JSON brief: {product_json_filename}")
    print(f"Saved Lua brief: {lua_brief_filename}")

    return md_filename




def research_company(company_name, role_name):
    log(1, "Starting deep company and interview research")

    sandbox = make_sandbox("research")

    try:
        sources = collect_research_sources(company_name, role_name)
        set_result("source_manifest", build_source_manifest(sources))

        log(1, f"Collected {len(sources)} usable research sources")

        if not sources:
            message = """
RESEARCH STATUS: FAILED

No usable online sources were collected. This is a system failure or search provider failure, not proof that sources do not exist.

Do not treat this as company intelligence.
Do not produce generic company claims.
Use only the job description, CV, and answer bank until research is fixed.
""".strip()
            set_result("intel_report", message)
            log(1, "Research failed because zero usable sources were collected", "error")
            return

        source_text = format_sources_for_prompt(sources)

        prompt = f"""
You are Nailit's company intelligence researcher.

Your job is to prepare serious interview intelligence for a candidate interviewing at:

Company: {company_name}
Role: {role_name}

You must use the numbered sources below. Do not invent facts. If a point is only inferred from public candidate reports, label it as directional, not official.

Important source rules:
1. Official company pages are highest confidence.
2. Glassdoor, Reddit, YouTube, blogs, and forums are directional candidate experience themes.
3. If a source is a search answer or snippet, say it is a snippet based source.
4. Every concrete company or interview claim must include source numbers in brackets, like [S1] or [S2, S5].
5. If role specific interview data is thin, say that clearly and explain what is inferred from adjacent Program Manager interviews.

Return the report in this exact structure:

### Research status
Say how many sources were used and whether official company sources were found.

### Sources used
List every useful source as:
S1. Title, category, URL, one sentence on why it matters.

### Official company signal map
Extract company values, principles, hiring philosophy, culture signals, and language the candidate should mirror.

### Hiring and interview process intelligence
Explain what the candidate should expect. Separate official information from public candidate experience.

### Role specific interview intelligence
Explain what is likely tested for this exact role. Include technical, operational, leadership, stakeholder, ambiguity, data, and process signals.

### Public candidate experience themes
Summarize recurring themes from Reddit, Glassdoor, YouTube, blogs, and interview prep pages. Mark them as directional.

### What the candidate must prove
Give 8 to 12 concrete things the candidate must prove in the interview.

### Likely interview questions
Give 15 likely questions. For each:
Question
Signal being tested
Source basis as OFFICIAL, PUBLIC EXPERIENCE, JOB DESCRIPTION INFERENCE, or ROLE INFERENCE
What a strong answer must prove

### Red flags to avoid
Give specific answer patterns that would weaken the candidate.

### Company specific answer strategy
Explain how to sound like a strong fit for this company and role without sounding generic.

### Confidence notes
Say what is well supported, what is directional, and what still needs manual checking.

Numbered sources:
{source_text}
"""

        intel = ask_llm(prompt, retries=3)
        set_result("intel_report", intel)
        log(1, "Deep research summary complete", "done")

    finally:
        cleanup_sandbox(sandbox)


def analyse_role_and_cv(company_name, role_name, job_description, full_profile):
    log(2, "Analysing role, CV, and answer bank")

    sandbox = make_sandbox("role and CV analysis")

    try:
        prompt = f"""
You are Nailit's candidate evidence analyst.

Company:
{company_name}

Role:
{role_name}

Company intelligence:
{get_result("intel_report")}

Job description:
{job_description}

Candidate CV plus answer bank:
{full_profile}

Your job is to map the role to exact candidate evidence. Do not be generic. Do not invent experience.

Return this exact structure:

### Role decoded
Explain what this job is really asking for in practical language.

### Role signal map
Create a table with:
Signal required
Where it appears in the job description
Why it matters
How the candidate can prove it

### Candidate evidence inventory
Extract at least 12 concrete evidence points from the CV and answer bank.
For each:
Evidence
Source area as CV or ANSWER BANK
Competency proven
Best interview use

### Strongest match areas
Give the strongest 8 matches between the candidate and the role. Each must include evidence.

### Risk areas
Give the biggest gaps or risks.
For each:
Risk
Why interviewers may care
Honest positioning
Story or evidence to reduce concern

### Best stories to prepare
Build a story bank with at least 10 stories from the candidate material.
For each:
Story name
Best question types
Competencies proven
Evidence to include
Metrics to include
Weakness to avoid

### Google or company alignment
Map candidate evidence to company signals from the research.

### Mock interview pressure points
List what the mock interviewer should test hardest.
"""

        analysis = ask_llm(prompt, retries=3)
        set_result("role_cv_analysis", analysis)
        log(2, "Role, CV, and answer bank analysis complete", "done")

    finally:
        cleanup_sandbox(sandbox)


def create_final_prep_pack(company_name, role_name, job_description, full_profile):
    log(3, "Creating final interview prep pack")

    sandbox = make_sandbox("final prep pack")

    try:
        prompt = f"""
You are Nailit's senior interview strategist.

Create a premium, detailed, evidence based interview prep pack.

Company:
{company_name}

Role:
{role_name}

Job description:
{job_description}

Candidate CV plus answer bank:
{full_profile}

Company intelligence:
{get_result("intel_report")}

Role and candidate analysis:
{get_result("role_cv_analysis")}

Rules:
1. Do not write generic advice.
2. Use exact evidence from the candidate material.
3. Use company research where available.
4. If research failed, say research failed instead of pretending sources do not exist.
5. Distinguish official company signals from public candidate experience themes.
6. Make the output detailed enough to actually prepare tonight.
7. Do not dump JSON in this section.
8. Do not invent candidate achievements or company facts.

Return this exact structure:

### Executive strategy
A sharp positioning strategy for this exact candidate and role.

### The interview is really testing
Explain the hidden evaluation criteria behind this role.

### Company signal translation
Translate company values, hiring language, and public interview themes into practical answer strategy.

### Candidate positioning statement
Write a strong 45 second positioning statement.

### Why this company answer
Write a strong answer that uses company specific signals and does not sound generic.

### Top strengths to lead with
Give 8 strengths. Each must include:
Candidate evidence
Why it matters for this role
How to say it in interview language

### Top risks and repair strategy
Give 8 risks. Each must include:
The risk
What the interviewer may worry about
Best honest answer strategy
Evidence to use

### Story bank
Give at least 10 stories from the CV or answer bank.
Each story must include:
Story title
Best question match
STAR outline
Metrics
Company or role signal it proves
How to tighten the answer

### Likely question bank
Give at least 20 likely interview questions.
For each:
Question
Why they ask
Best story to use
Must include
Avoid saying

### Technical or domain gap plan
Explain how to handle gaps such as networking, infrastructure, data centers, cloud, or technical depth if relevant.

### First 30, 60, and 90 day answer
Create a role specific answer, not a generic plan.

### Questions to ask the interviewer
Give 12 smart questions tailored to the company, team, role, and candidate risks.

### Seven day prep plan
Give a serious day by day plan. Each day must include outputs the candidate should create.

### Final interview checklist
Give a concise checklist for the day before and morning of the interview.
"""

        prep_pack = ask_llm(prompt, retries=3)
        set_result("final_prep_pack", prep_pack)
        log(3, "Final prep pack complete", "done")

    finally:
        cleanup_sandbox(sandbox)

def create_mock_interview(company_name, role_name):
    log(4, "Creating mock interview script")

    sandbox = make_sandbox("mock interview")

    try:
        prompt = f"""
You are an interviewer preparing a realistic mock interview.

Company:
{company_name}

Role:
{role_name}

Company research:
{get_result("intel_report")}

Prep pack:
{get_result("final_prep_pack")}

Create a mock interview script.

Return this structure:

1. Opening
Write what the interviewer says at the start.

2. Mock interview questions
Give 10 questions.
Ask one question at a time.
Make them realistic for the role.

3. Scoring guide
For each answer, score:
Specificity
Structure
Role relevance
Evidence
Confidence

4. Feedback format
Give a simple template for feedback after each answer:
Score out of 10
What worked
What was weak
Stronger version
Next improvement

5. Closing
Write how the interviewer ends the mock interview.
"""

        mock_interview = ask_llm(prompt)
        set_result("mock_interview", mock_interview)
        log(4, "Mock interview script complete", "done")

    finally:
        cleanup_sandbox(sandbox)




def create_product_brief(company_name, role_name):
    log(5, "Creating product ready JSON brief")

    sandbox = make_sandbox("product brief")

    try:
        prompt = f"""
You are creating structured data for Nailit, an interview preparation product.

Use the research and analysis below to create a product ready JSON object.

Company:
{company_name}

Role:
{role_name}

Company intelligence:
{get_result("intel_report")}

Source manifest:
{get_result("source_manifest")}

Role and CV analysis:
{get_result("role_cv_analysis")}

Final prep pack:
{get_result("final_prep_pack")}

Mock interview:
{get_result("mock_interview")}

Return ONLY valid JSON.
Do not wrap it in markdown.
Do not include commentary.

Use this schema exactly:

{{
  "company": "{company_name}",
  "role": "{role_name}",
  "research_status": {{
    "sources_used": [],
    "official_sources_found": true,
    "confidence": "",
    "limitations": []
  }},
  "company_signal_map": [
    {{
      "signal": "",
      "source_basis": "",
      "how_to_show_it": ""
    }}
  ],
  "candidate_positioning": {{
    "summary": "",
    "strengths": [],
    "risks": [],
    "how_to_position": ""
  }},
  "interview_intelligence": {{
    "likely_rounds": [],
    "competencies_tested": [],
    "red_flags": [],
    "confidence_notes": []
  }},
  "question_bank": [
    {{
      "question": "",
      "type": "behavioral",
      "why_it_matters": "",
      "best_story_to_use": "",
      "strong_answer_must_include": [],
      "follow_up_questions": []
    }}
  ],
  "story_bank": [
    {{
      "story_name": "",
      "competency": "",
      "source_area": "CV or ANSWER_BANK",
      "what_to_prepare": "",
      "metrics_to_include": [],
      "risks_to_avoid": []
    }}
  ],
  "mock_interview_plan": {{
    "opening": "",
    "question_order": [],
    "scoring_rubric": [
      "specificity",
      "structure",
      "role relevance",
      "evidence",
      "company alignment",
      "confidence"
    ],
    "feedback_template": {{
      "score": "",
      "what_worked": "",
      "what_was_weak": "",
      "stronger_version": "",
      "next_improvement": ""
    }}
  }},
  "seven_day_plan": []
}}
"""

        product_brief_raw = ask_llm(prompt, retries=3)
        product_brief = extract_json(product_brief_raw)
        set_result("product_brief", product_brief)
        log(5, "Product ready JSON brief complete", "done")

    finally:
        cleanup_sandbox(sandbox)

def create_lua_brief(company_name, role_name):
    log(6, "Creating Lua mock interview doctrine brief")

    lua_brief = build_lua_mock_interview_brief(
        company_name,
        role_name,
        get_result("intel_report"),
        get_result("role_cv_analysis"),
        get_result("role_cv_analysis"),
        get_result("final_prep_pack"),
        get_result("final_prep_pack"),
        get_result("product_brief"),
    )

    set_result("lua_brief", lua_brief)
    log(6, "Lua mock interview doctrine brief complete", "done")
    return lua_brief


def extract_external_research(extra):
    marker_start = "[NAILIT_EXTERNAL_RESEARCH]"
    marker_end = "[/NAILIT_EXTERNAL_RESEARCH]"

    if marker_start not in extra:
        return ""

    start = extra.find(marker_start)
    end = extra.find(marker_end, start)

    if end == -1:
        return extra[start:].strip()

    return extra[start:end + len(marker_end)].strip()


def create_intel_from_external_research(company_name, role_name, external_research):
    log(1, "Creating company intelligence from Vercel research")

    prompt = f"""
You are Nailit's company intelligence researcher.

Company:
{company_name}

Role:
{role_name}

External research:
{external_research}

Create a serious company and interview intelligence report.

Rules:
1. Use the external research.
2. Separate official sources from directional public candidate experience.
3. Do not claim Reddit, Glassdoor, YouTube, or blogs are official.
4. Include source titles and URLs when available.
5. Do not be generic.
6. If the research is thin, say exactly what is thin.

Return this exact structure:

### Research status
Say that research was supplied by the Vercel research bridge and summarize source quality.

### Sources used
List useful source titles and URLs.

### Official company signal map
Extract official values, hiring philosophy, culture, and language to mirror.

### Hiring and interview process intelligence
Explain expected interview process. Separate official from public candidate themes.

### Role specific interview intelligence
Explain what is likely tested for this role.

### Public candidate experience themes
Summarize Reddit, Glassdoor, YouTube, blogs, and interview prep themes as directional.

### What the candidate must prove
Give 8 to 12 concrete proof points.

### Likely interview questions
Give 15 likely questions. For each include:
Question
Signal being tested
Source basis
What a strong answer must prove

### Red flags to avoid
Specific mistakes to avoid.

### Company specific answer strategy
How to sound tailored to this company and role.

### Confidence notes
What is well supported, directional, or needs manual checking.
"""

    intel = ask_llm(prompt, retries=3)
    set_result("intel_report", intel)
    set_result("source_manifest", external_research[:10000])
    log(1, "External research intelligence complete", "done")


def run_pipeline(job_description, cv, extra, company_name, role_name):
    results.clear()
    progress_log.clear()

    full_profile = cv
    if extra.strip():
        full_profile += f"\n\nAdditional context:\n{extra}"

    external_research = extract_external_research(extra)

    if external_research:
        create_intel_from_external_research(company_name, role_name, external_research)
    else:
        research_company(company_name, role_name)

    analyse_role_and_cv(company_name, role_name, job_description, full_profile)
    create_final_prep_pack(company_name, role_name, job_description, full_profile)
    create_mock_interview(company_name, role_name)
    create_product_brief(company_name, role_name)
    create_lua_brief(company_name, role_name)

    return save_output(company_name, role_name)


if __name__ == "__main__":
    print("\nInterview Intel Agent\n")

    try:
        with open("job_description.txt", "r") as file:
            job_description = file.read()

        with open("cv.txt", "r") as file:
            cv = file.read()

        with open("extra_context.txt", "r") as file:
            extra = file.read()

    except FileNotFoundError as error:
        print(f"Missing file: {error}")
        print("Make sure job_description.txt, cv.txt, and extra_context.txt are in this folder.")
        exit(1)

    company_name = input("Company name: ").strip()
    role_name = input("Role title: ").strip()

    output_file = run_pipeline(
        job_description=job_description,
        cv=cv,
        extra=extra,
        company_name=company_name,
        role_name=role_name,
    )

    print("\n" + "=" * 60)
    print("INTERVIEW INTEL AGENT RESULT")
    print("=" * 60)

    sections = [
        ("intel_report", "COMPANY RESEARCH SUMMARY"),
        ("role_cv_analysis", "ROLE AND CV ANALYSIS"),
        ("final_prep_pack", "FINAL INTERVIEW PREP PACK"),
        ("mock_interview", "MOCK INTERVIEW SCRIPT"),
        ("product_brief", "PRODUCT READY JSON BRIEF"),
        ("lua_brief", "LUA MOCK INTERVIEW BRIEF"),
    ]

    for key, title in sections:
        print(f"\n{title}")
        print("=" * len(title))
        print(get_result(key) or "No output generated.")

    print("\n" + "=" * 60)
    print(f"Done. Best file to open: {output_file}")
    print("=" * 60)
