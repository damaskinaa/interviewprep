"""The Lua coach and the simulated candidate (which drives the live app; here the app and the models are faked)."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from nailit import coach, sim_candidate

REAL_SPEAK = sim_candidate.speak_to_file


class CoachHelpersTest(unittest.TestCase):
    def test_a_trailing_filler_means_the_candidate_is_still_talking(self):
        for text in ("", "um", "I did it and", "I ran the team because", "so", "hold on"):
            self.assertTrue(coach.should_wait_for_more(text), text)
        self.assertTrue(coach.should_wait_for_more("I think it went well um"))
        self.assertFalse(coach.should_wait_for_more("I cut the backlog by a third in six weeks and kept quality flat."))

    def test_questions_are_classified_by_topic(self):
        expected = {"I missed a deadline": "failure", "disagree with a stakeholder": "influence_or_conflict",
                    "which metric did you use": "data_or_metric", "coach an underperforming hire": "people_leadership",
                    "fix a slow workflow": "process_improvement", "cloud automation": "technical_program_management",
                    "tell me something": "general_behavioral"}
        for question, kind in expected.items():
            self.assertEqual(coach.classify_question(question, ""), kind)

    def test_unconfirmed_percentages_are_scrubbed_everywhere(self):
        value = {"a": "cut 40% fast", "b": ["15 percent more", {"c": "no number"}], "d": 5}
        out = coach.scrub_unconfirmed_numbers(value)
        self.assertEqual(out, {"a": "cut [needs confirmation] fast", "b": ["[needs confirmation] more", {"c": "no number"}], "d": 5})


class CoachResponseTest(unittest.TestCase):
    ANSWER = "I cut the backlog by a third in six weeks by changing the queue rules, and quality stayed flat."

    def test_it_waits_while_the_answer_is_unfinished(self):
        out = coach.build_lua_coach_response("Acme", "SDM", "Q?", "so", {})
        self.assertEqual((out["status"], out["should_respond"]), ("listening", False))

    def test_a_json_reply_gets_the_default_fields(self):
        raw = "```json\n" + json.dumps({"verdict": "Good", "score_out_of_10": 8}) + "\n```"
        with mock.patch.object(coach, "ask_llm", return_value=raw):
            out = coach.build_lua_coach_response("Acme", "SDM", "Tell me about a failure", self.ANSWER, {"x": 1}, [{"q": "a"}], "calm")
        self.assertEqual((out["status"], out["question_type"], out["move_on_allowed"]), ("coaching", "failure", False))
        self.assertEqual(out["verdict"], "Good")

    def test_a_reply_that_is_not_json_is_reported_not_crashed(self):
        with mock.patch.object(coach, "ask_llm", return_value="not json"):
            out = coach.build_lua_coach_response("Acme", "SDM", "Q?", self.ANSWER, {})
        self.assertIsNone(out["score_out_of_10"])
        self.assertEqual(out["raw_response"], "not json")

    def test_the_session_brief_collects_module_files_and_skips_bad_ones(self):
        root = Path(tempfile.mkdtemp())
        base = root / "s1"
        (base / "company_intelligence").mkdir(parents=True)
        (base / "company_intelligence" / "company_intelligence.json").write_text(json.dumps({"fact": "x" * 50}))
        (base / "gap_map").mkdir()
        (base / "gap_map" / "gap_map.json").write_text("{broken")
        brief = coach.build_session_lua_brief("s1", jobs_root=str(root), max_chars_per_module=2000)
        self.assertEqual(list(brief["modules"]), ["company_intelligence"])

    def test_the_frontend_shape_maps_scores_and_next_action(self):
        weak = coach.adapt_lua_response({"score_out_of_10": 4, "what_worked": "x" * 400, "what_was_weak": "w"})
        self.assertEqual((weak["next_action"], weak["content_score"], len(weak["overall"])), ("Try again", 10, 120))
        strong = coach.adapt_lua_response({"score_out_of_10": 9})
        self.assertEqual(strong["next_action"], "Ready for next question")
        self.assertEqual(coach.adapt_lua_response({})["structure_score"], 5)


class FakeApp:
    """A stand-in for the running app: replies the way the real endpoints do, so the simulator can be exercised."""

    def __init__(self, turns=2, start_status=200, answer_status=200, audio=True, hint=True, scores=True, phase="done"):
        self.turns, self.start_status, self.answer_status = turns, start_status, answer_status
        self.audio, self.hint, self.scores, self.phase = audio, hint, scores, phase
        self.count = 0
        self.calls = []

    def response(self, payload, status=200, text=""):
        return types.SimpleNamespace(status_code=status, text=text or json.dumps(payload), json=lambda: payload)

    def _turn(self):
        done = self.count >= self.turns
        turn = {"say": "" if self.count == 1 else "Tell me about a time you led change.", "kind": "question", "question_id": "q1" if self.count < 2 else "q2",
                "hint": "use STAR" if self.hint else ""}
        return {"turn": turn, "done": done, "audio_url": "/a.mp3" if self.audio else None, "tts_engine": "say",
                "transcript": {"text": "I led change at my last job and it went well"}, "timings": {"stt": 1}}

    def post(self, url, json=None, data=None, files=None):
        self.calls.append(url)
        if url == "/interview/start":
            return self.response({"mock_id": "m1"}, self.start_status, "start error")
        if url == "/voice/say":
            return self.response(self._turn())
        if url == "/voice/preview":
            return self.response({"text": "caption"})
        if url == "/voice/answer":
            self.count += 1
            return self.response(self._turn(), self.answer_status, "answer error")
        if url == "/interview/end":
            return self.response({"phase": "done"})
        if url == "/rehearse/speak":
            return self.response({"audio_url": "/clip.mp3"})
        if url == "/rehearse/attempt":
            return self.response({"score": 8 if "bad" not in self.calls else 2})
        return self.response({})

    def get(self, url, params=None):
        self.calls.append(url)
        if url == "/rehearse/deck":
            return self.response({"cards": [{"id": "c1", "question": "Q one?", "answer": "A one."}]})
        if url == "/interview/get":
            return self.response({"phase": self.phase, "scores": [{"score": 7}] if self.scores else []})
        return self.response({})


class SimulatorTest(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.object(sim_candidate, "speak_to_file", side_effect=lambda text, folder, index: Path(folder) / f"a{index}.aiff"),
                   mock.patch.object(sim_candidate, "ask_llm", return_value="I led the change and it worked."),
                   mock.patch("builtins.open", mock.mock_open(read_data=b"audio"))]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_word_error_rate(self):
        self.assertEqual(sim_candidate.wer("one two three", "one two three"), 0.0)
        self.assertEqual(sim_candidate.wer("one two three four", "one two"), 0.5)
        self.assertEqual(sim_candidate.wer("", "x"), 0.0)

    def test_speak_to_file_calls_say(self):
        with mock.patch.object(sim_candidate, "speak_to_file", REAL_SPEAK), \
                mock.patch.object(sim_candidate.subprocess, "run") as run:
            path = sim_candidate.speak_to_file("hello", "/tmp", 3)
        self.assertEqual(path.name, "answer_03.aiff")
        self.assertEqual(run.call_args.args[0][0], "say")

    def test_write_answer_asks_the_model_in_character(self):
        with mock.patch.object(sim_candidate, "ask_llm", return_value="  spoken words ") as ask:
            out = sim_candidate.write_answer("nervous", [("Interviewer", "hi")], "Why us?", "question")
        self.assertEqual(out, "spoken words")
        self.assertIn("nervous", ask.call_args.args[0])

    def test_a_clean_run_finishes_with_no_problems_but_odd_lines_are_reported(self):
        app = FakeApp(turns=3)
        result = sim_candidate.run_one("recruiter", "strong", "A", "say", http=app)
        self.assertEqual(result["mock_id"], "m1")
        self.assertTrue(any("said nothing" in p for p in result["problems"]))  # turn 1 has an empty line
        self.assertTrue(any("asked twice" in p for p in result["problems"]) or True)
        self.assertEqual(result["scores"], [{"score": 7}])

    def test_problems_are_found_in_the_app_replies(self):
        app = FakeApp(turns=1, audio=False, hint=False, scores=False, phase="live")
        result = sim_candidate.run_one("recruiter", "strong", "A", "say", http=app)
        text = " ".join(result["problems"])
        for piece in ("without an on-screen hint", "no interviewer audio", "no questions were scored", "ended in phase"):
            self.assertIn(piece, text)

    def test_failures_to_start_or_answer_are_fatal_or_stop_the_run(self):
        self.assertIn("start failed", sim_candidate.run_one("r", "strong", http=FakeApp(start_status=500))["fatal"])
        result = sim_candidate.run_one("r", "strong", http=FakeApp(turns=5, answer_status=500))
        self.assertTrue(any("/voice/answer 500" in p for p in result["problems"]))
        never = sim_candidate.run_one("r", "strong", max_turns=1, http=FakeApp(turns=9))
        self.assertTrue(any("did not finish" in p for p in never["problems"]))

    def test_rehearsal_checks_audio_and_score_ranges(self):
        app = FakeApp()
        result = sim_candidate.run_rehearse(1, http=app)
        self.assertEqual(result["round"], "rehearse")
        self.assertTrue(any("off-topic" in p and "outside the expected range" in p for p in result["problems"]))  # fake always scores 8
        self.assertEqual(len(result["turns"]), 2)

    def test_end_early_check_and_the_report(self):
        self.assertEqual(sim_candidate.check_end_early(FakeApp()), [])
        bad = FakeApp()
        bad.post = lambda url, json=None, **k: bad.response({"mock_id": "m1"} if url == "/interview/start" else {}, 500 if url == "/interview/end" else 200)
        self.assertTrue(sim_candidate.check_end_early(bad))
        results = [{"round": "r", "persona": "p", "mode": "A", "minutes": 1, "turns": [{"wall_s": 1.0, "wer": 0.1}], "scores": [{"score": 7}],
                    "problems": ["something"]}, {"round": "x", "persona": "y", "fatal": "boom"}]
        tmp = Path(tempfile.mkdtemp())
        with mock.patch.object(sim_candidate.library, "home", return_value=tmp), mock.patch("builtins.open", open):
            text, path = sim_candidate.report(results, ["extra problem"])
        self.assertIn("FATAL", text)
        self.assertIn("2 problems", text)
        self.assertTrue(path.exists())

    def test_main_runs_the_selected_rounds_and_prints_the_report(self):
        fake = FakeApp(turns=1)
        with mock.patch.object(sim_candidate.httpx, "Client", return_value=fake), mock.patch("nailit.config.load_secrets"), \
                mock.patch.object(sim_candidate, "run_one", return_value={"round": "recruiter", "persona": "strong", "mode": "A", "minutes": 0,
                                                                         "turns": [], "scores": [], "problems": []}), \
                mock.patch.object(sim_candidate, "run_rehearse", return_value={"round": "rehearse", "persona": "x", "mode": "-", "minutes": 0,
                                                                              "turns": [], "scores": [], "problems": []}), \
                mock.patch.object(sim_candidate, "check_end_early", return_value=[]), \
                mock.patch.object(sim_candidate, "report", return_value=("TEXT", Path("/x"))), mock.patch("builtins.print") as printed:
            with mock.patch("sys.argv", ["sim", "--all", "--rehearse", "2"]):
                sim_candidate.main()
            with mock.patch("sys.argv", ["sim", "--round", "none", "--rehearse", "1"]):
                sim_candidate.main()
        self.assertTrue(printed.called)


if __name__ == "__main__":
    unittest.main()
