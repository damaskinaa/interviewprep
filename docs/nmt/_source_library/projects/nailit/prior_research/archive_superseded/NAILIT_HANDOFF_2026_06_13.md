# NAILIT — Handoff Document
**For: a new Claude Code session, cold, with zero prior context.**
**Written: June 13 2026**

---

## Read this first — the philosophy, not just the facts

This project has one governing principle, stated explicitly and repeatedly by the founder over weeks of work: **slow, solid, built for scale — not rushed.**

That principle exists *because* the opposite was tried first and it failed, repeatedly, painfully, and the founder caught it every time. Do not treat that history as noise. It is the reason every fix in this codebase is narrow, tested, and confirmed before the next one starts. If you are tempted to "just also fix this nearby thing while you're in the file" — don't. That instinct is exactly what caused the damage documented below.

**The standard for "done" on this project is not "it compiled." It is "it was verified against a real test, on the real live site, with real inputs."** Internal test-script success has repeatedly diverged from live-site reality on this project. Every session below ends with a live confirmation step for that reason. Skipping it is the single most common way this project goes backward.

---

## The real failure history — why the caution exists

Early in the build (well before the current clean backend), the pipeline was rebuilt multiple times chasing a recurring symptom: **the product looked done when Codex reported on it, and was bad when the founder actually used it.**

