# NAILIT — Project Memory Document (PMD)
**Generated:** June 13 2026
**Conversation span:** May–June 2026
**Project type:** Mixed — technical (software build) + business strategy
**PMD version:** 1.0

---

> **Notable gaps upfront:**
> - The "other idea" the founder mentioned comparing NAILIT against was never disclosed. The comparison was never made.
> - Exact Codex commit history for early pipeline work (messages 0–100) is partially reconstructed from reports, not direct observation.
> - Pack quality on the live production site after the architecture rebuild has not been independently verified by this session — the founder was about to run this test when the PMD was requested.
> - The full prep pack the founder intended to submit for rigorous evaluation was not pasted before the PMD was requested.

---

## Section 0 — Orientation

**What this document is:** A complete knowledge artifact for the NAILIT interview intelligence platform project. It covers the full build arc from prototype through stress-tested backend, business strategy analysis, competitive positioning, regulatory compliance architecture, and the current state as of June 13 2026.

**What a new reader needs to know first:** NAILIT is a solo-founder B2C SaaS product built in Ireland. The backend pipeline is complete and stress-tested. Authentication and payment are not yet built. The product has zero paying customers. The next immediate action is the founder running a real end-to-end quality test using their own CV and a real JD, followed by building minimal auth and Stripe checkout.

**How to use this document:** Read Section 7 (Decisions) and Section 8 (Rejected Approaches) first. Then Section 15 (Action Items) for immediate next steps. Then Section 12 (Risks) before making any strategic decisions.

---

## Section 1 — Goals and Success Criteria

**[GOAL-1]** Build a B2C AI-powered interview intelligence platform that helps professional candidates prepare for high-stakes interviews at specific companies using their real CV and real company research.
Type: [Fact] — primary product goal
Success criterion: A user who completes a full prep pack and practices with Lua at least three times receives an offer at their target company at a rate meaningfully above baseline.
North star metric: Offer rate — percentage of users who complete a full pack and practice three Lua rounds and report an offer within 90 days.

**[GOAL-2]** Reach first paying customer within 6–8 weeks of the stress test completion date (June 2026).
Type: [Decision]
Success criterion: One real person pays real money, uses the product end to end, and receives the 30-day offer rate follow-up email.

**[GOAL-3]** Build a defensible moat through a proprietary interview question database built from user contributions.
Type: [Decision]
Moat milestone: Genuinely defensible at approximately 500 contributing users. Category-defining at 5,000+ contributors.
Current state: Zero contributors. Database schema not yet built. Requires auth to associate contributions with users.

**[GOAL-4]** Achieve 90%+ gross margin on a per-session basis.
Type: [Fact — verified]
Verified economics: AI cost per session approximately £0.78 using Claude Haiku 4.5 for Modules 1–4 and Claude Sonnet 4.6 with prompt caching for Module 5. Total variable cost including Tavily and Stripe approximately £3.50 per session. At £49 session price, contribution margin is 93–95%.

---

## Section 2 — Project Context

**Product name:** NAILIT
**Founder:** Solo founder, based in Ireland, introvert, non-technical (builds using Claude Code and Codex)
**Stage:** Prototype complete. Zero paying customers. Backend stress-tested. Auth and payment not built.
**Primary market:** Ireland and UK at launch. US expansion when fundraising.
**Legal jurisdiction:** Irish company. Irish Data Protection Commission is primary GDPR regulator.
**Infrastructure:** Next.js on Vercel (frontend), FastAPI on Daytona (current — migration target is Hetzner VPS), SQLite (current — migration target is PostgreSQL on Supabase), Redis Queue via Upstash, Claude Sonnet 4.6 + Haiku 4.5, Tavily for research, Stripe for payments.

---

## Section 3 — Stakeholders

**Founder / Builder:** Solo. Owns all decisions. Non-technical — uses Claude Code and Codex for all development.
**Primary customer segment (Step-Up Candidate):** Professional aged 28–38, currently employed at mid-tier company, just received first-round invitation at a company they consider a significant step up. 2–6 weeks to prepare. High willingness to pay. Trigger is the invitation email.
**Fractional CTO:** Planned — not yet hired. Target timing: after first 20 paying customers.
**Investors:** Not yet engaged. Target: Irish pre-seed or YC when traction exists.

---

## Section 4 — Requirements

**[REQ-1]** The prep pack must be company-specific, not generic. It must contain real signals about how the specific target company interviews by round. [Fact]

**[REQ-2]** The prep pack must be CV-grounded. Every answer must be drawn from the candidate's real experience, not invented careers. [Fact]

**[REQ-3]** The gap repair scripts must be verbatim — words the candidate can actually say when pressed on a weakness, not advice about what to say. [Fact]

**[REQ-4]** The product must deliver an aha-moment before Module 6 completes. Specifically: one danger question surfaced after Module 2, one verbatim gap repair script surfaced after Module 4. [Decision — implemented]

**[REQ-5]** The product must be legally compliant with GDPR before taking money from European users. Minimum viable compliance: privacy policy, data deletion endpoint, 90-day retention policy, consent checkbox, DPAs with processors. [Decision — partially implemented]

**[REQ-6]** All Lua coaching endpoints must require authentication. [Decision — implemented. 22 endpoints patched.]

**[REQ-7]** Raw CV must not be stored after prep pack generation. Only structured artifacts stored. [Decision — not yet implemented. Currently raw CV is stored in the sessions table.]

