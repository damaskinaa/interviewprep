# NAILIT — Complete Project Memory Document
**Generated:** June 22, 2026
**Purpose:** Full handoff document for a colleague joining this project cold.
**Scope:** Entire build history — every plan executed, every fix applied, every error encountered, every vulnerability identified, current state, and the forward roadmap.

---

> **Read this first.** This document assumes zero prior context. If you only read one section, read Section 7 (Decisions), Section 12 (Risks), and Section 15 (Action Items) — in that order. Section 19 contains the chronological log if you need to understand *how* we got here, not just *where* we are.

---

## Section 0 — Orientation

**What NAILIT is:** An AI-powered interview intelligence platform. It researches a candidate's target company, decodes the job description into round-by-round signals, maps the candidate's real CV to provable stories, generates verbatim gap-repair scripts for weaknesses, produces full interview answers grounded in real evidence, and provides an AI coaching layer (Lua) that gives structured feedback on practice answers.

**What stage this is at, right now, tonight:** The backend pipeline is built, stress-tested, and has had three real content-quality bugs found and fixed through a rigorous live-testing cycle. The product was just successfully deployed to its Daytona sandbox for the first time with fully current code and all dependencies installed. It is **not yet** auth-enabled, **not yet** taking payments, and **deliberately not yet** running on paid infrastructure — that is a considered decision, not an oversight, explained fully in Section 7.

**The single most important thing to understand about the philosophy here:** This project is governed by one explicit rule, stated and re-stated by the founder throughout: **build slow, build solid, build for scale — not rushed, and not "lean" in the sense of "thin."** The founder has explicitly rejected the idea that this product should just be a thin wrapper around what a candidate could get from an hour on Glassdoor. The standard is: if this isn't meaningfully better than what a motivated person could produce alone in two hours, there's no point building it. That standard has driven nearly every architectural decision below, and it is restated explicitly in Section 7 (DEC-14) as the active forward plan.

---

## Section 1 — Goals and Success Criteria

**[GOAL-1]** Build a B2C AI platform that produces interview preparation materially better than solo research, grounded entirely in the candidate's real CV and real, current company-specific intelligence.
Type: [Fact] — primary product goal, restated explicitly tonight.
Success criterion: A user who completes a full prep pack and practices with Lua receives a meaningfully higher offer rate than baseline. This is the **north star metric** — not yet measurable because auth/email collection don't exist yet.

**[GOAL-2]** Reach the first paying customer once the product is verified end-to-end, without spending on infrastructure before there is revenue to justify it.
Type: [Decision] — explicitly restated multiple times tonight ("this is when I get to users that was the deal").
Current state: Zero paying customers. Product not yet public. Auth not built.

**[GOAL-3]** Build the proprietary, user-contributed interview question database — the long-term competitive moat.
Type: [Decision]
Current state: Zero contributions. Blocked entirely on auth existing (no way to attribute a contribution to a user yet).

**[GOAL-4]** Achieve a research architecture that is genuinely deep and stage-specific per company — not a single generic pass — without becoming financially or operationally unsustainable.
Type: [Decision] — this is the **newly restated, explicit goal from tonight's final message**, and it deserves its own full explanation because it changes how research should be architected going forward. See DEC-14 below for the full detail.

---

## Section 2 — Project Context

**Product name:** NAILIT
**Founder:** Solo founder, Ireland-based, non-technical — builds exclusively through Claude Code and Codex sessions, with this conversation acting as the strategic/architectural reviewing layer for every change.
**Stage:** Backend complete and stress-tested. Frontend complete for the core flow. No auth. No payments live. No public users.
**Repository:** `https://github.com/damaskinaa/interviewprep` (confirmed via `git remote -v` tonight)
**Current deployment:** Daytona sandbox `775bc2b0-4308-4f0e-bb1f-dc94f935cfc9`, now running current code as of tonight, port 8000.
**Frontend hosting:** Vercel, proxying to the Daytona sandbox via internal route handlers.
**Legal jurisdiction:** Irish company. Irish Data Protection Commission is the relevant GDPR regulator.

---

## Section 3 — Stakeholders

**Founder/Builder:** Solo. Owns every decision. Reviews and directs all Claude Code/Codex sessions personally; does not write code directly.
**The colleague this document is for:** Joining cold. Needs to understand both the technical state and the *why* behind the architecture, especially the "not just Glassdoor" research philosophy, to avoid undoing deliberate decisions.
**Primary customer segment:** Professional, 28–38, who just received a step-up interview invitation (e.g., the test case used throughout tonight: a Stripe PM role). High urgency, 2–6 week prep window, willing to pay for genuine depth.
**Future stakeholders, not yet engaged:** Fractional CTO (planned after 20 paying customers), investors (not approached), human expert reviewers for a future premium tier (deliberately deferred).

---

## Section 4 — Requirements

**[REQ-1]** Every research-driven section of a prep pack must reflect real, current, round-specific signal for the target company — not a single undifferentiated research pass. Type: [Decision — newly elevated to explicit requirement tonight].

**[REQ-2]** Every answer and every metric in a generated answer must trace to the candidate's actual CV or answer bank. No fabricated numbers, ever. Type: [Fact — enforced in code as of tonight, see DEC-12].

**[REQ-3]** Gap-repair language must be verbatim — actual words a candidate can say — not advice about what to say. Type: [Fact — implemented].

**[REQ-4]** The product must never present an internal system state (e.g., "Research insufficient") as candidate-facing content. Type: [Fact — enforced as of tonight, see DEC-12].

**[REQ-5]** No infrastructure spend occurs before there are real, paying users. Type: [Decision — restated explicitly and forcefully multiple times tonight].

**[REQ-6]** All Lua coaching endpoints must require authentication to prevent unbilled LLM cost exposure. Type: [Decision — implemented, 22 endpoints].

