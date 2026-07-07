import os
import re
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = Path(
    os.getenv("NAILIT_FRONTEND_ROOT", str(BACKEND_ROOT.parent / "interview-frontend"))
).expanduser()


def read_repo_text(relative_path, root=BACKEND_ROOT):
    return (root / relative_path).read_text(encoding="utf-8")


def read_optional_text(path):
    path = Path(path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def normalized_requirements():
    requirements = []
    for raw_line in read_repo_text("requirements.txt").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[<>=~!;\[]", line, maxsplit=1)[0].strip().lower()
        requirements.append(name)
    return set(requirements)


def fastapi_routes(api_source):
    route_re = re.compile(
        r"@app\.(?P<method>get|post|delete|put|patch)\("
        r"(?P<quote>['\"])(?P<path>.*?)(?P=quote)(?P<decorator>[^\n]*)\)\n"
        r"(?:async\s+)?def\s+(?P<function>\w+)",
        re.MULTILINE,
    )
    return [match.groupdict() for match in route_re.finditer(api_source)]


def route_for(routes, path):
    return next((route for route in routes if route["path"] == path), None)


def has_app_key_guard(route):
    return bool(route and "Depends(require_app_key)" in route["decorator"])


def function_source(source, name):
    match = re.search(
        rf"^def {re.escape(name)}\(.*?(?=^def |\Z)",
        source,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(0) if match else ""


def test_requirements_declare_core_runtime_dependencies():
    declared = normalized_requirements()
    required = {
        "fastapi",
        "uvicorn",
        "openai",
        "pydantic",
        "stripe",
        "python-dotenv",
    }
    missing = sorted(required - declared)
    assert not missing, (
        "requirements.txt must declare core runtime packages used by the backend. "
        f"Missing: {missing}"
    )
    assert {"asyncpg", "psycopg2-binary"} & declared, (
        "requirements.txt must declare at least one Postgres driver used by the backend."
    )


def test_sensitive_routes_require_auth_or_signature_guard():
    api_source = read_repo_text("api.py")
    routes = fastapi_routes(api_source)
    sensitive_paths = [
        "/prepare",
        "/session/create",
        "/session/get",
        "/module/run",
        "/module/status",
        "/answers/generate",
        "/internal/send-followups",
        "/user/{user_id}/data",
        "/user/{user_id}/data-export",
    ]
    sensitive_paths.extend(route["path"] for route in routes if route["path"].startswith("/lua"))

    unprotected = [
        path for path in sorted(set(sensitive_paths))
        if not has_app_key_guard(route_for(routes, path))
    ]

    webhook = route_for(routes, "/webhooks/stripe")
    webhook_guarded_by_signature = (
        bool(webhook)
        and "stripe.Webhook.construct_event" in api_source
        and "STRIPE_WEBHOOK_SECRET" in api_source
    )

    assert webhook_guarded_by_signature, (
        "Stripe webhook must exist and verify Stripe signatures without relying on app-key auth."
    )
    assert not unprotected, (
        "Sensitive routes must use Depends(require_app_key). "
        f"Unprotected sensitive routes: {unprotected}"
    )


def test_gdpr_data_deletion_covers_all_known_storage_surfaces():
    job_store = read_repo_text("job_store.py")
    deletion_source = function_source(job_store, "delete_user_data")
    assert deletion_source, "delete_user_data must exist."

    expected_primary_surfaces = {
        "sessions": "sessions",
        "jobs": "jobs",
        "workspaces": "Path(\"jobs\")",
        "credits": "credits",
        "credit_transactions": "credit_transactions",
    }
    missing_primary = [
        name for name, token in expected_primary_surfaces.items()
        if token not in deletion_source
    ]
    assert not missing_primary, (
        "delete_user_data must delete or explicitly handle primary storage surfaces. "
        f"Missing: {missing_primary}"
    )

    lua_surfaces = {
        "lua session DBs": ["lua_sessions.db", "lua_session"],
        "lua benchmark DBs": ["lua_benchmark_sessions.db", "benchmark"],
        "lua memory DBs": ["lua_memory.db", "memory"],
        "lua mastery DBs": ["lua_mastery.db", "mastery"],
    }
    missing_lua = [
        name for name, tokens in lua_surfaces.items()
        if not any(token in deletion_source for token in tokens)
    ]
    assert not missing_lua, (
        "delete_user_data must delete or explicitly exclude Lua-related data stores. "
        f"Missing coverage: {missing_lua}"
    )


def test_user_data_routes_have_auth_or_ownership_guard():
    api_source = read_repo_text("api.py")
    routes = fastapi_routes(api_source)
    user_data_paths = ["/user/{user_id}/data", "/user/{user_id}/data-export"]
    unguarded = [
        path for path in user_data_paths
        if not has_app_key_guard(route_for(routes, path))
    ]
    assert not unguarded, (
        "GDPR export/delete endpoints expose user-scoped data and must require app-key "
        f"or equivalent ownership auth. Unguarded: {unguarded}"
    )


def test_payment_and_credit_wiring_is_complete():
    api_source = read_repo_text("api.py")
    job_store = read_repo_text("job_store.py")

    has_webhook = '@app.post("/webhooks/stripe")' in api_source
    has_crediting = "add_credits(" in api_source or "credit_user(" in api_source
    has_credit_store = "def add_credits(" in job_store or "def credit_user(" in job_store
    has_deduction_gate = "def check_and_deduct(" in api_source
    deduction_call_count = api_source.count("check_and_deduct(")
    has_checkout_creation = any(
        token in api_source
        for token in [
            "checkout.Session.create",
            "checkout.sessions.create",
            '"/checkout',
            '"/create-checkout',
            '"/payment/checkout',
        ]
    )
    checkout_explicitly_blocked = (
        "payment_checkout_not_ready" in api_source
        and "status_code=501" in api_source
        and '@app.post("/checkout/create", dependencies=[Depends(require_app_key)])' in api_source
    )

    assert has_webhook, "Stripe webhook route must exist."
    assert has_crediting and has_credit_store, "Payment completion must credit users in durable storage."
    assert has_checkout_creation or checkout_explicitly_blocked, (
        "Checkout must either be implemented or explicitly blocked with a protected 501 route."
    )
    assert checkout_explicitly_blocked or (has_deduction_gate and deduction_call_count > 1), (
        "check_and_deduct exists but is not wired into paid endpoints, and checkout is not explicitly blocked."
    )


def test_email_and_contribution_capture_are_real():
    api_source = read_repo_text("api.py")
    job_store = read_repo_text("job_store.py")

    send_email = function_source(api_source, "send_email")
    create_session = function_source(job_store, "create_session")
    route_paths = [route["path"] for route in fastapi_routes(api_source)]

    stub_markers = ["send_email stub", "stub", "print("]
    stores_user_email = "user_email" in create_session and "INSERT INTO sessions" in create_session
    has_contribution_endpoint = any(
        re.search(r"(outcome|contribution|offer|result|feedback)", path, flags=re.I)
        for path in route_paths
        if not path.startswith("/lua")
    )

    assert send_email and not any(marker in send_email.lower() for marker in stub_markers), (
        "send_email is stubbed or console-only; follow-up delivery is not real."
    )
    assert stores_user_email, "create_session must persist user_email for follow-up selection."
    assert "user_email IS NOT NULL" in job_store, (
        "follow-up selection must be able to find sessions with user_email."
    )
    assert has_contribution_endpoint, (
        "No non-Lua contribution/outcome/offer/result feedback capture endpoint was found."
    )


def test_lua_smoke_test_sends_app_key_for_protected_lua_routes():
    api_source = read_repo_text("api.py")
    smoke_source = read_repo_text("lua_smoke_test.py")
    lua_routes_are_protected = any(
        route["path"].startswith("/lua") and has_app_key_guard(route)
        for route in fastapi_routes(api_source)
    )

    assert lua_routes_are_protected, "Lua routes should be protected by require_app_key."
    assert "X-App-Key" in smoke_source, (
        "lua_smoke_test.py calls protected Lua routes but does not send X-App-Key."
    )


def test_answer_quality_guardrails_are_present_static():
    answer_generator = read_repo_text("answer_generator.py")
    agent = read_repo_text("agent_v2.py")
    combined = f"{answer_generator}\n{agent}"
    fallback_answer = function_source(answer_generator, "_fallback_answer")
    fallback_body = fallback_answer.split("\n", 1)[1] if "\n" in fallback_answer else fallback_answer

    required_guardrails = {
        "source story traceability": ["_story_lookup", "assigned_story_id", "assigned_story_title"],
        "boilerplate leakage": ["PACK_QUALITY_BANNED_STRINGS", "assert_no_banned_visible_strings"],
        "unsupported metrics": ["strip_hallucinated_metrics", "METRIC RULE"],
        "invented role/domain claims": ["forbidden_claims", "Do not invent"],
        "story repetition": ["No story may be assigned more than twice"],
    }
    missing = [
        name for name, tokens in required_guardrails.items()
        if not all(token in combined for token in tokens)
    ]
    assert not missing, f"Missing static answer guardrails: {missing}"
    assert re.search(r"fallback|unable|not generated|manual review", fallback_body, flags=re.I), (
        "Fallback answers should disclose fallback/manual-review status instead of looking complete."
    )


def test_backend_env_contract_is_required():
    api_source = read_repo_text("api.py")
    backend_env_example = read_optional_text(BACKEND_ROOT / ".env.example")

    assert 'os.getenv("APP_API_KEY")' in api_source, "Backend must read APP_API_KEY."
    assert "APP_API_KEY" in backend_env_example, (
        "Backend .env.example must document APP_API_KEY."
    )
    assert "APP_KEY" not in backend_env_example, (
        "Backend .env.example must not document stale APP_KEY instead of APP_API_KEY."
    )


def test_frontend_backend_contract_when_frontend_repo_is_available():
    frontend_backend_path = FRONTEND_ROOT / "lib" / "backend.ts"
    if not frontend_backend_path.exists():
        pytest.skip(
            "Frontend repo not available in backend-only CI; skipping sibling frontend contract check."
        )

    frontend_backend = read_repo_text("lib/backend.ts", root=FRONTEND_ROOT)
    frontend_env_example = read_optional_text(FRONTEND_ROOT / ".env.example")

    assert "process.env.APP_API_KEY" in frontend_backend, (
        "Frontend backend proxy must read APP_API_KEY."
    )
    assert '"X-App-Key"' in frontend_backend or "'X-App-Key'" in frontend_backend, (
        "Frontend backend proxy must send X-App-Key."
    )
    assert not frontend_env_example or "APP_API_KEY" in frontend_env_example, (
        "Frontend .env.example must document APP_API_KEY when present."
    )
