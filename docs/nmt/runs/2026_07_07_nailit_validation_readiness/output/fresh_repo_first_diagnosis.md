# Fresh Repo-First NailIt Validation Readiness Diagnosis

## 1. Validation Debt

- `NO EVIDENCE`: No field validation, user interviews, payment behavior, non-buyer evidence, analytics, offer outcomes, or real user completion data were inspected in this run.
- `NO EVIDENCE`: No market research or external web research was run in this diagnosis.
- `TESTED`: I performed repository file discovery and static code inspection only; I did not run the app, smoke tests, pytest, external API calls, or frontend build.
- `REPO FACT`: The backend repo contains executable FastAPI code, SQLite/Postgres-backed stores, generation modules, Lua coach modules, and a Next.js frontend contract path, but the inspected code does not prove production readiness.
- `HYPOTHESIS`: The highest validation risk is not feature absence alone; it is that the product can produce impressive prep artifacts without proof that users trust them, complete them, pay for them, or improve interview outcomes.

## 2. Fatal if wrong

- `HYPOTHESIS`: If paid users already exist outside the repo evidence, the business-readiness conclusion would change, but that evidence was not provided or inspected.
- `HYPOTHESIS`: If the deployed environment has additional private configuration, checkout routes, auth middleware, email provider code, or tests not present in these repos, several blockers would weaken.
- `HYPOTHESIS`: If generated answers have already been manually reviewed against real candidate source material at scale, the answer-quality risk would be lower, but no such review evidence was found in the inspected repo paths.
- `HYPOTHESIS`: If the frontend uses routes not present in the inspected active app tree, frontend/backend contract risk could be under- or overstated.

## 3. Cheapest real world test

`HYPOTHESIS`: Run a paid concierge validation with 3 to 5 real candidates who have scheduled interviews, using the current product manually assisted by the founder. Charge before delivery or request a real payment commitment, generate one prep pack, run one Lua practice session, capture whether they complete it, trust it, use it, and would pay again. This tests value, trust, completion, payment, and operational feasibility without building more features.

## 4. Block or proceed

`BLOCKED`: Block external self-serve validation and paid checkout launch. `PROCEED`: proceed only to controlled concierge or pilot validation after adding a thin smoke-test layer for setup/auth/runtime and manually operating the current backend.

## 5. First pass

### What NailIt actually implements today

- `REPO FACT`: `api.py` defines a FastAPI app with prep-pack endpoints (`/prepare`, `/prepare/start`, `/prepare/status/{job_id}`), session/module endpoints (`/session/create`, `/session/get`, `/module/run`, `/module/status`), answer generation (`/answers/generate`), many Lua coaching endpoints, Stripe webhook handling, follow-up email sending, and GDPR-style export/delete endpoints.
- `REPO FACT`: The current modular product flow is: create a session, run `company_intelligence`, `role_intelligence`, `candidate_profile`, `gap_map`, `interview_strategy`, then `prep_pack`.
- `REPO FACT`: `agent_v2.py` implements company research collection through Tavily when `TAVILY_API_KEY` exists, JD analysis, candidate profile extraction, gap map, interview strategy, prep pack assembly, artifact validation, banned-string checks, and metric stripping.
- `REPO FACT`: `answer_generator.py` implements `/answers/generate` by reading `jobs/{session_id}/candidate_profile/candidate_profile.json`, selecting an assigned story by ID or title, calling the LLM, normalizing three answer options, and using a deterministic fallback if answers are outside the word-count range.
- `REPO FACT`: Lua coach functionality exists across `lua_coach.py`, `lua_benchmark_coach.py`, `lua_memory_*`, `lua_mastery_store.py`, `lua_state_engine.py`, and pressure/drill/escalation modules.

### What is documented but not verified

- `DOC CLAIM`: `PRIVACY.md` says raw CV is not stored after prep-pack generation.
- `REPO FACT`: `job_store.py` stores `raw_cv`, `raw_jd`, `raw_answer_bank`, company context, and transcripts in the `sessions` table; so the privacy claim is not verified by repo behavior and appears contradicted for session-based flows.
- `DOC CLAIM`: `PRIVACY.md` says access and deletion rights exist via `/user/{your_id}/data-export` and `/user/{your_id}/data`.
- `REPO FACT`: those endpoints exist in `api.py`, but they do not use `Depends(require_app_key)` and no user authentication/ownership check was found.

