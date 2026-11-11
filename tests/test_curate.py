import unittest

from nailit.answers import curate, generate


class CurateTest(unittest.TestCase):
    def test_merge_folds_duplicate_into_variant(self):
        deck = {"cards": [{"question": "Tell me about a time you failed.", "answer": "A", "frequency": 5},
                          {"question": "What is your biggest mistake?", "answer": "B", "frequency": 2},
                          {"question": "Design a URL shortening system", "answer": "C", "frequency": 4},
                          {"question": "Tight Deadlines", "answer": "D", "frequency": 3}]}
        dropped, merged = curate.apply(deck, {"drop": [], "merge": {"What is your biggest mistake?": "Tell me about a time you failed."}})
        self.assertEqual(merged, 1)
        self.assertEqual(set(dropped), {"Design a URL shortening system", "Tight Deadlines"})
        card = deck["cards"][0]
        self.assertEqual((card["frequency"], card["variants"], card["merged"][0]["answer"]), (7, ["What is your biggest mistake?"], "B"))

    def test_star_tell_is_capitals_only(self):
        self.assertIsNone(generate.TELLS.search("Since then, I start every QBR with risks."))
        self.assertTrue(generate.TELLS.search("Using the STAR method, the situation was bad."))

    def test_pay_history_gets_its_own_rule(self):
        self.assertIn("CURRENT or PAST pay", generate.direct_rule("What are you earning now?"))
        self.assertIn("Dublin", generate.direct_rule("What are your salary expectations?"))


if __name__ == "__main__":
    unittest.main()