---

## Section 5 — Constraints

**[CON-1]** Solo founder. No team. All builds must be executable via Claude Code or Codex with well-specified prompts. Build complexity is constrained by what a solo non-technical founder can direct and review.

**[CON-2]** Bootstrapped. No external funding. Infrastructure costs must stay under £100/month until first revenue. Current monthly costs: Vercel Pro £20, Hetzner VPS (planned) ~£20, Supabase free tier, Upstash free tier, Tavily free tier (1,000 credits/month).

**[CON-3]** Tavily free tier: 1,000 API credits per month. One session uses approximately 35 credits (free tier config). Limit reached at approximately 28 sessions per month on free tier. Starter tier ($20/month) covers approximately 150 sessions. [Fact]

**[CON-4]** Glassdoor blocks automated scraping. NAILIT does not scrape Glassdoor directly. Tavily is used as a search intermediary — this is legally clean (Type 1 data access) but quality is non-deterministic. [Fact]

**[CON-5]** Claude Code and Codex context window limits. Long sessions require compact, targeted prompts. Each session must specify exact files to read using grep, not full file reads.

**[CON-6]** Daytona is a development workspace host, not production. It sleeps when idle, has no SLA, and will fail under concurrent load. Migration to Hetzner VPS is required before real users. [Fact — migration not yet executed]

**[CON-7]** Ireland-based incorporation. Enterprise Ireland grants available. Delaware C-Corp needed for US investment — not yet incorporated.

---

## Section 6 — Assumptions

**[ASM-1]** The Step-Up Candidate (professional aged 28–38 with a step-up invitation) is willing to pay £49–£199 for company-specific, CV-grounded interview preparation. [Assumption — not yet validated by paying customers]

**[ASM-2]** Offer rate will be measurably above baseline for users who complete all six modules and practice with Lua at least three times. [Hypothesis — not yet measured]

**[ASM-3]** Prompt caching reduces Module 5 token cost by approximately 60%, making the per-session AI cost approximately £0.78. [Assumption based on Anthropic published pricing — not yet verified in production at scale]

**[ASM-4]** CleverPrep ($19 one-time) does not have verbatim gap repair scripting, Evidence Ledger, or human expert review layer. This is NAILIT's primary differentiation. [Assumption — not independently verified since June 2026]

**[ASM-5]** Research quality for top-50 most-interviewed companies (Google, McKinsey, Goldman, Amazon, Meta) is sufficient for a genuinely useful prep pack. Research quality degrades significantly for companies outside the top 50. [Assumption based on architecture analysis — not verified by systematic quality audit]

**[ASM-6]** The 18–24 month window before LinkedIn or a well-funded competitor builds something similar remains open as of June 2026. [Assumption]

---

## Section 7 — Decisions and Rationale

**[DEC-1]** Use Claude Haiku 4.5 for Modules 1–4 and Claude Sonnet 4.6 for Module 5.
Status: Active
Rationale: Haiku is cheaper for extraction and analysis tasks. Sonnet is required for Module 5 (interview strategy) which requires highest-quality reasoning. Prompt caching on the repeated system prompt and context reduces Module 5 cost by approximately 60%.
Alternatives considered: GPT-4o (see REJ-1), all-Sonnet (higher cost, no quality benefit on extraction modules)
When: Mid-conversation, after AI pricing research

**[DEC-2]** Use credits model for pricing, not pure subscription.
Status: Active
Rationale: Interview prep is episodic not recurring. Monthly subscription feels wrong to a user who doesn't need the product for 20 months then needs it urgently for 6 weeks. Credits match the natural usage pattern. Heavy users pay proportionally more.
Pricing tiers: Free (1 lifetime session), Starter (£89/3 sessions, never expire), Monthly (£49/month, 5 sessions, 1-month rollover, £18/session extras), Premium (£199/10 sessions, never expire).
Credits system built: Yes. Not yet wired to payment flow.

**[DEC-3]** Use LiveKit as voice infrastructure for future voice mock interview layer.
Status: Active — deferred to month 2–3 post-launch
Rationale: LiveKit is open-source, handles 90% of production voice agents in 2026, can be self-hosted to eliminate per-minute fees at scale. Cost: approximately £1.20 per 25-minute mock interview session.
Stack decision: LiveKit + Deepgram Nova-3 (STT) + Claude Sonnet 4.6 (interviewer brain) + Cartesia Sonic (TTS at $0.03/min vs ElevenLabs $0.18/min)
Alternatives considered: Vapi (complex pricing, £0.20–0.33/min loaded), Bland AI (less reliable), Retell AI (good but vendor lock-in)

**[DEC-4]** Use Lua as text-based coaching persona now. Add voice layer later.
Status: Active
Rationale: Text Lua is already built. Voice adds LiveKit infrastructure complexity and new failure modes. Validate text Lua with real users before adding voice. Voice is a premium add-on, not a replacement.

**[DEC-5]** Do not scrape Glassdoor directly. Use Tavily as search intermediary only.
Status: Active
Rationale: Direct scraping violates Glassdoor ToS (section 2.3) and risks legal exposure. Tavily as intermediary is legally equivalent to a human using a search engine (Type 1 data access). Indirect legal exposure is minimal.
Long-term mitigation: Build proprietary question database from user contributions to reduce Glassdoor dependency entirely.

