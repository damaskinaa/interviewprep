# NAILIT × Next Move Theory — Full Canon Run
**Date:** July 4, 2026 · **Method:** the complete public NMT/AJTBD canon (per the full extraction, all theses read) applied to NAILIT, following the /nmt-market-research output structure. Brief = the founder's own July 4 description, not the drifted handoff docs. Live-web competitive facts from the July 4 verification pass are used where marked.

---

## 0. User-claims ledger (the brief, tagged)

| Claim | Tag |
|---|---|
| Product: JD + CV + prepared experience → AI scrapes company values, number/type of interview rounds, Glassdoor + open sources → pack with strengths, gaps, experience-to-job match/mismatch, expected questions per round → then mock/answer guidance | [data — founder] |
| Lua = AI mock interview on a live voice call | [data — founder] |
| The voice call keeps crashing | [data — founder] |
| Stack: Claude Code-built; Vercel; Daytona; Hetzner | [data — founder] |
| Pipeline previously verified end-to-end on one real session; hallucination guard strips untraceable numbers | [observation — prior direct inspection, one case] |
| Zero paying customers, zero validated segments | [data] |
| Everything else in prior documents | [hunch until re-verified] |

---

## 1. The Job analysis (the core of the run)

### 1.1 The Big Job vs the Core Job
- **Big Job (carries the motivation):** *"Get this specific job offer"* — and above it, *"restore stable income / land the career step."* NAILIT does not and cannot perform this fully; it contributes.
- **NAILIT's Core Job (what the product actually performs):** *"Walk into each round of this specific company's interview knowing what's coming and how my real experience answers it."*
- Per §24 (promise must match delivery): **marketing at the Big-Job level ("get the offer") while performing only the Core Job manufactures a Negative Prediction Error.** Sell the Core Job ("never walk in blind"), let the Big Job be implied.

### 1.2 The full Level-1 Job — primary segment hypothesis (gap-returner with an invite in hand)

**WHEN** — Context: mid-career professional (8–20 yrs experience), hasn't interviewed in 5+ years, laid off or leaving a long tenure; a real interview invite arrived 24–72 hours ago at a named company; interviewing has changed since they last did it (AI screening, structured behavioral rubrics, more rounds). Negative emotions: anxiety ("I don't know what interviews even look like now"), dread of being ambushed, shame-risk of underperforming below their seniority. Consideration Set: knows Glassdoor exists (stale, scattered), knows ChatGPT exists (generic), maybe heard of copilot tools (scary/cheating), knows human coaches exist ($200–500/hr — verified). Trigger: **the invite email** — the receptivity window your prior analysis estimated at ~10:1 vs steady state.

**I WANT TO** — know, before each round, what this company will ask and how my real experience answers it —
**WITH SUCCESS CRITERIA:** specific to *this* company and *this* role, not generic; broken down *per round* (the round map itself is a criterion — they don't know how many rounds there are); grounded only in *my real* CV (nothing I'd have to bluff); ready in hours, not a week; honest about my gaps with a way to address them, not flattery; costs less than one hour of a human coach.

**IN ORDER TO** perform confidently in the interview and get the offer → **FEEL** in control, prepared, safe — "I've done the work; whatever they ask, I have an answer that's actually mine."

**Job frequency:** bursty — 3–10 interview loops inside a 1–4 month search, then ~zero for years. **Job budget:** anchored by alternatives — coach $200–500/hr above, $0 ChatGPT below; plausibly £30–150 per *loop* in the urgency window. **Job importance:** 9/10 inside the window (income restoration sits above it).

**Canon check (§5):** same expected outcome with *different* criteria = different Jobs = different segments. "Prep me for interviews" (generic, ongoing, cheap) and "prep me for THIS company's loop by Thursday" (specific, urgent, premium) are **different Jobs.** NAILIT is built for the second. Every competitor at $10–49/mo is built for the first. This is the structural reason the premium price *can* survive — and only inside this Job.

