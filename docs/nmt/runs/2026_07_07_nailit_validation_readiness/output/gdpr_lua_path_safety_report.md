# GDPR Lua Store Path-Safety Report

## 1. Validation Debt

- `TESTED`: Production GDPR Lua deletion now has an explicit Lua DB base-directory boundary.
- `TESTED`: Dynamic tests prove `delete_user_data` can delete temp Lua sidecar DB rows without monkeypatching the deletion helper.
- `NO EVIDENCE`: This does not validate the product, checkout, email delivery, contribution capture, or field demand.

## 2. Fatal if wrong

- `HYPOTHESIS`: If `LUA_DB_BASE_DIR` is misconfigured in deployment, GDPR Lua deletion may inspect the wrong sidecar DB directory.
- `HYPOTHESIS`: Passing temp-file deletion tests does not prove all production user data is discoverable if future Lua stores are added without registering them.

## 3. Cheapest real world test

- Run the same dynamic tests in a clean environment with pytest installed, then verify deployment config explicitly sets or intentionally omits `LUA_DB_BASE_DIR`.

## 4. Block or proceed

- Decision: `PROCEED` for test-environment setup and broader runtime hardening.
- Decision: `BLOCKED` for open paid/self-serve validation.

## 5. Files changed

- `job_store.py`
- `tests/test_dynamic_readiness_contracts.py`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/output/gdpr_lua_path_safety_report.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/state/EVIDENCE_LEDGER.md`
- `docs/nmt/runs/2026_07_07_nailit_validation_readiness/state/NMT_RUN_STATE.md`

## 6. What was patched

- `REPO FACT`: Added `LUA_DB_BASE_DIR_ENV = "LUA_DB_BASE_DIR"` in `job_store.py`.
- `REPO FACT`: Added `_lua_db_path(db_name)` to resolve Lua sidecar DBs under `LUA_DB_BASE_DIR` when configured, while preserving cwd-based defaults.
- `REPO FACT`: Updated `_delete_sqlite_session_rows` to use `_lua_db_path`.
- `TESTED`: Removed the dynamic test monkeypatch of `job_store._delete_sqlite_session_rows`.
- `TESTED`: Dynamic tests now set `LUA_DB_BASE_DIR` to the temp directory and prove deletion through the production helper.

## 7. Tests run

- `TESTED`: `python3 -m unittest tests.test_dynamic_readiness_contracts -q`
- `TESTED`: `python3 -m unittest discover tests -q`
- `TESTED`: `python3 -m py_compile job_store.py tests/test_dynamic_readiness_contracts.py`
- `TESTED`: `python3 -m pytest tests -q`

## 8. Tests passed

- `TESTED`: `python3 -m unittest tests.test_dynamic_readiness_contracts -q` passed: 7 tests, 0 failures.
- `TESTED`: `python3 -m unittest discover tests -q` passed: 7 tests, 0 failures.
- `TESTED`: `python3 -m py_compile job_store.py tests/test_dynamic_readiness_contracts.py` passed.

## 9. Tests failed

- `TESTED`: `python3 -m pytest tests -q` failed before collection because pytest is not installed in the active interpreter.

## 10. Tests skipped

- `NO EVIDENCE`: No pytest tests ran because pytest is unavailable.
- `TESTED`: No unittest tests were skipped.

## 11. Remaining blockers

- `BLOCKED`: Pytest is declared but not installed in the active interpreter.
- `BLOCKED`: Checkout remains intentionally `501 payment_checkout_not_ready`.
- `BLOCKED`: Contribution/outcome capture remains intentionally `501 contribution_capture_not_ready`.
- `BLOCKED`: Email provider delivery remains intentionally not configured/implemented.
- `NO EVIDENCE`: No live payment, email, OpenAI, Tavily, frontend, deployment, or field validation behavior was checked.

## 12. Production files touched

- `TESTED`: Production edit was limited to `job_store.py`.
- `TESTED`: No frontend code was modified.

## 13. External APIs called

- `TESTED`: No external APIs were called.
- `TESTED`: No OpenAI, Tavily, Stripe network, or email provider calls were made.

## 14. Market research run

- `TESTED`: No market research was run.

## 15. Commit made

- `TESTED`: No commit was made.

## 16. Evidence used

- `DOC CLAIM`: `docs/nmt/runs/2026_07_07_nailit_validation_readiness/output/dynamic_tests_only_report.md`
- `TESTED`: `tests/test_dynamic_readiness_contracts.py`
- `REPO FACT`: `job_store.py`

## 17. What was not checked

- Pytest execution.
- Deployment environment configuration for `LUA_DB_BASE_DIR`.
- Live production database deletion.
- Frontend runtime/build behavior.
- Real Stripe checkout or webhook calls.
- Real email provider delivery.
- OpenAI/Tavily generation.
- Field validation, payment evidence, retention, or willingness to pay.

## 18. What would change the conclusion

- `TESTED`: Pytest runs cleanly in a reproducible environment.
- `TESTED`: Deployment config review confirms the intended Lua DB sidecar directory.
- `PAYMENT EVIDENCE`: Real checkout-to-credit behavior is implemented and verified.
- `FIELD DATA`: Controlled concierge validation produces real candidate behavior evidence.

## 19. Next lowest cost action

- Install/use the declared test environment so `python3 -m pytest tests -q` can run, then add CI or a repeatable local test command.

## 20. BLOCKED or PROCEED

- `PROCEED`: Test-environment setup or CI hardening.
- `BLOCKED`: Open paid/self-serve validation and product validation claims.