**[DEC-6]** Build user-contributed question database from session one.
Status: Active — not yet implemented (requires auth first)
Rationale: This is the primary moat. After each session ask which questions actually appeared in the real interview. Over time this produces a dataset no competitor can scrape or buy. Defensible at ~500 contributors.

**[DEC-7]** Ireland as primary incorporation. Delaware C-Corp as subsidiary when raising US money.
Status: Active
Rationale: Irish 12.5% corporate tax, Enterprise Ireland grants, lower cost base. US investors require Delaware structure — add it when fundraising, not before.

**[DEC-8]** Solo founder until first 20 paying customers. Fractional CTO after traction.
Status: Active
Rationale: No team payroll risk. Fixed costs minimal. Risk of moving too slowly exceeds risk of moving alone. A fractional CTO (2–3 days/week, £2,000–4,000/month, 0.25–0.5% equity with 1-year cliff) is the right first hire after traction.

**[DEC-9]** No human expert review layer until AI product is proven.
Status: Active
Rationale: Human layer amplifies a good product. Cannot rescue a broken one. Build AI to 9/10 quality first. Add humans to get from 9 to 10.
When human layer is built: Recruit former employees (not current) to avoid conflict of interest. Former Google/McKinsey/Goldman employees 1–5 years post-departure. Reviewer agreement: no confidential information, public information only, conflict declaration, employer identification withheld.

**[DEC-10]** GDPR minimum viable compliance before taking money from EU users.
Status: Active — infrastructure built, not yet complete
What is built: Privacy policy (PRIVACY.md), data deletion endpoint, data export endpoint, 90-day retention job, DPA instructions documented.
What is missing: Consent checkbox at session create, user_email not populated (requires auth), DPAs not yet signed with Anthropic/Vercel/Supabase.

**[DEC-11]** Activation layer: surface micro-value moments before full pack delivery.
Status: Active — implemented
Rationale: Sequential job chain means value only arrives at Module 6 completion. Customer's internal investor accumulates cost without proof during 12–15 minute pipeline. Micro-value moments reduce dropout and increase free-to-paid conversion.
Implementation: Danger question after Module 2 (danger_zones[0].requirement). Verbatim gap repair script after Module 4 (repair_scripts[0].verbatim_repair_answer). Both dismiss on click or when Module 6 completes.

**[DEC-12]** PostgreSQL via Supabase replacing SQLite. Redis Queue via Upstash replacing threading. Hetzner VPS replacing Daytona.
Status: Active — abstraction built, migration not yet executed
Rationale: SQLite serialises writes — breaks under concurrent load at ~25 users. Daytona sleeps, has no SLA, fails under concurrent load. Migration is triggered by setting DATABASE_URL and REDIS_URL environment variables — get_db() handles the rest automatically.

**[DEC-13]** Use Next Move Theory (Ivan Zamesin) AJTBD methodology as strategic framework.
Status: Active
Repo: https://github.com/zamesin/Next-Move-Theory-Canon-and-Skills
Installed skills: /ask-nmt, /market-research, /craft-value-proposition, /product-requirements, /craft-go-to-market
CLAUDE.md to be added to NAILIT project root to make all future Claude Code sessions methodology-aware.

---

## Section 8 — Rejected Approaches

**[REJ-1]** GPT-4o for all modules
Rejected because: More expensive than Claude Sonnet 4.6 for equivalent quality on long-context reasoning. Claude Haiku 4.5 is significantly cheaper for extraction modules where reasoning depth is not required.
Could reconsider if: Anthropic pricing increases materially or OpenAI releases a significantly better model at lower cost.

**[REJ-2]** Monthly subscription only pricing
Rejected because: Interview prep is episodic. Heavy users (10 sessions/month) would cost £50 in AI against £99 revenue — destroys margins at scale. Mismatches natural usage pattern of the Step-Up Candidate who interviews in bursts.
Could reconsider if: Product evolves into a career intelligence subscription used monthly not just during active interviews.

**[REJ-3]** Current employees as human expert reviewers
Rejected because: Current Google employee reviewing Google interview materials is a direct conflict of interest. Employment contracts at major firms typically prohibit this and it is grounds for termination. Legal exposure for reviewer and reputational risk for NAILIT.
Alternative: Former employees 1–5 years post-departure. No current conflict. Enforceable non-competes extremely rare in Ireland/UK for this type of work.

**[REJ-4]** Micro1's candidate data harvesting model
Rejected because: Micro1 posts fake job listings to harvest candidate data. This is deceptive. Reddit threads confirm significant negative word of mouth from candidates who felt misled. NAILIT's customers share CVs and career insecurities — this requires deep trust. Deception in acquisition is incompatible with that trust requirement.
What was taken from Micro1: The concept of turning successful users into expert contributors (the flywheel), the AI vetting interview concept for reviewer recruitment.

**[REJ-5]** Vapi for voice infrastructure
Rejected because: £0.20–0.33/minute fully loaded (headline $0.05/min is misleading). Complex multi-vendor pricing. Non-technical users find setup overwhelming.

**[REJ-6]** Bland AI for voice infrastructure
Rejected because: 800ms latency. More outages than competitors in 2025–2026. Less reliable than LiveKit or Retell.

