"""The deck-building pipeline with the model calls stubbed: card logic, tournament, competencies, audit, calibration."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from nailit.answers import ai, audit, calibrate, competencies, generate

STORIES = {"M1": "I cut backlog by a third in six weeks.", "M2": "I rebuilt the escalation path."}
ANSWER = "I cut the backlog by a third in six weeks by changing the queue rules. " * 4


def fake_embed(texts):
    """Same text, same vector; different first letters point in different directions."""
    out = []
    for text in texts:
        v = np.zeros(8)
        v[(ord((text.strip() or "a")[0].lower()) % 8)] = 1.0
        v[7] += 0.01 * len(text) % 1
        out.append(v)
    return out


class DirectRuleTest(unittest.TestCase):
    def test_pay_questions_get_the_right_rule(self):
        self.assertIn("Do not state a figure", generate.direct_rule("What are you earning now?"))
        self.assertIn("Dublin", generate.direct_rule("What are your salary expectations?"))
        self.assertIn("tools", generate.direct_rule("Which software have you used?").lower())
        self.assertIn("directly", generate.direct_rule("What is your notice period?"))
        self.assertIsNone(generate.direct_rule("Tell me about a time you failed."))


class StoryFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "02_model_stories_SDM_SOM.md").write_text("# Stories\n## M1 · Backlog\nText one\n## How to use\nignored\n## M2 · Escalation\nText two")
        (self.tmp / "06_model_TPM.md").write_text('# T\n## T1 · "Tell me about a launch" → competency\n> I shipped it.\n> Twice.\n## T2 · No quote\nnothing')
        (self.tmp / "07_model_HeadOfOps.md").write_text("# H\n## H1 · Why this role?\n> Because ▼ I scale ‖ teams.\n")
        patcher = mock.patch.object(generate, "ML", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_stories_and_role_answers_are_read_from_the_model_files(self):
        stories = generate.story_bank()
        self.assertEqual(sorted(stories), ["M1", "M2"])
        self.assertNotIn("ignored", stories["M1"])
        found = generate.role_answers()
        self.assertEqual(found["Tell me about a launch"], "I shipped it.\nTwice.")
        self.assertEqual(found["Why this role?"], "Because  I scale  teams.")
        self.assertNotIn("No quote", found)

    def test_missing_files_give_empty_results(self):
        with mock.patch.object(generate, "ML", self.tmp / "nowhere"):
            self.assertEqual((generate.story_bank(), generate.role_answers()), ({}, {}))

    def test_questions_come_from_the_harvest_or_the_library(self):
        (self.tmp / "harvest").mkdir()
        (self.tmp / "harvest" / "canonical.json").write_text(json.dumps([{"question": "a?"}, {"question": "b?"}]))
        self.assertEqual(generate.questions("harvest", 1), [{"question": "a?"}])
        lib = {"questions": object()}
        qs = [{"text": "Why us?", "variants": ["v"], "type": "motivation", "hard": False, "rounds": ["r1"], "id": "q1"}]
        with mock.patch.object(generate.library, "load_library", return_value=lib), \
                mock.patch.object(generate.library, "_questions", return_value=(qs, [])):
            out = generate.questions("library", 5)
        self.assertEqual((out[0]["question"], out[0]["id"], out[0]["roles"]), ("Why us?", "q1", ["r1"]))


class CardTest(unittest.TestCase):
    def chat(self, replies):
        """A model stub that answers by role so tests do not depend on call order."""
        def fake(model, prompt, json_mode=False, retries=3, role="drafter"):
            reply = replies[role]
            return reply(prompt) if callable(reply) else reply
        return mock.patch.object(generate, "chat", side_effect=fake)

    def test_a_story_question_builds_a_card_through_the_tournament(self):
        item = {"question": "Tell me about a time you cut a backlog.", "frequency": 3, "variants": ["v1"], "roles": ["sdm"]}
        replies = {"helper": lambda p: {"winner": 1} if False else ({"moves": ["Opens with result"], "hook": "I cut it."} if "List the 4-6" in p
                                                                   else {"best": "M1", "second": "M2", "type": "behavioral"}),
                   "drafter": ANSWER, "judge": {"winner": 1, "why": "clearer"},
                   "writer": {"answer": ANSWER + "Since then I check queues weekly.", "followups": [{"q": "q", "a": "a"}] * 4}}
        with self.chat(replies):
            card = generate.build_card(item, STORIES, {"tell me about a time you cut a backlog.": "An existing answer."})
        self.assertEqual((card["type"], card["story"], card["frequency"]), ("behavioural", "M1", 3))
        self.assertEqual(len(card["followups"]), 3)
        self.assertEqual(card["moves"], ["Opens with result"])
        self.assertTrue(card["polished_by"] and card["practice_only"])
        self.assertEqual(card["candidates"], 3)  # two generated + one existing
        self.assertTrue(card["runner_up"])

    def test_a_direct_question_uses_the_rule_and_no_story(self):
        item = {"question": "What are your salary expectations?"}
        prompts = []
        replies = {"helper": lambda p: {"best": "M1", "second": "M2", "type": "negotiation"},
                   "drafter": lambda p: prompts.append(p) or ANSWER, "judge": {"winner": 2, "why": "x"},
                   "writer": {"answer": "", "followups": []}}
        with self.chat(replies):
            card = generate.build_card(item, STORIES, {})
        self.assertIsNone(card["story"])
        self.assertIn("Dublin", prompts[0])
        self.assertIsNone(card["polished_by"])  # the polish returned nothing: the winner is kept as is

    def test_an_answer_that_names_its_structure_is_rewritten_and_nothing_is_built_without_text(self):
        item = {"question": "Tell me about a time you led change in your team.", "_samples": [{"answer": "S" * 300, "source": "web", "verdict": "great"}]}
        calls = []

        def drafter(prompt):
            calls.append(prompt)
            return "The trade-off was speed versus quality." if "Rewrite" not in prompt else "I chose speed over polish."
        replies = {"helper": {"best": "M1", "second": "none", "type": "behavioural"}, "drafter": drafter,
                   "judge": {"winner": 1, "why": ""}, "writer": {}}
        with self.chat(replies):
            qtype, cands = generate.write_candidates(item, STORIES, {})
        self.assertEqual(qtype, "behavioural")
        self.assertEqual([c["slot"] for c in cands], ["A", "B", "R"])
        self.assertTrue(cands[0]["text"].startswith("I chose speed"))
        self.assertTrue(cands[2]["origin"].startswith("harvested:"))
        with self.chat({"helper": {}, "drafter": None, "judge": {}, "writer": {}}):
            self.assertIsNone(generate.build_card({"question": "Why us?"}, STORIES, {}))

    def test_the_tournament_ranks_by_wins_and_ignores_judges_that_return_nothing(self):
        cands = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
        with mock.patch.object(generate, "judge_pair", side_effect=lambda q, a, b, j: (1, "first") if a == "b" or b == "b" and a != "b" else (None, "")):
            ranked = generate.tournament("q?", cands)
        self.assertEqual(len(ranked), 3)
        self.assertTrue(all("win_rate" in r for r in ranked))
        with self.chat({"judge": {"winner": 2, "why": "w"}}):
            self.assertEqual(generate.judge_pair("q", "a", "b", "judge"), (2, "w"))
        with self.chat({"judge": None, "helper": None}):
            self.assertEqual(generate.judge_pair("q", "a", "b", "judge"), (None, ""))
            self.assertEqual(generate.key_moves("q", "First sentence. Second."), ([], "First sentence"))


class MergeAndSamplesTest(unittest.TestCase):
    def test_merge_similar_drops_wordings_already_in_the_deck(self):
        items = [{"question": "apple?"}, {"question": "apple pie?"}, {"question": "zebra?"}]
        with mock.patch("nailit.answers.harvest.embed", side_effect=fake_embed):
            kept = generate.merge_similar(items, ["avocado?"], threshold=0.99)
        self.assertEqual([i["question"] for i in kept], ["zebra?"])
        self.assertEqual(generate.merge_similar([], ["x"]), [])

    def test_attach_samples_adds_the_best_matching_real_answer(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "harvest").mkdir()
        (tmp / "harvest" / "sample_answers.json").write_text(json.dumps([{"q": "apple?", "answer": "A" * 300, "source": "s"},
                                                                        {"q": "zebra?", "answer": "short", "source": "s"}]))
        items = [{"question": "apple?"}, {"question": "zebra?"}]
        with mock.patch.object(generate, "ML", tmp), mock.patch("nailit.answers.harvest.embed", side_effect=fake_embed):
            generate.attach_samples(items)
            self.assertEqual(len(items[0]["_samples"]), 1)
            self.assertEqual(items[1]["_samples"], [])  # too short to be a useful sample
            (tmp / "harvest" / "sample_answers.json").write_text("[]")
            generate.attach_samples([{"question": "q"}])
        with mock.patch.object(generate, "ML", tmp / "none"):
            generate.attach_samples(items)

    def test_the_dry_run_counts_calls_without_calling_a_model(self):
        out = []
        with mock.patch("builtins.print", side_effect=lambda *a, **k: out.append(" ".join(map(str, a)))):
            generate.dry_run([{"question": "Tell me about a time you led change."}], STORIES, {}, 10.0)
        self.assertTrue(any("dry run:" in line for line in out))
        self.assertTrue(any("estimated total" in line for line in out))


class GenerateMainTest(unittest.TestCase):
    def test_main_builds_cards_and_writes_the_deck(self):
        tmp = Path(tempfile.mkdtemp())
        deck = tmp / "deck.json"
        card = {"question": "Q one is long enough?", "frequency": 2, "candidates": 2, "win_rate": 0.5, "origin": "generated"}
        with mock.patch.object(generate, "DECK", deck), mock.patch.object(generate, "ML", tmp), \
                mock.patch.object(generate, "questions", return_value=[{"question": "Q one is long enough?", "frequency": 2}]), \
                mock.patch.object(generate, "merge_similar", side_effect=lambda items, known: items), \
                mock.patch.object(generate, "attach_samples"), mock.patch.object(generate, "build_card", return_value=card), \
                mock.patch("nailit.config.load_secrets"), mock.patch.object(ai, "usage_report", return_value="usage"), \
                mock.patch("sys.argv", ["generate", "--limit", "1"]):
            generate.main()
        saved = json.loads(deck.read_text())
        self.assertEqual(len(saved["cards"]), 1)
        self.assertIn("persona", saved)

    def test_main_stops_when_the_spending_cap_is_reached(self):
        tmp = Path(tempfile.mkdtemp())
        deck = tmp / "deck.json"
        with mock.patch.object(generate, "DECK", deck), mock.patch.object(generate, "ML", tmp), \
                mock.patch.object(generate, "questions", return_value=[{"question": "Q two is long enough?", "frequency": 1}]), \
                mock.patch.object(generate, "merge_similar", side_effect=lambda items, known: items), \
                mock.patch.object(generate, "attach_samples"), \
                mock.patch.object(generate, "build_card", side_effect=ai.BudgetExceeded("cap")), \
                mock.patch("nailit.config.load_secrets"), mock.patch.object(ai, "usage_report", return_value=""), \
                mock.patch("sys.argv", ["generate", "--limit", "1"]):
            generate.main()
        self.assertEqual(json.loads(deck.read_text())["cards"], [])

    def test_main_dry_run_and_redo_paths(self):
        tmp = Path(tempfile.mkdtemp())
        deck = tmp / "deck.json"
        deck.write_text(json.dumps({"cards": [{"question": "Salary question here?", "frequency": 1}, {"question": "Other?", "polished_by": "w"}]}))
        with mock.patch.object(generate, "DECK", deck), mock.patch.object(generate, "ML", tmp), \
                mock.patch.object(generate, "questions", return_value=[]), mock.patch.object(generate, "attach_samples"), \
                mock.patch.object(generate, "dry_run") as dry, mock.patch("nailit.config.load_secrets"), \
                mock.patch("sys.argv", ["generate", "--redo", "salary", "--dry-run"]):
            generate.main()
        self.assertEqual(dry.call_args.args[0][0]["question"], "Salary question here?")


class CompetenciesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(competencies, "MAP", self.tmp / "map.json")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.comps, self.groups = competencies.load()

    def test_the_competency_file_loads_and_the_prompt_lists_every_id(self):
        self.assertGreater(len(self.comps), 20)
        prompt = competencies._prompt(self.comps[:2], ["Why us?", "Tell me about yourself"])
        self.assertIn(self.comps[0]["id"], prompt)
        self.assertIn("0. Why us?", prompt)

    def test_classify_keeps_valid_ids_and_caches_the_map(self):
        cid = self.comps[0]["id"]
        with mock.patch.object(ai, "chat", return_value={"map": {"0": cid, "1": "made_up", "x": cid}}) as chat:
            known = competencies.classify(["Q one?", "Q two?"], self.comps)
        self.assertEqual(known, {"Q one?": cid})
        self.assertEqual(chat.call_count, 2)  # first try covered under 90 %, so it tried again
        with mock.patch.object(ai, "chat", return_value=None) as chat:
            again = competencies.classify(["Q one?"], self.comps)  # already known: no model call
        self.assertFalse(chat.called)
        self.assertEqual(again, {"Q one?": cid})

    def test_the_coverage_report_flags_competencies_with_no_card(self):
        a, b = self.comps[0], self.comps[1]
        canon = [{"question": "q1?", "frequency": 5}, {"question": "q2?", "frequency": 2}, {"question": "q3?", "frequency": 1},
                 {"question": "q4?", "frequency": 1}, {"question": "q5?", "frequency": 1}, {"question": "q6?", "frequency": 1},
                 {"question": "unmapped?", "frequency": 1}]
        mapping = {"q1?": a["id"], "q2?": b["id"], "q3?": a["id"], "q4?": a["id"], "q5?": "off_topic", "q6?": "other"}
        deck = [{"question": "q1?", "variants": ["alt"]}]
        text, by = competencies.report(canon, mapping, self.comps, self.groups, deck)
        self.assertIn("questions mapped: 6 of 7", text)
        self.assertIn("NO CARD", text)
        self.assertEqual(by[a["id"]]["freq"], 7)
        self.assertEqual(len(by[a["id"]]["top"]), 3)

    def test_main_classifies_and_writes_the_coverage_file(self):
        ml = self.tmp
        (ml / "harvest").mkdir()
        (ml / "harvest" / "canonical.json").write_text(json.dumps([{"question": "q1?", "frequency": 2}]))
        with mock.patch.object(competencies, "ML", ml), mock.patch.object(competencies, "DECK", ml / "none.json"), \
                mock.patch.object(competencies, "classify", return_value={"q1?": self.comps[0]["id"]}), \
                mock.patch("nailit.config.load_secrets"):
            competencies.main()
        self.assertTrue((ml / "harvest" / "coverage.md").exists())


class AuditTest(unittest.TestCase):
    def test_the_audit_reports_numbers_structure_tells_and_coverage(self):
        comps = [{"id": "c1", "name": "Core one", "core": True}, {"id": "c2", "name": "Core two", "core": True}]
        cards = [{"generation": 2, "story": "M1", "answer": "I cut it by 47% across 12 sites. The trade-off was speed.", "question": "Q?",
                  "company": "", "quality": 7.5, "competency": "c1", "followups": [1]},
                 {"generation": 1, "story": None, "answer": "Older answer here.", "question": "Old?", "competency": "c9"}]
        with mock.patch.object(audit, "story_bank", return_value={"M1": "I cut errors."}), \
                mock.patch.object(audit.competencies, "load", return_value=(comps, {})):
            text = audit.report(cards)
        self.assertIn("numbers not found in the story: 1 cards", text)
        self.assertIn("answers that name their own structure: 1", text)
        self.assertIn("under 8: 1", text)
        self.assertIn("still missing: Core two", text)
        self.assertIn("## older: 1 cards", text)
        self.assertEqual(audit.last_sentence("One. Two! Three?"), "Three?")


class CalibrateTest(unittest.TestCase):
    CARD = {"question": "Q one?", "answer": "Model answer.", "runner_up": "Runner up.", "type": "behavioural"}

    def test_attempts_cover_the_six_ranks(self):
        fake_ai = mock.Mock()
        fake_ai.chat.side_effect = ["paraphrase text", "weak text"]
        made = calibrate.attempts_for(self.CARD, {"answer": "Other answer."}, fake_ai, "writer")
        self.assertEqual(sorted(made), sorted(calibrate.EXPECT))
        self.assertEqual((made["model"], made["off_topic"], made["weak"]), ("Model answer.", "Other answer.", "weak text"))

    def test_main_scores_every_attempt_twice_and_reports_the_wobble(self):
        from nailit import rehearse
        deck = {"cards": [dict(self.CARD, question=f"Q {n}?") for n in range(4)]}
        scores = {"model": 10, "paraphrase": 9, "runner_up": 6, "weak": 3, "off_topic": 1, "fragment": 1}

        def fake_score(card, text, audio, secs, log=True):
            kind = next(k for k, v in self.attempts.items() if v == text)
            return {"score": scores[kind]}
        self.attempts = {"model": "Model answer.", "paraphrase": "para", "runner_up": "Runner up.", "weak": "weak",
                         "off_topic": "other", "fragment": "frag"}
        out, tmp = [], Path(tempfile.mkdtemp())
        with mock.patch.object(rehearse, "load_deck", return_value=deck), mock.patch.object(rehearse, "_score", side_effect=fake_score), \
                mock.patch.object(calibrate, "attempts_for", return_value=dict(self.attempts)), \
                mock.patch("nailit.config.load_secrets"), mock.patch("builtins.print", side_effect=lambda *a, **k: out.append(" ".join(map(str, a)))), \
                mock.patch("sys.argv", ["calibrate", "--cards", "2", "--out", str(tmp / "o.json"), "--save-attempts", str(tmp / "a.json"),
                                        "--scorer", "tx:test"]):
            calibrate.main()
        self.assertTrue(any("out of range: 0" in line for line in out))
        self.assertTrue((tmp / "o.json").exists() and (tmp / "a.json").exists())
        self.assertTrue(any("wobble" in line for line in out))

    def test_main_reports_attempts_the_scorer_gets_wrong_and_errors(self):
        from nailit import rehearse
        deck = {"cards": [dict(self.CARD)]}
        tmp = Path(tempfile.mkdtemp())
        (tmp / "saved.json").write_text(json.dumps({"Q one?": {"model": "m", "fragment": "f"}}))
        out = []

        def fake_score(card, text, audio, secs, log=True):
            if text == "f":
                raise RuntimeError("scorer down")
            return {"score": 2}  # the model answer scored 2: out of range
        with mock.patch.object(rehearse, "load_deck", return_value=deck), mock.patch.object(rehearse, "_score", side_effect=fake_score), \
                mock.patch("nailit.config.load_secrets"), mock.patch("builtins.print", side_effect=lambda *a, **k: out.append(" ".join(map(str, a)))), \
                mock.patch("sys.argv", ["calibrate", "--attempts", str(tmp / "saved.json")]):
            calibrate.main()
        self.assertTrue(any("✗ model" in line for line in out))


if __name__ == "__main__":
    unittest.main()
