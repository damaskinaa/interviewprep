import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit import library
from nailit.interview import interviewer as iv

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"
LIB = library.load_library(EXAMPLE / "library")
STRONG = ("I led the billing queue migration with a team of 4 engineers. I chose to migrate rather than patch, "
          "even though the stakeholders pushed back because of a launch, and I convinced them with the failure data. "
          "The result: failed payments dropped from about 9 to 3 a week, so support escalations stopped.")
WEAK = "We usually work together on things and it generally goes fine."


def fake_llm(prompt, **kwargs):
    return "LLM LINE"


class InterviewerTest(unittest.TestCase):
    def setUp(self):
        self._home = os.environ.get("NAILIT_HOME")
        os.environ["NAILIT_HOME"] = str(EXAMPLE)
        patcher = mock.patch.object(iv, "ask_llm", side_effect=fake_llm)
        self.llm = patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        os.environ.pop("NAILIT_HOME", None) if self._home is None else os.environ.__setitem__("NAILIT_HOME", self._home)

    def start(self, **kwargs):
        return iv.start_mock(kwargs.pop("round_id", "behavioural"), lib=LIB, seed=1, **kwargs)

    def test_flow_expands_questions_rounds_and_instructions(self):
        items = iv.expand_flow("loop", LIB["personas"], library._questions(LIB["questions"])[0], iv.random.Random(0))
        kinds = [(i["kind"], i.get("id")) for i in items]
        self.assertEqual(kinds[0], ("round", "behavioural"))
        self.assertIn(("question", "biggest_failure"), kinds)
        self.assertEqual(items[-1], {"kind": "instruction", "text": "Then a bar raiser round."})

    def test_first_turn_is_one_question_after_the_instruction(self):
        state, turn = self.start()
        self.assertEqual(turn["kind"], "question")
        self.assertEqual(turn["question_id"], "tell_me_about_yourself")
        self.assertTrue(turn["say"].startswith("LLM LINE"))
        self.assertIn("opening question", turn["say"])
        self.assertEqual(turn["say"].count("?") + turn["say"].count("Tell me"), 1)

    def test_weak_answer_gets_bank_followups_capped_at_three(self):
        state, _ = self.start(company_id="example_corp")
        kinds = []
        for _ in range(5):
            turn = iv.answer(state, WEAK, lib=LIB)
            kinds.append(turn["kind"])
            if turn["kind"] == "question":
                break
        self.assertEqual(kinds, ["followup", "followup", "followup", "question"])
        triggers = [t.get("trigger") for t in state["turns"] if t.get("kind") == "followup"]
        self.assertEqual(triggers[:2], ["missing_ownership", "missing_number"])

    def test_strong_answer_moves_on_after_one_followup(self):
        state, _ = self.start(company_id="example_corp")
        self.assertEqual(iv.answer(state, STRONG, lib=LIB)["trigger"], "company:example_corp")
        self.assertEqual(iv.answer(state, STRONG, lib=LIB)["kind"], "question")
        self.assertEqual(state["scores"][0]["score"], 5)
        self.assertEqual(state["stories_used"], {"S1": ["tell_me_about_yourself"]})

    def test_same_gap_three_times_is_logged_and_retired(self):
        state, _ = self.start()
        while state["phase"] == "questions" and len(state["scores"]) < 3:
            iv.answer(state, WEAK, lib=LIB)
        self.assertIn("missing_ownership", state["retired_gaps"])
        self.assertEqual(state["repeat_errors"][0]["gap"], "missing_ownership")

    def test_regression_deescalates(self):
        state, _ = self.start()
        while len(state["scores"]) < 2:
            iv.answer(state, STRONG, lib=LIB)
        while len(state["scores"]) < 3:
            iv.answer(state, WEAK, lib=LIB)
        self.assertTrue(state["deescalated"])

    def test_weak_last_answer_gets_extra_question_then_candidate_questions_and_closing(self):
        lib = copy.deepcopy(LIB)
        lib["questions"]["questions"].append({"id": "proud_of", "text": "What are you proud of?", "type": "strength"})
        state, _ = iv.start_mock("behavioural", lib=lib, seed=1)
        turn = None
        while state["phase"] == "questions":
            turn = iv.answer(state, WEAK if len(state["scores"]) == 2 else STRONG, lib=lib)
            if turn["kind"] == "question" and turn["question_id"] == "proud_of":
                self.assertTrue(turn["say"].startswith("One more before we finish."))
        self.assertTrue(state["extra_question_used"])
        self.assertEqual(turn["kind"], "candidate_questions")
        self.assertEqual(iv.answer(state, "What does success look like?", lib=LIB)["kind"], "answer")
        self.assertEqual(iv.answer(state, "No, that's all.", lib=LIB)["kind"], "closing")
        self.assertEqual(iv.answer(state, "Thank you, I'd love to join.", lib=LIB)["kind"], "end")
        self.assertEqual(state["phase"], "done")
        with self.assertRaises(ValueError):
            iv.answer(state, "hello", lib=LIB)

    def test_mode_c_is_locked_until_progress(self):
        with self.assertRaises(PermissionError):
            self.start(mode="C", progress={"freeze_drills": 4, "week2_average": 4})
        state, _ = self.start(mode="C", progress={"freeze_drills": 5, "week2_average": 3.5})
        self.assertEqual(state["mode"], "C")

    def test_mode_b_records_three_second_rule_and_cut_off(self):
        state, _ = self.start(mode="B")
        state["current"]["event"] = None
        turn = iv.answer(state, STRONG, seconds=95, pre_answer_silence_s=4.2, lib=LIB)
        self.assertTrue(turn["say"].startswith("Let me stop you there."))
        self.assertEqual(state["rule_violations"][0]["rule"], "3s_answer")

    def test_wrong_claim_event_misstates_a_number(self):
        state, _ = self.start(mode="B")
        state["current"]["event"] = "wrong_claim"
        turn = iv.answer(state, STRONG, lib=LIB)
        self.assertEqual(turn["event"], "wrong_claim")
        self.assertEqual(turn["expected"], {"true": "4", "said": "8"})
        self.assertIn("team of 8", turn["say"])

    def test_wrong_claim_keeps_decimals(self):
        self.assertEqual(iv._wrong_claim("It took 3.5 days.", iv.random.Random(0))[1], "7")
        self.assertEqual(iv._wrong_claim("It took 1.25 days.", iv.random.Random(0))[1], "2.5")

    def test_resume_skips_questions_removed_from_library(self):
        state, _ = self.start()
        state["queue"].insert(state["position"], {"kind": "question", "id": "removed_question"})
        turn = iv.answer(state, STRONG, lib=LIB)
        self.assertNotEqual(turn.get("question_id"), "removed_question")

    def test_no_coaching_words_in_code_lines(self):
        state, _ = self.start()
        while state["phase"] != "done":
            turn = iv.answer(state, WEAK, lib=LIB)
            self.assertNotRegex(turn["say"].lower(), r"\b(good answer|great|well done|tip|try to|you should)\b")


