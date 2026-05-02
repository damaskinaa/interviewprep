import os
import re
import json
import time
import requests
import threading
from datetime import datetime
from dotenv import load_dotenv
from daytona import Daytona, DaytonaConfig
from tavily import TavilyClient
from openai import OpenAI

load_dotenv()

daytona      = Daytona(DaytonaConfig(api_key=os.getenv("DAYTONA_API_KEY")))
tavily       = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Firecrawl is optional — we fall back gracefully if missing/broken
try:
    from firecrawl import FirecrawlApp
    firecrawl = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY")) if os.getenv("FIRECRAWL_API_KEY") else None
except ImportError:
    firecrawl = None

# ── Thread-safe results store ──────────────────────────────────────────────────
results: dict = {}
results_lock  = threading.Lock()

def set_result(key: str, value: str):
    with results_lock:
        results[key] = value

def get_result(key: str) -> str:
    with results_lock:
        return results.get(key, "")

# ── Progress logger ────────────────────────────────────────────────────────────
progress_log: list[dict] = []
progress_lock = threading.Lock()

def log(stage: int, message: str, status: str = "running"):
    event = {"ts": datetime.utcnow().isoformat(), "stage": stage,
             "message": message, "status": status}
    with progress_lock:
        progress_log.append(event)
    print(f"  [Stage {stage}] {message}")

# ── LLM helper ────────────────────────────────────────────────────────────────
def ask_llm(prompt: str, model: str = "gpt-4o", retries: int = 3) -> str:
    for attempt in range(1, retries + 1):
        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                timeout=120,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt == retries:
                return f"[LLM ERROR after {retries} attempts: {e}]"
            time.sleep(2 ** attempt)

# ── URL fetching — THREE-LAYER FALLBACK ───────────────────────────────────────
#
#   Layer 1: Firecrawl  (best quality, handles JS — but often fails silently)
#   Layer 2: requests + HTML strip  (fast, works on most static pages)
#   Layer 3: Tavily extract  (last resort — works on almost anything)
#
SKIP_DOMAINS = ("youtube.com", "youtu.be")  # video pages → no readable text

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

def _strip_html(html: str) -> str:
    text = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&[a-z]+;", "", text)
    text = re.sub(r"\s{3,}", "\n\n", text)
    return text.strip()

def fetch_url(url: str, tavily_client=None) -> str:
    """Return up to 8 000 chars of readable text, or '' on total failure."""
    if any(d in url for d in SKIP_DOMAINS):
        return ""

    # Layer 1: Firecrawl
    if firecrawl:
        try:
            result  = firecrawl.scrape_url(url, params={"formats": ["markdown"]})
            content = (result or {}).get("markdown", "")
            if content and len(content) > 200:
                return content[:8000]
        except Exception:
            pass

    # Layer 2: direct HTTP
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=12, allow_redirects=True)
        if resp.ok and resp.text:
            text = _strip_html(resp.text)
            if len(text) > 200:
                return text[:8000]
    except Exception:
        pass

    # Layer 3: Tavily extract
    if tavily_client:
        try:
            extract = tavily_client.extract(urls=[url])
            for item in (extract or {}).get("results", []):
                content = item.get("raw_content", "")
                if content and len(content) > 200:
                    return content[:8000]
        except Exception:
            pass

    return ""

# ── Output saver ──────────────────────────────────────────────────────────────
def save_output(company: str, role: str) -> str:
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"interview_prep_{company.replace(' ', '_')}_{ts}.json"
    with open(filename, "w") as f:
        json.dump({"company": company, "role": role, "generated_at": ts,
                   "results": results, "progress_log": progress_log}, f, indent=2)
    print(f"\n  Results saved → {filename}")
    return filename

# ==============================================================================
# MAIN PIPELINE
# ==============================================================================

