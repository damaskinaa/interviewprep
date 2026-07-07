# NAILIT — Ultimate Handoff Document
**For: a colleague taking over or joining this project, with zero prior context.**
**Generated:** June 23, 2026
**Status: this document supersedes NAILIT_PMD.md, NAILIT_COMPLETE_PMD.md, NAILIT_HANDOFF.md, and NAILIT_ADDENDUM_DEFENSIBILITY_FEASIBILITY.md as the single source of truth. Those files remain in the project folder as historical/granular backup if you need maximum detail on a specific moment — but if you only read one document, read this one.**

---

## 0. Read this first — the philosophy, in one paragraph

This project has one governing rule, stated and re-stated by the founder dozens of times across this build: **build slow, build solid, build for scale — not rushed, and not "lean" in the sense of "thin."** The founder explicitly rejected the idea that this should be a thin wrapper around what a person could get from ChatGPT or two hours of Glassdoor research. Every architectural decision below traces back to that standard. The project also has an earned, hard-won discipline: **diagnose before fixing, verify on a real live call before trusting any report (including AI self-reports), and never bundle two changes into one session.** This discipline was learned the hard way, repeatedly, across this build — see Section 6 for the receipts. Respect it.

---

## 1. What NAILIT actually is

An AI-powered interview intelligence platform. User inputs CV + job description + relevant experience. The platform:

1. Researches the target company — values, available interview reports, open-source information.
2. Generates a full prep pack from that research — company intelligence, role decoding, candidate-CV mapping, gap analysis, full Q&A by interview round.
3. Runs a mock interview based on the prep pack.
4. Gives feedback (via an AI coaching persona called **Lua**), with the ability to refine answers across attempts.
5. **Planned, not built:** voice-based mock interview.
6. **Planned, not built (V2/extras):** optional connection to an ex-employee of the target company, or to an interview coach, for human feedback after the AI mock — explicitly an upsell, not a dependency, and explicitly using *former* employees (e.g., professionals recently laid off) rather than current staff, to avoid conflict of interest.

**The long-term differentiator, and the only thing that matters for years 3–5:** a growing, first-party database of real candidates reporting which questions they were *actually* asked, tagged by company/role/round, after real interviews. This is the moat. It does not exist yet — it is fully designed but not built (see Section 5, ACT-1).

---

## 2. Current state, as of this document

**Architecture:** Six-module pipeline (Company Intelligence → Role Intelligence → Candidate Profile → Gap Map → Interview Strategy → Prep Pack), plus Module 7 (Answer Generator) and Module 8 (Mock Interview), gated to unlock only after Prep Pack completes. Runs end-to-end. Verified live on a real session (Google / Program Manager, `sess_20260622_152508_d205dd18`).

**Stack:** Next.js/Vercel frontend, FastAPI backend (currently in a Daytona sandbox — see Section 6 for why this is fragile), SQLite locally with a built-but-unexercised Postgres/Redis abstraction for future scale, OpenAI as the actual LLM provider (not Claude — see Section 4, the unresolved divergence), Tavily for research.

**Repository:** `https://github.com/damaskinaa/interviewprep`, `main` branch.

**What works, confirmed by direct inspection, not self-report:**
- Full pipeline runs end-to-end and produces a complete Prep Pack.
- CV-evidence extraction is genuinely good — correctly pulls real metrics (e.g., "34% backlog reduction," "77%→93% SLA") from a candidate's real CV/answer bank.
- The hallucination guard works — a validator strips any generated number that doesn't trace back to the candidate's actual source documents, confirmed by direct test (kept a real "31%," stripped a fabricated "77 percent" with no CV basis).
- Forbidden-claims detection works — correctly flagged "I have direct experience as a Senior Program Manager" as something the candidate must not say, given their real background.
- Gap detection works — correctly identifies real weaknesses without inventing false competence.
- Lua (the AI coaching layer) returns a complete, correct 10-field response shape.
- 22 Lua endpoints are authenticated; atomic job creation prevents race-condition duplicate runs; out-of-order module runs are rejected immediately at the HTTP layer with a clear error; GDPR delete/export endpoints work and actually remove data.

