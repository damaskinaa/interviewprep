"""Checks from the persona walk-through: home page, local-only guard, unique card ids, readiness, mock debrief."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit import api, rehearse
from nailit.interview import interviewer

DECK = {"cards": [{"id": "tmay", "question": "Tell me about yourself.", "answer": "x", "competency": "tmay"},
                  {"id": "tmay", "question": "Tell me about yourself", "answer": "y", "competency": "tmay"},
                  {"id": "fail", "question": "Tell me about a time you failed.", "answer": "x", "competency": "failure"}]}
RESULT = {"score": 8, "quality": 8.0, "fidelity": None, "verdict": "Hire", "one_fix": "Lead with the result.",
          "rules": [{"id": "R1.1", "name": "Answer first", "verdict": "fail", "evidence": ""}]}


class JourneyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "library" / "model_level").mkdir(parents=True)
        (self.tmp / "library" / "model_level" / "deck.json").write_text(json.dumps(DECK))
        patcher = mock.patch("nailit.library.home", return_value=self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(api.app)

    def test_home_is_a_page_with_the_three_ways_to_practise(self):
        page = self.client.get("/").text
        for link in ('href="/rehearse"', 'href="/mock"', 'href="/call"'):
            self.assertIn(link, page)
        self.assertEqual(self.client.get("/health").json()["status"], "running")

    def test_requests_under_another_host_name_or_from_another_site_are_refused(self):
        self.assertEqual(self.client.get("/health", headers={"host": "evil.example:8000"}).status_code, 403)
        crossed = self.client.post("/rehearse/attempt_text", json={"card_id": "fail", "text": "hello"},
                                   headers={"origin": "https://evil.example"})
        self.assertEqual(crossed.status_code, 403)
        self.assertEqual(self.client.get("/health", headers={"host": "localhost:8000"}).status_code, 200)
        huge = self.client.post("/rehearse/attempt_text", content=b"{}", headers={"content-length": str(api.MAX_UPLOAD + 1)})
        self.assertEqual(huge.status_code, 413)
        self.assertEqual(self.client.get("/health", headers={"host": "127.0.0.1.evil.example"}).status_code, 403)

    def test_two_cards_never_share_an_id(self):
        ids = [c["id"] for c in rehearse.load_deck()["cards"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(rehearse.card("tmay_2")["answer"], "y")

    def test_readiness_counts_the_best_score_per_competency(self):
        rehearse.progress_path().write_text(json.dumps({"at": "2026-11-12 10:00:00", "card_id": "fail", "score": 8}) + "\n"
                                            + json.dumps({"at": "2026-11-12 10:01:00", "card_id": "call:tmay", "score": 4,
                                                          "competency": "tmay"}) + "\n")
        got = {c["id"]: c for c in self.client.get("/rehearse/readiness").json()["competencies"]}
        self.assertEqual((got["failure"]["best"], got["tmay"]["best"], got["tmay"]["cards"]), (8, 4, 2))

    def test_mock_answers_are_grouped_per_question_and_scored_by_the_rubric(self):
        state = {"id": "mock_x", "phase": "done", "turns": [
            {"role": "interviewer", "kind": "question", "say": "Hi. Tell me about a failure.", "question_text": "Tell me about a failure.",
             "question_id": "q1"},
            {"role": "candidate", "say": "I missed a deadline."},
            {"role": "interviewer", "kind": "followup", "say": "What did you do?"},
            {"role": "candidate", "say": "I rebuilt the plan."},
            {"role": "interviewer", "kind": "candidate_questions", "say": "Any questions?"},
            {"role": "candidate", "say": "What is the team like?"}]}
        pairs = api.mock_pairs(state)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0]["answers"], ["I missed a deadline.", "I rebuilt the plan."])
        saved = {}
        with mock.patch.object(api, "load_mock", return_value=state), mock.patch.object(api, "save_mock", saved.update), \
                mock.patch.object(api, "_library", return_value={"questions": []}), \
                mock.patch("nailit.library._questions", return_value=([{"id": "q1", "type": "failure"}], None)), \
                mock.patch("nailit.scoring.score", return_value=dict(RESULT)) as scorer:
            debrief = self.client.get("/interview/debrief?mock_id=mock_x").json()
        self.assertIn("overall", debrief, debrief)
        self.assertEqual((debrief["overall"], debrief["verdict"], debrief["repeat_misses"]), (8.0, "Hire", [["Answer first", 1]]))
        self.assertEqual(scorer.call_args.args[1], "I missed a deadline. I rebuilt the plan.")
        self.assertIn("mock:q1", rehearse.progress_path().read_text())

    def test_a_round_note_never_adds_a_second_question_to_the_opening(self):
        lib = {"questions": []}
        state = {"id": "m", "queue": [{"kind": "instruction", "text": "behavioural from the coverage gaps"}, {"kind": "question", "id": "q1"}],
                 "position": 0, "turns": [], "scores": [], "mode": "B", "round_id": "behavioural", "seed": 1, "events_fired": []}
        with mock.patch("nailit.library._questions", return_value=([{"id": "q1", "text": "Tell me about a failure.", "type": "failure"}], None)), \
                mock.patch.object(interviewer, "_say", return_value="Give me an example of ownership. What did you do?"), \
                mock.patch.object(interviewer, "_pick_event", return_value=None):
            turn = interviewer._advance(state, lib)
        self.assertEqual(turn["say"].count("?"), 0)
        self.assertTrue(turn["say"].endswith("Tell me about a failure."))


if __name__ == "__main__":
    unittest.main()


class ManualsTest(unittest.TestCase):
    """The manuals' plain checks run in code: phrases to cut, length and pace."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "library").mkdir()
        (self.tmp / "library" / "detectors.yaml").write_text(json.dumps({
            "phrase_detectors": [
                {"id": "involved", "label": "Participation", "kind": "phrase", "patterns": ["I was involved in"], "scope": "all",
                 "severity": "warn", "fix": "Name what you owned.", "except_context": ["layoff"]},
                {"id": "hedge_result", "label": "Hedge in a result", "kind": "phrase", "patterns": ["roughly"],
                 "scope": "result_sentences", "severity": "fail", "fix": "Say the number."},
                {"id": "fillers", "label": "Fillers", "kind": "phrase", "patterns": ["basically"], "scope": "all", "threshold": 2,
                 "severity": "info"},
                {"id": "bad", "label": "Broken", "kind": "regex", "patterns": ["("], "scope": "all", "severity": "warn"}],
            "measured_detectors": [{"id": "too_long", "label": "Too long", "fix": "Cut context."},
                                   {"id": "pace_fast", "label": "Fast", "fix": "Slow down."}]}))
        patcher = mock.patch("nailit.library.home", return_value=self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_phrases_respect_scope_threshold_and_exceptions(self):
        from nailit import manuals
        hits = manuals.phrase_hits("I was involved in the migration, basically. We cut cost by roughly 20 percent.")
        self.assertEqual([h["id"] for h in hits], ["hedge_result", "involved"])  # worst first; one filler is under its threshold
        self.assertEqual(manuals.phrase_hits("It was roughly fine. I was involved in the layoff."), [])

    def test_length_and_pace_follow_the_manuals_limits(self):
        from nailit import manuals
        self.assertEqual([n["id"] for n in manuals.delivery_notes(130, 150, {"type": "behavioural"})], ["too_long"])
        self.assertEqual(manuals.delivery_notes(130, 150, {"competency": "tmay"}), [])
        self.assertEqual(manuals.delivery_notes(80, 190, {}, past_wpm=[150, 150]), [])  # no baseline yet
        self.assertEqual([n["id"] for n in manuals.delivery_notes(80, 190, {}, past_wpm=[150, 150, 150])], ["pace_fast"])

    def test_plan_page_data_survives_a_missing_library(self):
        client = TestClient(api.app)
        data = client.get("/plan/data").json()
        self.assertEqual((data["checklist"], data["programmes"]), ({}, []))
        self.assertIn("checklist", client.get("/plan").text.lower())