Concretely, across many sessions:
- A research-contamination bug caused one company's research to silently leak into a different company's job (an Atlassian job receiving Canva's research data). This was caught only because the founder ran a real session and the output was visibly wrong for the company — not because any automated test caught it.
- Multiple "fixed" prep packs were generated, reported clean internally, and then were "shockingly bad," "shallow," "wishy-washy," or contained banned phrases / template fragments / repeated answer openings when tested live by the founder with a real JD and CV.
- A live test that produced a genuinely bad pack turned out, on inspection, to be correct output for the JD the founder had actually pasted — a reminder that "this looks bad" and "this is broken" are not the same diagnosis, and must be separated before any fix is written.
- A frontend/backend key-shape mismatch (Lua's response) shipped silently: the adapter that was meant to fix the frontend contract *dropped two keys the frontend still depended on* (`score_out_of_10`, `voice_and_delivery_coaching`). The fix compiled clean, passed an isolated unit test, and was still broken in the actual UI — every score bar and delivery-coaching panel silently rendered nothing. It was only caught because the founder distrusted a "10/10 passed" report and asked for a deeper frontend-read check.
- A cleanup/verification prompt was nearly sent **twice** in a row — which would have silently created duplicate function definitions (Python lets the second definition silently overwrite the first; `py_compile` does not catch this). It was caught by grepping for definition counts *before* re-sending, not after.

**The lesson, stated as a rule for this project, not a vague principle:**
1. A passing compile is not a passing fix.
2. A passing isolated unit test is not a passing fix.
3. An AI's internal "report" that something works is not a passing fix.
4. The only thing that counts as a passing fix is: real call, real shape, real live site, founder's own eyes.
5. Before re-running any "verify and fix" prompt, grep for existing definitions first. Never assume a fix wasn't already applied.

This is why every build session in this project is deliberately narrow ("make exactly N changes, nothing else") and why every session ends with an explicit verification step rather than trusting the agent's own summary.

---

## What is actually confirmed working right now

Treat everything below as verified by grep/compile/test output the founder has personally seen, not by agent self-report.

**The six-module pipeline** (Company Intelligence → Role Intelligence → Candidate Profile → Gap Map → Interview Strategy → Prep Pack) runs sequentially, writes structured JSON artifacts per module, and each module reads only the artifacts it depends on.

**The full backend stress test (17 targeted tests) passed, including the harder second pass after the founder correctly pushed back that the first pass "felt shallow":**
- Tavily retry logic backs off correctly (2s, 5s) and on total exhaustion returns `[]` and logs a warning — it never crashes a job.
- Lua's response now returns all 10 contract keys the frontend actually reads (`structure_score`, `content_score`, `company_alignment_score`, `overall`, `what_was_strong`, `what_to_improve`, `better_version`, `next_action`, `score_out_of_10`, `voice_and_delivery_coaching`) — confirmed by reading every Lua-reading line in `page.tsx`, not just the adapter's own output.
- All error responses return `{"error": ..., "status_code": ...}` consistently — no endpoint leaks FastAPI's default `{"detail": ...}` shape anymore.
- A corrupted artifact file raises a clean `ValueError` with a human-readable message instead of a raw `JSONDecodeError` traceback.
- Double-clicking "run module" (or any race condition from two near-simultaneous requests) is now atomic via `get_or_create_job()` using `BEGIN IMMEDIATE` — confirmed with two real concurrent threads returning the *same* job_id.
- Running a module out of order (e.g. `interview_strategy` before its four prerequisite modules) now returns **HTTP 400 immediately**, not a false 200 followed by an async failure 10 seconds later.
- All 22 `/lua-*` endpoints require `X-App-Key` authentication — confirmed by listing every Lua route and checking each one individually, not just spot-checking three.
- SQL injection, unicode/emoji round-tripping, 20-concurrent-read locking, credits-overdraft protection, GDPR delete actually removing rows and workspace directories, Stripe webhook signature rejection — all individually tested and passing.
- `.env` confirmed **not** committed to git (checked explicitly — this is the one check that, if it ever fails, overrides every other priority on the list).

**Infrastructure abstraction is built** (not yet deployed): Dockerfile, docker-compose.yml, and a `get_db()` function in `job_store.py` that transparently uses PostgreSQL when `DATABASE_URL` is set and falls back to the existing SQLite path otherwise. Same pattern for Redis: `dispatch_job()` uses RQ when `REDIS_URL` is set, threading otherwise. This means switching to production infrastructure is an environment-variable change, not a rewrite — but **the switch itself has not been flipped yet.** The product is still running on Daytona with SQLite as of the last confirmed check.

**Credits and Stripe infrastructure is built**: `credits` and `credit_transactions` tables exist, `add_credits`/`deduct_credits`/`get_credits` work and are overdraft-protected, the Stripe webhook validates signatures correctly and rejects forged ones. `check_and_deduct()` exists but is deliberately *not wired into any endpoint yet* — because there is no user identity to check credits against (see Gap 1 below). This was a correct, deliberate sequencing decision, not an oversight.

**GDPR infrastructure is built**: `delete_user_data()` removes DB rows and workspace directories, `get_user_data_export()` returns everything held for a user_id, a 90-day retention job runs at startup, `PRIVACY.md` exists. The gap is that nothing currently populates `user_id`/`user_email` on a session, so these endpoints have nothing real to operate on yet.

**The activation layer is built and live**: after Module 2 completes, the UI surfaces one "question you may not have prepared for" pulled from the real artifact (`danger_zones[0].requirement`); after Module 4 completes, it surfaces one verbatim gap-repair script (`repair_scripts[0].verbatim_repair_answer`). This exists specifically because three independent strategic frameworks (Jobs-To-Be-Done sequential-chain analysis, Theory-of-Constraints bottleneck analysis, and Lean Startup activation-event analysis) converged independently on the same diagnosis: the product's biggest risk was that real value only appeared after a 12–15 minute wait, with nothing proving value along the way. When three unrelated frameworks agree on the same root cause, that is treated as high-confidence — it was built first, ahead of everything else.

**Analytics are wired** (PostHog: `session_completed`, `paid_conversion` entry point, `lua_three_rounds`) but the real API key has not been set in Vercel yet, so events fire into nothing.

---

## What is genuinely still open — the real gap, ranked

**Gap 1 — There is no user authentication. This is the one gap that blocks almost everything else.**
No login, no accounts, no session ownership. Concretely, this means: credits cannot be charged to anyone (no identity to deduct from), the offer-rate email cannot be sent (no `user_email` to send it to — confirmed: every existing session row has `user_email = NULL`), the GDPR delete/export endpoints have no real `user_id` to operate on, and the proprietary question-contribution database — the long-term moat — cannot start accumulating data because there's no one to attribute a contribution to.
**This is the next build, before anything else.** Minimal scope only: email + magic link (Clerk or Supabase Auth — not yet decided which). Do not build a full account system. Just enough to get a stable `user_id` and `user_email` attached to a session.

**Gap 2 — Prep pack quality on the live production site has not been re-verified since the architecture was rebuilt.**
The quality fixes from the earlier failure-history period were tested against the *old* pipeline. The pipeline has since been rebuilt into the clean, session-based, stress-tested version described above. Nobody has yet run a real CV + a real JD through the *current* code and judged the output with the same rigor as before. Given the project's own stated lesson ("internal report ≠ live reality"), **this must happen before any user acquisition work, and ideally before the auth build**, so that auth isn't built on top of a pipeline that turns out to need another rework.
The standard to test against, stated plainly: *would this prep pack be genuinely better than what the founder could produce alone in two hours of their own Glassdoor research?* Not perfect. Not exhaustive. Better than solo effort in the same time.

**Gap 3 — The product is still on Daytona, not production infrastructure.**
The Docker/Postgres/Redis abstraction is built and waiting. The actual cutover (point the domain at a Hetzner VPS, set `DATABASE_URL` and `REDIS_URL`) has not happened. Daytona sleeps when idle and has no SLA — it will not survive real concurrent users. This must happen before real users, but it can happen in parallel with the auth build since they don't conflict.

**Gap 4 — Three environment variables are unset, and one of them is a live security hole right now.**
- `APP_KEY` is unset in production. The auth check on all 22 Lua endpoints currently reads: if the key is empty, accept *any* key, including none. This is not a future risk — it is a live exposure the moment this URL is shared with anyone. **Set this before anything else, today, independent of any other work.**
- `NEXT_PUBLIC_POSTHOG_KEY` is unset, so the activation-layer instrumentation is firing into nothing.
- `send_email()` is a console-log stub — no real provider (Resend recommended) is wired, so the offer-rate email cannot actually send even once auth exists.

**Gap 5 — No payment flow exists for a real customer to pay with.**
The Stripe webhook is correct and tested. But no Stripe products/prices have been created in the dashboard, and the frontend has no pricing page or checkout button wired to them. `check_and_deduct()` has nowhere to plug in yet because of Gap 1.

**Gap 6 — The moat (user-contributed question database) has zero rows, because it cannot start until Gap 1 is closed.**
This is listed as a gap, not a risk, because it is not a problem to be fixed — it is simply blocked, and every week it stays blocked is a week of moat-building lost. It should be the very next thing built immediately after auth, not an eventual nice-to-have.

---

## The correct order to build in from here — and why this order, specifically

This order is not arbitrary. Each step either removes a live risk or unblocks several other steps simultaneously — that is the only criterion used to rank them.

1. **Set `APP_KEY` now.** Five minutes. It is a live exposure, not a backlog item. Do this before reading the rest of this list.
2. **Run the real live quality test** (Gap 2) using a real CV and a real JD. This is a judgment call, not a code change — but it gates everything after it. If the pack fails the "better than 2 hours solo effort" bar, the next step is fixing the pipeline, not building auth on top of it.
3. **Build minimal auth** (Gap 1). The single highest-leverage build remaining — it unblocks credits, GDPR, the offer-rate email, and the moat database simultaneously.
4. **Migrate Daytona → Hetzner** (Gap 3). Can run in parallel with step 3; does not depend on it.
5. **Wire Stripe checkout + create real products** (Gap 5). Depends on step 3 being done.
6. **Wire Resend for the offer-rate email; set the PostHog key** (Gap 4 remainder). Small, depends on step 3.
7. **Start the question-contribution database** (Gap 6). Begins the moment step 3 ships — every session from then on should ask its one contribution question.

Nothing past step 3 matters if step 2 fails. Nothing past step 1 is safe if step 1 hasn't happened. Hold that order.

---

## How to work in this codebase — operating rules, not preferences

- **One narrow session at a time.** Every Claude Code prompt in this project's history that worked stated "make exactly N changes, nothing else" and named the files to read with `grep` before reading anything in full. Sessions that tried to do more than one logical thing at once are the ones that needed cleanup later.
- **Grep before you fix.** Before touching anything that might already exist, check with grep first. At least one near-miss in this project's history came from almost re-applying a fix that had already shipped.
- **Verify with a real call, not a report.** After any change to a response shape (Lua, error handling, anything the frontend reads), trace every line in the frontend that reads that response — don't just confirm the backend returns the "right" keys in isolation.
- **The founder's instinct to distrust a clean report is correct and earned.** If something is reported as fixed and the founder says "this still feels off" or "this feels shallow" — that has been the *correct call* every single time it happened so far in this project. Don't argue against that instinct; investigate it.
- **Do not start anything not in the ordered list above** without an explicit reason tied to one of the six gaps. Voice mock interview, the human expert review layer, B2B tooling, programmatic SEO — all of these were deliberately deferred, in writing, multiple times, specifically *because* they are not on the critical path right now. Reintroducing them before Gap 1–5 are closed repeats a mistake this project has already made and corrected.

---

## What "next" means, concretely, for whoever reads this cold

If you are a new Claude Code session picking this up: your very first action is not to write code. It is to ask the founder which of the seven ordered steps above is currently in progress or about to start, and to confirm the state of `APP_KEY` specifically before doing anything else — because that one is time-sensitive in a way the others are not.
