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


if __name__ == "__main__":
    unittest.main()