### What is broken, risky, stubbed, or missing

- `REPO FACT`: `requirements.txt` lists only `daytona`, `asyncpg`, `psycopg2-binary`, `python-dotenv`, `rq`, `redis`, and `stripe`.
- `REPO FACT`: runtime imports include `fastapi`, `pydantic`, `openai`, and `uvicorn` usage in `Dockerfile`; these are not declared in `requirements.txt`.
- `REPO FACT`: `.env.example` uses `APP_KEY=your-secret-key-here`, while `api.py` and the frontend proxy expect `APP_API_KEY`.
- `REPO FACT`: `send_email()` is explicitly a stub and only logs/prints.
- `REPO FACT`: Stripe webhook crediting exists, but no backend route creates a checkout session, and `check_and_deduct()` says it is not wired into endpoints yet.
- `REPO FACT`: `create_session()` does not store `user_email` or `user_id` from request payload; follow-up emails query `user_email IS NOT NULL`, so normal session creation does not create follow-up-eligible records.
- `REPO FACT`: `delete_user_data()` deletes sessions before running a jobs-row deletion query that selects session IDs from the now-deleted sessions table, so job row deletion is likely incomplete even when workspaces are removed.

## 6. Self critique

- `MODEL INFERENCE`: This diagnosis is strong on static code evidence but weak on runtime behavior because no server, test suite, or smoke run was executed.
- `MODEL INFERENCE`: The frontend was inspected only for backend contract evidence; a full frontend UX or validation-readiness audit was not performed.
- `MODEL INFERENCE`: The repo has generated artifacts and SQLite DBs, but I did not inspect their data contents to avoid treating old local artifacts as current product truth.
- `MODEL INFERENCE`: Some backend behavior may work in the developer's local environment through undeclared dependencies installed in `.venv`, but missing dependency declarations still block reproducible validation.
- `MODEL INFERENCE`: Prior NailIt documents were excluded from the fresh pass; this reduces carryover risk but means historical claims, planned pricing, and New Frontiers evidence were intentionally not used.

## 7. Evidence check

- `REPO FACT`: Auth for most protected endpoints is a shared `X-App-Key` header checked by `require_app_key()`.
- `REPO FACT`: `/`, `/webhooks/stripe`, `/internal/send-followups`, `/user/{user_id}/data`, and `/user/{user_id}/data-export` do not use `Depends(require_app_key)` in `api.py`.
- `REPO FACT`: The frontend `lib/backend.ts` reads server-side `APP_API_KEY` and sends `X-App-Key` to backend proxies.
- `REPO FACT`: Frontend API routes exist for session creation, module run/status, answers, Lua, prepare, and prepare status.
- `REPO FACT`: No frontend route was found for Stripe checkout, GDPR export/delete, or follow-up contribution capture.
- `REPO FACT`: `lua_smoke_test.py` exists, but it does not set `X-App-Key` headers while Lua endpoints require `Depends(require_app_key)`, so it is not aligned with current backend auth.
- `NO EVIDENCE`: No pytest suite, CI config, or production smoke check was found in the inspected backend tree.

## 8. Missing information list

1. `NO EVIDENCE`: What we still do not know: whether real candidates complete the flow, trust the outputs, and use them in interviews.
2. `NO EVIDENCE`: Missing respondent types: buyers, non-buyers, urgent scheduled-interview candidates, skeptical users, and people who chose human coaches or free ChatGPT instead.
3. `NO EVIDENCE`: Missing non-buyer evidence: no refusals, objections, abandonment reasons, or price rejections.
4. `NO EVIDENCE`: Missing consideration set: repo does not show what users compare NailIt against.
5. `NO EVIDENCE`: Missing near-purchase barriers: no checkout-start, pricing-page, or purchase-abandon data.
6. `NO EVIDENCE`: Missing price threshold: no repo evidence of paid willingness-to-pay behavior.
7. `NO EVIDENCE`: Unclear first Aha moment: no instrumentation proves when a user first experiences value.
8. `NO EVIDENCE`: Whether alternatives were explored: no customer discovery evidence in this fresh pass.
9. `NO EVIDENCE`: Whether willingness to pay is behavior or opinion: no payment or refusal behavior found.
10. `REPO FACT`: Payment evidence exists as webhook code only, not as checkout or paid user behavior.
11. `NO EVIDENCE`: Stated interest is not separable from observed behavior because neither was inspected as field data.
12. `HYPOTHESIS`: The conclusion would change if real paid concierge sessions showed users pay, complete, trust, and reuse the product outputs.

