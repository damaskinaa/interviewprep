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
        prices = self.llm.SETTINGS["prices"][self.llm.MODEL_FAST]
        self.assertAlmostEqual(records[0]["cost_usd"], prices[0] + prices[1] / 2, places=4)

    def test_provider_failure_raises(self):
        self.llm._client = self._fake_client(fail=True)
        with self.assertRaises(self.llm.LLMError):
            self.llm.ask_llm("q", retries=1)


if __name__ == "__main__":
    unittest.main()
