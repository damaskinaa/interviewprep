# NAILIT — Unified Master Document

**Status:** Single source of truth. Supersedes NAILIT_PMD.md, NAILIT_COMPLETE_PMD.md, NAILIT_HANDOFF.md, NAILIT_ULTIMATE_HANDOFF.md, NAILIT_ADDENDUM_DEFENSIBILITY_FEASIBILITY.md, and NAILIT-Master-Research.md.
**Generated:** June 23, 2026. **Updated:** July 3, 2026 — integrated a deep NMT value-proposition run on Segment 5 (new Section 11a) and a Firecrawl-sourced competitive analysis (updates to Section 9, new Section 9a, reconciled Appendix A).
**Reading time:** ~55 minutes end-to-end. Section 0 (philosophy) and Section 19 (ordered action list) still give 80% of the picture in 5 minutes; add Section 11a for the current best segment-specific hypothesis.

### Revision log
- **July 3, 2026:** absorbed `2026-06-23-craft-value-proposition-result.md` (deep NMT analysis, Segment 5) and `competitive-analysis-2026-06-23.md` (Firecrawl-sourced pricing/competitor scrape). Added Sections 9a and 11a. Added Wedge 6. Updated Appendix A with a flagged pricing conflict (Big Interview, Final Round AI) between two independently-sourced analyses — needs a live pricing-page check before external use. Added VP-1/2/3 to the validation debt ledger.
- **June 23, 2026:** initial compilation from `NAILIT_ULTIMATE_HANDOFF.md`, `NAILIT-Master-Research.md`, and `answer_bank_condensed.txt`.

---

## Table of contents

**Part 1 — Orientation**
- 0. The governing philosophy
- 1. What NAILIT actually is
- 2. The founder — identity, background, lived context
- 3. Current state — built / broken / decided-not-built

**Part 2 — Economics and Architecture**
- 4. The economics
- 5. Stack details and architectural decisions
- 6. The open architecture question — OpenAI or Claude

**Part 3 — Market and Competition**
- 7. Market context
- 8. The 2026 market split — honest prep vs cheating overlays
- 9. Competitive landscape (June 2026)
- 9a. The real incumbent + PARITY/Hermes reconciliation (NEW)
- 10. Competitive wedges — what NAILIT uniquely does

**Part 4 — Segments, Risks, and Validation**
- 11. Segments — what's hypothesised
- 11a. Segment 5 deep-dive — full NMT analysis (NEW)
- 12. RAT — top 5 risks
- 13. Validation debt ledger
- 14. Survival math
- 15. Blind spots

**Part 5 — Defensibility, Moat, and Distribution**
- 16. The defensibility thesis — the moat is the data
- 17. Distribution and GTM for a solo, non-public-facing founder
- 18. On funding

**Part 6 — The Ordered Action Plan**
- 19. ACT-1 through ACT-8 with rationale
- 20. Sequencing — parallel vs serial
- 21. 4-week external validation roadmap

**Part 7 — Hard-Won Lessons**
- 22. The deployment debugging saga
- 23. Project discipline rules — the non-negotiables
- 24. The two external Hermes reports

**Part 8 — Verdict and Forward Roadmap**
- 25. The honest final feasibility verdict
- 26. Forward roadmap — 7 days / 30 days / 90 days / Year 1 / Years 2–3
- 27. Final warnings

**Appendices**
- A. Competitor pricing reference (June 2026)
- B. Interview kit (validation)
- C. API pricing reference (June 2026)
- D. File reference index
- E. The founder's full answer bank
- F. Glossary

---

# PART 1 — ORIENTATION

## 0. The governing philosophy (read this first)

This project has one governing rule, stated and re-stated dozens of times across this build: **build slow, build solid, build for scale — not rushed, and not "lean" in the sense of "thin."** The founder explicitly rejected the idea that this should be a thin wrapper around what a person could get from ChatGPT or two hours of Glassdoor research. Every architectural decision below traces back to that standard.

The project also has an earned discipline: **diagnose before fixing, verify on a real live call before trusting any report (including AI self-reports), and never bundle two changes into one session.** This discipline was learned the hard way, repeatedly, across this build (see Section 22 for the receipts). Respect it.

The one sentence everything else hangs off: **ship auth, then ship the contribution-capture mechanism immediately after — before any further UX polish, additional external validation reports, or distribution planning** — because nearly every other open question in this project either resolves itself once that sequence runs, or cannot be resolved by any further analysis and requires real usage data instead.

---

## 1. What NAILIT actually is

An AI-powered **interview intelligence platform**. User inputs CV + job description + relevant experience. The platform:

1. **Researches the target company** — values, available interview reports, open-source information.
2. **Generates a full prep pack** from that research — company intelligence, role decoding, candidate-CV mapping, gap analysis, full Q&A by interview round.
3. **Runs a mock interview** based on the prep pack.
4. **Gives feedback** (via an AI coaching persona called **Lua**), with the ability to refine answers across attempts.
5. **Planned, not built:** voice-based mock interview (LiveKit + Deepgram + Cartesia, ~£1.20/session).
6. **Planned, not built (V2/extras):** optional connection to an *ex*-employee of the target company, or to an interview coach, for human feedback after the AI mock — explicitly an upsell, not a dependency, and explicitly former employees (e.g., recently laid-off professionals) rather than current staff, to avoid conflict of interest.

**The long-term differentiator, and the only thing that matters for years 3–5:** a growing, first-party database of real candidates reporting which questions they were *actually* asked, tagged by company/role/round, after real interviews. **This is the moat.** It does not exist yet — it is fully designed but not built (see Section 19, ACT-3).

---

## 2. The founder — identity, background, lived context

The person building this is the same person the product is built to serve. That alignment matters because every product judgment call upstream of validation has been made by someone who can model the user from the inside.

**Role identity:** Operations Manager / Programme Manager / Team Lead, company-agnostic. 8 years cross-functional global delivery, leading a team of ~10 across EMEA / NA / APAC on the Meta Partnership account at Cognizant.

**Operating pattern (self-described and consistent across all the metrics below):** diagnose the root constraint in unclear systems, leave them measurably stronger.

**Verified metrics that exist in the answer bank as real evidence — not as resume polish:**
- **34% backlog reduction** — cross-regional EMEA/NA/APAC handover system designed with no formal authority over the regions; co-designed with regional leads so two initially-sceptical leads became advocates via shared data.
- **77% → 93% SLA** — found a hidden calc error (wrong denominator), rebuilt from 3 months of raw data, also discovered 40% of "closed" cases had reopened and were distorting the metric. Chose transparency over a quiet fix.
- **40 hrs/week saved** — queue redesign plus automated routing, response time down ~1 hr/case.
- **14% quality gain** — time freed by the queue redesign reinvested into quality work.
- **2 SLAs renegotiated, penalties eliminated, ~15% efficiency gain** — solo 72-hour KPI gap analysis when manager on leave with no playbook. Used Six Sigma: defined the problem per KPI, delegated deep-dives, ran 5 Whys. Manager subsequently asked them to lead the client meeting.
- **CSAT response 10% → ~50%** — added a direct survey link at case closure.
- **Agent → SME promotion** — diagnosed a skill-vs-will gap, built weekly QA plus reverse shadowing, hit top-5 productivity in 3 months.
- **23% KPI attainment gain** (from 8 met to 12 met) — workflow redesign plus sustained coaching.

**Self-known weakness (with the fix already in place):** bias toward execution over delegation — became a bottleneck. Fixed via mapping responsibilities and weekly SME planning. Earlier-career version: difficulty saying no — same fix.

**Why this matters for NAILIT:** the founder is a senior operations PM with quantified, story-rich experience — i.e. *exactly* the candidate NAILIT's pipeline has to handle well. The fact that the live quality test (Section 3) used a Google PM scenario and *did* correctly extract real metrics like "34% backlog reduction" from this answer bank is not a coincidence; the founder built the product against their own data and can spot a hallucinated number instantly. This is a structural advantage almost no consumer SaaS founder has.

---

## 3. Current state — what is built, what is broken, what is decided-but-not-built

### What is built and verified end-to-end by direct inspection (not self-report)

**Architecture:** Six-module pipeline:
1. Company Intelligence
2. Role Intelligence
3. Candidate Profile
4. Gap Map
5. Interview Strategy
6. Prep Pack

Plus **Module 7 (Answer Generator)** and **Module 8 (Mock Interview)**, gated to unlock only after the Prep Pack completes.

**Verified live on a real session:** Google / Program Manager, `sess_20260622_152508_d205dd18`. Confirmed working:
- Full pipeline runs end-to-end and produces a complete Prep Pack.
- **CV-evidence extraction works** — correctly pulls real metrics (e.g., "34% backlog reduction," "77%→93% SLA") from the candidate's real CV/answer bank.
- **Hallucination guard works** — a validator strips any generated number that doesn't trace back to the candidate's actual source documents; confirmed by direct test (kept a real "31%," stripped a fabricated "77 percent" with no CV basis).
- **Forbidden-claims detection works** — correctly flagged "I have direct experience as a Senior Program Manager" as something the candidate must not say, given their real background.
- **Gap detection works** — correctly identifies real weaknesses without inventing false competence.
- **Lua (the AI coaching layer)** returns a complete, correct 10-field response shape.
- **22 Lua endpoints are authenticated.**
- **Atomic job creation** prevents race-condition duplicate runs.
- **Out-of-order module runs** are rejected at the HTTP layer with a clear error.
- **GDPR delete/export endpoints** work and actually remove data.

### What is broken — confirmed by direct inspection, not assumption

- **Story repetition.** Across ~24 generated Q&A answers in the test session, roughly half defaulted to the same single story (one specific metric) regardless of question fit, even when it was a poor match (e.g., forced into a question about "influencing software tool development"). The candidate's answer bank had ~17 distinct stories available; the pipeline's `story_inventory` artifact only contained 2 of them.
- **Boilerplate leak.** The exact same disclaimer paragraph appeared verbatim, unmodified, at the end of roughly 15 different answers. A careful reader would notice this immediately and lose trust in the rest of the pack.
- **Root cause not yet found.** An investigation prompt is written (Section 19, ACT-2) but has not been run. The fact that *other* modules (Candidate Profile, Gap Map) did NOT show this defect is strong evidence the bug is narrow — confined to the answer-generation/story-selection step — not a sign the architecture is broken.

### What is decided but not built at all

- **User authentication.** No login, no accounts, no session ownership. This is the **single highest-leverage blocker** — it gates payments, GDPR-by-user, the offer-rate follow-up email, and the entire contribution-database moat, simultaneously.
- **The contribution-capture mechanism** (the actual moat). Fully spec'd, zero rows exist.
- **Payment flow.** Stripe webhook code exists and is tested for signature validation; no real Stripe products have been created in the dashboard; no checkout UI exists.
- **Real email delivery.** `send_email()` is a console-log stub; no provider (Resend recommended) is wired.
- **Voice mock interview.** Researched, explicitly deferred to after the text product is validated with paying users.
- **UX state-signaling on the module dashboard.** A "DONE" module currently shows its original action button still gold/primary next to "View Results," which is confusing — see Section 22 for the exact fix spec.

### Repository and stack snapshot

- **Repo:** `https://github.com/damaskinaa/interviewprep`, `main` branch.
- **Frontend:** Next.js on Vercel.
- **Backend:** FastAPI, currently in a Daytona sandbox (which is fragile — see Section 22).
- **Database:** SQLite locally, with a built-but-unexercised Postgres/Redis abstraction for future scale.
- **LLM provider:** OpenAI (this contradicts the original modelling assumption — see Section 6).
- **Research provider:** Tavily.

---

# PART 2 — ECONOMICS AND ARCHITECTURE

## 4. The economics — modelled, not yet verified against real OpenAI costs

**Per-session AI cost** is approximately **£0.78** — but this was modelled against a Claude Haiku/Sonnet split, *not* against the OpenAI calls the code actually makes today. This figure needs re-verification (see Section 6).

**Revenue per session: £49–£199** under a **credits-based pricing model**:

| Plan | Price | Sessions | Notes |
|---|---|---|---|
| Free | £0 | 1 lifetime | Trial / acquisition |
| Starter | £89 | 3 | Credits never expire |
| Monthly | £49 | 5 + rollover | Lowest commitment |
| Premium | £199 | 10 | Credits never expire |

**Why credits-not-subscription was a deliberate choice:** interview prep is episodic — credits that don't expire sidestep the "cancel after 3 months" problem that kills generic subscription products in this category. This is exactly the structural answer to Risk 2 ("Episodic Use = No Habit") that competitors keep failing on (see Section 9 for the Final Round AI billing-complaint pattern this protects against).

**Gross margin per session at the modelled £0.78 cost:**
- Free: -£0.78 (acquisition cost)
- Starter: ~£28.85 per session (88% margin after AI cost)
- Monthly: ~£9.02 per session (92% margin)
- Premium: ~£19.12 per session (96% margin)

The economics are excellent *pending* resolution of the OpenAI/Claude question. If real OpenAI cost-per-session is meaningfully higher than the modelled £0.78, the margin compresses but stays positive at all tiers. If it's lower, even better.

---

## 5. Stack details and architectural decisions

### Confirmed file inventory
- `agent_v2.py` — primary pipeline orchestrator, currently uses `from openai import OpenAI` exclusively.
- Six pipeline modules (Company Intelligence → Role Intelligence → Candidate Profile → Gap Map → Interview Strategy → Prep Pack).
- Modules 7 and 8 (Answer Generator, Mock Interview) gated on Prep Pack completion.
- Lua (AI coaching layer) — 22 authenticated endpoints, 10-field standard response shape.
- Atomic job creation layer (prevents race-condition duplicates).
- HTTP-layer validation rejecting out-of-order module runs.
- GDPR delete/export endpoints — functional, tested.
- Stripe webhook signature validation — present and tested, but no Stripe products defined yet.
- `send_email()` — console-log stub only.