## 9. Final diagnosis

`BLOCKED`: NailIt is not ready for open external validation as a self-serve paid product. It is closer to a founder-operated concierge validation tool: the backend has substantial prep-pack and Lua coaching capability, but validation-critical infrastructure is incomplete or unproven.

`REPO FACT`: The core preparation product is implemented enough to create sessions, run modules, generate prep artifacts, generate answer options, and run Lua coaching flows.

`REPO FACT`: The product is not payment-ready because there is no checkout creation route, credit deduction is not wired into paid actions, and no frontend checkout path was found.

`REPO FACT`: The product is not auth-ready for real users because it uses a shared app key, does not implement user accounts or ownership checks, and exposes GDPR export/delete endpoints without the app-key dependency.

`REPO FACT`: The product is not email/contribution-ready because email delivery is a stub, session creation does not store user email, and no outcome-capture endpoint for "got the offer / did not get the offer / still in process" was found.

`REPO FACT`: The product is not reproducibly deployable from declared backend dependencies because `requirements.txt` omits core imported/runtime packages.

`STORY RISK`: It would be misleading to claim validation readiness, paid readiness, privacy readiness, or defensible quality assurance from repo evidence alone.

## 10. Evidence ledger

| Claim | Label | Evidence |
|---|---|---|
| Backend repo confirmed at `/Users/asia/interview-agent` | `REPO FACT` | `pwd`, `git remote -v` |
| Frontend related repo confirmed at `/Users/asia/interview-frontend` | `REPO FACT` | frontend `git remote -v` |
| Main backend app is FastAPI | `REPO FACT` | `api.py` imports and `app = FastAPI()` |
| Shared API-key auth exists | `REPO FACT` | `require_app_key()` and protected endpoint dependencies in `api.py` |
| User account auth was not found | `NO EVIDENCE` | no account/session ownership implementation found in inspected backend |
| Stripe webhook exists | `REPO FACT` | `/webhooks/stripe` in `api.py` |
| Checkout creation route not found | `NO EVIDENCE` | searched backend and frontend for checkout/payment routes |
| Email provider delivery is stubbed | `REPO FACT` | `send_email()` docstring and implementation in `api.py` |
| GDPR export/delete endpoints exist | `REPO FACT` | `/user/{user_id}/data-export`, `/user/{user_id}/data` in `api.py` |
| GDPR endpoints are not protected by app-key dependency | `REPO FACT` | endpoint decorators in `api.py` lack `Depends(require_app_key)` |
| Lua endpoints exist and are protected by app key | `REPO FACT` | `/lua-*` decorators in `api.py` |
| Lua smoke test exists but lacks app-key headers | `REPO FACT` | `lua_smoke_test.py` uses plain `urllib.request` headers without `X-App-Key` |
| No pytest suite found | `REPO FACT` | file discovery found `lua_smoke_test.py` but no pytest suite/config |
| Real user demand is unproven | `NO EVIDENCE` | no field/payment evidence inspected |

## 11. Verified repo facts

- `REPO FACT`: Backend files inspected include `api.py`, `agent_v2.py`, `answer_generator.py`, `job_store.py`, Lua store/coach modules, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `.env.example`, `README.md`, and `PRIVACY.md`.
- `REPO FACT`: Frontend contract files inspected include `lib/backend.ts`, selected `app/api/*/route.ts` proxy routes, and `app/page.tsx` call sites.
- `REPO FACT`: `api.py` protects session/module/prep/answers/Lua endpoints with `Depends(require_app_key)`.
- `REPO FACT`: `api.py` does not protect GDPR endpoints with `Depends(require_app_key)`.
- `REPO FACT`: frontend proxy helper sends `X-App-Key` from server-side `APP_API_KEY`.
- `REPO FACT`: `.env.example` in backend uses `APP_KEY`, not `APP_API_KEY`.
- `REPO FACT`: the frontend has no `.env.example` file in the inspected path.
- `REPO FACT`: `Dockerfile` runs `uvicorn api:app`, but `requirements.txt` does not list `uvicorn`.

