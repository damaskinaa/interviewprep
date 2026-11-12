import importlib
import os
import types
import unittest


class GuardsTest(unittest.TestCase):
    def setUp(self):
        self.guards = importlib.import_module("nailit.guards")

    def test_invented_numbers_are_flagged(self):
        facts = "Cut onboarding time from 14 days to 9 days for a team of 6."
        answer = "I led 6 people, cut onboarding from 14 to 9 days, saved 40% of cost and $250k across 3 regions."
        self.assertEqual(self.guards.invented_numbers(answer, facts), ["40%", "$250k", "3"])

    def test_formatting_variants_match(self):
        self.assertEqual(self.guards.invented_numbers("We served 1,200 users", "1200 users"), [])
        self.assertEqual(self.guards.invented_numbers("No numbers here.", ""), [])

    def test_magnitude_and_unit_must_match(self):
        self.assertEqual(self.guards.invented_numbers("Saved $250k", "Saved 250 hours"), ["$250k"])
        self.assertEqual(self.guards.invented_numbers("Cut churn 40%", "Took 40 days"), ["40%"])
        self.assertEqual(self.guards.invented_numbers("Saved 250k and 40 percent", "Saved $250,000, a 40% drop"), [])
        self.assertEqual(self.guards.invented_numbers("A team of 40", "a 40% drop"), [])
        self.assertEqual(self.guards.invented_numbers("Reached 1m users", "Reached 1 million users"), [])
        cleaned, stripped = self.guards.strip_hallucinated_metrics("We reached 1m users.", "Reached 1 million users", "")
        self.assertEqual((cleaned, stripped), ("We reached 1m users.", []))
        self.assertEqual(self.guards.invented_numbers("Grew 1 thousand percent", "1k users"), ["1 thousand percent"])
        _, stripped = self.guards.strip_hallucinated_metrics("Grew 1 thousand percent.", "1k users", "")
        self.assertEqual(stripped, ["1 thousand percent"])

    def test_strip_keeps_comma_formatted_verified_metric(self):
        cleaned, stripped = self.guards.strip_hallucinated_metrics("We onboarded 1,200 users.", "Onboarded 1200 users", "")
        self.assertEqual((cleaned, stripped), ("We onboarded 1,200 users.", []))

    def test_strip_keeps_metrics_written_with_separators_in_source(self):
        cleaned, stripped = self.guards.strip_hallucinated_metrics("We onboarded 1200 users in 30 days.", "Onboarded 1,200 users", "")
        self.assertIn("1200 users", cleaned)
        self.assertEqual(stripped, ["30 days"])


class ResearchRetryTest(unittest.TestCase):
    def test_http_errors_never_crash_tavily_retry(self):
        import urllib.error

        research = importlib.import_module("nailit.prep.research")

        def rate_limited(*args, **kwargs):
            raise urllib.error.HTTPError("https://api.tavily.com", 500, "boom", {}, None)

        old_urlopen, old_key = research.urllib.request.urlopen, research.TAVILY_API_KEY
        research.urllib.request.urlopen, research.TAVILY_API_KEY = rate_limited, "test-key"
        try:
            self.assertEqual(research.tavily_with_retry("synthetic query"), [])
        finally:
            research.urllib.request.urlopen, research.TAVILY_API_KEY = old_urlopen, old_key


class LLMClientTest(unittest.TestCase):
    def setUp(self):
        self.llm = importlib.import_module("nailit.llm")
        self._old_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"

    def tearDown(self):
        self.llm._client = None
        if self._old_key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self._old_key

    def _fake_client(self, content="ok", fail=False):
        def create(**kwargs):
            if fail:
                raise RuntimeError("provider down")
            usage = types.SimpleNamespace(prompt_tokens=1_000_000, completion_tokens=500_000)
            message = types.SimpleNamespace(content=content)
            return types.SimpleNamespace(usage=usage, choices=[types.SimpleNamespace(message=message)])

        completions = types.SimpleNamespace(create=create)
        return types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))

    def test_cost_is_logged_per_call(self):
        self.llm._client = self._fake_client('{"a": 1}')
        records = self.llm.start_cost_log()
        self.assertEqual(self.llm.ask_json("q", model=self.llm.MODEL_FAST), {"a": 1})
        self.assertEqual(len(records), 1)
        prices = self.llm.SETTINGS["prices"]["fast"]
        self.assertAlmostEqual(records[0]["cost_usd"], prices[0] + prices[1] / 2, places=4)

    def test_cost_total_is_logged(self):
        self.llm._client = self._fake_client("ok")
        records = self.llm.start_cost_log()
        self.llm.ask_llm("q")
        with self.assertLogs("nailit.llm", level="INFO") as logs:
            self.llm.log_cost_total(records, "sess/module")
        self.assertIn("sess/module: 1 calls", logs.output[0])

    def test_provider_failure_raises(self):
        self.llm._client = self._fake_client(fail=True)
        with self.assertRaises(self.llm.LLMError):
            self.llm.ask_llm("q", retries=1)


class ProviderOrderTest(unittest.TestCase):
    def test_env_then_settings_then_tensorx_then_openai(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest import mock

        from nailit import llm
        home = Path(tempfile.mkdtemp())
        env = {"NAILIT_PROVIDER": "", "TENSORX_API_KEY": ""}
        with mock.patch("nailit.library.home", return_value=home), mock.patch.dict(os.environ, env):
            self.assertEqual(llm.provider(), "openai")
            os.environ["TENSORX_API_KEY"] = "test-key"
            self.assertEqual(llm.provider(), "tensorx")
            (home / "settings.json").write_text("{not json")
            self.assertEqual(llm.provider(), "tensorx")  # a broken settings file falls through
            (home / "settings.json").write_text(json.dumps({"engine": "nonsense"}))
            self.assertEqual(llm.provider(), "tensorx")  # unknown engine falls through
            (home / "settings.json").write_text(json.dumps({"engine": "lua"}))
            self.assertEqual(llm.provider(), "lua")
            os.environ["NAILIT_PROVIDER"] = "CLAUDE"
            self.assertEqual(llm.provider(), "claude")  # the env var wins, any case
            os.environ["NAILIT_PROVIDER"] = "bogus"
            self.assertEqual(llm.provider(), "lua")


if __name__ == "__main__":
    unittest.main()
