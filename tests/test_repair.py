import unittest
from unittest import mock

from nailit.answers import ai, repair

CARD = {"id": "c1", "question": "Tell me about a failure.", "answer": "old answer " * 40, "generation": 2, "quality": 5.5,
        "competency": "failure", "story": "M1", "rules": [{"id": "R1.1", "name": "Answer first", "verdict": "fail", "evidence": ""}]}
NEW = "I missed the launch date by two weeks because I trusted an estimate I had not checked. " * 6


class RepairTest(unittest.TestCase):
    def run_rewrite(self, scores, leftover=()):
        with mock.patch.object(repair, "judge", side_effect=[(s, []) for s in scores]), \
                mock.patch.object(ai, "chat", return_value={"answer": NEW}) as writer, \
                mock.patch.object(repair, "gate_numbers", side_effect=lambda card, text, story: (text, list(leftover))):
            return repair.rewrite(dict(CARD), {"M1": "the story"}), writer

    def test_a_rewrite_is_kept_only_when_independent_judges_score_it_clearly_higher(self):
        better, writer = self.run_rewrite([5.0, 9.0])
        self.assertTrue(repair.accept(better))
        self.assertEqual(writer.call_args.args[0], "claude-fable-5-2")
        self.assertIn("the story", writer.call_args.args[1])
        self.assertFalse(repair.accept(self.run_rewrite([8.0, 8.2])[0]))  # inside the noise margin
        self.assertFalse(repair.accept(self.run_rewrite([5.0, 9.0], leftover=["37%"])[0]))  # a number not in the story
        self.assertFalse(repair.accept(None))
        fine, writer = self.run_rewrite([9.0])  # two judges already pass the stored answer: no rewrite, no Fable call
        self.assertEqual((fine, writer.called), ({"before": 9.0, "remarked": True}, False))

    def test_the_replaced_answer_is_kept_in_the_deck_file(self):
        deck, card = {"cards": [dict(CARD)]}, None
        card = deck["cards"][0]
        with mock.patch.object(repair.scoring, "score", return_value={"quality": 9.1, "rules": []}), \
                mock.patch.object(repair, "key_moves", return_value=(["Opens with the miss"], "hook")):
            repair.apply(deck, card, {"before": 5.0, "after": 9.0, "answer": NEW, "leftover": []})
        self.assertEqual((card["answer"], card["quality"], card["writer"]), (NEW, 9.1, "claude-fable-5-2"))
        self.assertEqual(deck["retired"][0]["answer"], CARD["answer"])

    def test_only_rebuilt_cards_under_the_threshold_are_picked_weakest_first(self):
        deck = {"cards": [{"generation": 2, "quality": 7.7, "question": "a"}, {"generation": 2, "quality": 3.4, "question": "b"},
                          {"generation": 2, "quality": 9.5, "question": "c"}, {"quality": 2, "question": "old"}]}
        self.assertEqual([c["question"] for c in repair.weak_cards(deck, 8)], ["b", "a"])

    def test_fable_is_registered_for_the_claude_plan_route(self):
        self.assertEqual(ai.CLI_MODELS["claude-fable-5-2"], "claude-fable-5-2")  # the alias resolved to 5.1

    def test_a_different_model_answering_for_fable_is_an_error_not_a_silent_swap(self):
        import json as _json
        import subprocess
        def fake(served):
            out = _json.dumps({"result": "ok", "is_error": False, "modelUsage": {served: {}}, "usage": {}})
            return mock.patch.object(subprocess, "run", return_value=mock.Mock(stdout=out, stderr=""))
        with fake("claude-fable-5-2"):
            self.assertEqual(ai._cli("claude-fable-5-2", "hi", "low"), "ok")
        with fake("claude-fable-5-1"), self.assertRaises(ai.CLIError):
            ai._cli("claude-fable-5-2", "hi", "low")


if __name__ == "__main__":
    unittest.main()


class ManualQuestionsTest(unittest.TestCase):
    def test_manual_questions_without_a_card_are_planned_with_the_manuals_direction(self):
        import tempfile
        from pathlib import Path

        import yaml

        from nailit.answers import build
        tmp = Path(tempfile.mkdtemp())
        (tmp / "library").mkdir()
        (tmp / "library" / "questions.yaml").write_text(yaml.safe_dump([
            {"id": "q_have", "text": "Tell me about yourself.", "type": "opening"},
            {"id": "q_variant", "text": "Describe a failure.", "variants": ["Tell me about a time you failed"], "type": "failure"},
            {"id": "q_new", "text": "What would you not work on?", "type": "situational", "best_direction": "Name the cut and why.",
             "tests_for": ["says no with a reason"]},
            {"id": "q_close", "text": "Any questions for us?", "type": "closing"}]))
        deck = [{"question": "Tell me about yourself", "variants": []}, {"question": "X", "variants": ["Tell me about a time you failed."]}]
        with mock.patch("nailit.library.home", return_value=tmp):
            found = build.manual_questions(deck, planned=[])
            self.assertEqual([q["manual"] for q in found], ["q_new"])
            self.assertEqual(build.manual_questions(deck, planned=["What would you NOT work on"]), [])
        self.assertEqual((found[0]["direction"], found[0]["must_show"]), ("Name the cut and why.", ["says no with a reason"]))