## 12. Doc claims excluded from this fresh pass

- `DOC CLAIM`: Prior NailIt hypotheses, prior NailIt findings, prior segment assumptions, prior pricing assumptions, prior market assumptions, prior New Frontiers claims, old NMT verdicts, and old research conclusions were excluded from the diagnosis.
- `DOC CLAIM`: A repo-wide search accidentally surfaced lines from excluded prior-research folders; those lines were not used as evidence.
- `DOC CLAIM`: This fresh pass used only repo behavior and the allowed workbench/manifest rules for conclusions.

## 13. Product blockers

1. `REPO FACT`: Backend dependency declaration is incomplete; fresh deploy/build from `requirements.txt` is likely to fail without `fastapi`, `uvicorn`, `openai`, and possibly other imported packages.
2. `REPO FACT`: Shared app-key auth is not real user auth and does not prove per-user data protection.
3. `REPO FACT`: GDPR export/delete endpoints are reachable without app-key dependency.
4. `REPO FACT`: Stripe webhook can credit users after checkout, but no checkout creation path was found.
5. `REPO FACT`: Credit deduction is not wired into paid endpoints.
6. `REPO FACT`: Email follow-up is stubbed and normal session creation does not store `user_email`.
7. `REPO FACT`: Lua smoke test is out of sync with protected Lua endpoints because it omits `X-App-Key`.
8. `REPO FACT`: Answer generation and Lua coach prompts permit invented realistic detail/metrics within boundaries; this is useful for practice but risky for trust unless clearly disclosed and tested.

## 14. Validation blockers

1. `NO EVIDENCE`: No proof users will pay.
2. `NO EVIDENCE`: No proof users trust AI-generated answer options or Lua feedback.
3. `NO EVIDENCE`: No proof users complete a full prep pack plus practice loop.
4. `NO EVIDENCE`: No proof the first Aha moment occurs before abandonment.
5. `NO EVIDENCE`: No non-buyer objections or alternative-choice evidence.
6. `NO EVIDENCE`: No payment threshold, checkout-start, or purchase-abandon data.
7. `NO EVIDENCE`: No actual offer outcome capture or contribution loop.

## 15. Missing tests

- `HYPOTHESIS`: Add API-key tests for every protected and unprotected route, especially GDPR export/delete and Lua endpoints.
- `HYPOTHESIS`: Add setup/import test that installs from `requirements.txt` and imports `api:app`.
- `HYPOTHESIS`: Add checkout/payment tests for checkout creation, webhook crediting, insufficient credits, and credit deduction per module.
- `HYPOTHESIS`: Add GDPR deletion/export tests proving user ownership, sessions, jobs, workspaces, credits, transactions, Lua session DBs, benchmark DBs, memory DBs, and mastery DBs are included or explicitly excluded.
- `HYPOTHESIS`: Add answer-quality regression tests for repeated stories, boilerplate leakage, unsupported metrics, forbidden role/domain claims, and fallback answer disclosure.
- `HYPOTHESIS`: Add smoke tests aligned with `X-App-Key` for session creation, module dependency gating, answer generation, Lua health, Lua memory, benchmark practice, and state.
- `HYPOTHESIS`: Add frontend/backend contract tests for proxy routes and required environment variables.

## 16. Readiness rating

- `REPO FACT`: Core product implementation depth: medium-high for backend prep and Lua features.
- `REPO FACT`: Self-serve production readiness: low.
- `NO EVIDENCE`: Paid validation readiness: unproven.
- `HYPOTHESIS`: Concierge validation readiness: medium, if manually operated and if setup/auth/runtime smoke checks pass first.
- `BLOCKED`: Do not launch open paid checkout or broad external validation yet.

## 17. Recommended next Codex loop

`PROCEED`: Run a read-only or tests-only harness audit next, not market research. The next Codex loop should be:

1. `TESTED`: create or run a no-external-API setup/import smoke check.
2. `TESTED`: add route-protection tests for auth/GDPR/Lua endpoints.
3. `TESTED`: add payment/credit wiring tests before any production patch.
4. `TESTED`: add answer-quality regression tests before changing prompts or generation logic.
5. `HYPOTHESIS`: only after those pass, run a paid concierge validation sprint.