**[REJ-7]** Daytona as production server
Rejected because: Development workspace host. Sleeps when idle. No SLA. Will fail under concurrent load at ~10 users. Not suitable for production.

**[REJ-8]** SQLite in production
Rejected because: Serialises writes. Will cause visible slowdowns at ~25 concurrent users. Not a production database for multi-user web product.
Note: SQLite remains as fallback when DATABASE_URL is not set — appropriate for local development.

**[REJ-9]** Building voice mock interview before text Lua is proven
Rejected because: Voice adds LiveKit infrastructure complexity, new failure modes, and operational cost before the core product is validated. Text Lua must be proven with real paying users first.

**[REJ-10]** Adding OpenClaw (personal AI agent runtime) to NAILIT
Rejected because: OpenClaw is a personal agent runtime, not relevant to NAILIT's interview intelligence use case. The quality fixes to the pipeline are what matters, not adding another AI orchestration layer.

**[REJ-11]** Building B2B corporate tier before B2C is proven
Rejected because: B2B has a longer sales cycle, different buyer, different product frame. Build B2C revenue first. Design architecture to support B2B but do not build it yet.

---

## Section 9 — Architecture and Technical State

**Pipeline architecture (6 modules, sequential):**
1. Company Intelligence — researches target company across 30+ sources via Tavily
2. Role Intelligence — decodes JD into must-prove signals by round
3. Candidate Profile — maps CV to 17+ provable stories, transferable bridges, forbidden claims
4. Gap Map — produces verbatim gap repair scripts for biggest weaknesses
5. Interview Strategy — generates 12+ round-organised questions with full answers, Evidence Ledger
6. Prep Pack — assembles everything into structured output

**Phase 2 (answer cards):** Three elite answer options per question — safest, strongest stretch, bold top 1%. Grounded in real CV. Plausible story detail within candidate's career lane. Built — not fully verified in production.

**Phase 3 (Lua coaching):** Per-answer feedback on structure, content, company alignment. Shows what was strong, what to improve, better version, next action. Returns 10 keys confirmed: structure_score, content_score, company_alignment_score, overall, what_was_strong, what_to_improve, better_version, next_action, score_out_of_10, voice_and_delivery_coaching.

**Phase 4 (mock interview):** Sequential question presentation, no prep pack visible, session scoring, readiness report. Built — not fully stress-tested.

**Confirmed working (stress test — 17/17 tests passed):**
- Tavily retry logic: 3 attempts with 2s/5s backoff, returns [] on exhaustion, never crashes
- Lua response: all 10 keys confirmed
- Error handling: all endpoints return {error, status_code} not {detail}
- Corrupted artifact: raises ValueError with clean message
- Stale cleanup: delete_old_jobs(days=7) runs at startup
- SQL injection: parameterised queries throughout
- Unicode/emoji: round-trips clean
- Concurrent sessions: 5 simultaneous creates, no collisions
- Double module run: atomic get_or_create_job prevents duplicate jobs
- Out-of-order modules: HTTP 400 immediately with clear dependency message
- 20 concurrent SQLite reads: no locking errors
- Credits overdraft: ValueError raised correctly
- Stripe webhook: rejects invalid signatures
- GDPR delete: removes all data including workspace directories
- Lua auth: 22 endpoints require X-App-Key header

**Not yet confirmed:**
- Phase 2 answer card quality in production with real inputs
- Phase 4 mock interview end-to-end
- Research quality for non-top-50 companies systematically tested
- Production performance on Hetzner VPS (migration not yet executed)

**Key files:**
- agent_v2.py — pipeline logic, tavily_with_retry, read_module_artifact
- api.py — FastAPI endpoints, Stripe webhook, GDPR endpoints, dispatch_job, get_or_create_job
- job_store.py — SQLite/PostgreSQL abstraction, credits functions, GDPR functions, cleanup jobs
- lua_coach.py — Lua coaching logic, adapt_lua_response
- app/page.tsx — Next.js frontend, PostHog events, activation hints
- research_config.py — Tavily tier config (free/starter/production), one-line tier switching
- Dockerfile, docker-compose.yml — production deployment configuration

**Git state:** Clean. .env not in git (confirmed). Last commits: b65d768, 10fb39c, 5bd21f3, 86dcd32, af96b57, 9938f1a, 2c173e3.

---

## Section 10 — Research and Findings

**Market size:** Global interview preparation tool market $2.5B in 2023, growing at 11.8% CAGR to $6.3B by 2031. Step-Up Candidate subsegment approximately $800M–$1.2B globally. [Verified Market Research 2025]

**Job market context:** Median time from search to offer hit 108 days in Q1 2026, up 30% from Q4 2025 — longest ever measured. 93% of candidates experience interview anxiety. 84% of job seekers spend money on interview preparation. [Multiple sources, June 2026]

**AI pricing (verified June 2026):** Claude Sonnet 4.6: $3.00/million input, $15.00/million output. Claude Haiku 4.5: $1.00/million input, $5.00/million output. Prompt caching reduces cached input by 90%. Batch processing 50% off. [Anthropic pricing page]

**Competitors confirmed:**
- CleverPrep: ~$19 one-time, company-specific pages, programmatic SEO moat, closest direct competitor
- Final Round AI: generic AI mock interview
- Yoodli: speech coaching, not intelligence — complementary not competitive
- Interviewing.io: human technical interviews, $100–$225/session
- Exponent: $79/month, unlimited sessions, acquired Pramp
- Big Interview: legacy video practice, no AI coaching
- Interview Warmup by Google: free, generic, no research or CV grounding
- HiredKit: dual AI personality (interviewer + coach), no company research

