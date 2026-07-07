# Tests-Only Hardening Report

## 1. Validation Debt

- `TESTED`: A static tests-only harness now checks setup/dependency declarations, sensitive route protection, GDPR deletion/export coverage, payment/credit wiring, email/contribution capture, Lua smoke auth alignment, answer-quality guardrails, and frontend/backend key/header contract.
- `TESTED`: The harness was run without importing the FastAPI app, starting a server, calling OpenAI, calling Tavily, calling Stripe network APIs, sending email, or mutating production databases.
- `NO EVIDENCE`: No runtime readiness is proven yet because `pytest` is not installed and no dynamic app tests were run.

## 2. Fatal if wrong

- `REPO FACT`: These tests are static checks over repository files. Passing them later would not by itself prove production behavior.
- `HYPOTHESIS`: If a failing static test is dismissed without an owner decision or a runtime replacement test, the product can appear validation-ready while still failing users on auth, payment, privacy, email, setup, or answer quality.

## 3. Cheapest real world test

- `HYPOTHESIS`: Fix only the blockers exposed by this harness, install the declared test runner in a reproducible dev environment, then run the same tests plus a minimal FastAPI TestClient suite with mocked external services.

## 4. Block or proceed

- Decision: `BLOCKED` for open external validation and paid self-serve launch.
- Decision: `PROCEED` for a narrow patch-and-test loop that addresses these test failures without adding new product scope.

## 5. Tests created

- `TESTED`: Created `tests/test_validation_readiness_static.py`.
- The test file contains 9 static tests:
  - `test_requirements_declare_core_runtime_dependencies`
  - `test_sensitive_routes_require_auth_or_signature_guard`
  - `test_gdpr_data_deletion_covers_all_known_storage_surfaces`
  - `test_user_data_routes_have_auth_or_ownership_guard`
  - `test_payment_and_credit_wiring_is_complete`
  - `test_email_and_contribution_capture_are_real`
  - `test_lua_smoke_test_sends_app_key_for_protected_lua_routes`
  - `test_answer_quality_guardrails_are_present_static`
  - `test_frontend_backend_env_and_header_contract`

## 6. Tests run

- `TESTED`: `python3 -m pytest tests/test_validation_readiness_static.py -q`
  - Result: not run by pytest because the environment lacks `pytest`.
  - Output: `No module named pytest`.
- `TESTED`: A stdlib-only runner imported `tests/test_validation_readiness_static.py` and executed every `test_*` function directly.
  - Result: 0 passed, 9 failed.

## 7. Tests passed

- `TESTED`: 0 tests passed after the hardened static checks were executed.

## 8. Tests failed

- `TESTED`: 9 tests failed:
  - `test_answer_quality_guardrails_are_present_static`: fallback answers do not disclose fallback/manual-review status.
  - `test_email_and_contribution_capture_are_real`: `send_email` is stubbed or console-only.
  - `test_frontend_backend_env_and_header_contract`: backend `.env.example` does not document `APP_API_KEY`.
  - `test_gdpr_data_deletion_covers_all_known_storage_surfaces`: GDPR deletion does not cover or explicitly exclude Lua session, benchmark, memory, and mastery stores.
  - `test_lua_smoke_test_sends_app_key_for_protected_lua_routes`: Lua smoke test does not send `X-App-Key` while Lua routes are protected.
  - `test_payment_and_credit_wiring_is_complete`: checkout creation route is missing.
  - `test_requirements_declare_core_runtime_dependencies`: `requirements.txt` is missing `fastapi`, `openai`, `pydantic`, and `uvicorn`.
  - `test_sensitive_routes_require_auth_or_signature_guard`: `/internal/send-followups`, `/user/{user_id}/data`, and `/user/{user_id}/data-export` lack `Depends(require_app_key)`.
  - `test_user_data_routes_have_auth_or_ownership_guard`: GDPR export/delete endpoints lack app-key or equivalent ownership auth.

## 9. Tests not run