## 18. Files inspected

### Workbench files

- `docs/nmt/WORKBENCH_READY_STATUS.md`
- `docs/nmt/START_HERE_FOR_ANASTASIA.md`
- `docs/nmt/_harness/CODEX_NMT_HARNESS_ADVANCED.md`
- `docs/nmt/_harness/OUTPUT_CONTRACT.md`
- `docs/nmt/_harness/CLAIM_TAGGING_SCHEMA.md`
- `docs/nmt/_harness/RUN_LIFECYCLE.md`
- `docs/nmt/_templates/EVIDENCE_LEDGER_TEMPLATE.md`
- `docs/nmt/_templates/RUN_STATE_TEMPLATE.md`
- `docs/nmt/_source_library/validation_gate/VALIDATION_GATE.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/RUN_MANIFEST.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/state/EVIDENCE_LEDGER.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/state/NMT_RUN_STATE.md`

### Backend files

- `api.py`
- `agent_v2.py`
- `answer_generator.py`
- `job_store.py`
- `lua_coach.py`
- `lua_benchmark_coach.py`
- `lua_session_store.py`
- `lua_benchmark_store.py`
- `lua_memory_engine.py`
- `lua_memory_store.py`
- `lua_mastery_store.py`
- `lua_state_engine.py`
- `lua_pressure_repair_engine.py`
- `lua_smoke_test.py`
- `research_config.py`
- `requirements.txt`
- `.env.example`
- `Dockerfile`
- `docker-compose.yml`
- `PRIVACY.md`
- `README.md`

### Frontend files inspected only for contract evidence

- `/Users/asia/interview-frontend/lib/backend.ts`
- `/Users/asia/interview-frontend/app/api/session/create/route.ts`
- `/Users/asia/interview-frontend/app/api/module/run/route.ts`
- `/Users/asia/interview-frontend/app/api/answers/route.ts`
- `/Users/asia/interview-frontend/app/api/lua/route.ts`
- `/Users/asia/interview-frontend/app/api/prepare/route.ts`
- `/Users/asia/interview-frontend/app/api/prepare/start/route.ts`
- `/Users/asia/interview-frontend/app/page.tsx`

## 19. Evidence used

- `REPO FACT`: Static inspection of backend and limited frontend contract code.
- `TESTED`: File discovery, `git remote -v`, grep/rg searches, and `git status --short --untracked-files=no`.
- `DOC CLAIM`: Workbench rules and manifest only, not prior NailIt research.
- `NO EVIDENCE`: No field data, payment evidence, or external source was used.

## 20. What was not checked

- `NO EVIDENCE`: No prior NailIt research or New Frontiers source was read as evidence after the repo-first pass.
- `NO EVIDENCE`: No external web research was run.
- `NO EVIDENCE`: No app server, smoke test, pytest, frontend build, Docker build, or live endpoint call was run.
- `NO EVIDENCE`: No deployed environment, logs, analytics, Stripe dashboard, PostHog dashboard, email provider, or customer data was inspected.
- `NO EVIDENCE`: No actual generated prep pack was evaluated against a fresh real candidate fixture in this pass.

## 21. What would change the conclusion

- `TESTED`: A clean install/build from declared dependencies and a passing route smoke suite.
- `TESTED`: Auth/ownership tests proving GDPR export/delete and user data access are protected.
- `TESTED`: Payment tests proving checkout creation, webhook crediting, and credit deduction across paid actions.
- `FIELD DATA`: Real candidate sessions showing completion, trust, and use in actual interview preparation.
- `PAYMENT EVIDENCE`: Paid concierge sessions or checkout/payment attempts from qualified candidates.
- `FIELD DATA`: Non-buyer interviews showing why people refuse, what alternatives they choose, and their price threshold.

## 22. Next lowest cost action

`HYPOTHESIS`: Do not build new product scope. Add the smallest tests-only validation harness around the existing backend: import/setup, auth protection, GDPR route protection, payment/credit wiring, and answer-quality guardrails. Then run one founder-led paid concierge test.

## 23. BLOCKED or PROCEED

`BLOCKED`: self-serve paid launch, open external validation, broad feature build, market research, and claims of validation readiness.

`PROCEED`: tests-only hardening and a controlled paid concierge validation after smoke checks pass.