def run_pipeline(job_description: str, cv: str, extra: str,
                 company_name: str, role_name: str) -> str:

    full_profile = cv + (f"\n\nAdditional context:\n{extra}" if extra.strip() else "")

    # ── STAGE 1: Deep Research ─────────────────────────────────────────────────
    log(1, "Starting deep research — reading up to 30 sources")

    sandbox_research = daytona.create()
    try:
        queries = [
            f"{company_name} {role_name} interview process 2024 2025",
            f"{company_name} {role_name} interview experience Reddit",
            f"{company_name} interview questions {role_name} behavioral",
            f"{company_name} bar raiser interview tips what they look for",
            f"{company_name} interview rejected reason why failed",
            f"{company_name} interview hired offer what worked",
            f"{company_name} leadership principles interview examples",
            f"{company_name} {role_name} interview Glassdoor",
            f"how to pass {company_name} interview insider tips",
            f"{company_name} interview loop structure rounds explained",
        ]

        all_urls: list[str]       = []
        tavily_snippets: list[str] = []  # real text Tavily always returns for free

        log(1, "Searching across 10 query types...")
        for q in queries:
            try:
                r = tavily.search(q, max_results=4)
                for item in r.get("results", []):
                    url     = item.get("url", "")
                    snippet = item.get("content", "")   # Tavily always populates this
                    if url and url not in all_urls:
                        all_urls.append(url)
                    if snippet and len(snippet) > 100:
                        tavily_snippets.append(f"SOURCE (snippet) [{url}]:\n{snippet}")
            except Exception as e:
                log(1, f"Search error: {e}", "error")
            time.sleep(0.3)

        log(1, f"Found {len(all_urls)} unique URLs + {len(tavily_snippets)} Tavily snippets")

        # Fetch full content with three-layer fallback
        raw_intel: list[str] = []
        for i, url in enumerate(all_urls[:30]):
            log(1, f"Fetching {i+1}/{min(len(all_urls), 30)}: {url[:70]}")
            content = fetch_url(url, tavily_client=tavily)
            if content:
                raw_intel.append(f"\n\nSOURCE {i+1} (full text): {url}\n{content}")
                log(1, f"  ✓ {len(content)} chars")
            else:
                log(1, f"  ✗ no content")

        log(1, f"Full pages: {len(raw_intel)} | Snippets: {len(tavily_snippets)}")

        # Combine full pages + snippets — always non-empty if Tavily works
        combined = raw_intel + tavily_snippets
        if not combined:
            log(1, "CRITICAL: zero sources — check API keys", "error")
            set_result("intel_report", "")
            return save_output(company_name, role_name)

        full_raw = "\n".join(combined)[:70000]
        log(1, f"Sending {len(full_raw):,} chars to LLM for synthesis...")

        synthesis_prompt = f"""
You are a researcher building the definitive insider guide to getting hired at {company_name}
as a {role_name}. You have {len(raw_intel)} full articles + {len(tavily_snippets)} real search
result excerpts below — all sourced from real candidates, Glassdoor, Reddit, and insider blogs.

RULES:
- Every claim must be grounded in the source content below.
- Quote directly wherever possible and cite [SOURCE N] or the URL.
- If something appears in 2+ sources, flag it HIGH SIGNAL.
- If you cannot find something in the sources, say "not found in sources" — do NOT invent.

Extract and synthesise:

1. EXACT INTERVIEW STRUCTURE
- How many rounds total? (cite source)
- What happens in each round — exact format, duration, who's present?
- Bar raiser: what is it, which round, what do they test?
- Virtual vs in-person? 2024/2025 changes?

2. REAL QUESTIONS ACTUALLY ASKED (verbatim — quote them with source)
- Every specific question mentioned
- Round it appeared in
- HIGH SIGNAL if in 2+ sources

3. WHAT GETS PEOPLE REJECTED (from real failed candidates — quote them)
- Exact rejection reasons from sources
- Behaviours that failed
- What bar raisers specifically killed candidates on

4. WHAT GETS PEOPLE HIRED (from real successful candidates — quote them)
- What strong-hire candidates did differently
- Specific phrasings or approaches that worked
- What impressed interviewers most

5. COMPANY-SPECIFIC INTERVIEW CULTURE
- Unwritten rules from insiders
- How it differs from other FAANG interviews
- Key signals interviewers care about most

6. RECENT CHANGES 2024-2025
- Any format, difficulty, or process changes

RAW SOURCE CONTENT:
{full_raw}
"""
        intel = ask_llm(synthesis_prompt)
        set_result("intel_report", intel)
        log(1, f"Intelligence report: {len(intel):,} chars", "done")

    except Exception as e:
        log(1, f"Stage 1 error: {e}", "error")
        set_result("intel_report", "")
    finally:
        sandbox_research.delete()

    if not get_result("intel_report"):
        log(1, "No intel — aborting pipeline", "error")
        return save_output(company_name, role_name)

    # ── STAGE 2: Three Parallel Sandboxes ─────────────────────────────────────
    log(2, "Launching three parallel analysis sandboxes")

    def sandbox_jd_decoder():
        sandbox = daytona.create()
        try:
            log(2, "Decoding JD with real company intel...")
            prompt = f"""
You are a senior {company_name} bar raiser.
Every claim you make must reference the REAL INTEL below. No generic advice.

REAL COMPANY INTELLIGENCE (from actual candidate experiences):
{get_result('intel_report')}

JOB DESCRIPTION:
{job_description}

1. SIGNAL EXTRACTION TABLE
"JD phrase" → What real interviewers test → Evidence from intel (quote it)

2. COMPETENCY SCORECARD
Top 5 competencies. For each:
- JD evidence
- Real intel evidence (quote + cite source)
- Failure pattern (from real rejections — quote it)
- Exact real interview question that tests it

3. BAR RAISER ELIMINATORS — real rejection patterns only, quoted from intel

4. INTERVIEW ROUND BREAKDOWN — use actual structure from intel

5. TOP 1% SEPARATOR — what real STRONG HIRE candidates did (from intel only)
"""
            set_result("competencies", ask_llm(prompt))
            log(2, "JD decoder done", "done")
        except Exception as e:
            log(2, f"JD decoder error: {e}", "error")
            set_result("competencies", "")
        finally:
            sandbox.delete()

    def sandbox_cv_gap():
        sandbox = daytona.create()
        try:
            log(2, "Gap analysis using real rejection patterns...")
            prompt = f"""
You are a FAANG hiring panel doing a brutal resume screen.
Base every gap and advantage on the REAL INTEL — not generic advice.

REAL REJECTION AND HIRE PATTERNS:
{get_result('intel_report')}

CANDIDATE PROFILE:
{full_profile}

JOB DESCRIPTION:
{job_description}

1. COMPETENCY SCORECARD (0-10)
"Real hired candidates had [X from intel]. This candidate shows [Y]. Gap: [Z]"

2. FAILURE MODE ANALYSIS
Which real rejection patterns does this candidate risk? + exact follow-up that exposes it.

3. DEALBREAKER GAPS — bar raiser flags, grounded in intel

4. HIDDEN COMPETITIVE ADVANTAGES — maps to what real successful candidates showed

5. REFRAMING PLAYBOOK
"Don't say [X] → Say [Y] → Because {company_name} interviewers care about [Z from intel]"

6. STORY BANK MAPPING
Map candidate's experiences to REAL questions from intel.
Flag every intel question that has NO story to cover it.
"""
            set_result("gaps", ask_llm(prompt))
            log(2, "Gap analysis done", "done")
        except Exception as e:
            log(2, f"Gap analysis error: {e}", "error")
            set_result("gaps", "")
        finally:
            sandbox.delete()

    def sandbox_questions():
        sandbox = daytona.create()
        try:
            log(2, "Building question bank from real interviews...")
            prompt = f"""
Build a question bank for {company_name} {role_name} interviews.
PRIMARY SOURCE: real questions verbatim from the intel. Only add WILDCARD where gaps exist.

REAL INTERVIEW INTEL:
{get_result('intel_report')}

JOB DESCRIPTION:
{job_description}

12-15 questions total:

1. HIGH SIGNAL (2+ sources — quote the source)
QUESTION: [exact wording]
FREQUENCY: [N sources]
ROUND: [which round per intel]
SIGNAL: [what's tested]
WEAK ANSWER: [from failed candidates in intel]
STRONG ANSWER MUST CONTAIN: [from hired candidates in intel]
BAR RAISER FOLLOW-UP: [follow-up that breaks weak candidates]

2. MEDIUM SIGNAL (appeared once) — same format

3. WILDCARD (JD inference — clearly labelled) — same format
"""
            set_result("questions", ask_llm(prompt))
            log(2, "Question bank done", "done")
        except Exception as e:
            log(2, f"Question bank error: {e}", "error")
            set_result("questions", "")
        finally:
            sandbox.delete()

    threads = [
        threading.Thread(target=sandbox_jd_decoder, name="jd_decoder"),
        threading.Thread(target=sandbox_cv_gap,     name="cv_gap"),
        threading.Thread(target=sandbox_questions,  name="questions"),
    ]
    for t in threads: t.start()
    for t in threads: t.join()
    log(2, "All parallel sandboxes complete", "done")

    # ── STAGE 3: Answer Generation ─────────────────────────────────────────────
    log(3, "Generating answers grounded in real intel...")
    sandbox_5 = daytona.create()
    try:
        prompt = f"""
World-class interview coach for {company_name}.
Write STAR answers for EACH question. Ground in REAL intel, not generic advice.

Rules:
- ONLY real experiences from candidate profile — never invent
- Ground in what REAL {company_name} interviewers reward (use intel)
- Show: tradeoff made, failure mode avoided, cross-team impact
- If no direct experience → say so + best reframe from transferable experience
- End each answer:
  LP SIGNAL: [specific principle]
  TRADEOFF SHOWN: [chose X over Y because Z]
  REAL INTEL NOTE: [how this maps to what worked for real candidates]
- 150-200 words. Executive tone.

CANDIDATE PROFILE:
{full_profile}

QUESTIONS:
{get_result('questions')}

GAP ANALYSIS:
{get_result('gaps')}

REAL INTEL:
{get_result('intel_report')[:12000]}
"""
        set_result("answers_v1", ask_llm(prompt))
        log(3, "Generation 1 answers complete", "done")
    except Exception as e:
        log(3, f"Stage 3 error: {e}", "error")
        set_result("answers_v1", "")
    finally:
        sandbox_5.delete()

    # ── STAGES 4 & 5 (5 waits on 4's scores) ──────────────────────────────────
    log(4, "Bar raiser scoring Gen 1 + Evolution queued")
    scores_ready = threading.Event()

    def run_stage4():
        sandbox = daytona.create()
        try:
            prompt = f"""
{company_name} bar raiser scoring Gen 1 answers.
Calibrate against REAL {company_name} standards from the intel below.

For each answer:
VERDICT: STRONG HIRE / HIRE / NO HIRE
SPECIFICITY: X/10
SYSTEMS THINKING: X/10
TRADEOFF DEPTH: X/10
FAILURE AWARENESS: X/10
REAL INTEL ALIGNMENT: X/10
BAR RAISER NOTE: [debrief comment]
EXACT FIX: [one specific change for STRONG HIRE]

REAL STANDARDS:
{get_result('intel_report')[:6000]}

ANSWERS:
{get_result('answers_v1')}
"""
            set_result("scores_v1", ask_llm(prompt))
            log(4, "Gen 1 scoring complete", "done")
        except Exception as e:
            log(4, f"Stage 4 error: {e}", "error")
            set_result("scores_v1", "")
        finally:
            sandbox.delete()
            scores_ready.set()

    def run_stage5():
        scores_ready.wait()
        sandbox = daytona.create()
        try:
            log(5, "Evolving to Generation 2...")
            prompt = f"""
Evolution loop — produce Gen 2 answers strictly better than Gen 1.

RULES:
- NO HIRE → completely rewrite
- HIRE → sharpen the flagged dimension
- STRONG HIRE → keep unchanged
- Implement every EXACT FIX
- Reference real {company_name} intel in every evolved answer
- Never invent — only reframe real experience more powerfully

GEN 1:
{get_result('answers_v1')}

SCORES:
{get_result('scores_v1')}

CANDIDATE PROFILE:
{full_profile}

REAL INTEL:
{get_result('intel_report')[:10000]}

Label each: QUESTION X (GEN 2)
End with: EVOLUTION SUMMARY — what changed and why per answer
"""
            set_result("answers_v2", ask_llm(prompt))
            log(5, "Generation 2 complete", "done")
        except Exception as e:
            log(5, f"Stage 5 error: {e}", "error")
            set_result("answers_v2", "")
        finally:
            sandbox.delete()

    t4 = threading.Thread(target=run_stage4, name="stage4")
    t5 = threading.Thread(target=run_stage5, name="stage5")
    t4.start(); t5.start()
    t4.join();  t5.join()

    # ── STAGE 6: Final Scoring ─────────────────────────────────────────────────
    log(6, "Final bar raiser scoring...")
    sandbox_8 = daytona.create()
    try:
        prompt = f"""
{company_name} bar raiser — final debrief scoring.

Score evolved answers (same format as before). Then:

GENERATION COMPARISON:
- What genuinely improved Gen 1 → Gen 2?
- What still needs work?

FINAL HIRING RECOMMENDATION: STRONG HIRE / HIRE / NO HIRE

PREDICTED INTERVIEW OUTCOME:
Honest 3-sentence assessment.

TOP 3 THINGS TO NAIL ON THE DAY:
Grounded in what REAL {company_name} interviewers care about (from intel).

REAL INTEL CALIBRATION:
How does this candidate compare to successful candidates in the intel?

EVOLVED ANSWERS:
{get_result('answers_v2')}

REAL STANDARDS:
{get_result('intel_report')[:6000]}
"""
        set_result("scores_v2", ask_llm(prompt))
        log(6, "Final scoring complete", "done")
    except Exception as e:
        log(6, f"Stage 6 error: {e}", "error")
        set_result("scores_v2", "")
    finally:
        sandbox_8.delete()

    return save_output(company_name, role_name)


