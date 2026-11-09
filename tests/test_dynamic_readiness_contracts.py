import importlib
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]


class LocalAppContractsTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)
        self._old_env = os.environ.copy()
        os.environ["OPENAI_API_KEY"] = "test-disabled-openai"
        os.environ["DATA_DIR"] = str(self.tmp_path)
        for name in ["nailit.api", "nailit.store"]:
            sys.modules.pop(name, None)
        job_store = importlib.import_module("nailit.store")
        job_store.DB_PATH = self.tmp_path / "nailit_jobs.db"
        self.job_store = job_store
        self.api = importlib.import_module("nailit.api")
        self.client = TestClient(self.api.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        os.environ.clear()
        os.environ.update(self._old_env)
        self.tmpdir.cleanup()

    def _create_session(self):
        response = self.client.post("/session/create", json={
            "company_name": "ExampleCo",
            "role_name": "Program Manager",
            "job_description": "Own a program and coordinate stakeholders.",
            "cv": "Synthetic candidate with program delivery experience.",
        })
        self.assertEqual(response.status_code, 200)
        return response.json()["session_id"]

    def test_session_create_and_get(self):
        session_id = self._create_session()
        response = self.client.get(f"/session/get?session_id={session_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["company_name"], "ExampleCo")
        self.assertEqual(self.client.get("/session/get?session_id=missing").status_code, 404)

    def test_module_run_checks_prerequisites(self):
        session_id = self._create_session()
        response = self.client.post("/module/run", json={"session_id": session_id, "module_name": "gap_map"})
        self.assertEqual(response.status_code, 400)

    def test_module_status_hides_input_payload(self):
        session_id = self._create_session()
        job_id, _ = self.job_store.get_or_create_job(session_id, "role_intelligence", "mod_test_1")
        response = self.client.get(f"/module/status?job_id={job_id}")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("input_payload", response.json())

    def test_stale_jobs_are_failed(self):
        job_id, _ = self.job_store.get_or_create_job("sess_x", "gap_map", "mod_stale_1")
        with sqlite3.connect(self.tmp_path / "nailit_jobs.db") as con:
            con.execute(
                "UPDATE jobs SET status = 'running', updated_at = ? WHERE job_id = ?",
                ((datetime.now() - timedelta(hours=2)).isoformat(), job_id),
            )
            con.commit()
        self.assertEqual(self.job_store.fail_stale_jobs(minutes=30), 1)
        self.assertEqual(self.job_store.get_job(job_id)["status"], "failed")

    def test_lua_coach_requires_session_and_uses_session_artifacts(self):
        self.assertEqual(self.client.post("/lua-coach", json={"question": "q"}).status_code, 400)
        session_id = self._create_session()
        cwd = os.getcwd()
        os.chdir(self.tmp_path)
        try:
            artifact = self.tmp_path / "jobs" / session_id / "candidate_profile"
            artifact.mkdir(parents=True)
            (artifact / "candidate_profile.json").write_text('{"story_inventory": ["Synthetic routing redesign"]}')
            captured = {}

            def fake_coach(**kwargs):
                captured.update(kwargs)
                return {"score_out_of_10": 7, "what_worked": "ok", "what_was_weak": "", "top_1_percent_answers": {}}

            self.api.build_lua_coach_response = fake_coach
            response = self.client.post("/lua-coach", json={"session_id": session_id, "question": "q", "candidate_answer": "a"})
        finally:
            os.chdir(cwd)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "coaching")
        self.assertIn("Synthetic routing redesign", captured["lua_brief"]["modules"]["candidate_profile"])

    def test_llm_failures_raise_instead_of_returning_text(self):
        llm = importlib.import_module("nailit.llm")
        os.environ.pop("OPENAI_API_KEY", None)
        with self.assertRaises(llm.LLMError):
            llm.ask_llm("hello")

    def test_unparseable_model_output_never_becomes_an_artifact(self):
        llm = importlib.import_module("nailit.llm")
        self.assertEqual(llm.parse_json_object('{"questions_by_round": [', fallback={}), {})
        self.assertEqual(llm.parse_json_object('{"a": 1}'), {"a": 1})

    def test_round_research_threads_keep_job_context(self):
        common = importlib.import_module("nailit.prep.common")
        agent_v2 = importlib.import_module("nailit.prep.research")
        token_r = common._current_results.set({})
        token_p = common._current_progress_log.set([])
        old = agent_v2.collect_per_round_research

        def fake_round(company, role, round_name, round_type, what_it_tests):
            common.log(5, f"researching {round_name}")
            return {"round_name": round_name, "sources": [{"url": "x"}], "reported_questions": []}

        agent_v2.collect_per_round_research = fake_round
        try:
            results = agent_v2.run_all_rounds_research(
                "ExampleCo", "PM", [{"round_name": "R1", "round_type": "t", "what_it_tests": "w"}]
            )
        finally:
            agent_v2.collect_per_round_research = old
            common._current_progress_log.reset(token_p)
            common._current_results.reset(token_r)
        self.assertEqual(results[0]["sources"], [{"url": "x"}])


class LocalOnlyRulesTest(unittest.TestCase):
    def test_cli_binds_localhost_only(self):
        cli = importlib.import_module("nailit.cli")
        self.assertEqual(cli.HOST, "127.0.0.1")

    def test_no_rule_permits_inventing_facts(self):
        offenders = []
        for path in REPO_ROOT.rglob("*.py"):
            if "node_modules" in path.parts or path.name.startswith("test_"):
                continue
            text = path.read_text(encoding="utf-8").lower()
            for phrase in ("may invent", "invent realistic", "can invent"):
                if phrase in text:
                    offenders.append(f"{path.name}: {phrase}")
        self.assertEqual(offenders, [])

    def test_keychain_is_used_before_env_fallback(self):
        config = importlib.import_module("nailit.config")
        old = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "from-env"
        original = config.keychain_secret
        config.keychain_secret = lambda name: "from-keychain" if name == "OPENAI_API_KEY" else ""
        try:
            config.load_secrets(Path("/nonexistent/.env"))
            self.assertEqual(os.environ["OPENAI_API_KEY"], "from-keychain")
        finally:
            config.keychain_secret = original
            if old is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()