### Key architectural decisions made and held
- **SQLite locally + Postgres/Redis abstraction built but unexercised.** Avoids paid infra spend before paying users exist, while keeping migration path clean.
- **Daytona for current deployment.** It's a dev sandbox, not a host — explicitly understood as temporary (see Section 19, ACT-4 and Section 22 for why).
- **Tavily for research, not custom scraping.** Avoids brittle scrape-maintenance burden for a solo founder.
- **Two-layer answer validation: hallucination guard (numbers must trace to source) and forbidden-claims detection (must not assert experience the candidate doesn't have).** This is what gives NAILIT a defensible *quality* claim — generic ChatGPT use produces neither guarantee.
- **Lua as a named coaching persona with consistent 10-field response shape.** Both a UX device and a structural constraint that prevents the feedback step from drifting into vague encouragement.

---

## 6. The one open architecture question — OpenAI or Claude (UPDATED with June 2026 pricing)

**The finding that triggered this question:** `agent_v2.py` imports `from openai import OpenAI` exclusively. There is **zero Anthropic SDK reference anywhere in the backend.** This directly contradicts the unit-economics modelling, which assumed a Claude Sonnet 4.6 / Haiku 4.5 split.

**June 2026 published API pricing** (per million tokens, input / output):

| Tier | Anthropic | OpenAI |
|---|---|---|
| Frontier flagship | Opus 4.7 / 4.8: $5 / $25 | GPT-5.5: $5 / $30 |
| Workhorse / balanced | **Sonnet 4.6: $3 / $15** | **GPT-5.4: $2.50 / ~$14**; GPT-5.3-Codex: $1.75 / $14 |
| Fast / cost-control | **Haiku 4.5: $1 / $5** | GPT-5 mini: ~$0.25 / – |

**Key cost levers that change the calculus:**
- **Prompt caching: 90% off cached input tokens** on Claude (cached input on Sonnet 4.6 = $0.30/M, vs $3/M base). For a pipeline like NAILIT where company intelligence and the candidate's CV remain stable across many module runs in one session, this is a *massive* discount and was likely the implicit assumption behind the £0.78 modelled cost.
- **Batch API: 50% off** on both Anthropic and OpenAI for non-real-time work.
- **Context: 1M tokens at standard pricing on Sonnet 4.6, Opus 4.7/4.8** — no long-context surcharge. Useful if you ever fold the full candidate answer bank, full company research, and full role analysis into one stable prefix.
- **GPT-5.2/5.4 also offers cached input pricing** ($0.175/M for GPT-5.2), and OpenAI has cached pricing on GPT-5.5, GPT-5.4, and GPT-5.3-Codex.

**What the decision now looks like, concretely:**
- **Option A: Stay on OpenAI.** GPT-5.4 input is cheaper than Sonnet 4.6 input ($2.50 vs $3.00); output is comparable. Cached pricing favours OpenAI on input. Re-run the unit-economics model with real OpenAI invoices from the live session and adjust the £0.78 figure.
- **Option B: Migrate to Claude.** Sonnet 4.6 plus prompt caching produces the cheapest *cached* prefix cost in the industry ($0.30/M) — which suits NAILIT's pipeline shape (stable per-session context, many module calls). Plus the original modelled split was Haiku+Sonnet, which is the lowest-cost path given the modelling.
- **Option C (worth considering): Mixed routing.** Cheap classification / routing on Haiku 4.5 ($1/$5) or GPT-5 mini, frontier reasoning on Sonnet 4.6 or GPT-5.4 only where it earns its keep. This matches what the rest of the industry is doing for production AI agents.

**Do this as a single, dedicated, non-bundled decision session.** Don't bundle it with any other change. The principle of "never two changes per session" applies here. Until resolved, treat the £0.78/session figure as *modelled, not verified*.

---

# PART 3 — MARKET AND COMPETITION

## 7. Market context — size, growth, structural shift

### Interview prep market (overall)
- **Market size (2025):** $3.8 billion.
- **Projected (2034):** $9.7 billion.
- **CAGR:** 10.9%.
- *Source: Dataintelo market report.*

### AI interview software (subset of the above)
- **Market size (2024):** $200 million.
- **CAGR:** 24.2% (2026–2033).
- *Source: LinkedIn industry analysis.*

The AI-specific segment is growing **~2.2x faster** than the overall market. The structural shift is away from video libraries (Big Interview) and toward AI-native tools.

---

## 8. The 2026 market split — honest prep vs cheating overlays (CRITICAL POSITIONING)

This is the single biggest market-structure change in the last 12 months and it directly favours NAILIT.

**The AI interview tool market split clearly in 2025–2026 into two categories:**

1. **Coaches (honest prep)** — practice-mode tools used *before* the interview. Mock interview loops, structured rubric scoring, pattern feedback. NAILIT's category. Includes Revarta, Pramp, Big Interview, Google Interview Warmup, Hello Interview, InterviewBuddy, Yoodli, NAILIT.

2. **Copilots (live overlays)** — real-time tools used *during* live interviews. Transcribe the interviewer's audio. Generate answers in real time. Render them in a translucent window invisible to the interviewer. Includes Cluely, Final Round AI's stealth mode, Sensei Copilot, Parakeet AI, CoPilot Interview, Verve. Typical pricing $90–$488/month.

**The reputational tide is moving against the copilot category, fast:**
- Final Round AI Trustpilot data (June 2026): rating now 3.9/5 across ~260 reviews, with one analysis showing **40% negative** out of 100 reviewers — billing complaints, refund denials, $249–$488 auto-renewals without notice, "3-day money-back guarantee" effectively unusable, copilot freezing mid-interview, hallucinated answers.
- Recent Trustpilot reviews (June 2026) describe charges of nearly $500 for services that "did not function properly and continued billing after I had requested cancellation," and language like "running a scam disguised as a service."
- **Reddit moderators on r/cscareerquestions have started pinning warnings on overlay-tool promotion threads** — a leading indicator that the platform's incentives have shifted from amplifying these tools to flagging them.
- New independent reviews explicitly frame the choice as "honest prep vs stealth cheat" and recommend closing the copilot before the round starts.

**Why this matters for NAILIT's positioning:**
1. The honest-prep category is now ethically distinct from the overlay category in the buyer's mind — and the overlay category is getting a worse reputation by the month.
2. NAILIT's structural choices (no live copilot, no stealth mode, transparent credits pricing that never expires, hallucination guard, GDPR delete/export) put it cleanly on the honest-prep side without having to argue the case in copy.
3. The non-expiring credits model is the *literal opposite* of the auto-renew $249–$488 trap that's generating Final Round AI's negative review pile.
4. Distribution-wise, this means NAILIT can credibly engage in the same communities where mods are now hostile to overlay promotion — career-transition subreddits, LinkedIn job-search groups — without being flagged.

**This is a tailwind that did not exist when NAILIT's earliest planning was done.** Update the positioning to lean into it: "honest prep, transparent pricing, your data is yours."

---

## 9. Competitive landscape — full inventory with June 2026 updates

### The top 5 most relevant direct competitors

#### Big Interview ($79/mo or $349/yr — updated)
- 2M+ users, 170+ video lessons.
- Curriculum is well-built and actually teaches frameworks (STAR, behavioural types).
- AI feedback shallow ("be more specific"). NOT company-specific. No voice mock.
- "Video library you also pay for AI feedback on."
- **Threat: MEDIUM** — large but not innovating on AI.

#### Four-Leaf ($5–20/mo)
- All-in-one: AI mocks, resume, cover letter.
- Flexible 5-day pass ($5).
- Generic, not company-specific.
- **Threat: HIGH** — aggressive pricing, product is "good enough" for some segments.

#### Yoodli ($25/mo)
- Best AI feedback on *speaking* (filler words, pacing, tone).
- NOT interview-specific — no company research, no industry questions.
- Limited to 5 free roleplays.
- **Threat: MEDIUM** — could pivot to interview prep easily.

#### Road to Offer (Free + paid)
- 7-dimension AI grading, Voice Mode, Learning Mode.
- Strongest AI case-interview experience.
- Consulting-only.
- **Threat: LOW for NAILIT's segment** — different segment — but the model for what good AI feedback looks like.

#### Revarta (NEW — added June 2026 — closest philosophical competitor)
- Behavioural and leadership interview coach.
- Built by a former hiring manager (1,000+ interviews at Google, Amazon, Adobe).
- Calibrated against "what hiring managers actually assess" — the "question behind the question" — explicitly rejecting "agreeable validation."
- Positions itself as the only coach calibrated by a hiring manager who's run 1,000+ interviews.
- **Threat: HIGH** — this is the most direct philosophical overlap with NAILIT (rigorous, prep-focused, not generic). The competitive question becomes: does Revarta have company-specific intelligence and a candidate-CV-mapping layer? Based on public material, no — it's a hiring-manager-perspective coach, not a company-intelligence pipeline. That's NAILIT's wedge against it.

### The two-sided market dynamics
ChatGPT / Claude (Free–$20/mo) — generic, knowledge cutoff, inconsistent grading. **Threat: CRITICAL** — this is the #1 competitor in users' minds. Most try this first.

### Live-copilot category (mostly NOT NAILIT's competitor — different category)
- **Final Round AI** ($90–$148/mo, up to $488/mo "God Mode") — 10M users claimed, 17–40% negative review rate depending on cut, billing complaints generating disputes and bank chargebacks (see Section 8 above).
- **Cluely** — viral mid-2025 launch, ~753K monthly visits, brand awareness leader.
- **CoPilot Interview** — free tier + low-cost paid plans.
- **Sensei Copilot** — content-marketing moat (mostly off-strategy "excuses to skip work" content).
- **Parakeet AI** ($74.90/mo) — technical interview focus.
- **Verve (verveai.io)** — $20–40/mo range, structured coaching workflows.
- **OphyAI** ($148–488/mo) — real-time AI copilot during interviews.

These are tracked here mainly so future positioning copy can credibly contrast NAILIT's category against them — not because they compete for the same user-need.

### Practice-mode tools at lower price points
- **Interview Sidekick** — $10/mo premium, generous free plan, 10,000+ industry-based questions. Aggressive price anchor.
- **InterviewBuddy** — $29–99/mo, AI-powered mock interview prep, candidate-facing.
- **Pramp / Google Interview Warmup** — free supplements, useful for early-stage prep but not competitors at the pack-generation level.

### Free / "good enough" pile (the ROOT competitive risk — see Section 13)
- **ChatGPT / Claude** (free–$20/mo) — versatile but generic, no real-time company research.
- **YouTube** — partial (some experience reports), no feedback loop.
- **Glassdoor** — partial, stale, raw Q&A dump.
- **University career services** — quality varies, hard to access at scale.

### Competitor weaknesses in NAILIT's specific direction (gap-returner / career-changer / non-native speaker focus)

*Source: Claude Code PARITY analysis + Firecrawl-sourced reviews.*

- **LinkedIn Interview Prep (Premium):** no gap narrative support, no confidence scaffolding, "tailoring" is JD-keyword-matching not actual company intelligence.
- **Big Interview:** doesn't address how the interview landscape has changed since the user last interviewed, no AI screening prep, feedback doesn't help understand what modern interviewers look for vs. 5+ years ago.
- **Exponent:** explicitly tech-only — gap-returners in finance, marketing, ops, consulting, general management can't use it.
- **Glassdoor Q&A:** raw data, no interpretation, no guidance for rusty interviewers on how formats have changed.
- **ChatGPT:** stale company-specific data (knowledge cutoff), no delivery feedback, robotic-when-memorized answers.
- **Huru.ai:** technical bugs (broken QR, LinkedIn import failures), Trustpilot 3.4/5, sessions interrupted or fail to start, no company-specific research.
- **Career coaches (human):** $170/hr average — prohibitive, availability issues, advice can be outdated, no scalable practice.

**Key finding from new-entrants scan (2024–2026):** no product launched in this window specifically targets gap-returners or positions company-specific interview intelligence as its core value. **NAILIT's wedge is still open.**

---

## 9a. The real incumbent, and two findings that sharpen the wedge (NEW — from the PARITY/Hermes reconciliation, June 23 2026)

A second, more rigorous competitive pass (Claude Code's "PARITY" agent, cross-checked against a Hermes run) surfaced three findings that the inventory above doesn't fully capture. These come from a dedicated session that explicitly reconciled where the two analyses agreed, disagreed, and where one caught something the other missed.

### The missing competitor: "Do nothing / go in blind"

**PARITY's competitor table only covers named tools. It's missing the most important competitor for Segment 5 specifically: doing no structured prep at all.** For gap-returners with an interview in a few days, "go in blind, wing it, hope experience carries the day" is the real default — not ChatGPT, not Glassdoor. This matters because **the default-behaviour competitor sets the switching-cost floor.** If a candidate's real alternative is zero-effort and zero-cost, the bar NAILIT has to clear is different than if the alternative is "spend $25/mo on Yoodli." Add "do nothing" to every competitor table used for pricing or positioning decisions going forward.

### Glassdoor isn't just stale — it's actively managed

The wedge-1 framing in Section 10 below said Glassdoor is "stale, crowd-sourced." That understates it. **68% of HR professionals admit to actively managing their company's reputation on review platforms** (2023 Journal of Management study, cited via thecscafe.com's investigation into Glassdoor). Reviews can be flooded with positive submissions same-day, and there is no reliable way for a candidate to date or trust what they're reading. This is a stronger and more specific claim than "outdated" — the research layer gap-returners currently rely on is **partially adversarial**, not just imperfect. This directly strengthens NAILIT's data-sourcing differentiation and should replace the softer "stale" language in outward-facing copy.

### The AI-detectability problem — a reason generic AI prep actively backfires

A Quora thread on LinkedIn's AI interview-prep tool surfaced a finding neither the original Hermes run nor PARITY had fully weighted: **hiring managers report they can tell when a candidate's answers were generated by generic AI, and penalise it.** ("Interviewers love originality and can easily make out ChatGPT-type responses and don't appreciate them.") This is a direct, specific answer to *why* generic AI prep tools fail Segment 5 in particular: gap-returners already lack confidence, reach for ChatGPT or LinkedIn's tool to write answers, produce something that reads as scripted and generic, and get flagged as inauthentic — the tool that was supposed to help creates a new risk. **This belongs in NAILIT's wedge messaging**, not just the risk register: the hallucination guard and forbidden-claims layer (Wedge 2) don't just prevent fabrication, they keep answers grounded in the candidate's *actual, specific* experience — which is also what keeps them from reading as generic AI output.

### The three-way silo, named explicitly

Where Hermes described the gap as "generic feedback," PARITY sharpens it into a **three-way silo that nothing currently bridges**:
- **Yoodli / Huru** = delivery only (how you speak — pacing, filler words, tone).
- **ChatGPT / LinkedIn / Big Interview** = content only, and generic (what to say, but not calibrated to any specific company).
- **Exponent / human coaches** = content, but tech-only or not scalable.

**Nobody combines all three — delivery + content + company calibration — in one flow.** This is a sharper positioning frame than "generic feedback" and should replace that language in pitch materials (this refines, but doesn't replace, Wedge 3 below).

### Combined layer map (synthesis of both competitive analyses)

| Layer | Finding |
|---|---|
| **Default behaviour** | "Do nothing / go in blind" — the real incumbent; sets the switching-cost floor |
| **Research layer** | Glassdoor Q&A (static, actively manipulated, unsynthesised) + ChatGPT (stale, generic, no delivery layer) |
| **Practice layer** | Big Interview + Huru (generic AI mock, no company calibration) + Yoodli (delivery only, no content) |
| **Live-assist layer** | Final Round AI (real-time copilot; billing traps; no company intel; AI-detectable) |
| **Human layer** | Career coaches ($170–500/hr average; not scalable; often outdated advice) |
| **Company-specific layer** | Exponent (Google/Amazon/Microsoft static guides; tech only) + LinkedIn (JD keyword matching, not real research) |

**The gap every layer leaves open:** no tool in any layer does all four of — (1) live company research synthesis, (2) CV-to-company fit mapping, (3) company-calibrated content feedback, (4) gap-narrative scaffolding — in a single fast flow. NAILIT is the first attempt at all four together. The closest competitor (Final Round AI) does 0 of 4. LinkedIn does a weak version of 2.

### The Red Queen window — stated as a number

**Both analyses agree on the same window: 12–18 months** before a large incumbent (LinkedIn or OpenAI, most plausibly) ships company-specific research synthesis as a feature. Past that point, the *generation* layer commoditises — consistent with the defensibility thesis in Section 16. **The moat is not the feature, it's the data flywheel** (session data → better calibration → better outcomes → more users) plus the trust built specifically with gap-returners in that window. This is additional, independently-sourced confirmation of the ACT-3 urgency already established in Section 19 — two separate analyses landed on the same conclusion by different routes.

*Sources for this subsection: LinkedIn Interview Prep AI, Big Interview, Exponent, Final Round AI Trustpilot analysis (rainaiservices.com), Huru review (interviewsidekick.com), Yoodli review (resumehog.com), Revarta's "ChatGPT can't prepare you" post, Glassdoor-manipulation study via thecscafe.com, career coach pricing (careersidekick.com), ClavePrep layoff-prep post. Compiled via Claude Code's PARITY agent, cross-checked against a Hermes run, June 23 2026.*

---

## 10. The competitive wedges — what NAILIT does that nothing else does

### Wedge 1 — Live company intelligence (UNIQUE)
No competitor synthesises live company intelligence into a prep pack.
- Glassdoor = **not just stale — actively managed.** 68% of HR professionals admit to managing their company's reputation on review platforms (see Section 9a). The research layer candidates currently rely on is partially adversarial, not just outdated.
- LinkedIn = JD keywords.
- Exponent = static guides for Google/Amazon only.
- ChatGPT = knowledge cutoff.
- Final Round AI, Huru, Yoodli, Big Interview = don't pull company intelligence at all.

**The gap:** nobody researches how Company X interviews *today* (recent reports, current competency frameworks, post-2023 AI screening formats) and delivers it in synthesised, actionable form.

### Wedge 2 — Candidate-evidence-locked answer generation (UNIQUE, and provably so)
The hallucination guard plus forbidden-claims detection is structurally rare:
- Generic ChatGPT will happily invent metrics.
- Other AI prep tools optimise for generic STAR templates.
- **NAILIT only allows numbers and claims that trace back to the candidate's own source data.** This was tested live and works (stripped a fabricated "77 percent" with no CV basis; kept a real "31%").

This is the difference between *generative-feeling* output and *true-to-candidate* output. It's also the layer that makes NAILIT genuinely safer to recommend to a real candidate going to a real interview.

### Wedge 3 — Delivery + content + company context in one flow (UNIQUE)
- Yoodli and Huru coach HOW you speak.
- ChatGPT, LinkedIn, Big Interview coach WHAT to say (generically).
- Exponent addresses content for tech roles only.
- **Nobody does all three with company-specific calibration in one session.**

### Wedge 4 — The contribution database (FUTURE, the actual moat)
Not built yet (ACT-3). The mechanically precise distinction from the rest of the field: a foundation model getting better over time absorbs *generation quality* (better-written answers). **It cannot absorb first-party data it never had access to** — specifically, real candidates' after-the-fact reports of what they were actually asked. That data only exists because real people used NAILIT specifically. See Section 16 for the full defensibility argument.

### Wedge 5 — Pricing structure that respects episodic use (STRUCTURAL)
Non-expiring credits at £49–£199. Compared with Final Round AI's auto-renew $249–$488 trap, Big Interview's $349 annual upfront, or Four-Leaf's $20/mo subscription that retains zero value once you've got the job. Credits that survive the job-hunt cycle remove the structural reason most users churn. This isn't marketing copy; it's a unit-economics fix.

### Wedge 6 — Answers that don't read as AI-generated (NEW — June 23 2026)
Hiring managers report they can detect generic-AI-written interview answers and penalise candidates for them (see Section 9a). This means generic AI prep tools don't just fail to help — for a low-confidence gap-returner reaching for ChatGPT or LinkedIn's tool, they can actively *hurt* by producing scripted, detectable answers. NAILIT's evidence-locked generation (Wedge 2) — every answer traces back to the candidate's own specific, real experience — is structurally the *opposite* of generic AI output. This wedge is a direct product-level answer to a validated failure mode of every free/generic alternative, and should be named explicitly in messaging: not just "more accurate," but "sounds like you, because it's built only from what you actually did."

---

# PART 4 — SEGMENTS, RISKS, AND VALIDATION

## 11. Segments — what's hypothesised, with the Hermes caveat

**Important framing first.** Two separate prior efforts produced two different segment lists. Both are **hypotheses, not validated user research.** The Ultimate Handoff was explicit that earlier external analyses ("Hermes" runs) invented segments without actually being given NAILIT's real architecture or pricing model, so segment claims from those runs need to be treated as candidate-segments-to-test, not verified-user-truth.

### Segment list A — from the Mac-run initiative.md (earlier)
1. **FAANG / Big Tech Aspirant** — SOM ~20K users, ~$1.1M ARR Y1.
2. **Lateral Mover** — SOM ~16K users, ~$912K ARR Y1.
3. **Rejection Recoverer** — SOM ~8K users, ~$456K ARR Y1.
4. **Non-Native English Speaker** — SOM ~12K users, ~$432K ARR Y1.
5. **Career Switcher** — SOM ~6K users, ~$342K ARR Y1.

### Segment list B — from the more recent Hermes+Claude Code NMT pipeline run
The five segments below come with TAM/SAM/SOM estimates that are *unvalidated hypotheses* using publicly cited market sizing. Treat the ranges as priors, not facts.

#### Segment 1: Career Changer / Industry Pivoter
- **Core Jobs:** understand what interviewers in a new field expect; practise field-specific questions; translate past work into language this field respects.
- **Big Job:** identity formation — "become the person who belongs in this new world."
- **TAM/SAM/SOM:** TAM ~15M career changers × 20% who'd pay = 3M × $20–40/mo × 1–2 months = **$120M–$240M**. SAM ~4M English-speaking. SOM 5,000–15,000 paying users Y1 ($300K–$900K ARR).
- **Habit:** Low–Medium (episodic, 3–5x/week during active search).
- **Virality:** Medium (Discord/Reddit/Slack career communities).
- **Existential risk gate:** PASS. **Validation debt:** 6 assumptions, 3 lethal.

#### Segment 2: New Graduate / First Real Job Seeker
- **Core Jobs:** know what to expect on first real interview; practise speaking aloud; customise per company.
- **Big Job:** identity formation — "become the person who gets the job, not the student who keeps getting rejected."
- **TAM/SAM/SOM:** TAM ~50M graduates × 30% = 15M × $10–20/mo × 2–3 months = **$3.6B–$7.2B**. SAM ~8M English-speaking. SOM 20,000–50,000 paying users Y1 ($1.2M–$3M ARR).
- **Habit:** Medium (daily/weekly during search; high churn after job secured).
- **Virality:** HIGH (campus/friend networks — "I got the offer + link" = natural sharing).
- **Existential risk gate:** PASS (GDPR considerations for under-25s, EU students). **Validation debt:** 7 assumptions, 4 lethal.

#### Segment 3: Non-Native English Speaker Interviewing in English
- **Core Jobs:** express complex professional ideas clearly in English; practise industry vocabulary; understand cultural expectations.
- **Big Job:** status — "be seen as equally competent as a native speaker."
- **TAM/SAM/SOM:** TAM ~100M non-native English speakers × 15% = 15M × $15–30/mo × 2–3 months = **$4.5B–$13.5B**. SAM ~10M actively interviewing for English-language roles. SOM 10,000–30,000 paying users Y1 ($600K–$1.8M ARR).
- **Habit:** Medium (interview prep episodic, language practice ongoing).
- **Virality:** Medium–High (WhatsApp groups — "this helped me get a US remote job from India").
- **Existential risk gate:** PASS. **Validation debt:** 5 assumptions, 3 lethal.

#### Segment 4: Bootcamp Grad / Self-Taught Dev Breaking Into Tech
- **Core Jobs:** prove they can handle technical interviews without a CS degree; practise realistic company-specific questions; frame non-traditional background as advantage.
- **Big Job:** self-actualisation — "prove I made the right choice, that I belong in tech."
- **TAM/SAM/SOM:** TAM ~2M bootcamp grads + self-taught devs × 40% = 800K × $20–50/mo × 2–4 months = **$192M–$1.6B**. SAM ~300K English-speaking. SOM 3,000–8,000 paying users Y1 ($180K–$480K ARR).
- **Habit:** HIGH (daily LeetCode + mock interview = existing routine).
- **Virality:** Medium ("I got into Google without a CS degree").
- **Existential risk gate:** PASS. **Validation debt:** 5 assumptions, 2 lethal.

#### Segment 5: Comeback Professional (Returning After a Gap)
- **Core Jobs:** rebuild interview confidence after a gap; frame the gap positively; catch up on field changes.
- **Big Job:** security — "feel in control of my financial future and professional identity again."
- **TAM/SAM/SOM:** TAM ~8M re-entering × 25% = 2M × $20–40/mo × 2–3 months = **$80M–$240M**. SAM ~500K. SOM 2,000–6,000 paying users Y1 ($120K–$360K ARR).
- **Habit:** Low–Medium (episodic but emotionally intense).
- **Virality:** Medium (Facebook mom groups, returnship networks, LinkedIn).
- **Existential risk gate:** PASS. **Validation debt:** 6 assumptions, 3 lethal.
- **⚠️ This brief entry is superseded by a much deeper NMT analysis run specifically on this segment — see Section 11a immediately below.** Everything in that section is still a pre-interview hypothesis (0/15 interviews), but it is the most rigorously developed segment picture in the project and should be the reference version, not this summary.

### Hypothesised segment ranking (NOT validated)

| Rank | Segment | TAM est. | Habit | Virality | WTP | Aha potential | Competitor gap |
|---|---|---|---|---|---|---|---|
| 1 | New Grad | $3.6–7.2B | Medium | HIGH | Low-Med | HIGH | Medium |
| 2 | Career Changer | $120–240M | Low-Med | Medium | HIGH | HIGH | Large |
| 3 | Non-Native English | $4.5–13.5B | Medium | Med-High | HIGH | HIGH | Large |
| 4 | Bootcamp Grad | $192M–1.6B | HIGH | Medium | HIGH | Medium | Medium |
| 5 | Comeback Professional | $80–240M | Low-Med | Medium | HIGH | HIGH | Very large |

**Verdict:** GO — but go *to validation*, not to build. All five segments are low-confidence hypotheses with no validation data.

---

## 11a. Segment 5 deep-dive — full NMT analysis (NEW, June 23 2026)

**Status: still a pre-interview hypothesis (0/15 interviews conducted). This is a deeper, more rigorous *articulation* of the hypothesis, not evidence that it's correct.** It was produced by a dedicated Claude Code run using the Next Move Theory (Advanced JTBD) methodology in "Deep" mode, and it is the most developed piece of segment thinking in the project. Treat Layer 1 below as the current best externally-shareable articulation of NAILIT's value prop *for this segment specifically* — useful for designing the blind comparison test, writing interview guide questions, and choosing a landing-page variant. **Not yet useful for public or investor communication** until interviews confirm the segment exists as described.

Two disclaimers carried over from the source run, worth keeping visible: **(1) Numerical disclaimer** — every estimate, WTP figure, and probability below is an illustrative hypothesis, not a measured fact. **(2) Hallucination risk** — the competitor quotes and Reddit signals in the evidence floor (below) come from web search with real retrieval gaps; verify independently before using anything here in investor materials or public copy.

### Who this actually is (sharper than "Comeback Professional")

**Professionals who haven't interviewed in 5+ years and just found themselves back in the job market** — after a layoff, a career pause, or a long stretch at one company. They have real experience and are good at their jobs. But interviewing today looks nothing like what they remember: AI screening rounds they've never faced, structured behavioural formats with specific competency rubrics, companies assessing on culture attributes they've never prepped for. And they're already shaken.

**Explicitly not for:** someone who interviews every 2–3 years and just needs practice reps — they're fine with ChatGPT or LinkedIn prep. This is for the person who feels like a tourist in a country where the language changed.

### The three Core Jobs, precisely stated

1. *"When I haven't interviewed in 5+ years and just received an interview invitation, I want to understand how interviewing has changed at this specific company"* — success criteria: information reflects the last 6–12 months, covers both format (AI screening, behavioural, technical ratio) and culture-specific criteria. Fully current, no guessing.
2. *"When my confidence is shaken by a layoff and I feel rusty, I want to practice interview answers privately without anyone seeing me struggle"* — success criteria: zero external human evaluation during prep. Safe environment.
3. *"When I have an interview in 3–7 days, I want to get genuinely ready in that window"* — success criteria: confident enough to answer company-specific behavioural questions without blanking. Ready in days, not weeks.

**Big Job (the real underlying motivation):** *"Regain my professional standing and income after an unexpected disruption, on my terms."* Sits at the intersection of **security and self-actualisation** — two of the strongest motivational drivers in consumer products. High emotional charge; this is not a convenience purchase.

**Priority order over criteria — this is what makes it a distinct segment, not demographics:** **no-stress-and-private first, then speed, then company-specificity.** Not status-first (that's Segment 1) and not price-first (that's the student segments). Emotionally-first and urgency-driven.

**Anti-segment — who explicitly does NOT belong here:**
- People who interviewed in the last 2 years (no "currency update" Job).
- People with a strong professional network at the target company (insider access replaces research synthesis).
- Students / recent grads (different Big Job, lower WTP, different format needs).
- People who *enjoy* the research process and treat interview prep as their own project — this segment is control-first, not no-stress-first, and is the wrong fit.

**Segment size (still a hypothesis):** ~800K US tech workers laid off 2022–2025 per layoffs.fyi (unconfirmed), plus a larger population of non-tech professionals with long tenure. WTP hypothesis: $20–60 per prep session. TAM estimate: 2–5M active US English-speaking re-entry professionals at any given time.

### The Critical Chain — what this person actually does today, step by step

```
[Trigger: Interview invite arrives]
  → M1: Understand how interviewing has changed since I last did this
     (Google "2024 interview formats," read contradictory articles, feel confused)
  → M2: Find out how THIS specific company interviews RIGHT NOW
     (Glassdoor, read 50+ reports, try to date them, estimate patterns)
     ⚠️ CHAIN BREAK #1 — no efficient synthesis mechanism exists
     Tax Job imposed: "figure out which Glassdoor reviews are from 2024 vs 2020" (unpaid work)
  → M3: Identify the competencies and criteria this company assesses
     (cobble together from JD + Glassdoor + LinkedIn posts; still uncertain)
  → M4: Prepare STAR answers for likely questions
     (map own experience to likely questions, without knowing if the mapping is right)
  → M5: Practice answers out loud
     (solo rehearsal, or a friend saying "sounds great!" — uncalibrated)
  → M6: Know if my answers are actually right for THIS company
     ⚠️ CHAIN BREAK #2 — no calibrated feedback exists
     Career coaches ($200–500/hr, scheduling, generic frameworks) / ChatGPT (generic STAR critique,
     no company-culture awareness) / peers (can't evaluate against criteria they don't know)
  → M7: Refine answers until confident — blocked by Break #2, confidence built on unvalidated guessing
  → M8: Walk into the interview feeling ready → Big Job: regain professional standing and income
```

**Tax Jobs imposed by this chain (unpaid work the current market forces onto the candidate):**
- T1: Research 10+ sources to understand how the company interviews (4–8 hrs).
- T2: Mentally date-stamp and prioritise 50+ Glassdoor reviews.
- T3: Synthesise contradictory information from multiple prep sources.
- T4: Practise without knowing if the answers would actually score well for this company.
- T5: Go into the interview uncertain even after 8+ hours of prep.

**Aha Moment placement — as far left in the chain as possible:** fires at **M2**, the moment the person first sees a prep pack that shows "here is how this company interviews today, based on N recent reports" — before any practice, before any answer-writing. Earlier Aha = smaller abandonment window. **Second-session Aha** (retention) fires at **M6** — the first piece of feedback that names the company's actual assessment criteria by name, not generic STAR advice.

### Before / after, one page

| Dimension | Before (today) | After (with NAILIT) |
|---|---|---|
| Research time | 4–8 hours across Glassdoor, ChatGPT, YouTube | 60 seconds: prep pack generated from recent interview data |
| Company-specificity | Uncertain synthesis from dated, unreliable sources | Company-specific questions, criteria, format from the last 6–12 months |
| Practice environment | Alone (no feedback), a friend (unqualified), or a coach ($200–500/hr) | Private AI mock interview with company-calibrated feedback |
| Emotional state pre-interview | Uncertain, worried they missed something | "I know what they'll ask, I've practised it, I know where I'm weaker and what to fix" |
| Time to interview-ready | 2+ weeks with a coach; 1+ week DIY | 3–5 day window maintained |
| Cost | $0 (DIY, 6–8 hrs) or $200–500+ (coach) | $20–60/session (hypothesis, consistent with the credits pricing in Section 4) |

### The two value-hypothesis candidates

**Candidate A — "Kill the Research Job, Practice in Private" (PRIMARY)**
The core bet: the most valuable thing NAILIT does is take the 4–8 hour research Tax Job off the candidate entirely. They don't need to find, date, synthesise, or interpret interview reports — they get the output in 60 seconds. Primary value levers: lowers Cost (time, cognitive load, negative emotion) and raises Probability (prep is grounded in current data, not outdated impressions). **Why primary:** fires earliest in the chain, hits every Segment 5 user, is the fastest and cheapest thing to test (a blind comparison, effectively $0 tech investment). If this doesn't win, nothing downstream matters.

**Candidate B — "Company-Calibrated Feedback" (SUPPLEMENTARY, second-session value)**
The core bet: feedback that names the company's actual assessment criteria ("this answer misses what Amazon calls 'Think Big,' typically evaluated in round 2") is materially more useful than generic STAR critique. Primary value levers: raises Outcome (calibrated feedback → better answers → higher probability of offer) and lowers Cost (removes the uncertainty of "I don't know if this answer is good"). **Why supplementary:** depends on Candidate A landing first — you need the research layer to establish the criteria before you can calibrate feedback against them. Not the first thing to test.

**What the product is explicitly NOT**, per this analysis: not a career-coaching product (no human expertise in the loop for V1), not a generic interview-prep platform (doesn't serve people who just want practice reps), not a job-search tool (doesn't help find the job, only helps with the interview), not a confidence-coaching product (doesn't address the emotional dimensions of a layoff beyond the safe-practice dimension).

### Feasibility filter (specific to this segment)

| Dimension | Assessment |
|---|---|
| Technical feasibility | Achievable with existing pipeline: pull public interview reports (Glassdoor, Blind, Reddit), LLM synthesis, structured output. No proprietary data required for V1 — consistent with the pipeline already built (Section 3). |
| Data freshness risk | Glassdoor scraping policy and staleness are real constraints. Mitigation: multiple sources, date filtering, consider API access where available. |
| Quality bar | AI synthesis must beat 30 minutes of DIY browsing — this is RAT-VP-1 below. If this fails, the core mechanic doesn't work for this segment regardless of anything else. |
| Cost to build MVP | Low — the six-module pipeline already runs end-to-end (Section 3). The delta for this segment is validation and messaging, not new infrastructure. |
| Unit economics | WTP hypothesis $20–60/session; cost-to-serve <$2/session at current LLM API rates (consistent with the £0.78 modelled figure in Section 4, pending ACT-5). Margin is strong if conversion holds. |
| Red Queen risk | 12–18 month window before LinkedIn/OpenAI ship comparable research synthesis (see Section 9a) — consistent, independently-derived confirmation of the ACT-3 urgency. |

### RAT cards specific to this segment

**RAT-VP-1 — Core Value Hypothesis (LETHAL)**
- **Assumption:** the AI prep pack gives the candidate materially more useful, current, company-specific information than they'd get from 30 minutes of their own Glassdoor + ChatGPT research.
- **If wrong:** the free alternative is "good enough" — the product's reason to exist collapses. This is the segment-specific instance of the project's root risk (Risk 1, Section 12).
- **P(wrong):** 4/5 — plausible the gap exists, but untested; Glassdoor data is noisy, LLM synthesis quality at scale is unknown.
- **I(mpact):** 5/5 — kills the value proposition entirely; cannot be pivoted around at the product level.
- **Cost to validate:** 1/5 — cheap. Build one prep pack, run a blind comparison with 10 Segment 5 people.
- **Score:** (4×5)/1 = **20**.
- **Test method:** blind quality comparison — AI prep pack vs. the candidate's own 30-minute research, no labels, 10 users. Threshold: 7/10 prefer the AI version.
- **Kill/Pivot/Proceed:** KILL if users can't distinguish quality. PIVOT to "better UX on the same data" if information is equivalent but presentation is better. PROCEED if 7/10 prefer the AI version.
- **Droppable?** No — this is the root of the segment-specific value proposition.

**RAT-VP-2 — Company-Calibrated Feedback (IMPORTANT)**
- **Assumption:** feedback naming the company's specific criteria improves answer quality materially more than generic STAR feedback.
- **P(wrong):** 3/5. **I:** 4/5. **Cost:** 2/5. **Score:** (3×4)/2 = **6**.
- **Test method:** show the same answer to 5 recent interviewees with two feedback versions (generic vs. company-calibrated). Ask which would actually change how they'd answer.
- **Kill/Pivot/Proceed:** PIVOT to generic feedback (drop calibration) if it doesn't help — Candidate A still holds. PROCEED if calibrated feedback changes the answer in 4/5 cases.
- **Droppable?** Yes, partially — V1 can launch on research synthesis alone and add calibrated feedback once validated.

**RAT-VP-3 — Emotional Safety as a Buying Driver**
- **Assumption:** "private practice without judgment" is a real buying driver for this segment, not just a nice-to-have.
- **P(wrong):** 2/5 — the segment is explicitly shaken (re-entry after a layoff), making this plausible; other segments (e.g. Segment 1) would rate it lower. **I:** 3/5 — affects communication strategy more than product design; Candidate A still holds either way. **Cost:** 1/5. **Score:** (2×3)/1 = **6**.
- **Test method:** interview question — "When you thought about practising for this interview, what felt hardest?" Emotional answer validates; pragmatic answer doesn't. Threshold: 5 of 7 interviews surface unprompted anxiety or shame about being rusty.
- **Kill/Pivot/Proceed:** PIVOT communication (lead on speed, not safety) if emotional language doesn't surface unprompted.
- **Droppable?** Yes — the communication angle is droppable, the underlying product feature (private practice) is not.

**Segment-specific survival math:** RAT-VP-1 (P wrong 0.80 → survival 0.20) × RAT-VP-2 (P wrong 0.60 → survival 0.40) × RAT-VP-3 (P wrong 0.40 → survival 0.60) = **4.8%** — this stacks on top of, and is separate from, the project-wide ~0.8% survival figure in Section 14. **The single highest-leverage action for this segment: run the RAT-VP-1 blind comparison this week** — same conclusion the project-wide survival math reaches independently in Section 14.

### Behaviour-change classification — why the messaging has to lead differently for each half of the product

The Core Job "use an AI tool to research how a company interviews" is **Class 2** (an unfamiliar category) for most of this segment — they've never used a company-specific AI prep tool before, so the category doesn't exist in their mental model yet. Implications:
- **Communication must lead with the Big Job** (regain professional standing) rather than the Core Job feature ("AI-generated prep pack").
- **The Aha Moment must be forward-loaded** — Consideration Activators (peer stories, a demo, a free first experience) are needed *before* the first session, not during it.
- **Fear work must address category-existence first:** "Is it actually safe to get interview prep from AI?" / "Will it actually know about my specific company?"
- **Fear-reduction message:** the product shows real company data, not hallucinations — proof of source quality is a key Consideration Activator.

By contrast, the mock-interview feedback component (Candidate B) is closer to **Class 1** — "AI gives feedback on interview answers" is familiar from ChatGPT. This is easier to communicate: lead on the *delta* (company-calibration), not on convincing people the category exists.

**The five things a Segment 5 person needs to believe before switching** (Consideration Activators, in load order):
1. *"There is a way to get company-specific prep in minutes — I don't have to piece it together myself."* (Most don't know this is possible yet.)
2. *"The AI actually knows how THIS company interviews, not just companies in general."* (The single biggest barrier — this is exactly where ChatGPT fails.)
3. *"I can practise wrong in front of this tool without consequences."* (Private-practice dimension; peers and coaches carry social cost, this doesn't.)
4. *"Being out of the market for 5 years doesn't mean I'm behind — I just need to update my interviewing, not my career."* (Identity-level fear; product language must normalise the gap, not implicitly stigmatise it.)
5. *"ChatGPT gave me generic questions — it didn't know how this company actually interviews."* (Firing the competing approach — doesn't need to be aggressive, just a concrete contrast.)

**Best channel to load these:** Reddit threads (r/layoffs, r/cscareerquestions) where people are already asking "how do I prep for an interview after 6 years at one company?" — a chain-break moment where a well-placed, specific comment can fire all five activators in a paragraph. **Trigger timing:** the strongest receptivity window is **24–48 hours after an interview invite arrives** — marketing that hits this window is estimated to outperform steady-state marketing roughly 10:1. Channel priority: (1) Reddit/Discord posts showing the trigger live, (2) LinkedIn "Open to Work" + recent interview activity signals, (3) email to job-board signups who haven't converted, triggered by an interview-invite event.

### Segment-specific evidence floor (partial — needs expansion before finalising positioning)

*Caveat from the source run: the reviews-mining pass was partial due to session constraints. Reddit-specific signal is recommended but not yet gathered — expand with targeted searches (r/layoffs "interview after years", r/cscareerquestions "out of practice" / "haven't interviewed") before finalising competitor positioning copy.*

- ChatGPT: "typing into ChatGPT feels safe with no time limit, no one watching, and no stakes, but interviews are high-pressure" and it "treats every question in isolation" without tracking patterns over time (revarta.com).
- Glassdoor: the 68% HR-manipulation stat (Section 9a) plus the general dating/staleness problem.
- LinkedIn's AI prep tool: the AI-detectability finding (Section 9a) — hiring managers report they can identify and penalise AI-generated answers.
- Exponent: described as "on the expensive side" across review platforms, with cancellation requiring direct contact with support (Trustpilot).

### Implementation spec for this segment — and an important reconciliation with the existing build plan

The source NMT run produced a 3-stage build spec (Research Synthesis MVP → Mock Interview + Feedback → Confidence Signal / Re-entry Framing), explicitly gated by validation checkpoints between stages. **This needs to be read against Section 3's "current state," not as a separate build plan** — because NAILIT's pipeline is already substantially past Stage 1 and into Stage 2:

- **"Stage 1: Research Synthesis MVP"** — company research + prep pack generation. **This already exists** as Modules 1–6 of the live pipeline (Company Intelligence through Prep Pack), verified end-to-end. The gap isn't building this; it's **validating it against RAT-VP-1** with real Segment 5 users, and fixing the known story-repetition/boilerplate defect (ACT-2) that would undermine a blind quality comparison if left unfixed.
- **"Stage 2: Mock Interview + Feedback"** — company-calibrated feedback on practice answers. **This also already exists** as Module 8 (Mock Interview) plus Lua (the AI coaching layer, 22 authenticated endpoints, 10-field response shape). The gap is validating RAT-VP-2 specifically — does the *existing* feedback already read as company-calibrated to a real user, or does it read as generic STAR advice? This is a question the second quality test (ACT-8) should be explicitly designed to answer for this segment.
- **"Stage 3: Confidence Signal + Re-entry Framing"** — session summaries, normalised gap-framing language, a calibrated "you're ready" signal. **This is a genuinely new, small scope of work** — a session-summary UI layer plus copy that explicitly normalises the employment gap rather than glossing over it. Worth scoping as a small addition once ACT-1/ACT-2 ship, likely bundled with ACT-7 (UX polish) rather than as a new numbered action.

**Practical takeaway: the product is closer to "ready to validate on this segment" than "needs building for this segment."** The highest-leverage move is routing the Week 1 validation interviews (Section 21) and the RAT-VP-1 blind comparison test at Segment 5 specifically, using the existing pipeline, rather than treating this as new build scope.

**Anti-patterns flagged by this run — do not build before validating:**
| Anti-pattern | Why not |
|---|---|
| Voice-based mock interview | High effort (audio processing, latency); text feedback is faster to validate first — consistent with the existing ACT ordering (voice is explicitly deferred, Section 3). |
| Ex-employee connection | Already killed for V1 (RAT Risk 5, Section 12); reactivate only once network coverage would plausibly exceed 60%. |
| Generic interview-coaching content | Misses the company-specificity that is the core value prop; competes with well-funded incumbents on their own turf. |
| Career-outcome tracking (did you get the offer?) | Useful data eventually, but not V1 scope — validate the core loop first. |

*Full methodology trail (Advanced JTBD / Next Move Theory, Ivan Zamesin): value-creation.md, value-creation-mechanics.md, critical-chain.md, behaviour-change.md, communication.md. Compiled by a dedicated Claude Code run, Deep mode, June 23 2026.*

---

### Segment commentary from the Ultimate Handoff
The Ultimate Handoff specifically called out two segments by name as already-considered in NAILIT's *real* internal segmentation work: **Active Multi-Company Searcher** and **Corporate Talent Developer**. These were used as the structural answer to the "retention ceiling" concern (Section 13, Risk 2) — both segments need NAILIT across multiple interview cycles rather than once-and-done, which sidesteps episodic churn. They are not in either of the two lists above and should be reconciled before final segment commitment.

---

## 12. RAT — top 5 risks ranked by (Probability × Impact) / Cost-of-Validation

*Note: these are the project-wide risks. Section 11a adds three more risks (RAT-VP-1, VP-2, VP-3) specific to Segment 5, which stack on top of — not replace — the risks below. RAT-VP-1 is functionally the same risk as Risk 1 here, restated with Segment 5's specific evidence and test design.*

### Risk 1 — "Free is Good Enough" | Score: 20.0 | ROOT

- **Assumption:** users believe YouTube + ChatGPT + friends = 80%+ of the value of a paid interview prep tool, making them unwilling to pay.
- **Risk:** if true, freemium conversion stays below 2%, CAC exceeds LTV, the business model fails.
- **P:** 5 (very high — this is how students *already* behave).
- **I:** 4 (kills the business model).
- **Cost-of-Validation:** 1 (landing page + $50 traffic).
- **Score:** (5×4)/1 = **20.0**.
- **Test methods:** landing page + $50 Google/TikTok ads; social listening (Reddit r/jobs, r/cscareerquestions); app store review mining (Big Interview, Pramp 1–2 star); expert interview with university career advisor.
- **If fails →** KILL — no business model works for this segment.
- **Can be dropped?** NO — root assumption.

### Risk 2 — "Episodic Use = No Habit" | Score: 8.0 | Upstream

- **Assumption:** interview prep is a 2–8 week episodic need, so median retention <2 months and LTV is too low to support CAC.
- **Risk:** at 1.5 months × $15/month, LTV = $22.50; if CAC = $25, every user loses money.
- **P:** 4. **I:** 4. **Cost-of-Validation:** 2 (competitor data + interviews). **Score:** **8.0**.
- **If fails →** PIVOT — expand "interview prep" to "career development platform."
- **NAILIT's structural answer:** non-expiring credits + Active Multi-Company Searcher / Corporate Talent Developer segments. This risk is *already designed around*, but the design needs validation.

### Risk 3 — "AI Quality Gap" | Score: 6.0 | Downstream

- **Assumption:** the AI-generated prep pack is accurate, current, and specific enough that users trust it over their own Googling.
- **Risk:** if generic or inaccurate, users lose trust after first use, no conversion.
- **P:** 3. **I:** 4. **Cost-of-Validation:** 2 (prototype test + blind comparison). **Score:** **6.0**.
- **If fails →** PIVOT — narrow to industries with abundant public data (tech).
- **NAILIT's status here:** core pipeline live-tested; hallucination guard works; one known content defect (story repetition + boilerplate leak — ACT-2) needs fixing before broad trust claim.

### Risk 4 — "Feedback Not Worth Paying For" | Score: 5.0 | Downstream

- **Assumption:** AI feedback on mock answers is specific, actionable, and noticeably better than free ChatGPT.
- **Risk:** if generic ("be more specific," "use STAR method"), no perceived value over free alternatives.
- **P:** 3. **I:** 5 (this *is* the core product). **Cost-of-Validation:** 3. **Score:** **5.0**.
- **If fails →** PIVOT — shift to human feedback marketplace or hybrid (AI flags, human reviews).
- **Can be dropped?** NO — core value prop.

### Risk 5 — "Ex-Employee Marketplace Never Reaches Liquidity" | Score: 4.0 | DROPPED

- **Assumption:** enough ex-employees willing to provide feedback to create a liquid two-sided marketplace.
- **Risk:** classic marketplace cold-start. Expensive to build, may never reach liquidity.
- **P:** 4. **I:** 2 (optional feature — core product still works). **Cost-of-Validation:** 2. **Score:** **4.0**.
- **Decision:** DROPPED from V1 entirely. Saves $50K+ in dev cost. The Ultimate Handoff notes this could return as an upsell *after* validation, specifically using *former* employees to avoid conflict of interest.

### Subtractive analysis (what was dropped to improve survival odds)
- **Dropped:** Risk 5 (ex-employee marketplace) — removes one full risk multiplier; saves $50K+.
- **Pivoted:** Risk 2 — reframed from "interview prep subscription" to "career development with non-expiring credits + retention-segment targeting."

---

## 13. Validation debt ledger

| Risk | Status | Interviews done | Evidence | Next step |
|---|---|---|---|---|
| 1. Free is good enough | UNVALIDATED | 0 / 15 | None | Test FIRST: landing page + $50 traffic |
| 2. Episodic use | UNVALIDATED | 0 / 15 | None | Test in parallel |
| 3. AI quality gap | PARTIALLY MITIGATED (live pipeline test) | 0 / 15 user interviews | One live session, founder's own data | Run ACT-8 (second quality test, different JD/CV) |
| 4. Feedback not worth paying | UNVALIDATED | 0 / 15 | None | Side-by-side comparison with ChatGPT |
| 5. Marketplace | DROPPED | N/A | N/A | Revisit at scale post-V1 |
| VP-1. AI pack > 30-min DIY research (Segment 5, lethal) | UNVALIDATED — same risk as #1, segment-specific test design ready | 0 / 10 blind-comparison | None | Run blind comparison this week — see Section 11a |
| VP-2. Company-calibrated feedback > generic STAR (Segment 5) | UNVALIDATED | 0 / 5 | None | Prototype test, 5 recent interviewees |
| VP-3. Emotional safety is a buying driver, not just nice-to-have (Segment 5) | UNVALIDATED | 0 / 7 | None | Interview Block B/E signal, listen for unprompted anxiety language |

**Total validation debt:** 4 project-wide unvalidated risks (1 dropped) + 3 Segment-5-specific risks layered on top.
**Interviews conducted:** 0 / 15 project-wide; 0 / 10 for the Segment 5 blind comparison specifically.
**Next run trigger:** after 15 interviews, re-run RAT scoring. **The single most time-efficient next move: design the Week 1 interviews (Section 21) and the blind comparison (RAT-VP-1) to run on Segment 5 specifically** — one test round can validate both the project-wide Risk 1 and the segment-specific VP-1 simultaneously, since they're the same underlying question asked of the same population.

---

## 14. Survival math

```
Risk 1 (Free is good enough):    P(wrong) = 80%  → Survival = 20%
Risk 2 (Episodic = no habit):    P(wrong) = 75%  → Survival = 25%
Risk 3 (AI quality gap):         P(wrong) = 60%  → Survival = 40%
Risk 4 (Feedback not worth it):  P(wrong) = 60%  → Survival = 40%
Risk 5 (Marketplace):            DROPPED         → Survival = 100% (removed)

Combined survival = 0.20 × 0.25 × 0.40 × 0.40 = 0.008 = 0.8%
```

**What this number actually means:** 0.8% is the *unconditional* survival probability assuming none of the risks have been validated yet. Each validated risk multiplies survival by 1/p(wrong). With Risk 1 mitigated alone, combined survival jumps to **4.0% — a 5x improvement from one cheap test.** This is why the entire validation sequence starts with Risk 1.

**The single highest-leverage action of the entire validation programme:** validate Risk 1 first. Cheapest test ($50 landing page), highest-impact result (kills or saves the entire product).

---

## 15. Blind spots — what can't be tested without going outside the building

### Cannot be tested by analysis alone (need real users)
1. Segment existence and size — all five segments are hypothesised.
2. "Free is good enough" — the ROOT risk.
3. AI quality vs manual research — needs blind comparison.
4. Feedback quality — must beat free ChatGPT.
5. Retention / episodic use — needs competitor retention analysis + user interviews.
6. Willingness to pay — pricing is assumed.
7. Channel / CAC assumptions — TikTok/Reddit channels are guesses.
8. Unit economics at scale — blocked by validation methodology.
9. Gap-narrative resonance — does the gap-reframing feature actually help returners?
10. Voice mock differentiation — would voice be the Aha Moment? Untested.

### Unvalidated assumptions (full list)
- Core pipeline runs end-to-end → confirmed structurally; quality untested at scale.
- Component quality is "uneven" → *how* uneven? Which components? (Now narrowed: story-selection in answer generation is the known weak spot.)
- 5 segments exist as described → unvalidated.
- TAM/SAM/SOM estimates → no data.
- Users will pay £49–199 in non-expiring credits → unvalidated.
- AI feedback beats ChatGPT → unvalidated.
- Company-specific research is accurate → partially live-tested.
- Virality through friend networks → unvalidated.
- Voice-based mock would differentiate → unvalidated.


# PART 5 — DEFENSIBILITY, MOAT, AND DISTRIBUTION

## 16. The defensibility thesis — the moat is the data, not the prompts

**The thesis, stated plainly.** The generation layer (writing answers, structuring packs) is not defensible long-term against a smarter foundation model and should be assumed to commoditise over time, not fought. **The data layer — the contribution database (ACT-3) — is the only component that gets *more* defensible every year**, specifically because it requires real users and real elapsed time, which raw model capability cannot shortcut.

### Why the data layer is acquisition-grade, even in a worst case

Even if NAILIT is eventually out-competed on generation quality, a sufficiently large, structured, multi-year dataset of real candidate contributions tied to real outcomes is independently valuable to:
- Recruiting platforms (LinkedIn, Indeed).
- HR tech (Greenhouse, Lever).
- The AI labs themselves (OpenAI, Anthropic, Google) — none of whom can acquire this data through model improvement alone.

This reframes "could we get acquired" from a hope into a specific thesis: **the dataset is the asset an acquirer would actually be paying for, not the UI or the prompts.**

### The mechanically precise statement of why generation isn't defensible but data is

A foundation model getting better over time **absorbs generation quality** (better-written answers). It **cannot absorb first-party data it never had access to** — specifically, real candidates' after-the-fact reports of what they were *actually* asked at named companies in named roles in named rounds. That data only exists because real people used NAILIT specifically and contributed it post-interview. This is why the contribution database is the actual long-term defence, not "a nice to have."

### Why this is solo-founder-feasible
The moat-building mechanism (ACT-3) is a **one-time, narrow code build — not ongoing labour.** Once built, it runs itself forever for every user. This is the reason the moat is solo-founder-feasible at all: it doesn't require a team, it requires writing one feature once.

### What seeding the moat actually requires
A small *first* cohort of **20–50 real users** — not mass reach. Achievable through quiet, asynchronous, written engagement in places where step-up candidates already exist:
- Career-transition subreddits.
- LinkedIn job-search communities.
- Relevant alumni and professional groups.

**Not required:** video content, personal brand on TikTok/Instagram, public-facing founder presence. LinkedIn presence is acceptable and sufficient; nothing more public-facing is required.

### Where fractional / freelance help is and isn't appropriate
- **Appropriate, later, occasionally:** light paid-per-project data analysis once the database has real volume.
- **Not appropriate, ever, for the moat specifically:** any form of manually "going and getting" contributions via a freelancer defeats the entire point. The asset's value comes from being an *automatic byproduct of organic usage* — a freelancer-assembled dataset is not the same asset.

---

## 17. Distribution and GTM — for a solo, non-public-facing founder

### The principle
Distribution effort comes *after* the first cohort proves the conversion mechanic works, not before. Raising money to fund distribution before product-market fit is backwards — it funds a story, not an asset, because the actual proof that distribution effort would convert doesn't exist yet.

### The correct sequence
1. Build the first cohort manually and slowly (Week 1–4 validation programme — Section 21).
2. Let the contribution database start accumulating real rows.
3. Use *early revenue, not raised capital* to bring in a fractional growth person once there's a proven conversion signal to scale.

### Where to find the first 20–50 users
**Asynchronous, written, low-public-surface-area channels** that fit a non-public-facing founder:
- **Reddit:** r/jobs, r/cscareerquestions, r/careerguidance, r/GetEmployed, r/findapath, country/region-specific career subs.
- **LinkedIn:** comment thoughtfully on job-search posts in your existing network; LinkedIn groups for career transitions; LinkedIn posts from your own profile (low-frequency, high-value).
- **Discord:** coding bootcamp servers, career-changer servers, returnship community servers.
- **Alumni networks:** your own university alumni list, cross-industry alumni lists you can access.
- **Professional associations:** PMI for project managers, IIBA for business analysts, etc.

### Channel hypotheses worth a $50–100 traffic test (not commitment)
- **TikTok/Reels:** "I got into [Company] using this" creator content. Hypothesis only. Test before investing.
- **Reddit organic + sponsored:** r/jobs, r/cscareerquestions.
- **University partnerships:** career centres distribute to students.
- **Discord communities:** as above.

### Landing page hypothesis (test, don't commit)
- **Headline:** "Stop guessing what they'll ask. Know before you walk in."
- **Sub:** "Company-specific interview prep with AI feedback that actually tells you what to fix."
- **CTA:** "Try free — enter your target company."
- **Pricing hypothesis to A/B:** £15/mo vs £20/mo vs £25/mo *equivalent* — but use the credits pricing model, not subscription.

### What NOT to do for distribution
- Don't run paid acquisition before product-market fit signal.
- Don't build personal brand as a precondition to distribution.
- Don't outsource the first-cohort outreach to a freelancer.
- Don't follow generic "AI startup growth" playbooks that assume venture-funded distribution budget.

---

## 18. On funding

**Position:** raising money *to fund distribution* before product-market fit is backwards. Building a moat requires real usage data over time, which capital cannot accelerate past organic growth speed in this category.

**Correct sequence:**
1. Build moat infrastructure (ACT-1 auth → ACT-3 contribution capture).
2. Seed first cohort 20–50 users manually.
3. Confirm the conversion mechanic works (paying user → contribution row → improved data).
4. Use *early revenue* (not raised capital) for a fractional growth person.
5. Consider raising only after the data flywheel has visible compounding signal — which is the only thing an investor in this category could be buying anyway.

**Firm project principle:** **no infrastructure spend before real paying users exist.** This has been explicitly, repeatedly decided. Treat it as a firm rule, not an open question to revisit casually.

---

# PART 6 — THE ORDERED ACTION PLAN

## 19. The ordered action list — ACT-1 through ACT-8, with rationale for ordering

This order is not arbitrary. Each step either removes a live risk or unblocks several later steps at once.

### ACT-1 — Ship minimal auth (email + magic link)
- **Tool choice:** Clerk or Supabase Auth — undecided which, either is fine. Pick in a dedicated 1-hour session, don't bundle with implementation.
- **Why this is #1:** single highest-leverage remaining build. Unblocks: payments, the offer-rate email, GDPR-by-user, the contribution database. **Nothing past this step matters until it's done.**
- **Acceptance criteria:** new user can sign up via email; magic link works; session ownership is enforced server-side; existing endpoints recognise authenticated user.

### ACT-2 — Run the story-repetition / boilerplate-leak root-cause investigation, then fix
- **In parallel with ACT-1; they don't conflict** (different parts of the codebase).
- **Investigation prompt, already written, ready to run:**
  ```
  Read only: the function in agent_v2.py that selects which
  story/evidence entry to assign per question, and the location
  where the "reason this matters" disclaimer text is inserted.
  Report root cause for: (1) why story_inventory only contains
  2 entries when many more exist in the candidate's source data,
  (2) why the disclaimer paragraph appears identical/hardcoded
  across answers instead of varying.
  Do not fix yet — diagnose only.
  ```
- **Why this matters:** this is the highest-priority *content* fix — the difference between "the pipeline runs" and "the pipeline produces something genuinely good." The bug is narrow (other modules don't show it), confined to the answer-generation/story-selection step, and has the same shape as other defects this project has already cleanly fixed.

### ACT-3 — Build the contribution-capture mechanism (the moat)
- **Depends on ACT-1** (needs `user_id`).
- **Spec, ready to execute the moment auth exists:**
  ```
  After a session reaches mock-interview-complete or a defined
  "session closed" state, trigger an email (reuse the existing
  send_email() offer-rate stub) asking which questions from the
  pack were actually asked in the real interview.
  Add /contribution/submit storing: contribution_id, user_id,
  company_name, role_name, round_name, question_text,
  confirmed_by_user, created_at.
  No manual curation. Purely automatic, triggered by real usage.
  ```
- **Why this is third:** the moat-builder. One-time code build, not ongoing labour. Once shipped, it runs itself forever for every user. **This is the single greatest long-term risk if not built quickly** — every day this isn't running is a day with no contribution rows accumulating, and elapsed time is the one resource raw capability can't replace.

### ACT-4 — Move off the Daytona sandbox
- **What:** redeploy to Render or Fly.io free tier (real always-on host, real public URL, zero cost).
- **Why fourth:** Daytona is a dev sandbox, not a production host — it sleeps when idle, has no SLA. The entire deployment debugging saga (Section 22) traces back to treating it as if it were production. Once auth and contribution capture are stable locally, move to a real host.
- **Constraint:** **no paid infrastructure spend before real paying users exist.** Free tier on Render/Fly is correct *next* step. Hetzner or paid infra only once paying users exist.

### ACT-5 — Resolve the OpenAI / Claude question
- **Dedicated single-decision session, no bundled changes.**
- **Inputs:** the June 2026 pricing table from Section 6; the actual OpenAI invoice for the live test session; the prompt-caching opportunity analysis.
- **Output:** a written decision with rationale, committed to the repo.

### ACT-6 — Wire Stripe checkout + Resend for real email
- **Depends on ACT-1** (needs `user_id` for payment association).
- **What:** create real Stripe products in the dashboard (Starter £89, Monthly £49, Premium £199), build the checkout UI, integrate the existing signature-validated webhook. Replace the `send_email()` stub with Resend.
- **Why sixth:** without auth, payments can't be associated with a user; without real email, the contribution-capture mechanism in ACT-3 can't actually run.

### ACT-7 — UX state-signaling fix on the module dashboard
- **Low priority, cosmetic, already spec'd:**
  ```
  Frontend only, no backend changes.
  1. When a module's status is "done": grey out the primary
     action button and relabel it "Regenerate." Make "View
     Results" the visually primary (gold/accent) button instead.
  2. Clicking "Regenerate" on a done module shows a confirmation:
     "This module already ran. Regenerate and overwrite the
     existing result?" before re-running.
  3. Do not change LOCKED, IDLE, or RUNNING states.
  ```

### ACT-8 — Run a second, independent quality test on a different JD/CV pair
- **Why eighth:** before treating the answer-generation pipeline as broadly trustworthy, verify on data that isn't the founder's own. The current verification is based on one test session against the founder's CV. Pick a second realistic JD/CV pair (e.g., a marketing manager applying to a SaaS scaleup, or a finance analyst applying to a bank) and run the full pipeline. Apply the same hallucination-guard and forbidden-claims checks.
- **Trigger:** ACT-2 fix complete.

---

## 20. Sequencing — what runs in parallel vs serial

```
Week 1:  [ACT-1 auth] || [ACT-2 story-repetition diagnose+fix]
Week 2:  [ACT-3 contribution capture] depends on ACT-1
         [ACT-6 Stripe + Resend] depends on ACT-1
Week 3:  [ACT-4 move off Daytona] requires ACT-1, ACT-3 stable locally
         [ACT-5 OpenAI/Claude decision session] independent
Week 4:  [ACT-7 UX state-signaling] cosmetic, fit in when convenient
         [ACT-8 second quality test] requires ACT-2 fix shipped
```

This is a 4-week build window if all goes well. Slip to 6 weeks is realistic given solo-founder load.

---

## 21. The 4-week external validation roadmap — runs in parallel with the build

The build above is internal. Validation is external — talking to real users. These need to overlap, not sequence.

**Targeting update (July 3, 2026): point this at Segment 5 first.** Since Section 11a was compiled, Segment 5 (laid-off/gap-returner professionals, 5+ years since last interview) is the most rigorously specified hypothesis in the project — full Critical Chain, both value candidates, three ready-to-run RAT-VP test designs, and Consideration Activators already sequenced. Recruiting Week 1's 15 interviewees from this segment specifically (r/layoffs, r/cscareerquestions "out of practice" threads) means one interview round validates both the project-wide Risk 1 (Section 12) and the segment-specific RAT-VP-1 (Section 11a) at the same time, since they're the same underlying question. The blind-comparison test design in RAT-VP-1 is more concrete than the general Test 1 below — use it as the template.

### Week 1: Validate the ROOT risk
| Day | Action | Tests |
|---|---|---|
| 1 | Build landing page with value prop + pricing page, using the Segment 5 one-liner from Section 11a | Fake-door test |
| 2 | Launch $50 TikTok + Google ads ("interview prep" keywords) | Risk 1: clicks? attempt-to-pay? |
| 3–5 | Recruit 15 interviewees — prioritise r/layoffs and r/cscareerquestions "out of practice" / "haven't interviewed in years" threads (Segment 5) alongside r/jobs, r/GetEmployed, r/careerguidance, Discord | Risks 1 + 2, and RAT-VP-1/2/3 |
| 5–7 | Conduct 15 interviews (20–30 min each) using interview kit (Appendix B) — for Segment 5 interviewees, run the RAT-VP-1 blind comparison (Section 11a) as part of the session | Risks 1–4, VP-1–3 |

### Week 2: Analyse + iterate
| Day | Action |
|---|---|
| 8–9 | Code interview results (dual-layer template) |
| 10 | Re-run RAT with updated assumption statuses |
| 11 | Update validation debt ledger |
| 12–14 | If Risk 1 mitigated → start building prototype mock + feedback specifically against findings |

### Week 3: Prototype test
| Day | Action |
|---|---|
| 15–17 | Build prototype: company research + 1 mock interview + AI feedback (or just route real test users to the existing live pipeline) |
| 18–19 | Test with 20 users (blind comparison: NAILIT vs ChatGPT vs manual research) |
| 20–21 | Analyse: does NAILIT beat ChatGPT on user-perceived quality? |

### Week 4: Go / No-Go
| Day | Action |
|---|---|
| 22–24 | If AI quality passes → test pricing (£15/mo vs £20/mo vs £25/mo *credit equivalents*) |
| 25–26 | Final analysis: 15 interviews + landing page data + prototype test + pricing test |
| 27–28 | **GO / NO-GO decision** |

### Decision framework

| Outcome | Action |
|---|---|
| Risk 1 confirmed (free is good enough) | KILL or PIVOT to segment where free is insufficient (gap-returners, non-native speakers) |
| Risk 1 mitigated + Risk 4 passes | PROCEED to ship V1 publicly (auth, contribution capture, Stripe, real domain) |
| Risk 1 mitigated + Risk 4 fails | PIVOT to human feedback (delayed marketplace) or hybrid model |
| All risks mitigated | Build V1 → launch → test retention (Risk 2) on real users |

---

# PART 7 — HARD-WON LESSONS AND DISCIPLINE RULES

## 22. The deployment debugging saga — every step taught something real

A colleague redeploying NAILIT elsewhere will hit this exact sequence if they don't know this history. The whole thing is here because every step taught a lesson that is *narrower than the symptom suggests* — and the lessons compose into the project discipline rules in Section 23.

### Symptom 1
Live Vercel form → `400 Bad Request: failed to resolve container IP... Is the Sandbox started?`
- **Real cause:** Daytona sandbox had gone to sleep — its designed behaviour when idle. It is a coding sandbox, not a host.
- **Fix:** `daytona start <id>` — required first fixing expired CLI auth (`daytona login`) and a CLI/API version mismatch.

### Symptom 2
After waking the sandbox, `502` error.
- **Real cause:** no backend process was running inside the sandbox at all.
- **Fix:** found the real code path (`/home/daytona/interviewprep/`) via `daytona exec` / `daytona ssh`, started uvicorn manually.

### Symptom 3
`ModuleNotFoundError: No module named 'fastapi'`.
- **Real cause — the most important finding of that night:** `git log` showed the local repo was 3 commits ahead of `origin/main`. **Every fix from the entire debugging session existed only on the founder's laptop, never pushed.** The sandbox was running stale pre-fix code the whole time — this explained both the original 400 and the 502.
- **Fix:** `git push origin main`, then `git pull origin main` inside the sandbox.

### Symptom 4
`pip3 install -r requirements.txt` partially failed.
- **Real cause:** `asyncpg` and `psycopg2-binary` (added for a *future* Postgres migration, not needed today) failed to compile their C extensions against the sandbox's Python 3.14 — a genuine version incompatibility. Because pip's install is all-or-nothing, this *also silently blocked* `fastapi` from installing.
- **Fix:** installed only what's actually needed for current SQLite-mode operation (`fastapi uvicorn python-dotenv rq redis stripe`), skipping the Postgres-only packages.

### Symptom 5 (false alarm, but wasted real time)
A shell polling script appeared to hang indefinitely on the slowest module, printing hundreds of blank `running: ...` lines.
- **Real cause:** not a hang. The job had actually completed in 3.5 minutes — the polling *script's* inline JSON parser was choking on control characters in the large response and failing to print the real status.
- **Lesson:** this exact failure mode happened twice across this build. Always verify directly against `get_job()` in Python before assuming the pipeline itself is broken.

### The single biggest lesson from this entire saga, stated as a rule

**Local fixes do not exist anywhere else until explicitly pushed, pulled into the deployment target, and the environment rebuilt** (dependencies reinstalled, process restarted). This gap is invisible until something breaks. Always specify *where* something is fixed — local-only, pushed, or actually deployed — these are not interchangeable.

---

## 23. Project discipline rules — the non-negotiables

These are derived from the build history above. They are not preferences. Treating any of them as preferences has cost real time and real trust on this project.

1. **Diagnose before fixing.** Always. The investigation prompt for ACT-2 is written and *not yet run* on purpose — fixing without diagnosing has cost time on this project before.

2. **Verify on a real live call, on the real running system, with real data — every fix. Every time.** Self-reports from AI agents that "the fix worked" are not evidence. The build history has multiple instances of trusting a self-report and discovering the fix didn't actually run.

3. **Never bundle two changes into one session.** Architectural decisions, refactors, and feature additions go in their own session each. The cost of debugging "which of the three things I changed broke it" is high enough to dwarf the time saved by combining.

4. **Before re-running any "fix and verify" session, grep for existing definitions first.** This project has had near-misses where a fix was almost reapplied, risking silent duplicate function definitions that would have shipped.

5. **No paid infrastructure spend before real paying users exist.** Firm rule. Render/Fly free tier is the correct host until paying users justify Hetzner/paid infra.

6. **Treat external AI analysis of "the product" with suspicion until you confirm it was given NAILIT's *real* architecture** — not a generic one-paragraph description. Two separate Hermes runs already demonstrated how easily this goes wrong (see Section 24).

7. **The founder's instinct to push back on scope creep, spend, or a suspiciously bad/good external score has been correct every time it happened in this project's history.** Don't argue past it — investigate it.

8. **Push, pull, restart.** Local fixes are not deployed fixes. Always specify which state something is in.

9. **Single-source-of-truth documents are explicitly versioned.** This document supersedes the prior six. When a new SSOT is generated, mark the old ones as superseded; don't delete them, but don't read them either.

---

## 24. The two external Hermes reports — what they got wrong and the one thing they got right

**Context:** the founder deliberately sought outside validation by running NAILIT's concept through an external AI pipeline tool ("Hermes" in conversation), twice. The first run produced a 5.5/10 score. The second produced an unscored "real analysis" that was more flattering.

**Critical finding: neither report analysed NAILIT.** Both were given a generic one-paragraph "AI interview prep" prompt and **invented their own hypothetical product from scratch**:
- Different segments (FAANG Aspirant, Rejection Recoverer, etc.) — none overlapping with NAILIT's real internal segments.
- A two-sided insider marketplace NAILIT doesn't have.
- $19/month subscription pricing — NAILIT's actual model is £49–£199 non-expiring credits.
- Praised "voice-based adaptive mock interview" as a current differentiator when it's an explicitly *future, unbuilt* feature.
- Zero awareness of the actual six-module pipeline, Evidence Ledger, hallucination guard, or gap-repair framework.

**The 5.5/10 score is a real, methodologically sound score of a *different, simpler, hypothetical product* — not of NAILIT.**

### What's genuinely useful from these reports despite the mismatch

1. **The RAT methodology itself** — (Probability × Impact) / Cost-of-validation scoring, chain-break logic (fix the ROOT risk before anything downstream), subtractive analysis — is structurally sound and worth reusing for NAILIT's *actual* risks (which is exactly what Sections 12–14 do).

2. **The retention-ceiling concern** (episodic usage caps subscription LTV) is real in general, but **already solved in NAILIT's actual design** — the non-expiring credits model and the Active Multi-Company Searcher / Corporate Talent Developer segments are the structural answer. Hermes re-discovered a problem NAILIT had already designed around, then didn't realise it had been solved because it never saw NAILIT's actual pricing model.

3. **The core caution — "prove differentiation is real before scaling"** — is valid, and is exactly what ACT-2 (story-repetition fix) and ACT-8 (second quality test) are for.

4. **The 17-competitor scan and Claude Code PARITY gap-returner analysis** (Section 9 above) are independently useful and don't depend on the segment invention.

5. **The 29-point checklist methodology and Validation Debt ledger format** (Section 13) are reusable.

### What to do with future external AI reports

- **Always show them the real architecture before asking for analysis.** The six-module pipeline. The hallucination guard. The forbidden-claims layer. The credits pricing. The contribution-database plan.
- **Read the segment list they output as the first sanity check.** If it doesn't match NAILIT's real segments, they invented a different product — discard the segment-specific conclusions, keep the methodology.
- **Don't argue with surprising scores until you've checked what was actually analysed.** Surprisingly-bad scores have been correct *only* about a product NAILIT isn't building.

### The "ChatGPT will just do this for free" risk, resolved precisely

There is no current product, free or paid, that does what NAILIT does. A person manually pasting CV + JD into ChatGPT is a person doing a worse, manual version of one slice of NAILIT's pipeline — not a competing shipped product.

**The mechanically precise distinction:** a foundation model getting better over time absorbs *generation quality* (better-written answers). It cannot absorb *first-party data it never had access to* — specifically, real candidates' after-the-fact reports of what they were actually asked. That data only exists because real people used NAILIT specifically. This is why ACT-3 (the contribution database) is the actual long-term defence, not "a nice to have."


# PART 8 — THE HONEST FEASIBILITY VERDICT AND FORWARD ROADMAP

## 25. The honest final feasibility verdict

**Is this feasible?** Yes — conditionally, and the condition is fully within the founder's control, not an external unknown.

- **The technology works** (verified live, not assumed).
- **The economics are excellent** *pending* resolution of the OpenAI/Claude question.
- **The one real content defect found** (story repetition + boilerplate leak) is narrow, has a clear diagnostic path, and is the same shape as several other bugs this project has already cleanly fixed — evidence of a fixable bug, not a broken architecture.
- **The market structure has shifted in NAILIT's favour** in the last 12 months — honest-prep vs cheating-overlay split is now a recognised distinction in the buyer's mind, and NAILIT is cleanly on the right side of it.

### Does it survive 3–5 years?

**Conditional on exactly one thing:** whether the contribution-capture mechanism (ACT-3) gets built and starts running as soon as auth ships, rather than continuing to be correctly identified, repeatedly, in documentation, and never executed.

This is the project's single greatest long-term risk — not a competitor, not ChatGPT, not the external 5.5/10 score (which scored a different product). Every other open piece — the pipeline, the economics, the safety guardrails — either already works or has a clear, narrow, solo-executable fix path. **The moat is the one component whose feasibility depends on elapsed real-world time, which cannot be rushed**, and is therefore the one piece where delay has a real, compounding, unrecoverable cost.

### Can a solo, non-public-facing founder build and defend this without a team or outside funding?

Yes — specifically because:
1. The moat-building mechanism is a one-time narrow build, not an ongoing labour-intensive task.
2. Seeding it requires only a small first cohort reachable through quiet, written engagement, not personal branding or video content.
3. The market tailwinds (honest-prep positioning, copilot-category reputation collapse) reduce the need for loud distribution.

---

## 26. Forward roadmap — what to do, in time windows

### Next 7 days
1. **Pick auth provider** (Clerk vs Supabase) in a 1-hour decision session. Don't bundle with implementation.
2. **Start ACT-1 (auth implementation)** in a fresh session, separately.
3. **In parallel, run the ACT-2 investigation prompt** (read-only, diagnose-only).
4. **Build the landing page** for Week 1 validation. Headline + sub + CTA + pricing display. No backend needed yet.
5. **Draft the interview discussion guide** from Appendix C below; identify 5 candidate interviewees to contact from your existing network.

### Next 30 days
1. Complete ACT-1 (auth shipped, sessions tied to users).
2. Complete ACT-2 (story-repetition fix verified on a fresh test).
3. Complete ACT-3 (contribution capture endpoint live, email trigger wired).
4. Run the 15 user interviews per Section 21.
5. Run $50 traffic test against the landing page.
6. Hold the ACT-5 OpenAI/Claude decision session and commit a written decision.
7. Move off Daytona to Render or Fly.io free tier (ACT-4).

### Next 90 days
1. ACT-6: Stripe products live, Resend wired, real checkout flow.
2. ACT-7: UX state-signaling polish.
3. ACT-8: second independent quality test on a different JD/CV.
4. First 20–50 real users acquired through quiet, written outreach.
5. First contribution rows accumulating in the database.
6. Retention measurement begins: how many of the first 20 buy a second credit pack?
7. Decision point: based on the data, either continue solo or bring in fractional growth help.

### Year 1
- Goal: contribution database reaches enough volume to be visibly valuable as a dataset.
- Goal: revenue covers full operating cost (currently ~£0 paid infra, so this is achievable with a small paying base).
- Optional: introduce ex-employee marketplace as a credits-priced upsell *if* validation supports it.
- Optional: voice mock interview as a credits-priced upsell *if* text product retention proves the willingness-to-pay-more thesis.

### Year 2–3
- Contribution database becomes the discussed asset, not the prep packs.
- Acquirer interest becomes a realistic question — not because NAILIT is for sale, but because the dataset's independent value to recruiting platforms and AI labs is real.
- Distribution can transition from hand-rolled to fractional-led, funded by revenue not capital.

---

## 27. Final warnings for whoever picks this up

(These are the supreme operating rules. If a conflict ever arises between something in the body of this document and one of these warnings, the warnings win.)

1. **Do not recommend paid infrastructure spend before real paying users exist.** Firm project principle, not an open question.
2. **Do not trust an AI agent's self-report that a fix works.** Verify on the real running system with real data — every fix in this project that skipped this step eventually caused a worse problem than the one it was meant to solve.
3. **Before re-running any "fix and verify" session, grep for existing definitions first.** Near-miss duplicates have happened.
4. **Treat any future external AI analysis of "the product" with suspicion until you confirm it was actually given NAILIT's real architecture** — not a generic paragraph. Two separate Hermes runs already demonstrated how easily this goes wrong.
5. **The founder's instinct to push back on scope creep, spend, or a suspiciously bad/good external score has been correct every time it happened in this project's history.** Don't argue past it — investigate it.

---

# APPENDICES

## Appendix A — Competitor pricing reference (June 2026, refreshed)

**⚠️ Pricing conflict flagged, not resolved.** Two independently-sourced competitive analyses in this project give different numbers for **Big Interview** and **Final Round AI**. Rather than silently pick one, both are shown below with their source. **Verify against the live pricing page before using either number in investor or public-facing materials** — pricing pages change often and both sources claim direct verification.

| Competitor | Price (Firecrawl scrape, competitive-analysis-2026-06-23.md) | Price (later web search, this document's original pass) | Model | Company-specific? | AI feedback depth | Notes |
|---|---|---|---|---|---|---|
| ChatGPT | Free / $20/mo | — | Subscription | ❌ No | Low (generic) | Critical #1 free competitor |
| Claude | Free / $20/mo | — | Subscription | ❌ No | Low–Med | Same category as ChatGPT |
| YouTube | Free | — | Free | Partial (experience reports) | ❌ None | |
| Glassdoor / Comparably | Free | — | Free | Partial — **actively managed, not just stale** (68% of HR pros manage reputation on these platforms, Section 9a) | ❌ None | Complements rather than competes, but captures the "company research" Job |
| Google Interview Warmup | Free | — | Free | ❌ No | Low | Limited but free supplement |
| Pramp | Free + paid (~$150/yr Premium per Firecrawl) | — | Freemium | ❌ No | Peer-based | Free supplement |
| Four-Leaf | $5 one-time 5-day pass OR $20/mo Pro, 3-day free trial no card | — | Subscription | ❌ No | Medium | Aggressive pricing; **HIGH threat** — direct price-point competitor |
| Interview Sidekick | ~$10/mo premium | — | Freemium | ❌ No | Med (10K+ questions) | New aggressive entry |
| CleverPrep | $19 Instant Prep / $29 Pro (3 mocks) / $39/mo Premium | — | One-time/subscription | ❌ No | Low–Med | |
| Yoodli | Free trial / ~$25/mo | — | Freemium | ❌ No | Med (delivery only — speech, filler words, tone, pacing) | NOT interview-specific; enterprise clients include Google, Sandler |
| InterviewBuddy | — | $29–99/mo | Subscription | ❌ No | Med | Mock-interview prep B2C |
| **Big Interview** | **$39/mo (30-day "BootCamp") / $99 (3-month "Accelerator") / $299 (lifetime "Pro")** | **$79/mo or $349/yr** | Subscription | ❌ No (generic playbooks) | Low–Med | 2M+ users, 170+ video lessons. **CONFLICT — verify current tier pricing before use.** |
| Revarta | Tiered, not publicly listed | — | Subscription | ❌ No | High (hiring-manager-calibrated) | Closest philosophical competitor |
| Verve (verveai.io) | ~$20–40/mo | — | Subscription | ❌ No | Med | Structured coaching workflows |
| Exponent (formerly Pramp) | ~$72–96/yr | — | Subscription | Partial (Google/Amazon/Microsoft static guides) | Medium | Tech-only (PM/eng/DS/design) |
| Parakeet AI | $74.90/mo | — | Subscription | ❌ No | High (coding focus) | Technical/coding interviews |
| VMock | Free (via university) / $109 individual | — | B2B2C/individual | ❌ No | Low–Med | University distribution channel |
| Road to Offer | Free tier (1 case + unlimited drills) / paid for unlimited | — | Freemium | ❌ No | **HIGH — 7-dimension grading, Voice Mode** | Consulting-only (MBB); the AI-feedback gold standard to benchmark against |
| CaseWithAI | Free trial + paid | — | Subscription | ❌ No | Medium — "AI struggles with nuanced probing" | Consulting niche |
| CaseStudyPrep.AI | Free trial / ~$15 per case | — | Pay-as-you-go | ❌ No | Medium | Ex-MBB-written cases; per-case pricing gets expensive at volume |
| CaseTutor | Free trial + subscription | — | Subscription | ❌ No | Medium — voice interaction, transcript review | Consulting niche, narrow drill library |
| MBB.AI | Tiered subscription | — | Subscription | ❌ No | Medium — adaptive practice paths | Consulting niche |
| University Career Services | Free (for students) | — | Free | ❌ No | Human, quality varies | Slow scheduling, not tech-savvy, but captures the free-tier market |
| Sensei Copilot | Free + paid | — | Freemium | ❌ No | Med | Content-marketing moat, off-strategy content funnel |
| CoPilot Interview | Free tier + low paid | — | Freemium | ❌ No | Med | Free-tier competitor in the copilot category |
| Cluely | Various | — | Live overlay | ❌ No | N/A (copilot) | ~753K monthly visits, viral 2025 launch, brand-awareness leader |
| **Final Round AI** | **$299/mo (down from $499), Lifetime available** | **$90–$148/mo, up to $488 "God Mode"** | Subscription | ❌ No | N/A (copilot, not prep) | **CONFLICT — verify current pricing.** Both sources agree on the pattern regardless of exact figure: **17–40% negative reviews, auto-renew complaints, billing disputes** (Section 8). |
| OphyAI | $148–488/mo | — | Subscription | ❌ No | N/A (copilot) | Real-time assistance during live interviews, not prep |

**Honest-prep sweet-spot pricing band:** $15–25/month equivalent (£15–25 equivalent) — "better than free ChatGPT" but "not as expensive as Big Interview" at either cited price point. NAILIT's credit model is structurally distinct (non-expiring), placing it cleanly outside the auto-renew complaint trap regardless of which Big Interview / Final Round AI figures turn out to be current.

**What NAILIT must beat, stated concretely (from the Firecrawl competitive analysis):**
- **To beat ChatGPT:** company-specificity (ChatGPT is generic), feedback depth (ChatGPT says "be more specific"; NAILIT should say "your answer lacks the technical depth Google expects at L4 — add a system design component"), structured flow (ChatGPT is a blank page; NAILIT is guided research → practice → feedback → improve).
- **To beat Four-Leaf ($20/mo, the closest price-point competitor):** company-specific research (Four-Leaf is generic) and feedback quality good enough to justify the price gap.
- **To beat Big Interview:** AI-first rather than video-first positioning, real company-specificity vs. generic playbooks, and (once built) real-time mock interview vs. Big Interview's lack of one.

**Recommended direct product testing (from the Firecrawl analysis, not yet done):** sign up for Four-Leaf's $5 five-day pass and Big Interview's trial to test their actual AI feedback quality firsthand; run the same JD/CV through ChatGPT to see exactly what NAILIT is being mentally compared against; review Road to Offer's 7-dimension grading system as the benchmark for feedback depth; check whether Yoodli has an API worth partnering with for speech analysis rather than building it in-house.

---

## Appendix B — Interview kit (15 user interviews for validation)

### Screening questions (4)
1. *"In the last 3 months, how many job interviews have you had or been preparing for?"* (PASS: 2+)
2. *"How do you currently prepare for interviews? Walk me through your last prep process."* (PASS: describes a specific process)
3. *"Have you ever paid for any tool, course, or service to help with interview prep?"* (PASS: yes, or considered it)
4. *"What's the most frustrating part of preparing for interviews right now?"* (PASS: specific frustration)

### Interview questions (20 total — 5 per RAT card)

#### RAT Card 1 — "Free is Good Enough"
1. Walk me through the last time you prepared for an interview. What did you do?
2. What tools or resources did you use? How did you find them?
3. How did you feel AFTER preparing? What was still missing?
4. What did [YouTube/ChatGPT/friends] NOT give you that you wished it did?
5. Have you ever paid for anything to help with interview prep? What made you decide?

#### RAT Card 2 — "Episodic Use = No Habit"
1. How long did your last job search last? How many interviews?
2. During your search, how often were you actively preparing?
3. After you got the job, did you keep using any tools?
4. If there was a tool that helped with interviews AND career growth, would you use it?
5. What do you do NOW between job searches to develop your career?

#### RAT Card 3 — "AI Quality Gap"
1. When you researched a company before an interview, what did you look for? Where?
2. Did you ever find wrong or outdated information? What happened?
3. What would "perfect" company research look like?
4. How long did you spend researching? Was it worth the time?
5. If an AI gave you a 2-page company summary — would you trust it? What would make you trust it?

#### RAT Card 4 — "Feedback Not Worth Paying For"
1. After your last interview, did you get any feedback? From who?
2. When you practise answering questions, how do you know if your answer is good?
3. Have you ever practised with ChatGPT? What did it tell you?
4. What would make feedback valuable enough to pay for?
5. If you could get feedback from a real person at [Company] vs AI — which would you prefer?

#### RAT Card 5 — "Marketplace" (DROPPED — exploratory only)
1. Have you ever talked to someone who worked at the company you were interviewing for?
2. If you could chat with an ex-employee — what would you ask?
3. Would you pay for a 30-minute session with an ex-employee? How much?

### Coding template
Dual-layer:
- **Layer 1 (Plain):** what they do, how they feel, what they wish.
- **Layer 2 (Methodology):** Core Jobs, Big Job, success criteria, current Solution, Aha Moment gap, Consideration Activators, social context, habit potential, willingness to pay.

### Logistics
- **15 interviews minimum.**
- **20–30 minutes each.**
- **$15–25 gift card incentive.**
- **Channels:** Reddit, Facebook groups, UserTesting, university Discord, TikTok career content, LinkedIn.

---

## Appendix C — API pricing reference (June 2026, current)

Per million tokens, input / output.

### Anthropic Claude
- **Opus 4.8** (newest, released May 2026): $5 / $25 — adaptive thinking, "3x cheaper Fast Mode" at $10 / $50
- **Opus 4.7** (released April 2026): $5 / $25
- **Opus 4.6**: $5 / $25
- **Sonnet 4.6** (workhorse): $3 / $15 — 1M context at standard pricing
- **Haiku 4.5** (fast/cheap): $1 / $5 — 200K context

### OpenAI
- **GPT-5.5** (newest flagship, summer 2026): $5 / $30, $0.50 cached input
- **GPT-5.4**: $2.50 / ~$14
- **GPT-5.3-Codex**: $1.75 / $14
- **GPT-5.2**: $1.75 / $14 (Pro: $21+)
- **GPT-5 mini**: ~$0.25 / – (budget)

### Cost levers worth knowing
- **Anthropic prompt caching: 90% off cached input.** Sonnet 4.6 cache reads = $0.30/M (vs $3/M base).
- **OpenAI cached input:** GPT-5.2 = $0.175/M, GPT-5.5 = $0.50/M cached.
- **Batch API discount: 50% off** on both Anthropic and OpenAI (24-hour turnaround).
- **Long context with no surcharge:** Anthropic Sonnet 4.6 / Opus 4.6+ all support 1M context at standard rate.
- **Reasoning model warning:** o-series and Pro variants charge for hidden "thinking" tokens at output rate; always cap `max_output_tokens`.

### Cost comparison for NAILIT's pipeline shape
NAILIT runs many module calls per session with a *stable per-session context* (CV + JD + company research stays the same). This is exactly the workload prompt caching is designed for.

**Estimated cost for a NAILIT session** (rough, needs verification per ACT-5):
- ~30K stable prefix (CV + JD + company research)
- ~50K module-specific generation across 6+ modules
- ~10K output
- At Sonnet 4.6 with caching: 30K × $0.30/M (cached) + 50K × $3/M (input) + 10K × $15/M (output) = $0.009 + $0.15 + $0.15 = **~$0.31/session** (~£0.24)
- At GPT-5.4 with caching: ~$0.20–0.30/session
- At Haiku 4.5 with caching: ~$0.10–0.15/session

The modelled **£0.78/session** assumed less aggressive caching and probably a Haiku/Sonnet split with Sonnet doing the heavier modules. Real measurement against the live OpenAI invoice is the right next step.

---

## Appendix D — File reference index

What's in the project folder and what each file is for:

- **`NAILIT_MASTER.md` (THIS FILE)** — single source of truth. First compiled June 23, 2026; updated July 3, 2026 to absorb the two files below. Supersedes everything else in this list.
- **`NAILIT_ULTIMATE_HANDOFF.md`** — the prior single source of truth, generated June 23, 2026. Content fully absorbed into this document. Keep for historical reference.
- **`NAILIT-Master-Research.md`** — Hermes + Claude Code research output, June 23, 2026. Useful for: 17-competitor scan, RAT methodology reference, interview kit, validation debt ledger format. Caveat: the segments listed (Career Changer, New Grad, etc.) are *Hermes-invented hypotheses*, not NAILIT's verified user segments — see Section 11 in this document.
- **`2026-06-23-craft-value-proposition-result.md`** — a dedicated, deep-mode NMT (Next Move Theory / Advanced JTBD) analysis run specifically on Segment 5 (laid-off/gap-returner professionals). Fully absorbed into Section 11a of this document — the Critical Chain, both value candidates, all three RAT-VP cards, the behaviour-change classification, and the Stage 1–3 implementation spec (reconciled against the existing ACT-1–8 build plan) all originate here. This is currently the single most rigorously developed piece of segment thinking in the project.
- **`competitive-analysis-2026-06-23.md`** — a Firecrawl-sourced, page-scraped competitive analysis (17 competitors across 4 tiers, real pricing pulled from live pricing pages at time of scrape). Fully absorbed into Section 9 (updated pricing), Appendix A (reconciled against later web-search pricing, conflicts flagged), and the "what NAILIT must beat" framing. Higher data-confidence than the Hermes-only research for pricing specifically, since it scraped live pages rather than relying on general knowledge — but note the pricing conflict flagged in Appendix A between this source and this document's own later web search.
- **`NAILIT_COMPLETE_PMD.md`** — earlier exhaustive build history with DEC-1 through DEC-14 decision log. Now absorbed into this document. Read only if you need maximum granular detail on a specific historical moment.
- **`NAILIT_ADDENDUM_DEFENSIBILITY_FEASIBILITY.md`** — original defensibility reasoning (DEC-15 through DEC-19). Absorbed here in Sections 16–18.
- **`NAILIT_HANDOFF.md`** — earliest, shorter handoff covering philosophy + history. Superseded.
- **`Hermes_NMT_Pipeline_Run.md`** — full Hermes pipeline run archive (all 5 invented segments, 5 RAT cards, interview kit, 29-point checklist). Read as a *methodology reference* for running NAILIT's own RAT, not as a verdict on NAILIT.
- **`answer_bank_condensed.txt`** — working example of a condensed, high-signal answer-bank input (4,160 characters distilled from a 66,000-character source). Used in the live Google/PM quality test. Useful template for explaining the `answer_bank` field's intended size/purpose to future users.
- **`nailit-website.html`** — landing/website draft. Still not received/absorbed as of this update — re-upload if you want it reviewed against the positioning in Sections 8–10.

**Files referenced by name in the source documents but not yet uploaded to this project:** `NAILIT_PMD.md`, `NAILIT_COMPLETE_PMD.md`, `NAILIT_ADDENDUM_DEFENSIBILITY_FEASIBILITY.md`, `NAILIT_HANDOFF.md`, `Hermes_NMT_Pipeline_Run.md`, `nailit-website.html`. Their content is believed absorbed via the Ultimate Handoff's own supersession claim, but if you have the actual files, upload them and this document can verify nothing was missed.

---

## Appendix E — The founder's full answer bank (verbatim, for reference)

This is the actual data the live pipeline test ran against. It is included here for completeness — both as evidence that the pipeline works on real candidate data, and as the canonical example of what a good `answer_bank` looks like.

**IDENTITY:** Operations/programme manager, 8 yrs, cross-functional global delivery. Led team of ~10 across EMEA/NA/APAC, Meta Partnership account at Cognizant. Pattern: diagnose root constraint in unclear systems, leave them measurably stronger.

**METRICS:**
- 34% backlog reduction: cross-regional EMEA/NA/APAC handover system, no authority over regions. Co-designed with regional leads; 2 sceptical leads became advocates via shared data.
- 77%→93% SLA: found hidden calc error (wrong denominator); rebuilt from 3mo raw data. Also found 40% of "closed" cases reopened, distorting the metric. Chose transparency over a quiet fix.
- 40 hrs/wk saved: queue redesign + automated routing; response time down ~1hr/case.
- 14% quality gain: time freed by queue redesign reinvested into quality work.
- 2 SLAs renegotiated, penalties eliminated, ~15% efficiency gain: solo 72-hr KPI gap analysis, manager on leave, no guidelines. Six Sigma: defined problem per KPI, delegated deep-dives, 5 Whys — manager asked me to lead the resulting client meeting.
- CSAT response 10%→~50%: added direct survey link at case closure.
- Agent→SME: diagnosed skill-vs-will gap, built weekly QA + reverse shadowing; top-5 productivity in 3mo, promoted.
- 23% KPI attainment gain (8→12 met): workflow redesign + sustained coaching.

**WEAKNESS:** Bias toward execution over delegation — became a bottleneck. Fixed via mapping responsibilities, weekly SME planning. Earlier-career: difficulty saying no — same fix.

**MANAGER DISAGREEMENT:** Pushed back on plan to terminate an underperformer without recovery attempt; agreed a 4-week plan instead. Agent didn't improve, terminated after — manager was right. Now ask more before disagreeing, use data not instinct.

**COLLEAGUE DISAGREEMENT:** Disagreed with QA lead over inconsistent rubric scoring; raised it with examples, proposed shared calibration — adopted, scores more consistent.

**BAD NEWS:** Told team they needed extended hours, no benefit to them. Led with empathy, gave max notice, monitored morale after.

**TEAM CONFLICT:** Two team members in tension over working styles. Met separately first, then facilitated joint conversation on work not personalities. Resolved, no escalation.

**CALCULATED RISK:** Gave a high-stakes 1-week client task to a new joiner over the most experienced agent, based on observing her investigate beyond her tasks unprompted. She found what others missed.

**FAILURE:** Knew a 3-month delivery timeline was unrealistic but stayed silent. Cost 6mo delivery drag, KPI decline, trust damage. Recovered via transparency, biweekly reviews, revised plan. Now do feasibility review before agreeing to major proposals.

**INCOMPLETE-DATA DECISION:** New project, 2-week launch, no historical data. Assigned 4 agents, monitored 3 months. Data showed overresourced — moved 1 agent elsewhere; team of 3 delivered fine.

**UNPOPULAR DECISION:** Implemented extended-hours coverage, no team benefit. Owned communication, gave reason upfront, recognised effort publicly.

**ABOVE & BEYOND:**
1. Partner had unresolved asset-ownership issue; took ownership outside my role, found right Tier 2 contact, ~1mo coordinating — resolved, leadership recognition.
2. Colleague building a tracker tool had no process knowledge, build behind; wrote a process SOP, ran a joint design session — tool built, adopted globally.

**CRITICISM RECEIVED:** Feedback that presentation detail buried key points. Agreed, switched to headline-first structure. Later presentations better received.

**BAD HIRE LESSON:** Rushed a hire from a thin pool under deadline pressure; issues persisted, terminated in probation. Now flag thin pools proactively rather than rush.

**INFLUENCE WITHOUT AUTHORITY:** Fixed an escalation pattern from a gap with a Tier 2 engineering team I had no authority over. Documented 3 months of data, quantified impact — asked for the meeting only after months of reliably delivering on smaller commitments, so trust existed. Agreed in one meeting, implemented in 2 weeks, escalations dropped materially.

**ROLE:** Operations Manager / Programme Manager / Team Lead, company-agnostic. Background: Cognizant, Meta Partnership account.

---

## Appendix F — Glossary

- **ACT-N:** the ordered action items from Section 19.
- **Aha Moment:** the first moment a user perceives the product's specific value — for NAILIT, the first time they see real company-specific questions plus AI feedback on their own answer that names something they didn't realise they were doing wrong.
- **Boilerplate leak:** a content defect in which generated answers share the same verbatim disclaimer paragraph (one of the two known issues in the live pipeline test).
- **CAC:** Customer Acquisition Cost.
- **Contribution database:** the planned (ACT-3) first-party data store of post-interview question reports. The moat.
- **Daytona:** the dev sandbox NAILIT's backend currently lives in. Not a production host.
- **Evidence Ledger:** the layer that traces every claim and number in generated output back to the candidate's actual source data.
- **Forbidden-claims detection:** the layer that flags claims a candidate must not make in interview given their real background.
- **Gap Map:** Module 4 — identifies real weaknesses without inventing false competence.
- **Hallucination guard:** the layer that strips generated numbers that don't trace to the candidate's source documents.
- **Hermes:** the external AI pipeline tool used for two external "second opinion" runs, both of which invented a different hypothetical product. See Section 24.
- **Lua:** NAILIT's AI coaching persona; the layer that delivers feedback in a consistent 10-field response shape.
- **LTV:** Lifetime Value.
- **Magic link:** passwordless auth via email link, the proposed auth mechanism for ACT-1.
- **MOAT:** the durable competitive advantage; for NAILIT, the contribution database.
- **NMT:** the validation methodology framework used in the Master Research run (Ivan Zamesin's framework — canon = 25%, GO means "go validate").
- **Offer-rate email:** the planned email triggered post-session asking which questions were actually asked. The trigger mechanism for ACT-3.
- **PARITY agent:** the Claude Code agent that ran the gap-returner-focused competitive analysis.
- **Prep Pack:** the output of Modules 1–6 — the synthesised company intel, role decoding, candidate mapping, gap analysis, interview strategy, and Q&A.
- **RAT:** Risk Assessment Table — (Probability × Impact) / Cost-of-Validation scoring.
- **SOM/SAM/TAM:** Serviceable Obtainable / Addressable / Total Addressable Market.
- **Story repetition:** the content defect in which generated Q&A defaults to the same single story regardless of question fit (one of the two known issues).
- **Subtractive analysis:** the RAT method of dropping risks to improve combined survival probability.
- **WTP:** Willingness To Pay.

---

*Compiled June 23, 2026, from: NAILIT_ULTIMATE_HANDOFF.md (the prior single source of truth), NAILIT-Master-Research.md (Hermes + Claude Code research output), and answer_bank_condensed.txt (the founder's verified evidence base). Latest June 2026 market intelligence merged in. Repetitions removed. Source files retained for historical reference per the discipline rules in Section 23.*