class InterviewApiTest(unittest.TestCase):
    def setUp(self):
        import importlib

        api = importlib.import_module("nailit.api")
        self.store = importlib.import_module("nailit.store")
        self.tmp = tempfile.mkdtemp()
        self.patches = [mock.patch.object(self.store, "DB_PATH", Path(self.tmp) / "t.db"),
                        mock.patch.object(api.interviewer, "ask_llm", side_effect=fake_llm),
                        mock.patch.dict(os.environ, {"NAILIT_HOME": str(EXAMPLE)})]
        for p in self.patches:
            p.start()
        self.client = TestClient(api.app)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_start_answer_get_and_mode_c_lock(self):
        options = self.client.get("/interview/options").json()
        self.assertTrue(next(m for m in options["modes"] if m["id"] == "C")["locked"])
        self.assertEqual(self.client.post("/interview/start", json={"round_id": "behavioural", "mode": "C"}).status_code, 403)
        started = self.client.post("/interview/start", json={"round_id": "behavioural", "seed": 3}).json()
        reply = self.client.post("/interview/answer", json={"mock_id": started["mock_id"], "text": STRONG}).json()
        self.assertFalse(reply["done"])
        got = self.client.get("/interview/get", params={"mock_id": started["mock_id"]}).json()
        self.assertEqual(len(got["turns"]), 3)
        for week in range(5):
            self.store.log_drill(f"freeze_{week}", kind="freeze", score=4)
        self.assertEqual(self.store.mode_c_progress()["freeze_drills"], 5)


if __name__ == "__main__":
    unittest.main()