- `TESTED`: Pytest did not run because `pytest` is not installed.
- `NO EVIDENCE`: No FastAPI TestClient tests were run.
- `NO EVIDENCE`: No dynamic answer-generation tests were run.
- `NO EVIDENCE`: No Stripe, email, OpenAI, Tavily, frontend build, or database mutation tests were run.

## 10. What each failure proves

- `REPO FACT`: Missing runtime dependencies in `requirements.txt` make setup/import readiness unproven.
- `REPO FACT`: Sensitive route protection is incomplete for internal follow-up and GDPR user-data endpoints.
- `REPO FACT`: GDPR delete/export coverage is incomplete for Lua-related data stores or lacks explicit exclusions.
- `REPO FACT`: Stripe webhook crediting exists, but checkout creation and paid-endpoint credit deduction are not wired.
- `REPO FACT`: Follow-up email delivery is stubbed, and contribution/outcome capture is not exposed as a non-Lua endpoint.
- `REPO FACT`: Lua smoke testing is out of sync with Lua route auth.
- `REPO FACT`: Answer fallback output can look complete instead of clearly marking fallback/manual-review status.
- `REPO FACT`: Backend environment example documents a stale app-key variable name.

## 11. Production files touched

- `TESTED`: No production code files were edited.
- `TESTED`: Only `tests/` and NMT run documentation/state paths were modified.

## 12. Market research run

- `TESTED`: No market research was run.

## 13. External APIs called

- `TESTED`: No external APIs were called.
- `TESTED`: No OpenAI, Tavily, Stripe network, or email delivery calls were made.

## 14. Commit made

- `TESTED`: No commit was made.

## 15. Recommended next loop

- `PROCEED`: Run a narrow patch-only loop for the 9 failing static tests, with production edits limited to dependency declaration, auth guards, GDPR scope/explicit exclusions, payment checkout/credit deduction decisions, email/contribution capture decisions, Lua smoke header alignment, fallback answer disclosure, and env example consistency.
- `BLOCKED`: Do not add new product features or launch validation before these tests either pass or have explicit owner-approved deferrals with replacement checks.

## 16. Evidence used

- `REPO FACT`: `/Users/asia/interview-agent/requirements.txt`
- `REPO FACT`: `/Users/asia/interview-agent/api.py`
- `REPO FACT`: `/Users/asia/interview-agent/job_store.py`
- `REPO FACT`: `/Users/asia/interview-agent/lua_smoke_test.py`
- `REPO FACT`: `/Users/asia/interview-agent/answer_generator.py`
- `REPO FACT`: `/Users/asia/interview-agent/agent_v2.py`
- `REPO FACT`: `/Users/asia/interview-agent/.env.example`
- `REPO FACT`: `/Users/asia/interview-frontend/lib/backend.ts`
- `DOC CLAIM`: `docs/nmt/runs/2026_07_07_nailit_validation_readiness/output/fresh_repo_first_diagnosis.md`

## 17. What was not checked

- Runtime imports after dependency installation.
- FastAPI route behavior with TestClient.
- Real database deletion/export behavior.
- Stripe checkout or webhook behavior against Stripe.
- Email delivery behavior against any provider.
- OpenAI/Tavily answer generation.
- Frontend runtime behavior or build output.
- Live user, payment, or field validation evidence.

## 18. What would change the conclusion

- `TESTED`: The static harness passes under pytest in a clean environment.
- `TESTED`: Dynamic TestClient tests prove sensitive route auth, GDPR delete/export behavior, payment credit/deduction behavior, and mocked email/contribution flows.
- `FIELD DATA`: Controlled concierge validation produces real user behavior evidence after technical blockers are addressed.
- `PAYMENT EVIDENCE`: A real checkout-to-credit path is proven without manual intervention.

## 19. Next lowest cost action

- Install or declare the test runner in the dev/test environment, then run a narrow patch-only loop against `tests/test_validation_readiness_static.py` until each failure is either fixed or explicitly deferred with a safer replacement check.

## 20. BLOCKED or PROCEED

- `BLOCKED`: Open paid/self-serve validation and broad external validation remain blocked.
- `PROCEED`: Narrow patch-only loop against the failing tests is the next safe Codex loop.
