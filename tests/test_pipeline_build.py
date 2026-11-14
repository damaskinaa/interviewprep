"""The v5 deck builder: plan, story assignment, briefs, gates, one card, save and the build run, with models stubbed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from nailit.answers import build

COMP = {"id": "failure", "name": "Failure", "tests": "owning a miss", "group": "behavioural", "amazon": ["Ownership"],
        "google": ["Humility"], "roles": ["sdm"]}
WHY = {"id": "why_company", "name": "Why us", "tests": "fit", "group": "opening", "per_company": True}
TMAY = {"id": "tmay", "name": "About you", "tests": "summary", "group": "opening"}
COMPS = {c["id"]: c for c in (COMP, WHY, TMAY)}
STORIES = {"M1": "I cut backlog by 40 percent in six weeks.", "M12": "I fit the role."}
GOOD = {"quality": 9.0, "rules": [{"id": "R1.1", "name": "Answer first", "verdict": "pass", "evidence": ""}]}
BAD = {"quality": 5.0, "rules": [{"id": "R1.1", "name": "Answer first", "verdict": "fail", "evidence": ""}]}


class NumbersTest(unittest.TestCase):
    def test_number_words_equal_digits_and_generic_numbers_are_ignored(self):
        self.assertEqual(build.digits("forty-two people and fifty percent"), "42 people and 50%")
        self.assertEqual(build.digits(None), "")
        self.assertEqual(build.invented("I led forty specialists.", "40 specialists"), [])
        self.assertEqual(build.invented("A 30-60-90 plan.", ""), [])
        self.assertIn("47%", build.invented("Cut errors by 47%.", "Cut errors."))


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "harvest").mkdir()
        self.patches = [mock.patch.object(build, "ML", self.tmp), mock.patch.object(build, "PLAN", self.tmp / "harvest" / "plan.json"),
                        mock.patch.object(build, "DECK", self.tmp / "deck.json"),
                        mock.patch.object(build.comp_mod, "MAP", self.tmp / "harvest" / "map.json")]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)
        self.canon = [{"question": "Tell me about a failure?", "frequency": 90}, {"question": "A mistake you made?", "frequency": 10},
                      {"question": "Why this company?", "frequency": 60}]
        (self.tmp / "harvest" / "canonical.json").write_text(json.dumps(self.canon))
        (self.tmp / "harvest" / "map.json").write_text(json.dumps({"Tell me about a failure?": "failure", "A mistake you made?": "failure",
                                                                     "Why this company?": "why_company"}))

    def test_target_angles_grow_with_mentions(self):
        self.assertEqual([build.target_angles(n) for n in (10, 40, 80, 150)], [1, 2, 3, 4])

    def test_angles_keeps_frequent_ones_and_falls_back_to_the_top_question(self):
        items = [{"question": "Q a?", "frequency": 20}, {"question": "Q b?", "frequency": 3}]
        reply = {"angles": [{"question": "Q a?", "members": [0, 1, "x", 9]}, {"question": "Q b?", "members": [1]}]}
        with mock.patch.object(build, "chat", return_value=reply):
            out = build.angles(COMP, items, 2)
        self.assertEqual(out[0]["question"], "Q a?")
        self.assertEqual(out[0]["variants"], ["Q b?"])
        with mock.patch.object(build, "chat", return_value=None):
            fallback = build.angles(COMP, items, 1)
            self.assertEqual(fallback[0]["question"], "Q a?")
            self.assertEqual(build.angles(COMP, items, 1, existing=("Q a?",)), [])
        with mock.patch.object(build, "chat", return_value={"angles": [{"question": "Q a?", "members": [0]}]}):
            self.assertEqual(build.angles(COMP, items, 1, existing=("Q z?",)), [{"question": "Q a?", "variants": [], "frequency": 20}])

    def test_the_plan_adds_angles_company_cards_manual_questions_and_stories(self):
        old = {"cards": [{"question": "Legacy question here?", "competency": "failure", "frequency": 2, "variants": ["lv"]}]}
        build.DECK.write_text(json.dumps(old))
        angle = [{"question": "Tell me about a failure?", "variants": ["A mistake you made?"], "frequency": 100}]
        extra = [{"question": "Manual one?", "variants": [], "frequency": 50, "manual": "q9", "direction": "d", "must_show": []}]
        with mock.patch.object(build.comp_mod, "load", return_value=([COMP, WHY], {})), \
                mock.patch.object(build, "angles", return_value=angle), \
                mock.patch.object(build, "manual_questions", return_value=extra), \
                mock.patch.object(build.comp_mod, "classify", return_value={"Manual one?": "failure"}), \
                mock.patch.object(build, "assign_stories", side_effect=lambda cards, comps, used: [c.update(stories=["M1"]) for c in cards]):
            cards = build.make_plan(legacy=True, manual=True)
            questions = [c["question"] for c in cards]
            self.assertIn("Why do you want to work here?", questions)
            self.assertIn("Why Amazon?", questions)
            self.assertIn("Legacy question here?", questions)
            self.assertIn("Manual one?", questions)
            self.assertTrue(all(c["stories"] == ["M1"] for c in cards))
            again = build.make_plan(only={"failure"})  # resumes from the saved plan: no new angle calls
            self.assertTrue(all(c["competency"] == "failure" for c in again))

    def test_assign_stories_keeps_only_known_ids(self):
        cards = [{"competency": "failure", "question": "Q?"}, {"competency": "failure", "question": "R?"}]
        with mock.patch.object(build, "story_bank", return_value=STORIES), \
                mock.patch.object(build, "chat", return_value={"0": ["M1", "M99"], "1": ["none"]}):
            build.assign_stories(cards, COMPS, used={"M1": 2})
        self.assertEqual([c["stories"] for c in cards], [["M1"], []])

    def test_manual_questions_skip_what_the_deck_already_has(self):
        (self.tmp / "questions.yaml").write_text("x")
        with mock.patch.object(build.library, "home", return_value=self.tmp):
            self.assertEqual(build.manual_questions([], []), [])
            (self.tmp / "library").mkdir()
            (self.tmp / "library" / "questions.yaml").write_text(
                "questions:\n - {id: q1, text: 'Have you led change?', variants: ['Led change?'], best_direction: d, tests_for: [x]}\n"
                " - {id: q2, text: 'Closing one?', type: closing}\n - {id: q3, text: 'Known one?'}\n")
            out = build.manual_questions([{"question": "Known one?"}], [])
        self.assertEqual([q["manual"] for q in out], ["q1"])
        self.assertEqual(out[0]["must_show"], ["x"])


class BriefAndGatesTest(unittest.TestCase):
    def patched(self, chosen=("R1.4",)):
        return mock.patch.object(build, "rules_text", return_value=(list(chosen), "- rule one"))

    def test_the_brief_carries_the_question_rules_story_and_special_cases(self):
        card = {"question": "What are your salary expectations?", "competency": "failure", "_samples": [{"answer": "S" * 50, "verdict": "great"}],
                "direction": "Be brief", "must_show": ["range"]}
        with self.patched(("R1.4",)):
            text = build.brief(card, COMP, "the story", 0)
        for piece in ("salary", "rule one", "the story", "Be brief", "great", "150 to 200 words", "Dublin"):
            self.assertIn(piece, text)

    def test_company_and_opening_briefs_differ(self):
        with self.patched(("R2.1",)):
            company = build.brief({"question": "Why Amazon?", "competency": "why_company", "company": "amazon"}, WHY, None, 1)
            shell = build.brief({"question": "Why us?", "competency": "why_company"}, WHY, None, 1)
            tmay = build.brief({"question": "Tell me about yourself", "competency": "tmay"}, TMAY, None, 2)
            plain = build.brief({"question": "Describe your approach", "competency": "failure"}, COMP, None, 3)
        self.assertIn("Amazon", company)
        self.assertIn("reusable shell", shell)
        self.assertIn("60 to 80 seconds", tmay)
        self.assertIn("90 to 140 words", plain)

    def test_rules_text_lists_the_chosen_rules(self):
        with mock.patch.object(build.scoring, "rule_set", return_value=["R1.1"]), mock.patch.object(build.scoring, "rules", return_value={"R1.1": "Answer first"}):
            chosen, text = build.rules_text({"competency": "failure"})
        self.assertEqual((chosen, text), (["R1.1"], "- Answer first"))

    def test_judge_means_two_judges_and_survives_one_failing(self):
        card = {"question": "Q?", "competency": "failure"}
        with mock.patch.object(build, "_score", side_effect=[GOOD, BAD]):
            quality, failed = build.judge(card, "text")
        self.assertEqual((quality, failed), (7.0, ["Answer first (fail)"]))
        with mock.patch.object(build, "_score", side_effect=[RuntimeError("down"), GOOD]):
            self.assertEqual(build.judge(card, "text")[0], 9.0)
        with mock.patch.object(build, "_score", side_effect=RuntimeError("down")):
            self.assertEqual(build.judge(card, "text"), (0.0, []))

    def test_score_wrapper_calls_the_scorer_with_the_card(self):
        with mock.patch.object(build.scoring, "score", return_value=GOOD) as score:
            self.assertEqual(build._score({"question": "Q?"}, "answer", "judge", 5), GOOD)
        self.assertEqual(score.call_args.kwargs["judge"], "judge")

    def test_gate_numbers_repairs_once_and_reports_what_is_left(self):
        card = {"question": "Tell me about a failure.", "competency": "failure"}
        text, left = build.gate_numbers(card, "I cut it in six weeks.", "I cut it in six weeks.")
        self.assertEqual(left, [])
        with mock.patch.object(build, "chat", return_value="I cut it by 77%."):
            fixed, left = build.gate_numbers(card, "I cut it by 55%.", "I cut it.")
        self.assertEqual((fixed, left), ("I cut it by 77%.", ["77%"]))
        with mock.patch.object(build, "chat", return_value=None):
            self.assertEqual(build.gate_numbers(card, "Cut by 55%.", "")[0], "Cut by 55%.")


class OneCardTest(unittest.TestCase):
    def build(self, scores, writer=None, drafts=("I fixed it. " * 30,), card=None):
        card = card or {"question": "Tell me about a failure.", "competency": "failure", "stories": ["M1"], "frequency": 4,
                        "_samples": [{"source": "web", "answer": "A" * 50}]}
        replies = iter(drafts + drafts)

        def fake_chat(model, prompt, json_mode=False, retries=3, role="drafter"):
            if role == "writer":
                return writer if writer is not None else {"answer": "Final spoken answer. " * 10, "followups": [{"q": "a", "a": "b"}] * 5}
            return next(replies, drafts[0])
        with mock.patch.object(build, "chat", side_effect=fake_chat), mock.patch.object(build, "rules_text", return_value=(["R1.4"], "- r")), \
                mock.patch.object(build, "judge", return_value=(8.0, ["Answer first (fail)"])), \
                mock.patch.object(build, "_score", side_effect=scores), mock.patch.object(build.scoring, "rule_set", return_value=["R1.4"]), \
                mock.patch.object(build, "key_moves", return_value=(["move"], "hook")):
            return build.build_card(card, COMPS, STORIES, 0)

    def test_a_card_has_the_fields_the_deck_needs(self):
        built = self.build([GOOD])
        self.assertEqual((built["competency"], built["generation"], built["origin"], built["quality"]), ("failure", 2, "generated", 9.0))
        self.assertEqual(len(built["followups"]), 3)
        self.assertEqual(built["evidence"][0]["source"], "web")
        self.assertEqual(built["id"], "tell_me_about_a_failure")

    def test_when_the_polish_scores_worse_than_the_draft_the_draft_wins(self):
        built = self.build([BAD, GOOD], drafts=("I fixed it. " * 30, "Other draft. " * 30))
        self.assertEqual(built["quality"], 9.0)
        self.assertTrue(built["answer"].startswith(("I fixed", "Other")))

    def test_structure_tells_are_rewritten_and_a_failed_polish_keeps_the_draft(self):
        built = self.build([GOOD], writer={"answer": "The trade-off was speed. Since then I check it."})
        self.assertNotIn("Since then", built["answer"])
        built = self.build([GOOD], writer={})
        self.assertTrue(built["answer"].startswith("I fixed"))

    def test_company_and_manual_cards_are_marked(self):
        built = self.build([GOOD], card={"question": "Why Amazon?", "competency": "why_company", "company": "amazon", "manual": "q4"})
        self.assertEqual((built["origin"], built["manual"]), ("manual", "q4"))
        self.assertIn("30 days", built["refresh_note"])
        self.assertEqual(built["story"], "M12")  # the fit story is the proof in every why-us answer

    def test_no_drafts_means_no_card(self):
        with mock.patch.object(build, "chat", return_value=None), mock.patch.object(build, "rules_text", return_value=(["R1.4"], "")):
            self.assertIsNone(build.build_card({"question": "Q?", "competency": "failure"}, COMPS, STORIES, 0))


class SaveAndMainTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        for target in ("DECK", "PLAN", "ML"):
            pass
        self.patches = [mock.patch.object(build, "DECK", self.tmp / "deck.json"), mock.patch.object(build, "ML", self.tmp),
                        mock.patch("nailit.config.load_secrets")]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_save_replaces_the_same_question_and_keeps_the_old_answer(self):
        deck = {"cards": [{"question": "Tell me about yourself.", "answer": "old", "company": None}, {"question": "Other?", "answer": "x"}]}
        build.save(deck, {"question": "Tell me about yourself", "answer": "new", "company": None})
        self.assertEqual([c["answer"] for c in deck["cards"]], ["x", "new"])
        self.assertEqual(deck["retired"][0]["answer"], "old")
        self.assertEqual(json.loads(build.DECK.read_text())["cards"][-1]["answer"], "new")

    def run_main(self, args, plan, deck=None, built=None):
        if deck is not None:
            build.DECK.write_text(json.dumps(deck))
        out = []
        with mock.patch.object(build, "make_plan", return_value=plan), mock.patch.object(build.comp_mod, "load", return_value=([COMP], {})), \
                mock.patch.object(build, "story_bank", return_value=STORIES), mock.patch.object(build, "attach_samples"), \
                mock.patch.object(build, "build_card", side_effect=built or [RuntimeError("model down")]), \
                mock.patch("builtins.print", side_effect=lambda *a, **k: out.append(" ".join(map(str, a)))), \
                mock.patch("sys.argv", ["build"] + args):
            build.main()
        return out

    def test_the_plan_flag_prints_without_building(self):
        out = self.run_main(["--plan"], [{"competency": "failure", "frequency": 3, "stories": ["M1"], "question": "Q?", "variants": []}])
        self.assertIn("1 cards planned", out[-1])

    def test_a_build_saves_good_cards_reports_failures_and_retires_replaced_ones(self):
        plan = [{"competency": "failure", "frequency": 3, "question": "Q one?", "variants": ["Old wording?"]},
                {"competency": "failure", "frequency": 2, "question": "Q two?", "variants": []}]
        card = {"question": "Q one?", "competency": "failure", "quality": 9.0, "gate_numbers": ["5"], "generation": 2,
                "variants": ["Old wording?"], "frequency": 3, "answer": "a"}
        deck = {"cards": [{"question": "Old wording?", "competency": "failure", "answer": "old"}]}
        out = self.run_main([], plan, deck, built=[card, RuntimeError("down")])
        text = "\n".join(out)
        self.assertIn("numbers not in story", text)
        self.assertIn("✗", text)
        saved = json.loads(build.DECK.read_text())
        self.assertEqual([c["question"] for c in saved["cards"]], ["Q one?"])
        self.assertEqual(saved["retired"][0]["question"], "Old wording?")
        again = self.run_main([], plan[:1], saved, built=[card])  # already built: nothing to do
        self.assertIn("0 cards to build", again[0])


if __name__ == "__main__":
    unittest.main()
