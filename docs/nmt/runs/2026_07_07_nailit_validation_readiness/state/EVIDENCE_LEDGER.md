# Evidence Ledger

Use this ledger to keep every material claim source-tagged. Move claims between sections only when stronger evidence exists.

## Validation Debt

- `NO EVIDENCE`: No NailIt product claim has field validation in this run.
- `REPO FACT`: Actual backend and limited frontend contract code have been inspected in this repository during the fresh repo-first diagnosis.
- `NO EVIDENCE`: No NailIt app behavior has been tested at runtime in this run.
- `NO EVIDENCE`: No payment, analytics, interview, or usage evidence is present.

## Fatal If Wrong

- `HYPOTHESIS`: If this repository actually contains app code hidden outside the inspected paths, the repo-state claims need revision.
- `HYPOTHESIS`: If external NailIt evidence exists outside this repo, it must be imported or linked before use.

## Cheapest Real World Test

- `HYPOTHESIS`: Run setup/import, auth/GDPR, payment/credit, and answer-quality smoke tests, then conduct a paid concierge validation with 3 to 5 real candidates who have scheduled interviews.

## Block Or Proceed

- Decision: `BLOCKED` for open self-serve paid validation; `PROCEED` for tests-only hardening and controlled concierge validation after smoke checks.
- Reason: Repo evidence shows core backend product capability, but auth, payment, email, GDPR, setup reproducibility, and validation evidence are not ready for open external use.

## REPO FACT

- Backend primary repo path is `/Users/asia/interview-agent`.
- Backend git remote is `https://github.com/damaskinaa/interviewprep`.
- Frontend related repo path is `/Users/asia/interview-frontend`.
- Frontend git remote is `https://github.com/damaskinaa/interviewprep-frontend.git`.
- Backend files `api.py`, `agent_v2.py`, `job_store.py`, `lua_coach.py`, `answer_generator.py`, and `requirements.txt` exist.
- `api.py` defines FastAPI prep, session, module, answer generation, Lua coach, Stripe webhook, follow-up, and GDPR-style export/delete endpoints.
- Most prep/session/module/answer/Lua endpoints use `Depends(require_app_key)` with `X-App-Key`.
- GDPR export/delete endpoints in `api.py` now use `Depends(require_app_key)`.
- `send_email()` in `api.py` now returns an explicit provider-not-configured/not-implemented path instead of console-only behavior.
- Stripe webhook crediting exists in `api.py`; checkout creation is explicitly blocked by a protected `501 payment_checkout_not_ready` route.
- `check_and_deduct()` in `api.py` says it is not wired into endpoints yet.
- `requirements.txt` now declares `fastapi`, `uvicorn`, `openai`, and `pydantic`.
- `.env.example` now uses `APP_API_KEY`.
- `lua_smoke_test.py` now sends `X-App-Key` from `APP_API_KEY` when configured.
- Frontend proxy helper `lib/backend.ts` sends `X-App-Key` from server-side `APP_API_KEY`.
- `docs/nmt/_source_library/projects/nailit/prior_research/` exists.
- `docs/nmt/_source_library/projects/nailit/new_frontiers/` exists.
- This is a split repo product. Backend is the primary diagnosis repo. Frontend is related and may be inspected read only when frontend/backend contract evidence is needed.

## TESTED