**[REQ-7]** GDPR-compliant data handling: deletion endpoint, export endpoint, retention policy, privacy policy. Type: [Decision — infrastructure built, not yet fully wired to real user identities].

---

## Section 5 — Constraints

**[CON-1]** Solo, non-technical founder. All implementation goes through Claude Code/Codex sessions with carefully scoped, narrow prompts. This conversation's role has been to review, diagnose, and write those prompts — not to write code directly.

**[CON-2]** Bootstrapped, no external funding. Every infrastructure decision is evaluated against "do we need to pay for this *yet*."

**[CON-3]** Tavily free tier: 1,000 API credits/month. `research_config.py` has three tiers (free/starter/production) controlling research depth — currently set to **"starter"** for local/sandbox testing, which gives meaningfully better depth than free tier while staying within the existing free Tavily account.

**[CON-4]** OpenAI is the actual LLM provider in production code (`agent_v2.py` imports `from openai import OpenAI` exclusively — confirmed via grep tonight). This is a **significant, previously undocumented divergence** from the unit-economics modeling done earlier in this project, which was built entirely around Claude Sonnet 4.6 / Haiku 4.5 pricing. **No Anthropic SDK reference exists anywhere in `agent_v2.py`.** This is flagged as an open architectural decision in Section 14 (OQ-1) — it needs to be resolved deliberately, not left as silent drift.

**[CON-5]** The Daytona sandbox is explicitly a development environment, not a production host. It sleeps when idle and requires manual waking via `daytona start <sandbox-id>`. This caused the majority of tonight's deployment debugging (Section 11).

**[CON-6]** The Daytona sandbox runs **Python 3.14**, a version new enough that `asyncpg` and `psycopg2-binary` (both needed only for the future Postgres migration) fail to compile their C extensions against it. This is a real, confirmed blocker for that specific future migration step — not for anything running today, since the product currently runs on SQLite.

**[CON-7]** Glassdoor actively blocks automated scraping. NAILIT does not scrape directly — it uses Tavily as a search intermediary, which is legally distinct (Type 1 data access, equivalent to a human using a search engine) but produces non-deterministic research depth depending on Tavily's current ability to surface Glassdoor-indexed content.

---

## Section 6 — Assumptions

**[ASM-1]** The target customer (Step-Up Candidate) will pay £49–£199 for company-specific, CV-grounded prep. Not yet validated with real paying customers.

**[ASM-2]** Users who complete the full pipeline and practice with Lua at least 3 times will show a measurably higher offer rate. Not yet measurable — blocked on auth and email collection.

**[ASM-3]** Tonight's three content-quality fixes (metric hallucination guard, "Research insufficient" strip, "Why This Role" generation) generalize beyond the single Stripe PM test case used to verify them. **Not yet confirmed on a second, different JD/CV pair.** This is the single most important open verification item — see Section 14 (OQ-2).

**[ASM-4]** A per-stage, multi-pass research architecture (see DEC-14) is technically and financially viable within the existing Tavily/OpenAI cost structure once properly scoped. Not yet engineered or costed — currently a stated direction, not a built feature.

---

## Section 7 — Decisions and Rationale

This is the most important section for understanding *why* the product looks the way it does. Read all of it, even the ones marked superseded — they explain what was tried and rejected.

**[DEC-1]** Use a six-module sequential pipeline (Company Intelligence → Role Intelligence → Candidate Profile → Gap Map → Interview Strategy → Prep Pack).
Status: Active.
Rationale: Each module writes a structured JSON artifact that the next module reads. This replaced an earlier, more monolithic pipeline that suffered from research contamination between sessions (see REJ-2) and made debugging effectively impossible.

**[DEC-2]** Use a credits-based pricing model (not pure subscription).
Status: Active, not yet wired to a payment flow.
Rationale: Interview prep is episodic, not habitual. A subscription mismatches the customer's actual usage pattern. Tiers: Free (1 lifetime session), Starter (£89/3 sessions, never expire), Monthly (£49/5 sessions + rollover), Premium (£199/10 sessions).

**[DEC-3]** Do not scrape Glassdoor directly; use Tavily as an intermediary.
Status: Active.
Rationale: Direct scraping violates Glassdoor's ToS and creates real legal exposure. Tavily-as-intermediary is the same legal category as a human using a search engine. The tradeoff, accepted deliberately, is non-deterministic research depth — mitigated long-term by DEC-14 below.

**[DEC-4]** Build the user-contributed question database as the long-term moat.
Status: Active, entirely blocked on auth (Section 14, OQ-3).
Rationale: This is what makes the research progressively better and independent of any single data source over time — directly relevant to tonight's "this can't just be Glassdoor" concern. Once real users exist and report which questions they actually got asked, the system stops depending on what Tavily/Glassdoor can surface and starts depending on verified first-party data.

**[DEC-5]** No human expert review layer until the AI-only product is proven.
Status: Active, deferred.
Rationale: A human layer should *amplify* a good product, not rescue a weak one. Premature human-in-the-loop work was explicitly rejected as scope creep multiple times in this project's history.

**[DEC-6]** GDPR minimum-viable compliance before charging any EU user.
Status: Infrastructure built (delete endpoint, export endpoint, 90-day retention job, `PRIVACY.md`), not fully wired — no real `user_id`/`user_email` exists yet to attach this to.

**[DEC-7]** Build an activation layer that surfaces real value *during* the pipeline run, not only at the end.
Status: Active, implemented.
Rationale: Three independent strategic frameworks applied earlier in this project (Jobs-To-Be-Done sequential-chain analysis, Theory-of-Constraints bottleneck analysis, Lean Startup activation-event analysis) converged independently on the same diagnosis: a 12–15 minute pipeline with no intermediate proof-of-value risked losing users before they ever saw the payoff. Implementation: after Module 2 completes, surface one real "danger question" pulled directly from that module's artifact; after Module 4, surface one real verbatim gap-repair script. Both pull from actual generated content, not placeholder text.