### 1.3 Job taxonomy diagnostics (job-types-and-properties applied)
- **Emotional Job (the real hire):** *"stop feeling like I'm walking into an ambush."* The pack is the rational wrapper; anxiety-to-control is the state change being purchased. Communication should sell the state change.
- **Orientation Job:** before hiring anything, the user performs *"figure out what interview prep even looks like now."* NAILIT's landing page must perform this orientation Job free (this is the leftmost Aha opportunity — see §3).
- **Tax Jobs NAILIT imposes:** upload CV, write out "prepared experience," wait for the pipeline, create an account. Each is friction against an anxious, time-poor user. Minimize ruthlessly; "prepared experience" as a required long-form input is the heaviest tax — consider extracting it conversationally or from the CV first and only asking for gaps.
- **Fake Job warning (§15):** "I want to practice mock interviews" is a classic *stated* want. What people reliably pay for is the outcome-feeling, not the rehearsal. Do not let the voice mock's existence define the product's identity before usage data shows it's where value lands.

---

## 2. The Job Graph and NAILIT's mechanic

**The customer's current (DIY) Job Graph for this Big Job:** search Glassdoor for the company → read scattered/stale interview reports → guess the round structure → google "questions for X role" → paste JD into ChatGPT → get generic answers → try to force their own experience into them → rehearse alone or with a spouse → walk in anxious anyway. 4–8 hours, low confidence output.

**NAILIT's mechanic (per §22–23):** *take the Job off the customer* — the entire research-and-mapping sub-graph collapses into "paste JD + CV, receive the pack." This is the same mechanic class as the canon's Claude Code example, applied to interview prep. It is a genuine "climb" over the DIY graph — the customer's Job count collapses.

**Small Jobs = the growth map (§9):** Jobs adjacent to NAILIT's Core Job that others perform today: *write the tailored CV/cover letter* (Teal, Jobscan), *find the roles* (LinkedIn, auto-apply tools), *negotiate the offer*, *follow up after the interview*, *decide between offers*. These are NAILIT's future expansion slots — note them, do not build them.

**Micro Jobs where experience lives:** reading the pack (is it scannable at 11pm the night before?), doing the mock, reviewing feedback, re-drilling weak answers. The pack's *format* is a value surface, not a detail.

---

## 3. The Critical Chain — and the crash, located precisely