**Key differentiator confirmed:** No competitor combines company-specific research + CV-grounded answers + round-organised question structure + verbatim gap repair + Evidence Ledger + human expert review layer. This combination does not exist in the market.

**Voice infrastructure pricing (verified June 2026):**
- LiveKit fully loaded: ~$0.077/minute (agent $0.01 + LLM $0.0077 + STT $0.0092 + TTS $0.03 + observability $0.01)
- 25-minute mock interview: approximately £1.20 total cost
- LiveKit free tier: 1,000 agent session minutes/month (~33–50 sessions)

---

## Section 11 — Five-Segment AJTBD Analysis

**Segment 1 — Step-Up Candidate (PRIMARY)**
Age 28–38. Just received step-up invitation. 2–6 weeks. High urgency, high WTP.
Big job: Secure a career move that changes life trajectory.
Activation trigger: The invitation email.
TAM subsegment: ~$800M–$1.2B globally.

**Segment 2 — Active Multi-Company Job Searcher**
Interviewing at 3+ companies simultaneously over 2–4 month search.
Big job: End uncertainty by converting interviews to offers at highest rate.
Best served by: Monthly plan with rollover sessions.
LTV 3–5x higher than Segment 1.

**Segment 3 — Consulting/Finance Track Candidate**
MBA students targeting MBB/Goldman/top finance. Highest WTP of any segment.
Big job: Join an elite firm that defines professional identity for a decade.
Price irrelevant against expected salary differential.

**Segment 4 — Career Re-Entrant / Career Changer**
Employment gap or deliberate pivot. Highest emotional intensity.
Big job: Re-establish credibility after non-linear path.
Gap repair framework is uniquely valuable for this segment.

**Segment 5 — Corporate Talent Developer (B2B)**
HR directors, L&D managers at 200–5,000 employee companies.
Big job: Be known as the leader who invests in people's career capability.
Not built yet. Designed into architecture. Build after B2C revenue proven.

---

## Section 12 — Risks

**[RSK-1]** CleverPrep's SEO moat makes NAILIT invisible at launch
Type: Risk | Probability: 4/5 | Impact: 5/5 | Score: 20
CleverPrep is already ranked #1 for 2026 by multiple review sites, has hundreds of programmatic company pages indexed, and publishes competitive comparison content. New domain ranking for competitive interview prep terms takes 6–18 months.
Mitigation: Target uncontested long-tail queries (round-specific prep, gap repair technique). Reddit community presence at near-zero CAC. Human expert review layer as the one feature CleverPrep cannot quickly copy.
Status: Open — no SEO content built yet.

**[RSK-2]** Free-to-paid conversion below 5% because aha-moment arrives too late
Type: Risk | Probability: 4/5 | Impact: 4/5 | Score: 16
Average freemium conversion is 5.6% for AI tools. Without incremental proof of value during the pipeline, customers accumulate cost without reward.
Mitigation: Activation layer implemented (danger question after M2, repair script after M4). PostHog instrumentation in place to measure dropout by module.
Status: Partially mitigated. Not yet measured with real users.

**[RSK-3]** Research quality non-deterministic for non-top-50 companies
Type: Risk | Probability: 4/5 | Impact: 4/5 | Score: 16
Glassdoor blocking is documented and active. Research quality for companies outside the top 50 most-discussed employers degrades to JD-inference only. Silent degradation (polished-looking but generic output) is more damaging than visible failure.
Mitigation: Research confidence indicator showing user which sources were accessed. User contribution question database building over time.
Status: Indicator not yet built.

**[RSK-4]** Offer rate metric cannot validate PMF before founder's runway runs out
Type: Risk | Probability: 3/5 | Impact: 4/5 | Score: 12
Offer rate requires 30–90 day delay. Founder must make go/no-go decisions before data arrives.
Mitigation: 30-day follow-up email infrastructure built. Deep engagement (all 6 modules + 3 Lua rounds) as leading indicator. Personal follow-up with first 5 users by phone not email.
Status: Email stub built. Email provider not wired. user_email not populated (requires auth).

**[RSK-5]** SEO takes too long and paid search CAC exceeds LTV
Type: Risk | Probability: 3/5 | Impact: 4/5 | Score: 12
CPC for high-intent interview prep queries: £4–8. At 3% click-to-free-session conversion and 5% free-to-paid, CAC from paid search is £267–£533 against blended LTV of ~£89.
Mitigation: Community-led growth (Reddit, Blind) as primary channel at near-zero CAC. SEO as secondary amplifier, not primary.
Status: No SEO content built. No Reddit presence built.

**[RSK-6]** Single-founder key person risk
Type: Risk | Probability: 3/5 | Impact: 5/5 | Score: 15
If founder is unavailable for 3+ weeks, product development and customer support stop entirely.
Mitigation: Document everything. Fractional CTO planned after traction. Eventually build team.
Status: Open.

**[RSK-7]** Anthropic/OpenAI API policy change kills a product feature
Type: Risk | Probability: 2/5 | Impact: 5/5 | Score: 10
Model-agnostic code architecture partially mitigates this. Both Claude and OpenAI are available.
Mitigation: Core value is in pipeline architecture and data, not any specific model's output. User question database becomes independent of any AI provider over time.