**[DEC-8]** Build the entire product to run locally first, with zero paid infrastructure, before any public deployment.
Status: Active — this was the explicit decision made earlier tonight, in direct response to the founder catching that the conversation had drifted toward recommending a paid Hetzner upgrade. **The founder was correct to push back; the recommendation was withdrawn.**
Rationale: This *is* "the deal" — explicitly stated multiple times. No infrastructure spend before real users exist.

**[DEC-9]** Do not deploy NAILIT onto the founder's existing Hetzner box (which runs unrelated bots — Hermes, OpenClaw).
Status: Active — decided tonight.
Rationale: That box has 4GB RAM, already at 31% utilization at idle from the existing bots. NAILIT's per-session memory footprint (Claude/OpenAI calls + DB + Redis, concurrently, per user) would risk an out-of-memory kill on a shared box. Isolating blast radius matters here exactly as it does for data minimization elsewhere in this project.

**[DEC-10]** Use Render or Fly.io free tier as the eventual "real public link" bridge stage, once local testing is exhausted — *before* paying for Hetzner.
Status: Decided, not yet executed.
Rationale: Gives a genuine public URL with zero monthly cost, without Daytona's jarring "sandbox not started" failure mode. This is the correct middle stage between "local only" and "paid production," and has not yet been built.

**[DEC-11]** Generate the production `.env` and infrastructure abstraction (`get_db()`, `dispatch_job()`) so that switching from SQLite/threading to Postgres/Redis is a single environment-variable change, not a rewrite.
Status: Built, verified working in the SQLite/threading (local) mode. **Not yet verified in the Postgres/Redis mode** — and per CON-6, that verification is currently blocked by a Python 3.14 compatibility issue with `asyncpg`/`psycopg2-binary` specifically inside the Daytona sandbox. This does not block anything today, since the product runs on SQLite, but it is a known, real blocker for the eventual Hetzner migration and should be resolved (likely via a different Postgres driver, or pinning an older Python version in the production Docker image) before that migration is attempted.

**[DEC-12]** Three targeted content-quality fixes, applied and verified live tonight, after a rigorous quality audit found real, serious problems in a generated prep pack:
Status: Active, verified.
- **Fix 1 — Metric hallucination guard.** Root cause: example prompts fed to the LLM contained fake placeholder numbers (77%, 34%, "one hour") which the model copied verbatim into real candidate answers. Fix: removed the fake examples from the prompt, added an explicit "every number must trace to the CV" rule, and added `strip_hallucinated_metrics()` — a post-generation validator that regex-scans every generated answer for number+unit patterns and strips any number that doesn't appear in the candidate's actual `raw_cv`/`raw_answer_bank`.
- **Fix 2 — "Research insufficient" leak.** Root cause: a hardcoded fallback string (originally written for a Google-specific test case and never generalized) leaked the system's internal "insufficient research" state directly into candidate-facing text. Fix: that string is now in a banned-strings list checked before assembly; the fallback function was rewritten to be company-agnostic.
- **Fix 3 — Blank "Why This Role" section.** Root cause: no validation existed to catch an empty required field before assembly. Fix: `repair_why_role_answer()` generates a grounded, role-specific answer using real JD signals and CV evidence, with a deterministic fallback if the LLM call fails; pre-assembly validation now raises an error rather than shipping a blank section.
All three were independently verified tonight on a real, live pipeline run (not just unit tests) using a real Stripe PM CV/JD test case — see Section 11 for the full verification log, including the discovery that the original "Google" hardcoding existed because of leftover test data from an earlier development phase, not the same bug recurring.

**[DEC-13]** Local-only stabilization: route the frontend to a local backend (`BACKEND_URL=http://localhost:8000`) instead of through Daytona's proxy, for local development and testing.
Status: Built and verified tonight — full pipeline run, all 6 modules, Lua coaching, all confirmed working locally with zero Daytona/Vercel dependency.
Rationale: This is the actual mechanism behind DEC-8 (local-first development). It also exposed a real, separate bug (Fix in DEC-12 sidebar: `tavily_extract()` was being called with more than 20 URLs and Tavily was rejecting the request outright — this was found and fixed *because* local testing made it visible quickly, which is the whole argument for DEC-8).

**[DEC-14] — THE FORWARD ARCHITECTURE DECISION, STATED EXPLICITLY TONIGHT. READ THIS ONE CAREFULLY.**
Status: **Decided in principle tonight. Not yet engineered. This is the most important open build item for the colleague picking this up.**

**The decision, in the founder's own framing:** the product cannot just be "do one Tavily search and summarize it" — that's the same thing a candidate could do themselves on Glassdoor in an hour, which defeats the entire purpose of building this. The research architecture needs to be **staged and round-specific**, not a single undifferentiated pass.

**Concretely, using the founder's own example:** for a Google interview, the system should not run one generic "Google interview questions" search. It should run **separate, targeted research passes per interview stage** — for example, one pass specifically targeting "Google behavioral interview" signal, a separate pass specifically targeting "Google hiring manager interview" signal, and so on for each distinct round a Google process actually has. Each stage's research should pull from as many distinct sources as reasonably possible (not just Glassdoor — Reddit, Blind, official careers content, YouTube interview-experience transcripts, etc., per the multi-source research design established earlier in this project), and **each stage's research should be isolated from the others** so a failure or thinness in one stage's research doesn't degrade or contaminate a different stage's output (directly connected to the research-contamination bug already fixed once before, REJ-2 — this is the same principle applied more granularly).