**What is broken, confirmed by direct inspection of a real live session, not assumption:**
- **Story repetition.** Across ~24 generated Q&A answers in the test session, roughly half defaulted to the same single story (one specific metric) regardless of question fit, even when it was a poor match (e.g., forced into a question about "influencing software tool development"). The candidate's answer bank had ~17 distinct stories available; the pipeline's `story_inventory` artifact only contained 2 of them.
- **Boilerplate leak.** The exact same disclaimer paragraph appeared verbatim, unmodified, at the end of roughly 15 different answers. A careful reader would notice this immediately and lose trust in the rest of the pack.
- **Root cause not yet found.** An investigation prompt is written (Section 5, ACT-2) but had not been run as of this document. The fact that *other* modules (Candidate Profile, Gap Map) did NOT show this defect is strong evidence the bug is narrow — confined to the answer-generation/story-selection step — not a sign the architecture is broken.

**What is decided but not built at all:**
- **User authentication.** No login, no accounts, no session ownership. This is the single highest-leverage blocker — it gates payments, GDPR-by-user, the offer-rate follow-up email, and the entire contribution-database moat, simultaneously.
- **The contribution-capture mechanism** (the actual moat). Fully spec'd, zero rows exist.
- **Payment flow.** Stripe webhook code exists and is tested for signature validation; no real Stripe products have been created in the dashboard; no checkout UI exists.
- **Real email delivery.** `send_email()` is a console-log stub; no provider (Resend recommended) is wired.
- **Voice mock interview.** Researched (LiveKit + Deepgram + Cartesia, ~£1.20/session), explicitly deferred to after the text product is validated with paying users.
- **UX state-signaling on the module dashboard.** A "DONE" module currently shows its original action button still gold/primary next to "View Results," which is confusing — see Section 6 for the exact fix spec (not yet executed).

---

## 3. The economics — verified, not modeled

Per-session AI cost is approximately £0.78 (this was modeled against a Claude Haiku/Sonnet split — see Section 4 for why this number needs re-verification against actual OpenAI costs). Revenue per session is £49–£199 under a **credits-based pricing model** (Free: 1 lifetime session; Starter: £89/3 sessions, never expire; Monthly: £49/5 sessions + rollover; Premium: £199/10 sessions, never expire). This pricing model was deliberately chosen over a subscription specifically because interview prep is episodic — credits that don't expire sidestep the "cancel after 3 months" problem that kills generic subscription products in this category (see Section 7 for why this matters against external benchmarking).

---

## 4. The one open architecture question that needs deliberate resolution

**Tonight's most important technical finding:** `agent_v2.py` imports `from openai import OpenAI` exclusively. There is **zero Anthropic SDK reference anywhere in the backend.** This directly contradicts the unit-economics modeling done earlier in this project, which assumed a Claude Sonnet 4.6 / Haiku 4.5 split.

**This needs a single, dedicated, non-bundled decision session:** either (a) confirm staying on OpenAI deliberately and re-run the unit-economics model against real OpenAI pricing, or (b) migrate to the originally-planned Claude split. Do not let this stay silent — it affects whether the £0.78/session figure is even true, and it affects the cost calculus for any future research-architecture expansion (Section 8).

---

## 5. The ordered action list — what to actually do, in order, and why this order

This order is not arbitrary. Each step either removes a live risk or unblocks several later steps at once.

**ACT-1 — Ship minimal auth (email + magic link, Clerk or Supabase Auth — undecided which, either is fine).**
This is the single highest-leverage remaining build. It unblocks: payments, the offer-rate email, GDPR-by-user, and the contribution database. Nothing past this step matters until it's done.

**ACT-2 — Run the story-repetition / boilerplate-leak root-cause investigation, then fix.**
Investigation prompt, already written, not yet run:
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
This is the highest-priority *content* fix — it's the difference between "the pipeline runs" and "the pipeline produces something genuinely good." Do this in parallel with ACT-1; they don't conflict.

**ACT-3 — Build the contribution-capture mechanism (the actual moat). Depends on ACT-1.**
Spec, ready to execute the moment auth exists:
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
This is a **one-time code build, not ongoing labor** — once built, it runs itself forever for every user. This is why the moat is solo-founder-feasible: it doesn't require a team, it requires writing one feature once.

