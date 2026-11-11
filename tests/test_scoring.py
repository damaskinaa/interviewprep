import unittest
from unittest import mock

from nailit import scoring

CARD = {"question": "Tell me about a time you improved a process.", "answer": "I cut the backlog by a third in six weeks.",
        "moves": ["Opens with the result", "Names the trade-off"], "type": "behavioural"}
ALL_PASS = {rid: {"verdict": "pass", "evidence": "quote"} for rid in scoring.STORY_RULES}


class ScoringTest(unittest.TestCase):
    def run_score(self, text, reply):
        with mock.patch("nailit.answers.ai.chat", return_value=reply), mock.patch.object(scoring, "competency", return_value=None):
            return scoring.score(CARD, text)

    def test_code_checks_override_a_generous_model(self):
        text = ("We decided to change the queue and we chose a new routing rule, and the team worked hard on it for a while "
                "and things got better and everyone was happier with how it went in the end, basically. " * 2)
        result = self.run_score(text, {"on_topic": True, "rules": ALL_PASS, "moves_hit": CARD["moves"]})
        verdicts = {r["id"]: r["verdict"] for r in result["rules"]}
        self.assertEqual((verdicts["R1.3"], verdicts["R1.5"]), ("fail", "fail"))
        self.assertLess(result["quality"], 7.5)

    def test_off_topic_and_fragments_are_capped(self):
        long_text = "I cut the backlog by a third in six weeks by changing triage. " * 8
        self.assertLessEqual(self.run_score(long_text, {"on_topic": False, "rules": ALL_PASS, "moves_hit": CARD["moves"]})["score"], 2)
        self.assertLessEqual(self.run_score("I usually handle that well.", {"on_topic": True, "rules": ALL_PASS})["score"], 2)

    def test_pass_without_a_quote_is_only_partial(self):
        reply = {"on_topic": True, "rules": {rid: {"verdict": "pass", "evidence": ""} for rid in scoring.STORY_RULES}}
        result = self.run_score("I cut the backlog by 30% in six weeks. " * 10, reply)
        self.assertTrue(all(r["verdict"] == "partial" for r in result["rules"]))


if __name__ == "__main__":
    unittest.main()