**Why this matters and what it actually buys the product:** this is the concrete mechanism that makes the product's depth real rather than cosmetic. A single search pass labeled "Google interview prep" produces shallow, undifferentiated signal. A separate, round-targeted pass for *behavioral* specifically and a separate one for *hiring-manager-round* specifically allows the system to surface genuinely different, genuinely relevant signal for each stage — which is exactly the kind of depth a candidate cannot replicate by spending an hour on Glassdoor alone, because Glassdoor doesn't organize its content this way and a human reading through it linearly won't naturally separate signal by round either.

**What this requires, going forward, not yet built:**
- The round/stage structure for a given company+role needs to be determined (likely already partially exists in Role Intelligence module output, given it already produces "round-organized" signals — this needs to be confirmed and extended, not necessarily built from scratch).
- Company Intelligence module (or a new sub-module) needs to dispatch **multiple, separately-scoped Tavily research calls**, one per identified round/stage, rather than one undifferentiated call.
- Each stage's research results need to be stored and processed independently, then synthesized together at the Interview Strategy stage — without one stage's research bleeding into or diluting another's.
- This must be costed against the Tavily credit budget (CON-3) — multiple research passes per session uses more credits per session than the current single-pass approach, so the `research_config.py` tiering system likely needs a fourth dimension: not just "how deep is each search" but "how many separate, stage-scoped searches do we run."

**This is explicitly the "medium lean, not lean" instruction from tonight.** "Lean" in the thin sense (one shallow pass, minimum viable, basically what a human could do alone) is explicitly rejected. "Medium lean" means: properly architected, staged, multi-source research — built to be genuinely sustainable and non-trivial to replicate — while still being disciplined about not over-engineering features nobody's validated yet (no voice layer, no human reviewers, no B2B tier — see Section 8). The depth is in the *research architecture*, not in the breadth of unrelated features.

---

## Section 8 — Rejected Approaches

**[REJ-1]** GPT-4o exclusively for all modules.
Rejected in earlier unit-economics work in favor of a planned Claude Sonnet/Haiku split. **However — see CON-4 — the actual running code still uses OpenAI exclusively.** This rejection was never actually implemented in code. This is now an open architectural question, not a closed decision (Section 14, OQ-1).

**[REJ-2]** A single, undifferentiated research pass with no round/stage separation, and no isolation between sessions.
Rejected initially because of a real, confirmed bug: a research-contamination incident where one company's research (Canva) leaked into a different company's session (Atlassian) due to inadequate session isolation in an earlier pipeline version. Fixed via the session-based modular architecture (DEC-1). **Tonight's DEC-14 extends this same principle one level deeper** — isolating not just between different users' sessions, but between different interview-round research passes within the same session.

**[REJ-3]** Pure monthly subscription pricing.
Rejected because interview prep usage is episodic/bursty, not habitual — mismatches the actual customer usage pattern and risks subsidizing light users at the expense of heavy users.

**[REJ-4]** Current (not former) employees as human expert reviewers, for a future premium tier.
Rejected due to direct conflict-of-interest risk (e.g., a current Google employee reviewing materials for a Google interview). Deferred entirely regardless, per DEC-5.

**[REJ-5]** Deploying NAILIT onto the founder's existing Hermes/OpenClaw Hetzner box.
Rejected tonight specifically — see DEC-9. Insufficient memory headroom, risk of resource contention between unrelated services.

**[REJ-6]** Paying for Hetzner/production infrastructure before real users exist.
Rejected repeatedly and explicitly tonight — this was a direction this conversation drifted toward in error, and the founder correctly redirected back to "the deal" (REQ-5). **This rejection should be treated as firm and intentional, not a temporary stance** — the colleague picking this up should not reintroduce a "let's just pay for a server" recommendation without the founder explicitly revisiting it.

**[REJ-7]** Building a voice mock-interview layer (LiveKit-based) at this stage.
Deferred — researched and architecturally decided (LiveKit + Deepgram + Cartesia, ~£1.20/session), but explicitly not started. Premium add-on for a later stage once the text-based product is validated with real paying users.

**[REJ-8]** Installing `asyncpg`/`psycopg2-binary` to "fully" complete the requirements.txt install inside the Daytona sandbox tonight.
Correctly abandoned mid-session tonight once it became clear these packages aren't needed for the current SQLite-based local/sandbox operation and were causing a Python 3.14 C-extension compilation failure that was blocking the actually-needed packages (`fastapi`, etc.) from installing. The fix was to install only the packages actually required right now, not to fight the Postgres migration prematurely.

---

## Section 9 — Architecture and Technical State

**Pipeline (6 sequential modules):**
1. Company Intelligence — multi-source research on the target company
2. Role Intelligence — decodes JD into round-by-round signals (`danger_zones`, `question_seeds`)
3. Candidate Profile — maps CV to provable stories
4. Gap Map — produces verbatim repair scripts (`repair_scripts[].verbatim_repair_answer`)
5. Interview Strategy — full round-organized Q&A, validated against the hallucination guard (DEC-12)
6. Prep Pack — final assembly, with pre-assembly validation for required fields and banned strings

**Confirmed in code tonight (via direct grep, not self-report):**
- `strip_hallucinated_metrics()` — agent_v2.py, line 6040, called at line 5832
- `repair_why_role_answer()` and `repair_why_company_answer()` — agent_v2.py
- `adapt_lua_response()` — lua_coach.py, returns 10 contract keys including `score_out_of_10` and `voice_and_delivery_coaching` pass-throughs
- `get_or_create_job()` — atomic, `BEGIN IMMEDIATE` transaction-based, prevents duplicate job creation on concurrent requests
- All 22 `/lua-*` routes gated with `Depends(require_app_key)`
- Global exception handler returning `{"error": ..., "status_code": ...}` consistently
- `delete_user_data()`, `get_user_data_export()`, `delete_old_jobs()`, `delete_old_sessions(days=90)` — GDPR infrastructure
- `get_db()` — abstracted, SQLite by default, Postgres if `DATABASE_URL` is set (not yet exercised in Postgres mode — see CON-6)
- `dispatch_job()` — threading by default, RQ/Redis if `REDIS_URL` is set (not yet exercised in Redis mode)
- `research_config.py` — `RESEARCH_TIER` currently set to `"starter"`