**[RSK-8]** GDPR non-compliance fine from Irish DPC
Type: Risk | Probability: 2/5 | Impact: 4/5 | Score: 8
Irish DPC is one of the most active GDPR enforcement bodies in Europe. Fine range for small startups: €10,000–€500,000.
Mitigation: GDPR infrastructure built. Missing: consent checkbox, DPAs not signed, user_email not collected. Complete before taking first EU payment.

**[RSK-9]** APP_KEY not set in production — Lua endpoints accept any key
Type: Risk | Probability: 4/5 | Impact: 3/5 | Score: 12
If APP_KEY environment variable is empty, the auth function accepts any key. This means anyone with the URL can call LLM endpoints and generate cost.
Mitigation: Set APP_KEY to a long random string in Vercel and on server immediately.
Status: Critical — must be done before any public exposure.

---

## Section 13 — Dependencies

**[DEP-1]** Auth system — blocks: credits wiring, user_email collection, offer rate measurement, question contribution database, GDPR delete by user_id. Must be built before any of these work.

**[DEP-2]** Daytona to Hetzner migration — blocks: concurrent user reliability, production SLA, sleep-free server.

**[DEP-3]** Resend (email provider) — blocks: offer rate email delivery. send_email() is currently a console.log stub.

**[DEP-4]** Stripe products and checkout links — blocks: any revenue. Webhook handler exists but no products created in Stripe dashboard.

**[DEP-5]** PostHog key in Vercel env vars — blocks: analytics recording. Events fire but nothing records.

**[DEP-6]** APP_KEY set in production — blocks: Lua endpoint security. Currently accepts any key.

**[DEP-7]** User question contribution database — depends on DEP-1 (auth). The moat cannot start building without user identity.

---

## Section 14 — Open Questions

**[OQ-1]** What is the actual offer rate for users who complete a full pack and 3 Lua rounds? This is the north star metric and has never been measured. [Open Question]

**[OQ-2]** What is the real free-to-paid conversion rate with the activation layer? The activation layer is built but no real users have gone through it. [Open Question]

**[OQ-3]** Is the prep pack quality on the live production site (after the architecture rebuild) genuinely better than what a candidate could produce alone in 2 hours? The founder was about to test this when the PMD was requested. [Open Question — most urgent]

**[OQ-4]** Which Clerk or Supabase Auth for minimal auth? Decision not made. Both were mentioned as options. [Open Question]

**[OQ-5]** What is the other business idea the founder mentioned? The comparison was never made. [Open Question]

**[OQ-6]** Does the research_config.py credit estimate formula match the documented values? The stress test found discrepancies (starter shows 62 credits, documented as 70; production shows 94, documented as 150). Minor but worth resolving. [Open Question]

**[OQ-7]** Should raw CV storage be eliminated at session create (processing in memory only)? REQ-7 was stated as a requirement but not yet implemented. Current architecture stores raw CV in sessions table. [Open Question]

---

## Section 15 — Action Items

**[ACT-1]** Run real end-to-end quality test on live production site.
Owner: Founder
What: Use real CV + real JD for a role genuinely wanted. Evaluate each section of the prep pack against the quality standard (better than 2 hours solo Glassdoor research?). Score each module separately. Report specific failures.
Deadline: Immediate — before any other build work
Status: Open — founder was about to do this when PMD was requested.

**[ACT-2]** Set APP_KEY to a long random string in Vercel environment variables and on server.
Owner: Founder
Deadline: Today — before any public exposure of the URL
Status: Open — CRITICAL security gap

**[ACT-3]** Set NEXT_PUBLIC_POSTHOG_KEY in Vercel environment variables.
Owner: Founder
Deadline: This week
Status: Open — analytics fire but nothing records

**[ACT-4]** Execute Daytona to Hetzner VPS migration.
Owner: Founder (Claude Code session)
What: Point domain at Hetzner VPS running Docker Compose. Set DATABASE_URL to Supabase PostgreSQL connection string. Set REDIS_URL to Upstash URL. get_db() handles the rest automatically.
Deadline: Before first real users
Status: Open — Docker abstraction built, migration not executed

**[ACT-5]** Build minimal auth using Clerk or Supabase Auth.
Owner: Founder (Claude Code session)
What: Email + magic link authentication. Populates user_id and user_email at session create. Enables credits wiring, offer rate email, GDPR compliance, question contributions.
Deadline: After ACT-1 quality test passes
Status: Open — most important remaining build session

**[ACT-6]** Wire Stripe checkout to pricing page.
Owner: Founder (Claude Code session + Stripe dashboard)
What: Create 3 products in Stripe dashboard manually. Add checkout links to frontend pricing page. Webhook handler already exists.
Deadline: After ACT-5 (auth)
Status: Open

**[ACT-7]** Replace send_email() stub with Resend API call.
Owner: Founder
What: Resend free tier (3,000 emails/month). One hour of work.
Deadline: After ACT-5 (auth provides user_email)
Status: Open

**[ACT-8]** Sign DPAs with Anthropic, Vercel, Supabase.
Owner: Founder
What: Available in each provider's dashboard. One hour total.
Deadline: Before taking first EU payment
Status: Open

