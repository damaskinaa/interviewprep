import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient


APP_KEY = "dynamic-test-key"


class DynamicReadinessContractsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self._old_env = os.environ.copy()
        os.environ["APP_API_KEY"] = APP_KEY
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_no_network"
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_no_network"
        os.environ["OPENAI_API_KEY"] = "test-disabled-openai"
        os.environ["TAVILY_API_KEY"] = "test-disabled-tavily"
        os.environ["LUA_DB_BASE_DIR"] = str(self.tmp_path)
        os.environ.pop("EMAIL_PROVIDER", None)
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("REDIS_URL", None)

        self.api = self._fresh_api()
        self.client = TestClient(self.api.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        os.environ.clear()
        os.environ.update(self._old_env)
        self.tmpdir.cleanup()

    def _fresh_api(self):
        for module_name in [
            "api",
            "job_store",
            "lua_session_store",
            "lua_benchmark_store",
            "lua_memory_store",
            "lua_memory_engine",
            "lua_mastery_store",
        ]:
            sys.modules.pop(module_name, None)

        job_store = importlib.import_module("job_store")
        job_store.DB_PATH = self.tmp_path / "nailit_jobs.db"

        lua_session_store = importlib.import_module("lua_session_store")
        lua_benchmark_store = importlib.import_module("lua_benchmark_store")
        lua_memory_store = importlib.import_module("lua_memory_store")
        lua_mastery_store = importlib.import_module("lua_mastery_store")
        lua_session_store.DB_PATH = self.tmp_path / "lua_sessions.db"
        lua_benchmark_store.DB_PATH = self.tmp_path / "lua_benchmark_sessions.db"
        lua_memory_store.DB_PATH = self.tmp_path / "lua_memory.db"
        lua_mastery_store.DB_PATH = self.tmp_path / "lua_mastery.db"

        api = importlib.import_module("api")
        api.DB_PATH = self.tmp_path / "api_lua_sessions.db"
        return api

    def auth_headers(self):
        return {"X-App-Key": APP_KEY}

    def error_code(self, response):
        error = response.json().get("error")
        if isinstance(error, dict):
            return error.get("error")
        return error

    def create_session_payload(self, suffix="one"):
        return {
            "company_name": "TestCo",
            "role_name": "Program Manager",
            "job_description": "Own a program and coordinate stakeholders.",
            "cv": "Candidate has program delivery experience.",
            "answer_bank": "I led a cross-functional launch.",
            "company_description": "",
            "youtube_transcripts": "",
            "user_email": f"user-{suffix}@example.test",
            "user_id": f"user-{suffix}",
        }

    def test_fastapi_app_imports_with_declared_dependencies(self):
        self.assertTrue(hasattr(self.api, "app"))
        self.assertEqual(self.api.APP_API_KEY, APP_KEY)

    def test_protected_routes_reject_missing_app_key(self):
        checks = [
            ("post", "/checkout/create", {"user_id": "u1", "product": "starter_pack"}),
            ("post", "/contribution/outcome", {"session_id": "s1", "outcome": "offer"}),
            ("post", "/internal/send-followups", {}),
            ("get", "/user/u1/data-export", None),
            ("delete", "/user/u1/data", None),
            ("get", "/lua-health", None),
        ]
        for method, path, payload in checks:
            request = getattr(self.client, method)
            response = request(path, json=payload) if payload is not None else request(path)
            self.assertEqual(response.status_code, 401, path)

    def test_protected_routes_accept_correct_app_key_where_safe(self):
        checkout = self.client.post(
            "/checkout/create",
            headers=self.auth_headers(),
            json={"user_id": "u1", "product": "starter_pack"},
        )
        self.assertEqual(checkout.status_code, 501)
        self.assertEqual(self.error_code(checkout), "payment_checkout_not_ready")

        contribution = self.client.post(
            "/contribution/outcome",
            headers=self.auth_headers(),
            json={"session_id": "s1", "outcome": "offer", "feedback": "test"},
        )
        self.assertEqual(contribution.status_code, 501)
        self.assertEqual(self.error_code(contribution), "contribution_capture_not_ready")

        export = self.client.get("/user/u1/data-export", headers=self.auth_headers())
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.json()["user_id"], "u1")

        lua_health = self.client.get("/lua-health", headers=self.auth_headers())
        self.assertEqual(lua_health.status_code, 200)
        self.assertEqual(lua_health.json()["status"], "ok")

    def test_gdpr_export_and_delete_routes_are_protected_and_isolated(self):
        create = self.client.post(
            "/session/create",
            headers=self.auth_headers(),
            json=self.create_session_payload("gdpr"),
        )
        self.assertEqual(create.status_code, 200)
        session_id = create.json()["session_id"]

        self.api.save_turn(session_id, "user", "private lua turn")
        self.api.save_benchmark_event(session_id, "practice", {"private": True})
        self.api.add_coach_memory(session_id, "private", "memory", scope="session")
        self.api.update_mastery(session_id, "question", {"score_out_of_10": 6})

        missing_key = self.client.delete("/user/user-gdpr/data")
        self.assertEqual(missing_key.status_code, 401)

        delete = self.client.delete("/user/user-gdpr/data", headers=self.auth_headers())
        self.assertEqual(delete.status_code, 200)
        body = delete.json()
        self.assertEqual(body["deleted_sessions"], 1)
        self.assertGreaterEqual(body["deleted_lua_rows"]["lua_session"], 1)
        self.assertGreaterEqual(body["deleted_lua_rows"]["benchmark"], 1)
        self.assertGreaterEqual(body["deleted_lua_rows"]["memory"], 1)
        self.assertGreaterEqual(body["deleted_lua_rows"]["mastery"], 1)

        export = self.client.get("/user/user-gdpr/data-export", headers=self.auth_headers())
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export.json()["sessions"], [])

    def test_internal_followups_are_protected_and_do_not_send_real_email(self):
        create = self.client.post(
            "/session/create",
            headers=self.auth_headers(),
            json=self.create_session_payload("followup"),
        )
        self.assertEqual(create.status_code, 200)
        session_id = create.json()["session_id"]

        target_date = (datetime.utcnow() - timedelta(days=30)).date().isoformat()
        with sqlite3.connect(self.tmp_path / "nailit_jobs.db") as con:
            con.execute(
                "UPDATE sessions SET created_at = ? WHERE session_id = ?",
                (target_date, session_id),
            )
            con.commit()

        missing_key = self.client.post("/internal/send-followups")
        self.assertEqual(missing_key.status_code, 401)

        response = self.client.post("/internal/send-followups", headers=self.auth_headers())
        self.assertEqual(response.status_code, 501)
        self.assertEqual(self.error_code(response), "email_provider_not_configured")

    def test_session_creation_preserves_user_email_and_user_id_in_temp_db(self):
        response = self.client.post(
            "/session/create",
            headers=self.auth_headers(),
            json=self.create_session_payload("preserve"),
        )
        self.assertEqual(response.status_code, 200)
        session_id = response.json()["session_id"]

        with sqlite3.connect(self.tmp_path / "nailit_jobs.db") as con:
            con.row_factory = sqlite3.Row
            row = con.execute(
                "SELECT user_email, user_id FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row["user_email"], "user-preserve@example.test")
        self.assertEqual(row["user_id"], "user-preserve")

    def test_external_provider_network_calls_are_not_configured(self):
        self.assertEqual(self.api.EMAIL_PROVIDER, "")
        self.assertEqual(os.environ["STRIPE_SECRET_KEY"], "sk_test_no_network")
        self.assertEqual(os.environ["OPENAI_API_KEY"], "test-disabled-openai")
        self.assertEqual(os.environ["TAVILY_API_KEY"], "test-disabled-tavily")


    def _create_owned_session(self, user_id="owner-1"):
        response = self.client.post(
            "/session/create",
            headers={**self.auth_headers(), "X-User-Id": user_id},
            json=self.create_session_payload("owned"),
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["session_id"]

    def test_session_user_id_comes_from_proxy_header_not_body(self):
        session_id = self._create_owned_session("header-user")
        with sqlite3.connect(self.tmp_path / "nailit_jobs.db") as con:
            row = con.execute("SELECT user_id FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        self.assertEqual(row[0], "header-user")

    def test_other_users_cannot_read_or_run_a_session(self):
        session_id = self._create_owned_session("owner-1")
        intruder = {**self.auth_headers(), "X-User-Id": "intruder"}
        owner = {**self.auth_headers(), "X-User-Id": "owner-1"}

        self.assertEqual(self.client.get(f"/session/get?session_id={session_id}", headers=intruder).status_code, 403)
        self.assertEqual(self.client.get(f"/session/get?session_id={session_id}", headers=owner).status_code, 200)

        run = self.client.post(
            "/module/run",
            headers=intruder,
            json={"session_id": session_id, "module_name": "role_intelligence"},
        )
        self.assertEqual(run.status_code, 403)

        answers = self.client.post(
            "/answers/generate",
            headers=intruder,
            json={"session_id": session_id, "question": "Why us?"},
        )
        self.assertEqual(answers.status_code, 403)

        lua = self.client.post(
            "/lua-coach",
            headers=intruder,
            json={"session_id": session_id, "question": "q", "candidate_answer": "a"},
        )
        self.assertEqual(lua.status_code, 403)

    def test_module_status_is_owner_scoped(self):
        session_id = self._create_owned_session("owner-1")
        job_store = sys.modules["job_store"]
        job_id, created = job_store.get_or_create_job(session_id, "role_intelligence", "mod_test_1")
        self.assertTrue(created)

        intruder = self.client.get(
            f"/module/status?job_id={job_id}",
            headers={**self.auth_headers(), "X-User-Id": "intruder"},
        )
        self.assertEqual(intruder.status_code, 403)

        owner = self.client.get(
            f"/module/status?job_id={job_id}",
            headers={**self.auth_headers(), "X-User-Id": "owner-1"},
        )
        self.assertEqual(owner.status_code, 200)
        self.assertNotIn("input_payload", owner.json())

    def test_credits_are_charged_when_enforced(self):
        self.api.CREDITS_ENFORCED = True
        headers = {**self.auth_headers(), "X-User-Id": "payer"}

        broke = self.client.post("/session/create", headers=headers, json=self.create_session_payload("payer"))
        self.assertEqual(broke.status_code, 402)
        self.assertEqual(self.error_code(broke), "insufficient_credits")

        self.api.add_credits("payer", 12, "test grant")
        paid = self.client.post("/session/create", headers=headers, json=self.create_session_payload("payer"))
        self.assertEqual(paid.status_code, 200)

        balance = self.client.get("/credits/balance", headers=headers)
        self.assertEqual(balance.json()["balance"], 2)

    def test_stale_running_jobs_are_failed_on_startup_sweep(self):
        job_store = sys.modules["job_store"]
        job_id, _ = job_store.get_or_create_job("sess_x", "gap_map", "mod_stale_1")
        with sqlite3.connect(self.tmp_path / "nailit_jobs.db") as con:
            con.execute(
                "UPDATE jobs SET status = 'running', updated_at = ? WHERE job_id = ?",
                ((datetime.now() - timedelta(hours=2)).isoformat(), job_id),
            )
            con.commit()
        self.assertEqual(job_store.fail_stale_jobs(minutes=30), 1)
        self.assertEqual(job_store.get_job(job_id)["status"], "failed")

    def test_lua_coach_receives_session_artifacts_as_brief(self):
        session_id = self._create_owned_session("owner-1")
        cwd = os.getcwd()
        os.chdir(self.tmp_path)
        try:
            artifact = self.tmp_path / "jobs" / session_id / "candidate_profile"
            artifact.mkdir(parents=True)
            (artifact / "candidate_profile.json").write_text('{"story_inventory": ["Queue routing redesign"]}')

            captured = {}

            def fake_coach(**kwargs):
                captured.update(kwargs)
                return {"score_out_of_10": 7, "what_worked": "ok", "what_was_weak": "", "top_1_percent_answers": {}}

            self.api.build_lua_coach_response = fake_coach
            response = self.client.post(
                "/lua-coach",
                headers={**self.auth_headers(), "X-User-Id": "owner-1"},
                json={"session_id": session_id, "company": "TestCo", "role": "PM", "question": "q", "candidate_answer": "a"},
            )
        finally:
            os.chdir(cwd)

        self.assertEqual(response.status_code, 200)
        self.assertIn("candidate_profile", captured["lua_brief"]["modules"])
        self.assertIn("Queue routing redesign", captured["lua_brief"]["modules"]["candidate_profile"])

    def test_llm_failures_raise_instead_of_returning_text(self):
        agent_v2 = importlib.import_module("agent_v2")
        old_key = agent_v2.OPENAI_API_KEY
        agent_v2.OPENAI_API_KEY = ""
        try:
            with self.assertRaises(agent_v2.LLMError):
                agent_v2.ask_llm("hello")
        finally:
            agent_v2.OPENAI_API_KEY = old_key


if __name__ == "__main__":
    unittest.main()