- Repository file discovery was tested with `test -e`, `find`, `git remote -v`, and `git status --short`.
- Static repo diagnosis used `sed`, `find`, and `rg` to inspect backend and limited frontend contract files.
- No application tests were run; the Lua smoke script would call local endpoints and mutate SQLite stores.
- Tests-only hardening created `tests/test_validation_readiness_static.py`.
- `python3 -m pytest tests/test_validation_readiness_static.py -q` could not run because `pytest` is not installed.
- A stdlib-only runner executed all 9 static tests directly: 0 passed, 9 failed.
- The tests did not import the FastAPI app, start a server, call OpenAI, call Tavily, call Stripe network APIs, send emails, or mutate production databases.
- Narrow patch remediation updated the failing readiness surfaces without adding new product scope.
- `python3 -m pytest tests/test_validation_readiness_static.py -q` still could not run because `pytest` is not installed.
- A stdlib-only runner executed all 9 static tests after remediation: 9 passed, 0 failed.
- `python3 -m py_compile api.py job_store.py lua_smoke_test.py answer_generator.py tests/test_validation_readiness_static.py` passed.
- Dynamic tests-only coverage created `tests/test_dynamic_readiness_contracts.py`.
- `requirements.txt` now declares `pytest` and `httpx` for dynamic testing.
- `python3 -m pytest tests -q` could not run because `pytest` is not installed in the active interpreter.
- `python3 -m unittest tests.test_dynamic_readiness_contracts -q` passed: 7 tests, 0 failures.
- `python3 -m unittest discover tests -q` passed: 7 tests, 0 failures.
- Dynamic tests used FastAPI TestClient, temp SQLite files, dummy provider environment values, and no live external services.
- GDPR Lua path-safety remediation added an explicit `LUA_DB_BASE_DIR` boundary in `job_store.py`.
- Dynamic tests no longer monkeypatch `job_store._delete_sqlite_session_rows`; they set `LUA_DB_BASE_DIR` to temp storage.
- `python3 -m unittest tests.test_dynamic_readiness_contracts -q` passed after path-safety remediation: 7 tests, 0 failures.
- `python3 -m unittest discover tests -q` passed after path-safety remediation: 7 tests, 0 failures.
- `python3 -m py_compile job_store.py tests/test_dynamic_readiness_contracts.py` passed.
- `python3 -m pytest tests -q` still could not run because `pytest` is not installed in the active interpreter.
- Test-environment setup checked the active interpreter: `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`, Python 3.14.3, no active virtualenv.
- `pytest` is not installed in the active interpreter; `httpx` is installed.
- `requirements.txt` already declares `pytest` and `httpx`.
- Added `dev-requirements.txt` and `pytest.ini`.
- `python3 -m unittest discover tests -q` passed during test-environment setup: 7 tests, 0 failures.
- `python3 -m py_compile tests/test_dynamic_readiness_contracts.py tests/test_validation_readiness_static.py` passed.
- `python3 -m pytest tests -q` remains blocked before collection by missing local pytest installation.
- `.venv/bin/python -m pytest tests -q` ran successfully in the repo virtualenv: 16 tests passed, 0 failed.
- Remaining pytest output is warnings only: Starlette/FastAPI deprecation warnings and Python datetime.utcnow deprecation warnings.
- No external APIs were called during the repo-venv pytest verification.
- No market research was run during the repo-venv pytest verification.
- No production code was modified during the pytest-result recording step.

## FIELD DATA

- No field data found.

## DOC CLAIM

- User stated the three previously created files are draft files only.
- User instructed not to run NMT diagnosis.
- User instructed not to run market research.
- User instructed not to modify production code.
- User instructed not to commit.
- User requested a reusable clean Codex NMT workbench structure.
- User required NailIt to appear only inside the current run folder.
- User required every future business idea to get a new run folder.
- User required no carryover of previous business idea, segment, price, channel, moat, or conclusion unless the current `RUN_MANIFEST.md` explicitly allows it.
- User required prior research to be context only unless verified by repo behavior, tests, field evidence, payment, or reliable external source.

## EXTERNAL SOURCE

- Installed local NMT skill files exist under `/Users/asia/.agents/skills/nmt-*`.
- Installed local NMT skill instructions state that NMT work should ground methodology in canon, mark assumptions, validate cheaply, and avoid treating producer artifacts as proof.

## HYPOTHESIS

- The next useful step is tests-only hardening for setup/import, auth/GDPR, payment/credit, and answer-quality guardrails before any paid self-serve launch.
- The next useful loop is a narrow patch-only pass against the 9 failing static readiness tests.
- The next useful loop is dynamic tests-only coverage with pytest/TestClient and mocked external services.
- The next useful loop is test-environment setup plus narrow GDPR Lua store path-safety remediation.
- The next useful loop is test-environment setup so the declared pytest suite can run reproducibly.
- The next useful action is installing declared dev dependencies in a virtualenv, then running `python3 -m pytest tests -q`.
- The repo virtualenv now runs pytest successfully; the next useful action is CI/repeatable test-command hardening or a narrow product-readiness decision loop.

## MODEL INFERENCE

- Prior setup notes that referenced a different local folder are obsolete for this run and must not be used as current repo evidence.
- NailIt is closer to a founder-operated concierge validation tool than a self-serve paid product based on current repo evidence.

## NO EVIDENCE

- No evidence of NailIt product scope in this repository.
- No field evidence of target users or segments.
- No evidence of a Core Job.
- No evidence of a value proposition.
- No evidence of user interviews.
- No evidence of analytics.
- No evidence of sales, waitlist, retention, or usage.
- No evidence of market validation.
- No payment evidence beyond webhook code.
- No pytest suite or CI evidence found.
