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
    if not daytona:
        log(0, f"Daytona not configured. Running {stage_name} without sandbox.", "warning")
        return None

    try:
        sandbox = daytona.create()
        log(0, f"Daytona sandbox created for {stage_name}", "done")
        return sandbox
    except Exception as error:
        log(0, f"Could not create Daytona sandbox for {stage_name}: {error}", "warning")
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
    log(1, "Starting focused online research")

    sandbox = make_sandbox("research")

    queries = [
        f"{company_name} {role_name} interview process",
        f"{company_name} {role_name} interview questions",
        f"{company_name} {role_name} interview experience",
        f"{company_name} careers values interview",
        f"{company_name} {role_name} job requirements",
    ]

    all_urls = []
    snippets = []

    try:
        for query in queries:
            log(1, f"Searching: {query}")
            try:
                search_result = tavily.search(query, max_results=2)

                for item in search_result.get("results", []):
                    url = item.get("url", "")
                    content = item.get("content", "")

                    if url and url not in all_urls:
                        all_urls.append(url)

                    if content and len(content) > 80:
                        snippets.append(f"Source snippet from {url}\n{content}")

            except Exception as error:
                log(1, f"Search error: {error}", "error")

            time.sleep(0.2)

        log(1, f"Found {len(all_urls)} URLs and {len(snippets)} snippets")

        full_pages = []

        for index, url in enumerate(all_urls[:8]):
            log(1, f"Fetching source {index + 1} of {min(len(all_urls), 8)}")
            content = fetch_url(url)

            if content:
                full_pages.append(f"Source {index + 1}: {url}\n{content}")
                log(1, f"Fetched {len(content)} characters")
            else:
                log(1, "No readable content found")

        source_text = "\n\n".join(full_pages + snippets)[:35000]

        if not source_text.strip():
            set_result("intel_report", "No useful online sources found. Use the job description and CV only.")
            return

        prompt = f"""
You are an interview research assistant.

Prepare a practical research summary for someone interviewing at {company_name} for the role of {role_name}.

Use only the source content below.
If something is not found, write "not found in sources".
Do not exaggerate.
Do not give generic advice.
Keep the output useful and concise.

Return this structure:

1. Company interview summary
Give 5 useful bullets about what the candidate should expect.

2. Likely interview rounds
List likely rounds. If exact structure is not found, say so.

3. What interviewers may test
List skills, behaviours, values, and role signals.

4. Likely questions
Give 8 likely questions.
Mark each question as HIGH SIGNAL or INFERRED.

5. Red flags to avoid
List weak answers or mistakes to avoid.

6. Strong answer strategy
Explain how to answer well for this company and role.

7. Source confidence
Explain what seems well supported and what is only inferred.

Source content:
{source_text}
"""

        intel = ask_llm(prompt)
        set_result("intel_report", intel)
        log(1, "Research summary complete", "done")

    finally:
        cleanup_sandbox(sandbox)


def analyse_role_and_cv(company_name, role_name, job_description, full_profile):
    log(2, "Analysing job description and CV")

    sandbox = make_sandbox("role and CV analysis")

    try:
        prompt = f"""
You are an interview coach helping a job seeker prepare for a specific role.

Company:
{company_name}

Role:
{role_name}

Company research:
{get_result("intel_report")}

Job description:
{job_description}

Candidate CV and context:
{full_profile}

Create a practical analysis.

Return this structure:

1. Role summary
Explain what this job seems to require in plain English.

2. Top competencies
List the 6 most important skills or behaviours the candidate must show.

3. Candidate strengths
List the strongest matches between the CV and the role.

4. Candidate gaps
List the biggest risks or missing evidence.
For each gap, explain how the candidate can handle it honestly.

5. Best stories to prepare
Suggest 5 interview stories the candidate should prepare from their real experience.
Do not invent details.

6. Positioning strategy
Write a short strategy for how the candidate should present themselves.

7. What the mock interview should test
List the areas that should be tested hardest.
"""

        analysis = ask_llm(prompt)
        set_result("role_cv_analysis", analysis)
        log(2, "Role and CV analysis complete", "done")

    finally:
        cleanup_sandbox(sandbox)


def create_final_prep_pack(company_name, role_name, job_description, full_profile):
    log(3, "Creating final interview prep pack")

    sandbox = make_sandbox("final prep pack")

    try:
        prompt = f"""
You are a practical interview coach.

Create a final interview prep pack for this candidate.

Company:
{company_name}

Role:
{role_name}

Job description:
{job_description}

Candidate CV and context:
{full_profile}

Company research:
{get_result("intel_report")}

Role and CV analysis:
{get_result("role_cv_analysis")}

The output must be clear, useful, and not too long.

Return this structure:

1. Interview strategy
A short paragraph explaining how the candidate should position themselves.

2. Top 5 things to highlight
Each point should connect the candidate to the role.

3. Top 5 risks to prepare for
Each point should include how to answer if asked.

4. Top 10 likely interview questions
For each question include:
Why they may ask it
What a strong answer must include

5. Story bank
Give 5 story prompts the candidate should prepare using real experience.

6. Questions to ask the interviewer
Give 8 smart questions.

7. Seven day prep plan
Give a practical day by day plan.

Rules:
Do not invent candidate experience.
Do not invent company facts.
If evidence is weak, say so.
Use plain English.
Make it feel like something a real job seeker can use tonight.
"""

        prep_pack = ask_llm(prompt)
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
You are creating structured data for an interview preparation product.

Use the research and analysis below to create a product ready JSON object.

Company:
{company_name}

Role:
{role_name}

Company research:
{get_result("intel_report")}

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
      "strong_answer_must_include": [],
      "follow_up_questions": []
    }}
  ],
  "story_bank": [
    {{
      "story_name": "",
      "competency": "",
      "what_to_prepare": "",
      "metrics_to_include": []
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

        product_brief_raw = ask_llm(prompt)
        product_brief = extract_json(product_brief_raw)
        set_result("product_brief", product_brief)
        log(5, "Product ready JSON brief complete", "done")

    finally:
        cleanup_sandbox(sandbox)


def create_lua_brief(company_name, role_name):
    log(6, "Creating Lua mock interview brief")

    sandbox = make_sandbox("Lua brief")

    try:
        prompt = f"""
You are preparing a compact briefing for a live Lua mock interview agent.

The live agent will use this brief to interview the candidate one question at a time.

Company:
{company_name}

Role:
{role_name}

Product JSON brief:
{get_result("product_brief")}

Create a compact brief with this structure:

1. Target role
One sentence.

2. Candidate positioning
Three bullets.

3. Main strengths to test
Five bullets.

4. Main risks to test
Five bullets.

5. Interview questions
Ten questions in the exact order the mock interviewer should ask them.

6. Scoring rules
Explain what makes a strong answer for this role.

7. Feedback rules
Tell the mock interviewer to score each answer out of 10, explain what worked, explain what was weak, give a stronger version, identify the weakest skill shown, and choose the next question based on that weakness.

8. Instruction for Lua agent
Write a direct instruction the user can paste into Lua chat to start the mock interview.

Keep this brief clear and compact.
Do not include long explanations.
Do not invent candidate experience.
"""

        lua_brief = ask_llm(prompt)
        set_result("lua_brief", lua_brief)
        log(6, "Lua mock interview brief complete", "done")

    finally:
        cleanup_sandbox(sandbox)


def run_pipeline(job_description, cv, extra, company_name, role_name):
    results.clear()
    progress_log.clear()

    full_profile = cv
    if extra.strip():
        full_profile += f"\n\nAdditional context:\n{extra}"

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
