# FULL PORTFOLIO HANDOFF — Everything, Both Projects
### The single document to take over the whole operation

**Generated:** July 3, 2026
**For:** a colleague taking over the entire project portfolio with zero prior context.
**Scope:** BOTH projects, fully — architecture, next steps, market research, strategy, segments, assumptions, risks, and the reasoning behind every major decision.

> **How to use this document.** This is the master orientation. It is deliberately complete enough to run from on its own, but each project also has its own deep-dive file (named at the end of each project's section) for when you need maximum granular detail. Read this top-to-bottom once; then work from the per-project deep-dives.

---

# PART 0 — THE PORTFOLIO AT A GLANCE

There are **two separate projects**. They share a founder, a philosophy, and one server provider — nothing else. Keep them mentally and architecturally separate.

| | **PROJECT 1 — NAILIT** | **PROJECT 2 — PKS** |
|---|---|---|
| **What it is** | AI interview intelligence product (CV+JD → company-specific prep pack → mock interview with AI feedback) | Private, model-agnostic AI knowledge infrastructure (Obsidian truth layer + swappable models + a safety layer that makes data corruption structurally impossible) |
| **Type** | A product, for paying customers | Internal/business infrastructure |
| **Stage** | Built & live-verified; pre-auth, pre-revenue | Fully architected; not yet built |
| **The one thing that matters** | Ship auth → start the contribution database (the moat) before the 12–18 month window closes | Build Phase 1 (Git-versioned vault + OS-level read-only-for-AI) first — small, high-value |
| **Deep-dive file** | `PROJECT-1_NAILIT/NAILIT_MASTER.md` | `PROJECT-2.../PKS_Architecture_Blueprint.md` |

**The governing philosophy, shared across both, stated once:** build slow, solid, and for scale — not thin, not rushed. Never a wrapper around what someone could get from ChatGPT or two hours of Glassdoor. Diagnose before fixing. Verify on the real running system — an AI's self-report is not evidence. Never bundle two changes. **No paid infrastructure before real paying users.** The founder is solo, non-technical, Ireland-based, builds through Claude Code/Codex with a strategic reviewing layer on top, and is deliberately not a public-facing person (LinkedIn acceptable; no Instagram/TikTok/CEO-persona).

---

# ═══════════════════════════════════════
# PART 1 — PROJECT 1: NAILIT (THE PRODUCT)
# ═══════════════════════════════════════

## 1.1 — What NAILIT is

A user inputs their CV, a job description, and their relevant experience. A six-module pipeline researches the target company, decodes the role by interview round, maps the candidate's real CV evidence to provable stories, finds genuine gaps and writes verbatim scripts to address them, generates answers grounded strictly in the candidate's real experience, then runs a mock interview with an AI coaching layer ("Lua") that gives structured feedback. Two later modules (voice mock, human expert review) are explicitly deferred.

**The differentiator that actually matters long-term:** a first-party database of real candidates reporting which questions they were *actually* asked, tagged by company/role/round, after real interviews. This is the moat. It doesn't exist yet — designed, not built. Everything strategic below points at building it before the market window closes.

## 1.2 — Current state (verified, not assumed)

**Works, confirmed by direct live inspection** (a real Google/Program-Manager session, not a self-report): the full six-module pipeline runs end-to-end; CV-evidence extraction pulls real metrics correctly; the hallucination guard strips any number not traceable to the candidate's real documents (verified: stripped a fabricated "77%", kept a real "31%"); forbidden-claims detection fires correctly; gap detection works; Lua returns its full 10-field response; 22 Lua endpoints are authenticated; atomic job creation prevents race-condition duplicates; a 17-test stress suite passes; the Stripe webhook validates signatures; GDPR delete/export endpoints actually remove data.

**Broken, confirmed by direct inspection (narrow, fixable):** the answer generator over-uses the same 1–2 stories across many questions (the `story_inventory` artifact holds 2 of ~17 available stories) and leaks an identical boilerplate paragraph into ~15 answers. Other modules don't show this — the bug is confined to the answer-generation/story-selection step. Root cause not yet found; investigation prompt written and ready.

**Decided but not built:** authentication (blocks four downstream things); the contribution database (the moat); Stripe checkout UI (webhook exists, no products/UI); real email delivery (`send_email()` is a stub); multi-pass round-specific research (decided, unbuilt); voice mock (deferred); human expert review layer (V2).

**Zero paying customers; zero validated market assumptions.** Deliberately pre-revenue until the product quality and the value proposition are verified.

## 1.3 — Architecture

**Shape:** six sequential modules (Company Intelligence → Role Intelligence → Candidate Profile → Gap Map → Interview Strategy → Prep Pack), each writing a structured JSON artifact read only by later modules; out-of-order runs return HTTP 400. Then Module 7 (Answer Generator) and Module 8 (Mock Interview with Lua) unlock after Prep Pack completes.

**Stack:** Next.js/Vercel frontend; FastAPI backend; SQLite locally with a `get_db()` abstraction that switches to Postgres via `DATABASE_URL`; threading with a `dispatch_job()` abstraction that switches to RQ/Redis via `REDIS_URL`; **OpenAI exclusively** for LLM calls (grep-confirmed, zero Anthropic — see the open conflict below); Tavily for research. Repo: `github.com/damaskinaa/interviewprep`, `main`. Key files: `agent_v2.py`, `api.py`, `job_store.py`, `lua_coach.py`, `app/page.tsx`, `research_config.py`.

**Design decisions with rationale:** modular pipeline with per-module artifacts (each stage independently debuggable, no cross-contamination); credits pricing not subscription (interview prep is episodic — non-expiring credits avoid the "cancel after 3 months" churn); hallucination guard (never put a number in a candidate's mouth that isn't in their real CV — the core trust mechanism); contribution database as the moat (generation commoditizes as models improve; first-party data doesn't).

## 1.4 — Economics (modeled, needs one verification)

Per-session AI cost modeled at ~£0.78; revenue £49–£199 via non-expiring credit packs (Free 1 / Starter £89·3 / Monthly £49·5 / Premium £199·10). **Open conflict to resolve deliberately:** the cost model assumed a Claude Sonnet/Haiku split, but the code runs on OpenAI exclusively. With June 2026 pricing and prompt caching, a real session likely costs **~$0.31 (~£0.24)** — *lower* than modeled — but this must be verified against the actual OpenAI invoice before any pricing or margin claim is trusted. (Full pricing table in the deep-dive, Appendix C.)

## 1.5 — Market (June 2026 intelligence — this is the freshest strategic layer)

**Market size:** interview-prep overall $3.8B (2025) → $9.7B (2034), 10.9% CAGR. The AI-interview subset is ~$200M (2024) growing at **24.2% CAGR — ~2.2x faster** than the overall market. The structural shift is away from video libraries toward AI-native tools.

**The single most important market shift, and it favors NAILIT:** the AI interview-tool market split in 2025–2026 into two ethically distinct categories. **Coaches (honest prep)** — practice-mode tools used *before* the interview (NAILIT's category). **Copilots (live overlays)** — real-time tools that transcribe the interviewer and feed answers during the live interview (Final Round AI, Cluely, etc.), priced $90–$488/mo. The copilot category is suffering a **reputation collapse**: Final Round AI shows ~40% negative reviews in one cut, billing-trap complaints, auto-renew disputes, and Reddit moderators now *pinning warnings* on overlay-tool promotion threads. NAILIT's structural choices (no live copilot, non-expiring transparent credits, hallucination guard, GDPR delete/export) put it cleanly on the honest-prep side without having to argue the case — and let it engage in exactly the communities now hostile to copilots. **This tailwind did not exist when the earliest planning was done. Lean into it: "honest prep, transparent pricing, your data is yours."**

**Competitive landscape (top direct competitors, June 2026):** Big Interview ($39–$299 across tiers depending on source — *pricing conflict flagged, verify live*; large but not innovating on AI, MEDIUM threat); Four-Leaf ($5–20/mo, aggressive pricing, "good enough" for some, **HIGH threat**); Yoodli ($25/mo, best *delivery* feedback but not interview-specific, MEDIUM); Road to Offer (free+paid, best AI-feedback model but consulting-only, LOW for NAILIT's segment); **Revarta (NEW — closest philosophical competitor**, built by an ex-hiring-manager, calibrated to "what hiring managers actually assess," HIGH threat — but lacks company-specific intelligence and CV-mapping, which is NAILIT's wedge against it). ChatGPT/Claude (free–$20/mo) remain the **CRITICAL #1 competitor in users' minds** — most people try this first.

**Two findings that sharpen the wedge (from the PARITY competitive pass):**
- **The real incumbent is "do nothing / go in blind"** — for a gap-returner with an interview in days, the true default is zero prep, not ChatGPT. This sets the switching-cost floor and belongs in every pricing/positioning decision.
- **Glassdoor isn't just stale — it's actively managed.** 68% of HR professionals admit to managing their company's reputation on review platforms. The research layer candidates rely on is *partially adversarial*, not merely imperfect — a stronger differentiation claim than "outdated."
- **The AI-detectability problem:** hiring managers report they can identify and *penalize* generic-AI-written answers. So generic AI prep doesn't just fail to help a low-confidence candidate — it can actively hurt by producing scripted, detectable answers. NAILIT's evidence-locked generation is structurally the opposite of generic AI output.
- **The three-way silo nobody bridges:** delivery-only (Yoodli/Huru), generic-content-only (ChatGPT/LinkedIn/Big Interview), and content-but-tech-only-or-unscalable (Exponent/human coaches). **Nobody combines delivery + content + company calibration in one flow.** NAILIT is the first attempt at all three together.

**The six competitive wedges:** (1) live company intelligence synthesis — unique; (2) candidate-evidence-locked answer generation — unique and provably so; (3) delivery + content + company context in one flow — unique; (4) the contribution database — the future moat; (5) episodic-respecting non-expiring credits pricing — structural, the opposite of the auto-renew traps generating competitors' negative reviews; (6) answers that don't read as AI-generated — a direct product-level answer to the AI-detectability failure mode of every free alternative.

**The Red Queen window:** two independent analyses agree — **12–18 months** before a large incumbent (LinkedIn or OpenAI, most plausibly) ships company-specific research synthesis as a feature. Past that point, the *generation* layer commoditizes. The moat is not the feature; it's the data flywheel (session data → better calibration → better outcomes → more users) plus trust built with the target segment in that window. This independently confirms the urgency of building the contribution database now.

## 1.6 — Segments (all hypotheses — 0 interviews conducted)

**Critical framing:** every segment below is a *hypothesis to test*, not validated user research. Two earlier external "Hermes" runs invented their own segments without being shown NAILIT's real architecture — so those are candidate-segments-to-test, not truth (see the "external reports" caution below).

**Five hypothesized segments (most recent list), ranked:** (1) New Grad — huge TAM ($3.6–7.2B), HIGH virality, but low WTP; (2) Career Changer — smaller ($120–240M) but HIGH WTP and large competitor gap; (3) Non-Native English speaker — large ($4.5–13.5B), HIGH WTP; (4) Bootcamp Grad — HIGH existing habit; (5) **Comeback Professional / gap-returner — the most rigorously developed segment in the project.**

**Segment 5 (Comeback Professional) — the deepest analysis, and the recommended first validation target.** This is the person who hasn't interviewed in 5+ years — after a layoff or a long tenure — and finds that interviewing today (AI screening, structured behavioral rubrics, culture-fit assessment) looks nothing like they remember, and they're already shaken. Their priority order is **private-and-low-stress first, then speed, then company-specificity** — emotionally-driven and urgency-driven, not status- or price-driven. Their real alternative today is 4–8 hours of DIY Glassdoor/ChatGPT research with two chain-breaks: no efficient synthesis of "how does this company interview *now*," and no calibrated feedback on whether their answers are actually right for this company. The strongest receptivity window is **24–48 hours after an interview invite arrives** (estimated ~10:1 better than steady-state). Best channel: Reddit threads (r/layoffs, r/cscareerquestions "haven't interviewed in years") where the chain-break is happening live.

**Two segments to reconcile:** the Ultimate Handoff named **Active Multi-Company Searcher** and **Corporate Talent Developer** as NAILIT's real internal segments used to answer the retention-ceiling concern (both need NAILIT across multiple cycles, sidestepping episodic churn). These aren't in the Hermes lists and should be reconciled before final segment commitment.

## 1.7 — Risks (RAT: Probability × Impact / Cost-of-Validation)

**Risk 1 — "Free is Good Enough" | Score 20 | ROOT.** Users believe YouTube+ChatGPT+friends = 80% of the value, so won't pay. If true, the business model fails. Cheapest to test ($50 landing page), highest impact. **Test this first.** Cannot be dropped.

**Risk 2 — "Episodic Use = No Habit" | Score 8.** Prep is a 2–8 week need, so retention/LTV may be too low for CAC. **Already designed around** via non-expiring credits + the multi-cycle segments — but the design needs validation.

**Risk 3 — "AI Quality Gap" | Score 6.** Is the pack accurate/current/specific enough to trust over Googling? Pipeline is live-tested and the hallucination guard works; the one content defect (story repetition) must be fixed before any broad trust claim.

**Risk 4 — "Feedback Not Worth Paying For" | Score 5.** Is the AI feedback noticeably better than free ChatGPT? This *is* the core product. Cannot be dropped.

**Risk 5 — "Ex-Employee Marketplace" | Score 4 | DROPPED from V1.** Classic marketplace cold-start; saves $50K+ in dev cost; could return as an upsell using *former* employees post-validation.

**Survival math:** unconditionally ~0.8% with nothing validated — but **validating Risk 1 alone lifts it to ~4% (a 5x jump from one cheap test).** That's why everything starts with Risk 1. (Segment 5 adds three stacked risks, RAT-VP-1/2/3; VP-1 is the same root question as Risk 1, with a ready blind-comparison test design — so one interview round at Segment 5 validates both at once.)

## 1.8 — Defensibility, distribution, funding

**Defensibility:** the generation layer isn't defensible against smarter models (assume it commoditizes). The **data layer — the contribution database — gets more defensible every year** because it requires real users and elapsed time that model capability can't shortcut. Even in a worst case, a multi-year dataset of real candidate contributions tied to outcomes is acquisition-grade to recruiting platforms, HR tech, or the AI labs — none of whom can acquire it through model improvement. **The dataset is the asset an acquirer pays for, not the UI.** It's solo-feasible because building the capture mechanism is a one-time narrow code build that then runs itself forever.

**Distribution (for a non-public-facing founder):** the moat needs only a *first* cohort of 20–50 real users, not mass reach — reachable through quiet, asynchronous, written engagement (career-transition subreddits, LinkedIn job-search communities, Discord, alumni networks). No video, no personal brand required. The copilot-reputation collapse means NAILIT can credibly engage in communities now hostile to overlay tools.

**Funding:** raising money to fund distribution before product-market fit is backwards — it funds a story, not an asset. Correct sequence: build the moat infrastructure → seed 20–50 users manually → confirm the conversion mechanic → use *early revenue* (not raised capital) for a fractional growth person → consider raising only once the data flywheel shows compounding signal.

## 1.9 — The ordered action plan (ACT-1 → ACT-8)

1. **ACT-1 — Ship minimal auth** (email + magic link; Clerk or Supabase, decide in a 1-hour session). Highest leverage — unblocks payments, offer-rate email, GDPR-by-user, and the contribution database. *Nothing past this matters until it's done.*
2. **ACT-2 — Diagnose then fix the story-repetition/boilerplate bug** (in parallel with ACT-1; investigation prompt written, run it read-only first). The difference between "runs" and "genuinely good."
3. **ACT-3 — Build the contribution-capture mechanism** (the moat; depends on ACT-1). One-time build, runs itself forever. **Greatest long-term risk if deferred** — every day it's not running is a day of un-accumulable data lost.
4. **ACT-4 — Move off Daytona** to Render/Fly free tier (real always-on host; no paid infra before paying users).
5. **ACT-5 — Resolve OpenAI vs Claude** in a dedicated session; verify real per-session cost against the invoice.
6. **ACT-6 — Wire Stripe checkout + Resend email** (depends on ACT-1).
7. **ACT-7 — UX state-signaling fix** on the module dashboard (cosmetic, spec'd).
8. **ACT-8 — Second independent quality test** on a different JD/CV (not the founder's own), after ACT-2.

**Sequencing:** Week 1: ACT-1 ∥ ACT-2. Week 2: ACT-3, ACT-6 (both need ACT-1). Week 3: ACT-4, ACT-5. Week 4: ACT-7, ACT-8. ~4-week window if smooth; 6 realistic for solo load.

## 1.10 — The 4-week validation program (runs in parallel, point it at Segment 5 first)

Week 1: build the landing page + launch $50 traffic (Risk 1) + recruit and run 15 interviews, prioritizing r/layoffs and "haven't interviewed in years" threads (Segment 5), running the RAT-VP-1 blind comparison inside those sessions. Week 2: code results, re-run RAT, update the validation-debt ledger. Week 3: prototype/route real users through the live pipeline; blind comparison vs ChatGPT vs manual research. Week 4: pricing test (£15/£20/£25 credit-equivalents) → GO/NO-GO. Decision framework: Risk 1 confirmed → KILL or pivot to a segment where free is insufficient; Risk 1 mitigated + Risk 4 passes → ship V1 publicly.

## 1.11 — The honest verdict on NAILIT

**Feasible — conditionally, and the condition is within the founder's control.** The technology works (verified live). The economics are excellent pending the OpenAI/Claude verification. The one real content defect is narrow and fixable. The market shifted in NAILIT's favor (honest-prep positioning). **Survival at 3–5 years hinges on exactly one thing:** whether the contribution database gets built and running as soon as auth ships, rather than being correctly identified in documentation forever and never executed. That is the single greatest long-term risk — not any competitor. **Do this, in order: ship auth, then the contribution mechanism, before anything else** — because nearly every other open question either resolves once that sequence runs, or can only be answered by real usage data.

**NAILIT deep-dive:** `PROJECT-1_NAILIT/NAILIT_MASTER.md` (the full 27-section master + 6 appendices, including the competitor pricing table, the interview kit, API pricing, and the founder's verified answer bank). Supporting: the context-extraction set (`nailit-developer-handoff.md`, `nailit-knowledge-base.md`, `nailit-extraction-ledger.md`, `nailit-audit-report.md`) and the granular history (`NAILIT_COMPLETE_PMD.md`).

---

# ═══════════════════════════════════════════════
# PART 2 — PROJECT 2: PKS (THE INFRASTRUCTURE)
# ═══════════════════════════════════════════════

## 2.1 — What PKS is

A **model-agnostic private AI knowledge system.** Obsidian (plain Markdown, Git-versioned) is the permanent, human-owned source of truth. AI models are interchangeable plug-in reasoning engines. A deterministic safety layer makes it *structurally impossible* for any AI to delete, overwrite, or corrupt the knowledge base. Sensitive data (customer names, contracts) routes only to privately-hosted models on infrastructure the founder controls; non-sensitive work may use cloud models. The design survives models, vendors, and orchestration tools changing — because it depends on interfaces and rules, not on any specific model.

**Governing principle:** *Obsidian stores knowledge. The AI never owns it. AI can suggest; only humans commit.*

## 2.2 — Why it exists

The founder generates large volumes of ideas and documents with AI (Claude, and an agent called Hermes) and needs them stored somewhere durable, private, searchable, and safe from AI corruption — without being locked into any one model, and without customer data ever leaking to a cloud API. The design conversation worked through every layer of this and repeatedly ended with "I can design the next piece if you want" — so PKS takes it from discussion to a concrete, buildable architecture.

## 2.3 — The seven-layer architecture

1. **Knowledge (Obsidian)** — plain Markdown, Git-versioned, READ-ONLY to all AI. The only source of truth. Personal and business vaults physically separated. Never stores secrets.
2. **Retrieval (RAG)** — index + hybrid search; returns only the relevant chunks, never the whole vault; tags each chunk with the sensitivity of its source folder. Model-independent.
3. **Orchestration** — pure routing + policy; holds no knowledge and no model-specific logic. Replaceable (Hermes today, anything tomorrow). "Traffic controller, not driver."
4. **Routing & sensitivity classification** — deterministic rules *first*, cheap model second. Hard-routes anything sensitive to private models only — this is both the performance layer AND the privacy guarantee. Includes data-minimization (replace raw identifiers with abstractions before inference).
5. **Model pool (adapters)** — every model, any provider, behind one identical interface (`generate(task_envelope) → {response, confidence, uncertainty_flags, missing_info}`). Swapping a model = writing one adapter; nothing else changes. Cheap / strong / specialist tiers, private-hosted + cloud-escape-hatch split by sensitivity.
6. **Evaluation & fallback gate** — cheap-first, escalate only if a quality gate fails, with a **hard cap (`max_escalations = 1`)** so escalation can't loop and explode cost. Each stage re-validates against original context to catch cascading errors. Every answer surfaces its own `uncertainty_flags` and `missing_info`.
7. **Safety, sandbox & commit** — defense in depth: OS-level read-only vault + action gateway (create/append only, never delete) + sandbox-only writes + human approval gate + Git rollback + audit log. Code runs in isolated Docker containers. The guarantee is structural (OS permissions), not behavioral (prompt guardrails).

## 2.4 — The core insight (why guardrails alone fail)

The founder's own hard-won conclusion, adopted as the design's backbone: **prompt guardrails reduce risk but cannot guarantee it — only system-level permissions can.** "AI cannot directly touch critical data paths." So the guarantee that AI can't corrupt your knowledge comes from OS-level read-only permissions and Git versioning, not from telling a model "please don't." This is *the* reason PKS is architected the way it is.

## 2.5 — Infrastructure (on the founder's existing Hetzner)

Separate storage from compute: a lightweight orchestration/routing/safety server; a GPU inference server for private models (needed for the strong-reasoning-on-sensitive-data tier); a vector-search service; the Git-versioned vault, read-only-mounted to AI. Inference engines: Ollama (simplest, start here) or vLLM/TGI (higher throughput for team scale). Open models (Llama/Qwen/Mistral/Gemma) hosted privately — safe *because you host them*, not because of who made them.

## 2.6 — The phased build (each phase independently useful)

- **Phase 1 (this week — small, ~80% of the safety value):** Git-versioned Obsidian vault + OS-level read-only-for-AI permissions + an `_Inbox` for drafts. Test that the AI physically *cannot* delete a note. Seed it with NAILIT's knowledge as `Projects/NAILIT/`.
- **Phase 2:** retrieval/index layer (stop loading whole files — biggest performance upgrade).
- **Phase 3:** the adapter interface + one privately-hosted model; prove model-agnosticism by writing a second adapter.
- **Phase 4:** the deterministic sensitivity gate (the privacy guarantee) + data minimization.
- **Phase 5:** evaluation/fallback with the hard escalation cap + the full draft→approve→commit pipeline + audit log.
- **Phase 6:** scale/harden (GPU inference server, job queue, Docker-per-task sandboxes, per-user permissions, encrypted 3-copy backups) — only when the need is real.

## 2.7 — The honest verdict on PKS

The **durable core** (read-only Git-versioned vault + retrieval + deterministic routing/sensitivity gate + adapter interface + sandbox/approval safety layer) is what never changes — build it first and exactly right, then plug in whatever models are best at any moment as fully-replaceable parts. This is a real multi-month engineering effort at full scope, but **Phase 1 is a week's work and delivers most of the safety value immediately.** Strong private reasoning models need real GPU hardware — a genuine cost, worth incurring only when proven, consistent with the portfolio's no-spend-before-need discipline. The hardest part to get right is the evaluation/judge layer — budget the most design attention there.

**PKS deep-dive:** `PROJECT-2_PKS-Knowledge-Infrastructure/PKS_Architecture_Blueprint.md` (full seven-layer spec) and `PKS_Implementation_Plan.md` (phased build with stop-and-verify gates).

---

# ═══════════════════════════════════════
# PART 3 — HOW THE TWO PROJECTS RELATE
# ═══════════════════════════════════════

They are **separate projects** and must stay so — different goals, lifecycles, and risk profiles. Project 1 is a product with a market and customers; Project 2 is durable personal/business infrastructure. They touch at exactly two clean points:

1. **NAILIT's knowledge can live *inside* the PKS vault** as `Projects/NAILIT/` — giving NAILIT a durable memory home instead of scattered chat logs and one-off handoffs. The context-extraction documents already produced for NAILIT are the perfect seed content.
2. **Both may run on Hetzner — but keep them on separate machines.** The standing NAILIT decision (don't co-locate on the box running the orchestrator/bots — memory headroom, blast-radius) applies to PKS too. If PKS's private inference grows to large models on Hetzner, NAILIT's production backend still stays isolated.

**What must NOT happen:** don't let PKS's model-agnostic multi-model ambitions leak into NAILIT's much simpler needs; don't let NAILIT's specific pipeline logic contaminate PKS's deliberately general design.

---

# ═══════════════════════════════════════
# PART 4 — SHARED DISCIPLINE & ASSUMPTIONS
# ═══════════════════════════════════════

## 4.1 — The non-negotiable discipline rules (both projects)

1. **Diagnose before fixing** — always. (The ACT-2 investigation prompt is deliberately written but unrun for this reason.)
2. **Verify on the real running system with real data — every fix, every time.** An AI's self-report that "the fix worked" is not evidence. Multiple times on this project, trusting a self-report meant the fix hadn't actually run.
3. **Never bundle two changes into one session.** Debugging "which of three things broke it" dwarfs the time saved by combining.
4. **Grep for existing definitions before re-running any fix session** — near-miss duplicate function definitions have happened.
5. **No paid infrastructure before real paying users.** Firm rule, not an open question. Free tier until revenue justifies paid.
6. **Treat external AI analysis of "the product" with suspicion until you confirm it was given the *real* architecture** — two Hermes runs already scored an invented product (see below).
7. **The founder's pushback on scope/spend/suspicious scores has been correct every time** — investigate it, don't argue past it.
8. **Local fixes are not deployed fixes** — push, pull, restart, and always specify which state something is in.
9. **Single-source-of-truth documents are explicitly versioned** — mark superseded ones, don't delete but don't read them.

## 4.2 — The external "Hermes" reports (a standing caution)

The founder twice ran NAILIT's concept through an external tool ("Hermes"); it produced a 5.5/10 score and, later, a flattering re-run. **Neither analyzed NAILIT** — both invented a different, simpler product from a one-paragraph prompt (wrong segments, a marketplace NAILIT doesn't have, $19/mo subscription instead of the real credits model, praise for an unbuilt voice feature). **The 5.5 is a real score of a product NAILIT isn't building.** What's reusable from them: the RAT methodology, the retention-ceiling caution (already solved via non-expiring credits), and the competitor scans. The rule going forward: always show the real architecture first; if the segment list they output doesn't match NAILIT's real segments, discard their conclusions and keep only the methodology.

## 4.3 — The "ChatGPT will do this free" question, resolved

There is no current product, free or paid, that does what NAILIT does. A person pasting CV+JD into ChatGPT is doing a worse manual version of one slice of the pipeline. A foundation model improving absorbs *generation quality* — it cannot absorb *first-party data it never had*: real candidates' after-the-fact reports of what they were actually asked. That data exists only because real people used NAILIT. This is exactly why ACT-3 (the contribution database) is the real defense, in both the near and long term.

## 4.4 — Shared open assumptions & caveats

- **GDPR is a legal obligation, not an engineering one.** Both projects handle personal data (candidate CVs; customer records). Architecture supports compliance but doesn't grant it — get qualified review before real EU data flows at scale.
- **Every NAILIT segment and market number is an unvalidated hypothesis** until interviews are run (0/15 conducted).
- **The OpenAI/Claude cost conflict** is unresolved and gates any confident economics claim.
- **NAILIT's content-quality fixes are verified on one case only** (the founder's own CV) — ACT-8 exists to test generalization.
- **Some competitor pricing figures conflict between sources** — verify live before using any in investor/public materials.

---

# PART 5 — WHAT TO DO NEXT (THE WHOLE PORTFOLIO, RANKED)

**This week:**
1. NAILIT: pick the auth provider (1-hour decision session), then start ACT-1 in a fresh session.
2. NAILIT: run the ACT-2 investigation prompt (read-only, diagnose-only).
3. NAILIT: build the landing page for Week 1 validation; draft the interview guide (Appendix B of the deep-dive); line up 5 Segment-5 interviewees.
4. PKS: build Phase 1 — Git-versioned vault + OS read-only-for-AI + `_Inbox`. Small, and it makes your knowledge structurally safe immediately. Seed it with the NAILIT docs.

**Next 30 days:** finish NAILIT ACT-1/2/3; run 15 interviews (Segment 5 first) + the $50 traffic test; hold the OpenAI/Claude decision session; move off Daytona.

**Next 90 days:** NAILIT ACT-6/7/8; first 20–50 real users via quiet written outreach; first contribution rows accumulating; begin retention measurement. PKS Phases 2–3 as capacity allows.

**Year 1+:** NAILIT contribution database reaches visibly-valuable volume; revenue covers the (near-zero) operating cost; optional upsells (voice, ex-employee review) only if validation supports them. PKS matures into the durable knowledge layer for both the founder's work and NAILIT's development.

**The one sentence for the whole portfolio:** ship NAILIT's auth then its contribution mechanism before anything else, build PKS Phase 1 alongside it this week, and treat every other open question as either downstream of those two moves or answerable only by real usage — because the moat is the one thing whose cost of delay compounds and can't be recovered.

---

## Document map

- **This file** — full portfolio orientation, both projects.
- `_INDEX/MASTER_INDEX.md` — the folder map.
- **Project 1:** `PROJECT-1_NAILIT/NAILIT_MASTER.md` (authoritative deep-dive) + context-extraction set + granular history.
- **Project 2:** `PROJECT-2_PKS-Knowledge-Infrastructure/PKS_Architecture_Blueprint.md` + `PKS_Implementation_Plan.md`.