**Not yet built (see DEC-14 for the most important one):**
- Multi-pass, round/stage-isolated research dispatch (DEC-14) — this is the primary forward build item.
- Auth (no login, no user accounts, no session ownership — blocks credits, GDPR-by-user, offer-rate email, question database).
- Payment flow (Stripe webhook and signature validation exist and are tested; no Stripe products created in dashboard, no checkout UI wired).
- Email delivery (`send_email()` is a console-log stub; no Resend/SendGrid wired).
- PostHog analytics key (events fire, nothing records — key not set in Vercel).

**Repository state as of tonight:** `main` branch at commit `d203494`, pushed and pulled into the Daytona sandbox successfully. Sandbox dependencies (`fastapi`, `uvicorn`, `python-dotenv`, `rq`, `redis`, `stripe`) installed and confirmed. Backend confirmed running cleanly: `Application startup complete`, `Uvicorn running on http://0.0.0.0:8000`.

---

## Section 10 — Research and Findings (carried over from earlier strategic work, still valid)

- Global interview prep tool market: ~$2.5B (2023) → $6.3B by 2031, 11.8% CAGR.
- Closest direct competitor: CleverPrep (~$19 one-time), strong programmatic SEO, lacks gap-repair scripting and Evidence Ledger depth.
- Verified AI cost economics (as modeled — see CON-4 for the caveat that production code currently uses OpenAI, not the Claude split this was modeled on): ~£0.78/session with the planned Haiku/Sonnet split; actual current OpenAI-based cost not yet re-verified.
- Tonight's live pipeline timing (Stripe PM test session): role_intelligence 26s, candidate_profile 15s, gap_map 16s, interview_strategy ~3.5 minutes (the slowest module, now slightly slower than its original ~196s baseline due to the new per-answer validation loop from DEC-12 — a real, known, accepted UX tradeoff for content safety).

---

## Section 11 — Tonight's Deployment Debugging Log (full detail, because every step taught something real)

This matters enough to document in full because every single step traced back to a *different* real cause, and a colleague repeating this deployment elsewhere will hit the same sequence if they don't know this history.

**Symptom 1:** Vercel form submission → `400 Bad Request: failed to resolve container IP... Is the Sandbox started?`
**Real cause:** The Daytona sandbox had gone to sleep (its designed behavior when idle — it is a dev sandbox, not a production host).
**Fix:** `daytona start <sandbox-id>` — required first fixing an expired CLI auth (`daytona login`) and a CLI/API version mismatch (`brew upgrade daytonaio/cli/daytona`, v0.173.0 → v0.189.0).

**Symptom 2:** After waking the sandbox, form submission → `502` error.
**Real cause:** No backend process was actually running inside the sandbox at all (`ps aux | grep uvicorn` returned nothing).
**Diagnostic path:** Used `daytona exec` and `daytona ssh` to get a real shell inside the sandbox. Attempted to `cd` to a placeholder path, which correctly failed (a literal copy-paste artifact, not a real bug) — corrected by using `find` to locate the real code at `/home/daytona/interviewprep/`.