**[ACT-9]** Add consent checkbox at session create.
Owner: Founder (Claude Code frontend session)
What: "I consent to NAILIT processing my CV data to generate my interview preparation pack."
Deadline: Before taking first EU payment
Status: Open

**[ACT-10]** Run /ask-nmt skill from Next Move Theory repo against NAILIT.
Owner: Founder
What: Paste the prepared prompt into the running /ask-nmt Claude Code session.
Status: In progress — founder had started this session when PMD was requested.

**[ACT-11]** Add CLAUDE.md from Next Move Theory repo to NAILIT project root.
Owner: Founder
What: Makes all future Claude Code sessions methodology-aware without additional prompt engineering.
Status: Open

**[ACT-12]** Build research confidence indicator in prep pack UI.
Owner: Founder (Claude Code session)
What: When fewer than 10 real reported questions found from verified sources, show user "Research-limited: using JD analysis as primary source. Contribute your real questions after your interview."
Status: Open — addresses RSK-3

---

## Section 16 — Lessons Learned

**[LES-1]** Internal Codex test quality consistently reported better than live site quality. When evaluating output quality, always test on the live site with real inputs, never trust internal test results alone. [Fact]

**[LES-2]** Sending the same Claude Code session twice caused duplicate function definitions silently. Always verify with grep before re-sending any session. Compile passes even with duplicate Python definitions — the second one silently overwrites the first. [Fact]

**[LES-3]** Test scripts that test path resolution against the actual file system often fail with FileNotFoundError before reaching the code being tested. Test harness path alignment must be verified before concluding a fix is broken. [Fact]

**[LES-4]** The gap between what a product builder reports and what a user experiences is real and persistent. The live test by the founder (ACT-1) is the only measurement that matters. [Fact]

**[LES-5]** Specifying exact token-efficient prompts (grep first, read only specific lines, one push per session) dramatically reduces Claude Code context window consumption and prevents context compaction failures. [Fact]

**[LES-6]** The activation bottleneck (aha-moment arriving too late) was identified by three independent frameworks simultaneously — JTBD sequential chain analysis, TOC bottleneck analysis, and Lean Startup minimum viable experiment design. When multiple frameworks converge on the same finding, treat it as high-confidence. [Fact]

**[LES-7]** The Lua endpoint key mismatch (0 of 8 contract keys matching between backend and frontend) was a silent failure — Lua appeared to work but returned undefined for every field. Silent failures are more dangerous than crashes because they are harder to detect. Always verify response shapes in a real call, not just a compile check. [Fact]

---

## Section 17 — Future Opportunities

**[FUT-1]** Voice mock interview layer using LiveKit
Why interesting: Premium differentiator at £15–£20 add-on. Context-aware interviewer knows the candidate's prep pack — uniquely better than all generic voice interview competitors.
When: Month 2–3 post-launch, after text Lua is validated with paying users.
Priority: High

**[FUT-2]** Human expert review marketplace
Why interesting: AI-only pack at £49. Human-reviewed pack at £149. £100 uplift, £40–60 paid to reviewer, 72% margin on premium tier.
Recruiting: Former employees 1–5 years post-departure at relevant companies.
When: After AI product proven and first cohort of successful users to recruit from.
Priority: High

**[FUT-3]** User-contributed question database
Why interesting: The primary moat. Defensible at ~500 contributors. Category-defining at 5,000+. Cannot be scraped or bought. Requires auth to build.
When: From session one after auth is built.
Priority: Critical — start immediately after ACT-5

**[FUT-4]** Outcome data collection and offer rate marketing
Why interesting: If offer rate exceeds 60%, the product markets itself. "NAILIT users who completed a full prep pack got offers at X% rate" is the most powerful marketing statement possible.
When: From session one. 30-day follow-up email infrastructure already built.
Priority: Critical — requires ACT-5 and ACT-7

**[FUT-5]** B2B corporate tier
Why interesting: Single corporate account at £800/month generates more revenue than 16 individual subscribers. HR director personal job (status, looking good to leadership) drives purchase decision.
When: After B2C revenue proven. Architecture designed to support B2B already.
Priority: Medium — month 6–12

**[FUT-6]** Fine-tuned domain-specific coaching model
Why interesting: After accumulating outcome data (which answers led to offers, which questions appeared most), training data exists for a model that general-purpose AI cannot match.
When: 3–5 year horizon. Requires 50,000+ real session data points.
Priority: Low — long-term strategic asset

**[FUT-7]** Enterprise Ireland grant application
Why interesting: Non-dilutive funding for Irish-incorporated companies. Available now.
When: As soon as product has first revenue.
Priority: Medium

**[FUT-8]** YC application
Why interesting: Network, credibility, Demo Day access. Worth 7% equity dilution.
When: Apply with real metrics, not a pitch deck. After offer rate data exists.
Priority: High — when traction exists

**[FUT-9]** Programmatic SEO — company-specific prep pages
Why interesting: Captures high-intent search traffic at zero marginal cost.
Risk: CleverPrep already owns much of this SERP territory. Target uncontested long-tail angles.
When: Week 7+ of the 90-day playbook. Not before conversion is proven.
Priority: Medium

---

## Section 18 — Terminology and Definitions

**NAILIT:** The product name. AI-powered interview intelligence platform.