# ==============================================================================
# CLI ENTRY POINT
# ==============================================================================

if __name__ == "__main__":
    print("\n=== Self-Evolving Interview Prep Agent ===\n")

    # Read from files instead of user input
    try:
        with open('job_description.txt', 'r') as f:
            job_description = f.read()
        with open('cv.txt', 'r') as f:
            cv = f.read()
        with open('extra_context.txt', 'r') as f:
            extra = f.read()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure job_description.txt, cv.txt, and extra_context.txt exist in this directory.")
        exit(1)

    company_name    = input("Company name: ").strip()
    role_name       = input("Role title: ").strip()

    output_file = run_pipeline(
        job_description=job_description,
        cv=cv, extra=extra,
        company_name=company_name,
        role_name=role_name,
    )

    print("\n" + "=" * 60)
    print("SELF-EVOLVING INTERVIEW PREP PACK")
    print("=" * 60)

    sections = [
        ("intel_report", "COMPANY INTELLIGENCE REPORT"),
        ("competencies",  "ROLE DECODED WITH REAL INTEL"),
        ("gaps",          "GAP ANALYSIS & REFRAMING PLAYBOOK"),
        ("questions",     "REAL QUESTION BANK"),
        ("answers_v1",    "GENERATION 1 ANSWERS"),
        ("scores_v1",     "BAR RAISER SCORES: GEN 1"),
        ("answers_v2",    "GENERATION 2 ANSWERS (EVOLVED)"),
        ("scores_v2",     "FINAL BAR RAISER SCORECARD"),
    ]
    for key, title in sections:
        print(f"\n{'─'*60}\n{title}\n{'─'*60}")
        print(get_result(key) or "[No output — check error log above]")

    print(f"\n{'='*60}")
    print(f"Evolution complete. Full results → {output_file}")
    print(f"{'='*60}\n")