**ACT-4 — Move off the Daytona sandbox.**
Daytona is a dev sandbox, not a production host — it sleeps when idle and has no SLA. Tonight's entire deployment saga (Section 6) traces back to treating it as if it were production. Once auth and the contribution mechanism are stable locally, move to a real always-on host. Render or Fly.io free tier is the right *next* step (real public URL, zero cost) — Hetzner/paid infrastructure only once real paying users exist (this is "the deal" the founder set explicitly and correctly: **no infrastructure spend before real users**).

**ACT-5 — Resolve the OpenAI/Claude question (Section 4) in its own dedicated session.**

**ACT-6 — Wire Stripe checkout (create real products in the dashboard, build the checkout UI) and Resend for real email delivery.** Depends on ACT-1.

**ACT-7 — UX state-signaling fix on the module dashboard.** Low priority, cosmetic, already spec'd (Section 6).

**ACT-8 — Run a second, independent quality test on a different JD/CV pair** before considering the answer-generation pipeline broadly trustworthy — the current verification is based on one test session.

---

## 6. The deployment debugging saga — full detail, because every step taught something real and a colleague redeploying elsewhere will hit the same sequence if they don't know this history

**Symptom 1:** Live Vercel form → `400 Bad Request: failed to resolve container IP... Is the Sandbox started?`
**Real cause:** Daytona sandbox had gone to sleep — its designed behavior when idle. It is a coding sandbox, not a host.
**Fix:** `daytona start <id>` — required first fixing expired CLI auth (`daytona login`) and a CLI/API version mismatch.

**Symptom 2:** After waking it, `502` error.
**Real cause:** No backend process was running inside the sandbox at all.
**Fix:** Found the real code path (`/home/daytona/interviewprep/`) via `daytona exec`/`daytona ssh`, started uvicorn manually.

**Symptom 3:** `ModuleNotFoundError: No module named 'fastapi'`.
**Real cause — the most important finding of that night:** `git log` showed the local repo was 3 commits ahead of `origin/main`. Every fix from that entire debugging session existed only on the founder's laptop, never pushed. The sandbox was running stale, pre-fix code the whole time — this explained both the original 400 and the 502.
**Fix:** `git push origin main`, then `git pull origin main` inside the sandbox.

**Symptom 4:** `pip3 install -r requirements.txt` partially failed.
**Real cause:** `asyncpg` and `psycopg2-binary` (added for a *future* Postgres migration, not needed today) failed to compile their C extensions against the sandbox's Python 3.14 — a genuine version incompatibility. Because pip's install is all-or-nothing, this also silently blocked `fastapi` from installing.
**Fix:** Installed only what's actually needed for current SQLite-mode operation (`fastapi uvicorn python-dotenv rq redis stripe`), skipping the Postgres-only packages.

**Symptom 5 (false alarm, but wasted real time):** A shell polling script appeared to hang indefinitely on the slowest module, printing hundreds of blank `running: ...` lines.
**Real cause:** Not a hang. The job had actually completed in 3.5 minutes — the *polling script's* inline JSON parser was choking on control characters in the large response and failing to print real status.
**Lesson:** this exact failure mode happened twice across this build. Always verify directly against `get_job()` in Python before assuming the pipeline itself is broken.

**The single biggest lesson from this entire saga, stated as a rule:** local fixes do not exist anywhere else until explicitly pushed, pulled into the deployment target, and the environment rebuilt (dependencies reinstalled, process restarted). This gap is invisible until something breaks. Always specify *where* something is fixed — local-only, pushed, or actually deployed — these are not interchangeable.

**The UX fix spec, mentioned in Section 5 (ACT-7), in full:**
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

---

## 7. The two external "second opinion" reports — what they got wrong and the one thing they got right