**Lua:** The AI coaching persona. Gives structured per-answer feedback in text coaching mode. Named character. Returns 10 keys: structure_score, content_score, company_alignment_score, overall, what_was_strong, what_to_improve, better_version, next_action, score_out_of_10, voice_and_delivery_coaching.

**Step-Up Candidate:** The primary customer segment. Professional aged 28–38 who just received a first-round invitation at a company significantly above their current employer. The trigger is the invitation email.

**Evidence Ledger:** A section of the prep pack where every claim is traced to its source. Distinguishes confirmed reported questions from JD-inferred questions.

**Gap repair script:** Verbatim words a candidate can say when an interviewer presses them on a weakness. Not advice about what to say — actual words to say.

**Forbidden claims:** Things the candidate must NOT say in the interview given their specific background. Part of the candidate profile and gap map.

**Research Lab:** Earlier name used for the Tavily research pipeline during development. Same as the research layer in the current architecture.

**Daytona:** The development workspace host currently used for the backend. Being replaced by Hetzner VPS.

**get_or_create_job:** Atomic database function using BEGIN IMMEDIATE transaction that prevents race condition when two concurrent requests try to run the same module for the same session. Returns (job_id, created: bool).

**adapt_lua_response:** Adapter function in lua_coach.py that maps internal Lua response keys to the 10-key contract the frontend expects.

**research_config.py:** Configuration file for Tavily tiers. Change RESEARCH_TIER from "free" to "starter" to "production" to change research depth. One-line change.

**PMD:** Project Memory Document — this document.

**AJTBD:** Advanced Jobs To Be Done — the primary strategic framework used throughout this project.

**RAT:** Riskiest Assumption Test — framework for identifying and testing the assumptions whose falseness would kill the business.

**TOC:** Theory of Constraints (Goldratt) — framework for identifying the single bottleneck limiting system throughput.

**NMT:** Next Move Theory — Ivan Zamesin's methodology integrating AJTBD, Unit Economics, RAT, ABCDX, and TOC into one algorithm.

---

## Section 19 — Chronological Development Log

**Phase 1 — Early pipeline (messages 0–43):**
Built async pipeline on Daytona. Fixed 504 timeout errors. Resolved research contamination bug (Atlassian job receiving Canva research). Implemented session-based modular architecture.

**Phase 2 — Quality crisis (messages 44–98):**
Live testing repeatedly showed shallow output, generic answers, template fragments, banned phrases. Multiple targeted fixes applied. Key insight: internal Codex test quality consistently better than live site quality. Root cause: assembly was not populating transcript fields, answer outlines were template shells not real content.

**Phase 3 — Architecture decisions (messages 92–140):**
Session-based modular architecture confirmed correct. Tavily tiered config designed and implemented. Research quality versus quantity debate resolved: quality over quantity, tiered approach. YouTube transcript manual extraction workflow designed.

**Phase 4 — Business strategy (messages 140–200):**
Full AJTBD analysis. 5-segment analysis. RAT top 5 risks. Lean/TOC/Antifragile/ABCDX/OKR master framework analysis. Unit economics verified with real 2026 Claude pricing. Competitive analysis. GDPR regulatory analysis. Pricing model finalised (credits). Cofounder decision (solo until 20 customers). Ireland strategy confirmed.

**Phase 5 — Clean build (messages 200–260+):**
8 Claude Code sessions planned and executed. Sessions 1–4: 5 backend fixes, activation layer, PostHog, offer rate email. Sessions 5–8: Docker/PostgreSQL abstraction, Redis queue, Stripe credits, GDPR compliance. Comprehensive 17-test stress test: all passed. Three bonus fixes (race condition, dependency check, Lua auth on 22 endpoints). 10-key Lua response confirmed. Final state: clean backend, Sessions 5–8 confirmed implemented.

---

## Section 20 — Knowledge Gaps and Warnings

**Gap 1:** Prep pack quality on live production site has not been verified since the architecture rebuild in Phase 5. The quality audits in Phase 2 were run against the old architecture. A real end-to-end test (ACT-1) must be done before any user acquisition.
**Verify before acting:** Run a real test with founder's own CV and a real target JD. Evaluate every section against the quality standard.

**Gap 2:** Auth system does not exist. This blocks: payment, offer rate measurement, user_email collection, GDPR delete by user (delete endpoint exists but user_id is not associated with sessions), question contribution database, credits wiring.
**Warning:** Do not launch publicly until auth exists. The credits system, GDPR compliance, and north star metric all depend on user identity.

**Gap 3:** This PMD was generated from a conversation summary document (JSON dump of 261 messages) not from real-time observation of the live codebase. Some details about exact current file state may be slightly outdated relative to the most recent commits.
**Verify before acting:** Run the 10-check verification script to confirm current implementation state before starting any new build session.

**Gap 4:** The "other business idea" compared against NAILIT was never disclosed. The PMD cannot document that comparison.

**Gap 5:** research_config.py credit estimate discrepancy (starter: 62 vs documented 70; production: 94 vs documented 150) was flagged but not resolved.
**Verify before acting:** Check research_config.py get_credit_estimate() formula against TIER_CONFIG max_credits_per_session values.

**Warning:** Do not send any Claude Code session without first running the 3-grep verification check for duplicate definitions. Sessions sent twice have silently created duplicate function definitions in the past.

**Warning:** APP_KEY must be set before any public URL exposure. Currently Lua endpoints accept any key if APP_KEY is empty.