**Symptom 3:** Attempting to start `uvicorn` inside the sandbox → `ModuleNotFoundError: No module named 'fastapi'`.
**Real cause, the most important finding of the night:** `git log` revealed the local repo was **3 commits ahead of `origin/main`** — every fix from tonight's entire content-quality debugging session (Section 7, DEC-12) existed only on the founder's laptop and had never been pushed. A grep for `strip_hallucinated_metrics` inside the sandbox's copy of `agent_v2.py` returned **zero results**, confirming the sandbox was running stale, pre-fix code. This explained *both* the original 400 error context *and* the 502 — the sandbox was never going to reflect any of tonight's work until code was actually pushed and pulled.
**Fix:** `git push origin main` (succeeded, `2c173e3..d203494`), then `git pull origin main` inside the sandbox via `daytona exec` (fast-forward, 1,447 insertions across 10 files — every Session 5-8 file plus tonight's content fixes).

**Symptom 4:** After pulling current code, `pip3 install -r requirements.txt` partially failed.
**Real cause:** `asyncpg` and `psycopg2-binary` (both added to `requirements.txt` in an earlier session, for the *future* Postgres migration only) failed to compile their C extensions against the sandbox's Python 3.14 — a genuine, confirmed version-incompatibility (internal CPython functions `_PyInterpreterState_GetConfig` and `_PyLong_AsByteArray` changed signature in 3.14, breaking the compiled extension code in these package versions). Critically, pip's all-or-nothing install behavior meant **`fastapi` itself was never installed**, because the install process stopped when it hit the failing packages partway through the list.
**Fix:** Installed only the packages actually needed for current (SQLite/threading) operation: `pip3 install fastapi uvicorn python-dotenv rq redis stripe` — explicitly skipping `asyncpg`/`psycopg2-binary` since they aren't exercised in the current `DATABASE_URL`-unset mode. This succeeded cleanly.

**Symptom 5 (false alarm, worth documenting because it wasted real diagnostic time):** A shell polling script used to monitor module-by-module pipeline progress appeared to hang indefinitely on `interview_strategy`, printing hundreds of repeated `→ running: ...` lines with no stage name.
**Real cause:** Not a hang at all. Direct verification via `get_job()` in Python (bypassing the shell script entirely) showed the job had completed successfully in 3.5 minutes. The shell script's inline Python JSON parser was choking on control characters inside the large `product_json` response blob and silently failing to update its displayed status, while the actual job had long since finished.
**Lesson, stated explicitly for the colleague:** This exact failure mode happened **twice** in this project's history. Any time this monitoring script appears stuck, verify directly against `get_job()` before assuming the pipeline itself is broken.

**Final result, confirmed at the end of tonight's session:** Backend running cleanly inside the Daytona sandbox, current code, all dependencies present, clean startup log (`Application startup complete`, `Uvicorn running on http://0.0.0.0:8000`). The live Vercel form has not yet been re-tested as of the writing of this document — **that is the very next action**, see Section 15 (ACT-1).

---

## Section 12 — Risks

**[RSK-1]** The OpenAI-vs-Claude architecture question is undecided and silently diverged from the original plan (CON-4).
Probability: Certain (already true). Impact: Medium — affects cost model accuracy and the future "round-isolated multi-pass research" cost calculus (DEC-14) directly, since the per-call cost assumptions used to plan that feature need to be based on whichever provider is actually used.
Mitigation: Resolve deliberately, in a single dedicated session — do not let it stay silent. See Section 14 (OQ-1).

**[RSK-2]** Tonight's three content-quality fixes were verified on only one test case (Stripe PM).
Probability: Medium that edge cases exist in other company/role combinations. Impact: High — this is exactly the kind of issue that previously caused multiple rebuild cycles in this project's history.
Mitigation: Run a second, different JD/CV pair through the full pipeline before considering the fixes "done." See Section 14 (OQ-2), Section 15 (ACT-2).

**[RSK-3]** The "Why This Role" generation depends on an LLM call with a deterministic fallback; the fallback's quality has not been independently tested (only the LLM-success path was verified tonight).
Probability: Medium. Impact: Medium.
Mitigation: Deliberately trigger the fallback path (e.g., by testing with malformed input) and verify the fallback text is still acceptable quality.

**[RSK-4]** Auth does not exist. This is now the single largest blocker, gating: payments, GDPR-by-user, the offer-rate email, and the entire question-contribution moat (DEC-4).
Probability: Certain. Impact: Critical — nothing past this point can move forward without it.
Mitigation: Build minimal auth (email + magic link, Clerk or Supabase Auth — not yet decided which) as the next major build session.

**[RSK-5]** Daytona is not a production host and will continue sleeping/requiring manual intervention indefinitely if left as the deployment target.
Probability: Certain (recurring). Impact: High for any real user trying to use the live link unpredictably.
Mitigation: DEC-10 (Render/Fly free tier) is the planned next step, not yet executed.

**[RSK-6]** The Python 3.14 / `asyncpg`/`psycopg2-binary` incompatibility (CON-6) will block the eventual Postgres migration if not resolved in advance.
Probability: Certain if the migration is attempted as-is. Impact: Medium (a real, fixable blocker, but would cause exactly the kind of mid-migration confusion this project has already experienced once tonight with the missing `fastapi` install).
Mitigation: Either pin the production Docker image to an older, compatible Python version, or evaluate a pure-Python/async-compatible alternative Postgres driver before attempting the Hetzner migration.

**[RSK-7]** The multi-pass, round-isolated research architecture (DEC-14) will materially increase Tavily credit consumption per session.
Probability: Certain by design. Impact: Medium — manageable, but needs explicit costing before being built, not discovered after.
Mitigation: Before building DEC-14, calculate expected Tavily credits-per-session under the new multi-pass design and confirm it still fits within the `research_config.py` tier budgets, adjusting the "starter" tier's call-count limits if needed.

**[RSK-8]** `interview_strategy`'s runtime has grown from ~196s to ~210s+ due to the new per-answer validation loop (DEC-12), and will likely grow further once DEC-14's multi-pass research is added on top.
Probability: Certain. Impact: Low-to-medium — a real UX cost (user waits longer with no fine-grained progress indicator), not a correctness issue.
Mitigation: Consider adding more granular progress messaging during this module specifically (e.g., "validating answer 6 of 12") rather than a single static "running" state, especially once DEC-14 adds more processing time on top.

---

## Section 13 — Dependencies

**[DEP-1]** Auth system — blocks payments, GDPR-by-user, offer-rate email, question database. Nothing past this point moves without it.

**[DEP-2]** Resolving the OpenAI-vs-Claude question (CON-4) — should happen before any further unit-economics or cost-modeling work, since current modeling may not reflect actual running costs.

**[DEP-3]** Render/Fly.io free-tier deployment — needed before any real external person tests the live product; currently the only "live" option is the Daytona sandbox, which requires the founder to manually keep it awake.

**[DEP-4]** Resolving the Python 3.14/asyncpg compatibility issue — blocks the eventual Postgres migration specifically, blocks nothing today.

**[DEP-5]** A second, independent JD/CV quality test — should happen before considering tonight's content fixes (DEC-12) fully closed.

---

## Section 14 — Open Questions

**[OQ-1]** Is the product deliberately staying on OpenAI, or should it migrate to the Claude split the earlier unit-economics work was based on?
Why it matters: Affects real cost-per-session, and affects the cost calculus for DEC-14's multi-pass research expansion.
Owner to resolve: Founder, in a single dedicated session — not silently, not mid-fix.
Priority: High.

**[OQ-2]** Do tonight's three content-quality fixes (DEC-12) hold up on a second, different company/role test case, or were they over-fit to the single Stripe PM test?
Why it matters: This exact failure pattern (works on one test, breaks on the next) has happened multiple times in this project's history.
Priority: High — should be resolved before considering the backend "done."

**[OQ-3]** What does the question/round structure actually look like across different companies, and does the existing Role Intelligence module's output already contain enough round-segmentation to drive DEC-14's multi-pass research, or does that segmentation need to be built fresh?
Why it matters: This determines whether DEC-14 is a moderate extension of existing code or a more significant new build.
Priority: High — this is the next major architecture question to resolve before writing the DEC-14 implementation prompt.

**[OQ-4]** Which auth provider — Clerk or Supabase Auth?
Why it matters: Determines the next build session's exact shape.
Priority: Medium — either is fine; pick one and move.

**[OQ-5]** Has the live Vercel form actually been successfully retested since tonight's deployment fix?
Why it matters: This is the single unverified action item hanging open at the exact moment this document was generated.
Priority: Immediate — see Section 15 (ACT-1).

---

## Section 15 — Action Items

**[ACT-1]** Retest the live Vercel form submission now that the Daytona sandbox is running current code with all dependencies installed.
Owner: Founder. Deadline: Immediate, the very next action.
Status: Open — this is the one thing left hanging at the moment this document was written.

**[ACT-2]** Run a second, independent JD/CV pair through the full local pipeline to verify tonight's three content fixes generalize.
Owner: Founder + Claude Code session.
Status: Open. Depends on: nothing — can happen immediately, in parallel with ACT-1.

**[ACT-3]** Resolve OQ-1 (OpenAI vs. Claude) in a single, dedicated, non-bundled session.
Owner: Founder.
Status: Open. Should happen before any further cost-modeling or before DEC-14's research-expansion costing.

**[ACT-4]** Investigate whether Role Intelligence's existing output already contains the round/stage structure needed to drive DEC-14's multi-pass research, before writing the implementation prompt for it.
Owner: Founder + Claude Code (read-only investigation session first).
Status: Open — this is the necessary first step before DEC-14 can be implemented.

**[ACT-5]** Build minimal auth (email + magic link).
Owner: Founder + Claude Code/Codex session.
Status: Open. The single highest-leverage remaining build item — unblocks payments, GDPR-by-user, the offer-rate email, and the question-contribution database simultaneously.

**[ACT-6]** Set up Render or Fly.io free-tier deployment for the backend, as the genuine public-link bridge stage before any paid infrastructure.
Owner: Founder + Claude Code session.
Status: Open. Depends on: nothing technically, but logically follows once ACT-1/ACT-2 confirm the current build is solid.

**[ACT-7]** Resolve the Python 3.14/asyncpg-psycopg2 compatibility issue before attempting any future Postgres migration.
Owner: Founder + Claude Code session (research session, not urgent today).
Status: Open, not urgent — only matters when the eventual Hetzner/Postgres migration is actually attempted.

**[ACT-8]** Once ACT-4 is resolved, write and execute the DEC-14 multi-pass, round-isolated research architecture build.
Owner: Founder + Claude Code/Codex session(s) — likely multiple narrow sessions given the project's established discipline of small, verified, one-thing-at-a-time changes.
Status: Open. This is the most significant remaining piece of net-new architecture in the entire project, and should not be rushed or bundled with anything else.

---

## Section 16 — Lessons Learned

**Lesson:** A clean compile, and even a clean isolated unit test, is not proof that a fix works. The only thing that counts as verification is a real call, on the real running system, with real input, checked directly — not through an agent's self-report.
What happened: This exact pattern recurred at least three times tonight alone (the Lua key-mismatch fix that compiled clean but silently dropped two keys the frontend needed; the shell polling script that looked "stuck" but the underlying job had actually finished; the repeated need to grep the *actual sandbox filesystem* rather than trust that a push/pull had landed).
Implication: Every future session should end with a real, live verification step, not a self-report.

**Lesson:** Local fixes do not exist anywhere else until they are explicitly pushed, pulled, and the dependent environment is rebuilt (dependencies reinstalled, process restarted). This gap is invisible until something breaks.
What happened: Tonight's entire deployment debugging chain (Section 11) was ultimately one root cause wearing four different costumes — code fixed locally, never propagated to the sandbox.
Implication: Going forward, any "this is fixed" claim needs to specify *where* it's fixed (local only? pushed? deployed?) — these are not interchangeable states.

**Lesson:** When an error message names a path or location (e.g., `/sandboxes/.../toolbox/proxy/8000/...`), read it literally before theorizing — it usually tells you exactly which system layer failed.
What happened: The original 400 error's path immediately identified Daytona as the failure point, which was correct, but it took several more steps to discover the *deeper* reason (stale code, missing deps) underneath that surface-level diagnosis.
Implication: Treat the first diagnosis as a starting point, not a complete answer — keep asking "but why is *that* true" one more level down.

**Lesson:** The founder's instinct to push back on scope and spend creep has been correct every time it happened in this project's history (rejecting premature Hetzner spend, rejecting the existing-Hermes-box reuse, insisting tonight's research architecture be genuinely deep rather than a thin Glassdoor-equivalent wrapper).
Implication: Future sessions, including whoever reads this document next, should treat founder pushback on scope/spend as a strong, historically-validated signal to investigate rather than a thing to argue past.

---

## Section 17 — Future Opportunities (explicitly deferred, not forgotten)

**[FUT-1]** DEC-14's multi-pass research architecture — already covered in full above; this is the most concrete and immediate "future" item, effectively the next major milestone.

**[FUT-2]** Voice mock interview layer (LiveKit + Deepgram + Cartesia, ~£1.20/session) — researched, architecturally decided, deferred until text product is validated with paying users.

**[FUT-3]** Human expert review marketplace (former-employee reviewers, premium tier uplift) — deferred until AI-only product is proven; legal/conflict-of-interest framework already researched.

**[FUT-4]** User-contributed question database — the long-term moat; blocked entirely on auth (ACT-5), should begin the moment auth ships.

**[FUT-5]** B2B corporate tier — designed into the architecture conceptually, not built; deferred until B2C revenue exists.

---

## Section 18 — Terminology

**NAILIT** — the product.
**Lua** — the AI coaching persona; text-based, returns a 10-key structured response.
**Step-Up Candidate** — primary customer persona: 28–38, just received a step-up interview invitation.
**Gap repair script** — verbatim words a candidate can say when challenged on a weakness.
**Evidence Ledger** — the section of the prep pack tracing every claim back to its source.
**Daytona** — the development sandbox currently hosting the backend; explicitly not a production host.
**DEC-14 / "medium lean" research** — tonight's core architectural decision: staged, round-isolated, multi-source research per interview stage, as opposed to a single shallow pass. This is the project's answer to "why is this better than an hour on Glassdoor."
**`get_or_create_job()`** — atomic job-creation function preventing duplicate concurrent module runs.
**`strip_hallucinated_metrics()`** — validator preventing fabricated numbers in generated answers.

---

## Section 19 — Full Chronological Build Log

**Earliest phase (separate, prior session — referenced in this conversation's history):** Conversion of a 30-day "Dry Month Experiment" workbook into Kindle EPUB/DOCX formats. Unrelated to NAILIT's core build; included here only because it appears at the start of this conversation's history and should not be confused with NAILIT-specific work.

**Phase 1 — Backend fixes and stress testing (Sessions 1–4):** Five critical backend fixes (Tavily crash on retry exhaustion, Lua response key mismatch, global error handler shape, corrupted-artifact safety, stale-job cleanup). Activation layer built (danger question + gap-repair script surfaced mid-pipeline). PostHog instrumentation added. Offer-rate email infrastructure scaffolded (stub, not yet live).

**Phase 2 — Comprehensive stress test, 17 tests, then 3 follow-up fixes:** Full input-boundary, concurrency, Tavily-retry, pipeline-integrity, Lua-contract, security, and resource/scale testing. Found and fixed: race condition on double module-run (atomic `get_or_create_job()`), unauthenticated Lua endpoints (22 routes patched), missing synchronous dependency check at the HTTP layer for out-of-order module runs.

**Phase 3 — Infrastructure abstraction (Sessions 5–8):** Docker/docker-compose scaffolding, PostgreSQL/Redis abstraction with SQLite/threading fallback, Stripe credits infrastructure (tables, webhook, signature validation), GDPR infrastructure (delete/export endpoints, retention job, privacy policy).

**Phase 4 — Strategic and business work (parallel track, throughout):** Full AJTBD analysis, 5-segment customer analysis, RAT risk scoring, Lean/TOC/Antifragile/ABCDX/OKR master framework pass, unit economics modeling (built around a Claude-based cost assumption — see CON-4 for why this needs revisiting), competitive analysis, GDPR/regulatory research, pricing model design.

**Phase 5 — Local-only stabilization and live quality verification (tonight, most recent):**
- Decision to test and stabilize entirely locally before any further paid-infrastructure discussion (correcting an earlier drift toward recommending paid Hetzner spend).
- Local backend/frontend wired together (`BACKEND_URL`), full pipeline verified end-to-end locally.
- Real bug found and fixed: `tavily_extract()` crashing on >20 URLs.
- Live quality audit of a real Stripe PM prep pack revealed three serious content problems (fabricated metrics, leaked internal placeholder text, blank required section).
- All three fixed (DEC-12), verified via a rigorous, scripted re-test — not self-report — confirming zero forbidden strings, a real grounded "Why This Role" section, and 100% of generated metrics tracing to the real CV.
- OpenAI billing issue encountered mid-verification (quota exhausted), resolved via a $5 manual top-up with auto-recharge deliberately left off (matching the project's "no surprise spend" principle).
- Deployment debugging (Section 11, full detail) — discovered and fixed: sleeping Daytona sandbox, missing backend process, three commits of unpushed fixes, missing dependencies, a Python 3.14/asyncpg incompatibility, and a false-alarm monitoring-script bug.
- Backend confirmed running cleanly inside Daytona with fully current code as of the end of tonight's session.
- Founder explicitly restated and elevated the "this must be genuinely deep, not Glassdoor-equivalent" research philosophy into a concrete architectural direction (DEC-14) — the most important forward-looking decision captured in this document.

---

## Section 20 — Knowledge Gaps and Warnings for Whoever Reads This Next

**Gap 1:** This document was generated from conversation history, not a fresh live read of the current repository state. Before building anything from Section 15's action items, re-verify the current state with direct greps/checks rather than assuming this document is still accurate by the time you read it.

**Gap 2:** OQ-1 (OpenAI vs. Claude) is a real, unresolved divergence between what was planned and what is actually running. Do not build further cost-sensitive features (especially DEC-14's multi-pass research) on top of unit-economics numbers that assume the wrong provider.

**Gap 3:** Tonight's content-quality fixes are verified on exactly one test case. Treat them as "likely correct, not yet proven general" until ACT-2 is done.

**Gap 4:** DEC-14 is a *decision*, not yet an *implementation*. Do not assume the multi-pass research architecture exists in code — it does not. The next colleague's most valuable first contribution is likely ACT-4 (investigating whether Role Intelligence's existing round-segmentation can be extended into DEC-14, rather than rebuilt).

**Warning:** Do not recommend paid infrastructure spend without the founder explicitly revisiting REQ-5/REJ-6. This has been explicitly, repeatedly rejected, and the rejection should be treated as a firm project principle, not an open question.

**Warning:** Before re-running any "fix and verify" Claude Code prompt, grep for existing definitions first. This project has had at least one near-miss where a fix was nearly reapplied, which would have silently created duplicate function definitions.

**Warning:** Verify ACT-1 (live Vercel retest) actually happened and succeeded before treating tonight's deployment work as complete. As of this document's writing, it had not yet been confirmed.