The founder deliberately sought outside validation by running NAILIT's concept through an external AI pipeline tool (referred to as "Hermes" in conversation), twice, getting two different scores (5.5/10, then a more flattering unscored "real analysis"). **Critical finding: neither report analyzed NAILIT.** Both were given a generic one-paragraph "AI interview prep" prompt and invented their own hypothetical product from scratch — different segments (FAANG Aspirant, Rejection Recoverer, etc. — none overlapping with NAILIT's real, researched segments), a two-sided insider marketplace NAILIT doesn't have, $19/month subscription pricing (vs. NAILIT's actual £49–199 non-expiring credits model), a "voice-based adaptive mock interview" praised as a current differentiator when it's explicitly a *future, unbuilt* feature, and zero awareness of the actual six-module pipeline, Evidence Ledger, hallucination guard, or gap-repair framework.

**The 5.5/10 score is a real, methodologically sound score of a different, simpler, hypothetical product — not of NAILIT.** Full archive of both Hermes runs (segments, RAT, interview kit, 29-point checklist, unit economics approximation) is saved separately in `Hermes_NMT_Pipeline_Run.md` in this same output folder, with the same warning at the top.

**What is genuinely useful from these reports, despite the mismatch:**
- The RAT methodology itself — (Probability × Impact) / Cost-of-validation scoring, chain-break logic (fix the ROOT risk before anything downstream), subtractive analysis (what can you drop to improve survival odds) — is structurally sound and worth reusing for NAILIT's *actual* risks, not the invented ones.
- The retention-ceiling concern (episodic usage caps subscription LTV) is real in general, but **already solved in NAILIT's actual design** — the non-expiring credits model and the Active Multi-Company Searcher / Corporate Talent Developer segments (already in the original segment research, not invented by Hermes) are the structural answer. Hermes re-discovered a problem NAILIT had already designed around, then didn't realize it had been solved, because it never saw NAILIT's actual pricing model.
- The core caution — "prove differentiation is real before scaling" — is valid and is exactly what ACT-2 (the story-repetition fix) and ACT-8 (second quality test) are for.

**The "ChatGPT will just do this for free" risk, resolved precisely:** There is no current product, free or paid, that does what NAILIT does. A person manually pasting a CV+JD into ChatGPT is a person doing a worse, manual version of one slice of NAILIT's pipeline — not a competing shipped product. The mechanically precise distinction: a foundation model getting better over time absorbs *generation quality* (better-written answers). It cannot absorb *first-party data it never had access to* — specifically, real candidates' after-the-fact reports of what they were actually asked. That data only exists because real people used NAILIT specifically. This is why ACT-3 (the contribution database) is the actual long-term defense, not a "nice to have."

---

## 8. Defensibility and distribution — for a solo, non-public-facing founder

**The defensibility thesis, stated plainly:** the generation layer (writing answers, structuring packs) is not defensible long-term against a smarter foundation model, and should be assumed to commoditize over time, not fought. **The data layer (the contribution database, ACT-3) is the only component that gets *more* defensible every year**, specifically because it requires real users and real elapsed time — something raw model capability cannot shortcut. Even in a worst-case scenario where NAILIT is out-competed on generation quality, a sufficiently large, structured, multi-year dataset of real candidate contributions tied to real outcomes is independently valuable to recruiting platforms, HR tech, or the AI labs themselves — none of whom can acquire this data through model improvement alone. This reframes "could we get acquired" from a hope into a specific thesis: **the dataset is the asset an acquirer would actually be paying for, not the UI or the prompts.**

**Building this without a team, without being a public-facing founder:** The moat-building mechanism (ACT-3) is a one-time, narrow code build — not ongoing labor — which is why it's solo-feasible. What it actually requires beyond the code: a small *first* cohort of real users (20–50 people, not mass reach) to start the data flywheel. This is achievable through quiet, asynchronous, written engagement in places step-up candidates already exist — career-transition subreddits, LinkedIn job-search communities, relevant alumni/professional groups — not video content, not a personal brand, not Instagram. LinkedIn presence is acceptable and sufficient; nothing more public-facing is required.

**Where fractional/freelance help is and isn't appropriate:** Appropriate, later, occasionally — light paid-per-project data analysis once the database has real volume. **Not appropriate, ever, for the moat specifically** — any form of manually "going and getting" contributions via a freelancer defeats the entire point; the asset's value comes from being an automatic byproduct of organic usage, which a freelancer-assembled dataset is not.