The chain the customer walks: **invite arrives (trigger) → panic/orientation → find NAILIT → input CV/JD/experience [tax] → wait [tax] → read the pack (Aha #1 candidate: "they mapped MY rounds at MY company") → voice mock with Lua (Aha #2 candidate: "that felt like the real thing") → real interview → outcome → (contribution: report what was asked).**

**Canon findings on this chain:**

1. **The crashing call is a chain-break at the single worst location.** §6: a Solution performing below the customer's success criteria fires a **Negative Prediction Error — a Problem**. The mock sits at the customer's moment of peak emotional investment (they are literally rehearsing their fear); a crash there doesn't subtract one feature's value — it fires a trust-destroying prediction error against the *whole* product ("if the mock crashes, can I trust the pack?"). §11: **fixing breaks in the Critical Chain is the highest-leverage move available when a break exists.** The canon is unambiguous: a *broken* chain link is strictly worse than an *absent* one. Therefore: **either make the call reliable or remove it from the paid path until it is. Shipping it crashing is the one option the methodology forbids.**
2. **Move the Aha left (§5, value-creation).** The leftmost honest Aha: show a *taste* of the pack before payment/full commitment — e.g., the company's round map + 2–3 likely questions for round 1, generated free from just the JD. That single artifact performs the customer's Orientation Job, proves company-specificity (the differentiator), and fires the Positive Prediction Error before any money or heavy Tax Job. This is the highest-ROI product change the canon run surfaces besides the crash.
3. **The contribution step is a chain extension** — it happens *after* the customer's Big Job resolved, when motivation is near zero. Canon: levels above Core carry motivation, below carry mechanism. Post-interview reporting is a mechanism-level ask with no motivation attached → it must be *paid for* (credit reward) or made near-zero-effort (one tap: "which of these 12 questions came up?" — pre-populated from their own pack, not a blank form). Pre-populating from their pack is both cheaper for them and *more valuable for you* (it directly measures pack accuracy = your success criteria = the moat data).

---

## 4. Segmentation — by Job Graph, scored

Candidate segments generated (Job-graph-defined, not demographic): (1) gap-returner with invite in hand; (2) active multi-loop searcher (running 3–6 processes in parallel, often recently laid-off tech/ops); (3) career switcher translating experience across domains; (4) non-native-English professional interviewing in English; (5) step-up candidate (interviewing one level above current title); (6) new grad / bootcamp grad; (7) returning parent after career break; (8) visa-constrained candidate (each interview existential); (9) B2B: outplacement firms / corporate talent teams; (10) recruiters prepping their own candidates (B2B2C).

**Top 5 scored (1–5 per factor): value gap vs current solutions · Job budget · size×frequency · reachability at target CAC · ability to win vs competition. Existential gate = evidence people in this segment have PAID for this Job before (§15).**

| Segment | Value gap | Budget | Size×Freq | Reach | Win | Gate: past payers? | Verdict |
|---|---|---|---|---|---|---|---|
| 1. Gap-returner, invite in hand | 5 | 4 | 3 | 4 (r/layoffs etc., trigger-timed) | 4 | YES — this cohort hires coaches at $200–500/hr | **GO (to validation)** |
| 2. Multi-loop searcher | 4 | 4 | 4 | 4 (same channels) | 3 (more tool-savvy → ChatGPT-capable) | Partial | **GO-adjacent — validate as secondary; also answers episodic-retention risk (multiple loops = multiple packs)** |
| 5. Step-up candidate | 4 | 3 | 3 | 3 | 4 (gap-repair feature fits exactly) | Partial | **NARROW — fold into 1/2 rather than target separately** |
| 3. Career switcher | 4 | 4 | 3 | 3 | 3 | YES (bootcamps, coaches) | **NARROW — the match/mismatch feature is built for them, but channel is diffuse** |
| 4. Non-native English | 4 | 4 | 5 | 3 | 2 (product is English-only; delivery coaching absent; Revarta/AceRound court them) | YES | **PIVOT-away for now — real Job, wrong product shape today** |
| 6. New grad | 3 | 1 | 5 | 4 | 2 | Weak (universities pay, students don't) | **PIVOT-away B2C; note B2B door via career centers = Big Interview's fortress** |

**Segment ruling:** one primary (gap-returner), one shadow (multi-loop searcher, same channels, same product, answers retention). Everything else is subtraction (§6) — named, parked, not marketed to. One person = one segment (§12): the laid-off ops manager running four processes is *one* segment whose graph contains both urgency and multiplicity — segments 1 and 2 likely merge under interviews into "the re-entering professional mid-search."

---

## 5. The cause-and-effect chain to profit — link-by-link status

```
Market with money        → PARTIAL: people demonstrably pay for this Job (coaches, Big Interview,
                           Revarta at $49/mo — live-verified). Market-with-money EXISTS.
                           Whether it exists at NAILIT's price point for THIS Job variant: unvalidated.
Segment + Job            → HYPOTHESIS (0 interviews). Sharpest available: §1.2 above.
Added Value              → PARTIALLY REAL: company-specific pack + evidence-locked answers is a real
                           delta vs every verified alternative. BUT: quality proven on 1 case (founder's
                           own), the chain has a confirmed break (crash), and research quality on
                           low-Glassdoor-signal companies (SMEs, non-US) is UNKNOWN — a lethal
                           assumption hiding in "scrape Glassdoor and open sources."
Three parallel conditions:
  · Unit economics       → LIKELY OK (survives even 3–5x cost-model error) but UNVERIFIED (provider
                           invoice never checked).
  · Demand creation      → UNVALIDATED. Channel hypothesis (trigger-timed Reddit/community) untested.
  · Scale w/o decay      → MOSTLY AUTOMATED, two decay risks: research quality on obscure companies;
                           silent pipeline-quality drift (no quality monitoring exists).
Conversion/retention     → UNKNOWN. Credits model is the structural answer to episodic use — untested.
Profit                   → downstream of all of the above.
```
**Diagnostic discipline (§5 NMT):** if early conversion is low, do NOT touch the funnel — the break will be upstream (segment/Job/value/claim mismatch). This rule, pre-committed now, will save weeks later.

---

## 6. Consideration Activators — what the landing page must load (and may claim)

1. **A new Job Graph exists:** "One tool researches your target company and builds your round-by-round prep pack from *your* CV." ✅ claimable now.
2. **It performs the Big Job more efficiently:** "4–8 hours of Glassdoor digging → a company-specific pack in ~20 minutes." ⚠️ **prerequisite (d): must be validated by real users before stated as fact** — until the blind comparisons run, phrase as the offer, not the proof.
3. **Named product + door:** NAILIT → "paste the JD, see your round map free." ✅ — and note this *is* the moved-left Aha from §3.
4. **Specific fears reduced:** (a) "Every answer traces to your real CV — nothing invented for you to get caught on" — ✅ provable, the hallucination guard is real and this maps to the verified hiring-manager AI-detection worry (59%/62% survey figures); (b) "Your data, deletable, never sold" — needs auth to be fully true per-user; (c) "This is prep, not a live cheat tool" — ✅, and load it explicitly given the verified copilot backlash.
5. **Alternative graphs fired, concretely:** ChatGPT → generic answers hiring managers report detecting and penalizing [verified]; Glassdoor → stale and partially reputation-managed [68% HR-admission stat]; copilots → billing traps + detection risk + freeze mid-interview [verified against Final Round AI]; human coach → $200–500/hr and not company-specific. ✅ all concrete and sourced.

**Barriers (§19) to remove, per segment:** CV-data trust (needs auth + delete-per-user — currently a real barrier, not a comms problem: "change reality first"); thin research signal for SME/non-US employers (a *coverage barrier* — detect it and say so honestly per-company rather than shipping a thin pack, which fires the §6 Problem); price friction in a just-laid-off segment (free round-map taste is the remover); the crashing call (a barrier the product itself erected).

---

## 7. RAT — the assumption stack, ranked (lethality-first)

**"Every idea is already dead — you just don't know what will kill it yet."**

| # | Assumption | Lethal? | Cheapest evidence |
|---|---|---|---|
| A1 | The re-entering professional will pay a premium for a *company-specific* pack when free generic prep exists | **LETHAL (root)** | 10–15 interviews recruiting ONLY past-payers for interview help (coach, course, Big Interview) + fake-door with the free round-map taste + price on the door |
| A2 | The research layer produces a good pack for companies *outside* well-documented big tech (Glassdoor signal is thin for SMEs/EU firms) | **LETHAL** | Run the live pipeline on 5 real SME/mid-market JDs this week; grade the packs honestly; measure signal coverage |
| A3 | Predicted questions match reality often enough to beat DIY (the accuracy claim) | **LETHAL** | Blind comparison: 10 users with real upcoming interviews get pack vs their own DIY; post-interview, count hits — doubles as the first contribution-DB rows |
| A4 | The voice mock is where the Aha fires (vs the pack itself) | High | Watch 5 real users; offer text-mock and voice-mock; observe which they use, finish, and mention unprompted |
| A5 | The voice call can be made reliable on current infra | High (currently FALSE) | Crash-log diagnosis first (host-sleep correlation check — Daytona is the prime suspect); one dedicated fix session; 10 consecutive clean 20-min calls as the acceptance test |
| A6 | Users will confirm which questions were asked, post-interview (the moat mechanic) | High (moat-killing, not product-killing) | First-cohort test: one-tap pre-populated confirmation + credit reward; measure rows/user |
| A7 | Trigger-timed community channels reach the segment at viable CAC | Medium | $50 test + 2 weeks of manual thread engagement, measured |
| A8 | Non-expiring credits at premium per-loop pricing is accepted | Medium | Price test inside A1 interviews (£29/£59/£99 per-loop framings, not per-month) |
| A9 | Real per-session cost ≈ model (provider unverified) | Low (margin math survives error) | Read the invoice. One hour. |
| A10 | GDPR posture adequate for EU CV data | Medium-legal | Qualified review before scale (not engineering) |

**Validation debt: 10 assumptions, 3 lethal, 0 validated.**
**Single riskiest assumption:** A1×A3 joint — *"a company-specific, evidence-locked pack beats free DIY by enough that people who've paid for prep before will pay again."*
**Cheapest way to check it:** one combined round — 10 past-payer interviews each containing the blind comparison, plus the free round-map fake door. ~2 weeks, ~$50, zero code beyond the taste artifact.

**Multiplicative math (§6 subtraction):** ten ~60–70% assumptions stacked ≈ low-single-digit joint survival — consistent with the earlier 0.8% estimate. Removing A5 from the stack entirely (subtract the crashing call from the paid path until reliable) is the single cheapest survival-probability increase available today, per the canon's own arithmetic.

---

## 8. Subtraction ledger (what the methodology says to remove NOW)

1. **The voice call from the paid path** — until it passes 10 consecutive clean calls. Replace with text mock (already the pipeline's native mode). Re-add as the upsell it was probably always going to be.
2. **All segments except the re-entering professional** — from marketing, not from the codebase.
3. **The Big-Job promise from copy** — sell "never walk in blind," not "get the job."
4. **The "prepared experience" long-form input** as a hard requirement — heaviest Tax Job at the most anxious moment; derive from CV + short prompts instead.
5. **Every roadmap item not on the critical chain** (payments polish, extra dashboards) until A1–A3 resolve.

**Local vs global optimum (§9), applied:** local track = fix the chain (crash or subtraction, pack quality on SMEs, the free taste); global track = the contribution/accuracy dataset (the only asset that compounds and the only credible acquisition story). Fund both from day one — the global track costs one schema + one email + one credit-reward rule, which is why it must not wait.

---

## 9. NMT 12-point diagnostic scorecard

1. Economic Map of Segments — **No** (hypotheses only). 2. One target segment via four-factor screen — **Yes as of this run** (re-entering professional). 3. Job Graph known — **Partially** (this doc; needs interview confirmation). 4. Success criteria known for Core + Big Job — **Hypothesized** (§1.2), unvalidated. 5. Aha surfaced and moved left — **No; concrete fix identified** (free round-map). 6. Value prop in canon formula — **Yes:** *For professionals re-entering interviews after years out [segment], who need to walk into each round of a specific company's process knowing what's coming [Job], NAILIT replaces 4–8 hours of stale Glassdoor digging with a round-by-round pack built only from your real experience [delta], via live company research, per-round question prediction, gap-repair scripts, and evidence-locked answers [features].* 7. Proof of value (pay/use/return) — **No.** 8. Three parallel conditions — **Untested / likely / two named decay risks.** 9. Cross-function alignment — N/A solo, but the *documents* were misaligned (drift) — the ground-truth doc is the alignment fix. 10. Conversion+retention at scale — **No data.** 11–12 (strategy chosen from visible alternatives; chain intact) — **Chosen as of this run; chain has one known break (the crash).**

Score: ~3.5 of 12. **Normal for pre-validation — the point is that every "No" above has a named cheapest test in §7.**

---

## 10. VERDICT

**NARROW → GO (to validation).**

- **GO on what:** the Core Job is real, the mechanic (take the research Job off the customer) is the canon's strongest class, the market-with-money gate passes on live evidence (people pay coaches, Big Interview, Revarta for this Job), and NAILIT's two provable deltas (company-specific round mapping; evidence-locked answers) attack the verified failure modes of every alternative.
- **NARROW to what:** one segment (the re-entering professional, invite in hand), one Job (§1.2), one promise (the Core Job), one price frame (per-loop, not per-month).
- **GO means GO-to-validation, not GO-build.** The build queue until A1–A3 resolve is exactly three items: (1) resolve the chain break — fix the call to 10-clean-calls standard or subtract it from the path; (2) the free round-map taste (the moved-left Aha and the fake-door instrument); (3) the pre-populated one-tap contribution confirmation + credit reward (the global-optimum track, and the measurement device for A3).
- **Kill/pivot criteria, pre-committed:** A1 fails with past-payers (they won't pay even in the urgency window) → the B2C premium thesis is dead; the remaining doors are the B2B ones (outplacement, corporate talent — where the B2B canon's *personal Jobs of the decision-maker* analysis would apply) or shutdown. A2 fails (packs are thin outside big-brand companies) → narrow the promise to well-documented employers or invest in a research layer beyond Glassdoor before any launch. A3 fails (predictions don't beat DIY) → the product is a formatting layer on public data; kill the accuracy claim and reposition or stop.

**Validation debt: 10 assumptions, 3 lethal. Riskiest: the pack beats free DIY enough that proven past-payers pay again. Cheapest check: 10 past-payer blind-comparison interviews + the free round-map fake door — two weeks, ~$50.**