**On funding:** Raising money *to fund distribution* before product-market fit is backwards — it funds a story, not an asset, since the actual proof that distribution effort would even convert doesn't exist yet. The correct sequence: build the first cohort manually/slowly, let the contribution database start accumulating real rows, *then* use early revenue (not raised capital) to bring in a fractional growth person once there's a proven conversion signal to scale.

---

## 9. The honest final feasibility verdict

**Is this feasible?** Yes — conditionally, and the condition is fully within the founder's control, not an external unknown. The technology works (verified live, not assumed). The economics are excellent *pending* resolution of the OpenAI/Claude question (Section 4). The one real content defect found (story repetition + boilerplate leak) is narrow, has a clear diagnostic path, and is the same shape as several other bugs this project has already found and cleanly fixed — evidence of a fixable bug, not a broken architecture.

**Does it survive 3–5 years?** Conditional on exactly one thing: whether the contribution-capture mechanism (ACT-3) gets built and starts running as soon as auth ships, rather than continuing to be correctly identified, repeatedly, in documentation, and never executed. This is the project's single greatest long-term risk — not a competitor, not ChatGPT, not the external 5.5/10 score (which scored a different product). Every other open piece — the pipeline, the economics, the safety guardrails — either already works or has a clear, narrow, solo-executable fix path. The moat is the one component whose feasibility depends on elapsed real-world time, which cannot be rushed, and is therefore the one piece where delay has a real, compounding, unrecoverable cost.

**Can a solo, non-public-facing founder build and defend this without a team or outside funding?** Yes — specifically because the moat-building mechanism is a one-time narrow build, not an ongoing labor-intensive task, and because seeding it requires only a small first cohort reachable through quiet, written engagement, not personal branding or video content.

**The one sentence to act on, above everything else in this document:** ship auth, then ship the contribution-capture mechanism immediately after — before any further UX polish, additional external validation reports, or distribution planning — because nearly every other open question in this project either resolves itself once that sequence runs, or cannot be resolved by any further analysis and requires real usage data instead.

---

## 10. Reference index — where to find more detail if you need it

- **`NAILIT_COMPLETE_PMD.md`** — exhaustive build history, every decision (DEC-1 through DEC-14) with full rationale, every rejected approach, full architecture file inventory, full chronological log from project inception through the first Daytona deployment fix.
- **`NAILIT_ADDENDUM_DEFENSIBILITY_FEASIBILITY.md`** — the live quality-test findings in full detail, the original reconciliation of the first Hermes 5.5/10 report, the original defensibility reasoning (DEC-15 through DEC-19).
- **`Hermes_NMT_Pipeline_Run.md`** — the complete, cleaned-up archive of the external Hermes pipeline run (all 5 invented segments, all 5 RAT cards, the full interview kit, the 29-point checklist) — useful as a *methodology reference* for running NAILIT's own RAT analysis correctly, not as a verdict on NAILIT.
- **`NAILIT_HANDOFF.md`** — an earlier, shorter handoff covering the same philosophy/history themes as this document, now superseded by it but kept for redundancy.
- **`answer_bank_condensed.txt`** — the working example of a condensed, high-signal answer-bank input (4,160 characters, distilled from a 66,000-character source document) used in the live Google/PM quality test — useful as a template for explaining the `answer_bank` field's intended size/purpose to future users.

---

## 11. Final warnings for whoever picks this up

- **Do not recommend paid infrastructure spend before real paying users exist.** This has been explicitly, repeatedly decided. Treat it as a firm project principle, not an open question to revisit casually.
- **Do not trust an AI agent's self-report that a fix works.** Verify with a real call, on the real running system, with real data — every fix in this project that skipped this step eventually caused a worse problem than the one it was meant to solve.
- **Before re-running any "fix and verify" session, grep for existing definitions first.** This project has had near-misses where a fix was almost reapplied, risking silent duplicate function definitions.
- **Treat any future external AI analysis of "the product" with suspicion until you confirm it was actually given NAILIT's real architecture** — not a generic one-paragraph description. Two separate runs this build already demonstrated how easily this goes wrong.
- **The founder's instinct to push back on scope creep, spend, or a suspiciously bad/good external score has been correct every time it happened in this project's history.** Don't argue past it — investigate it.
