"""Edge branches of the interviewer state machine and the rehearsal routes that need a deck on disk."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit import library
from nailit.interview import interviewer as iv
from nailit.interview import voice

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"
LIB = library.load_library(EXAMPLE / "library")


class InterviewerEdgeTest(unittest.TestCase):
    def setUp(self):
        patches = [mock.patch.dict(os.environ, {"NAILIT_HOME": str(EXAMPLE)}), mock.patch.object(iv, "ask_llm", return_value="LLM LINE")]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def start(self, **kwargs):
        return iv.start_mock(kwargs.pop("round_id", "behavioural"), lib=LIB, seed=1, **kwargs)

    def test_bad_options_are_refused_with_a_clear_reason(self):
        with self.assertRaisesRegex(ValueError, "mode must be"):
            self.start(mode="Z")
        with self.assertRaisesRegex(ValueError, "unknown company"):
            self.start(company_id="no_such_company")
        with self.assertRaisesRegex(ValueError, "unknown temperament"):
            self.start(temperament_id="no_such_temperament")
        with self.assertRaises(PermissionError):
            self.start(mode="C", progress={})

    def test_ending_early_scores_the_answer_in_progress(self):
        state, _ = self.start()
        iv.answer(state, "I led a migration and cut failed payments from nine to three a week.", 30, 1.0, lib=LIB)
        result = iv.end_mock(state)
        self.assertEqual(state["phase"], "done")
        self.assertIn("scores", result)

    def test_a_model_failure_falls_back_to_plain_text(self):
        with mock.patch.object(iv, "ask_llm", side_effect=iv.LLMError("down")):
            state, turn = self.start()
        self.assertTrue(turn["say"])

    def test_the_wrong_claim_event_needs_a_number_to_misstate(self):
        rng = iv.random.Random(0)
        self.assertIsNone(iv._wrong_claim("No figures at all here.", rng))
        true, wrong, line = iv._wrong_claim("We cut errors from 9 to 3.", rng)
        self.assertNotEqual(true, wrong)
        self.assertIn("Just so I have it right", line)

    def test_pressure_events_produce_their_own_turns(self):
        state, _ = self.start()
        events = {"silence": {"id": "long_silence", "label": "Silence", "how": "wait"}, "wrong": {"id": "wrong_claim", "label": "Wrong", "how": "misstate"},
                  "drop": {"id": "connection_drop", "label": "Drop", "how": "cut out"}, "other": {"id": "interrupt", "label": "Interrupt", "how": "cut in"}}
        silent = iv._event_turn(state, LIB, events["silence"], "answer")
        self.assertEqual((silent["kind"], silent["silence_before_s"]), ("event", 6))
        self.assertIsNone(iv._event_turn(state, LIB, events["wrong"], "no numbers here"))
        claim = iv._event_turn(state, LIB, events["wrong"], "We cut errors from 9 to 3 in a week.")
        self.assertEqual(claim["expected"]["true"], "9")
        self.assertIn("cut out", iv._event_turn(state, LIB, events["drop"], "x")["say"])
        self.assertEqual(iv._event_turn(state, LIB, events["other"], "x")["event"], "interrupt")


class RehearseRoutesTest(unittest.TestCase):
    CARDS = [{"id": "c1", "question": "Tell me about a failure.", "answer": "I missed a launch by two weeks. " * 12, "type": "behavioral",
              "competency": "failure", "moves": ["Opens with the miss"], "variants": ["Tell me about a failure", "A failure?"],
              "followups": [{"q": "What would you change?", "a": "I would check the estimate first."}]},
             {"id": "c1", "question": "Duplicate id card.", "answer": "x " * 100, "type": "hard_skills"}]

    def setUp(self):
        self.api = __import__("importlib").import_module("nailit.api")
        self.rehearse = __import__("importlib").import_module("nailit.rehearse")
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "library" / "model_level").mkdir(parents=True)
        (self.tmp / "library" / "model_level" / "deck.json").write_text(json.dumps({"cards": self.CARDS, "built": "today"}))
        patches = [mock.patch.dict(os.environ, {"NAILIT_HOME": str(self.tmp), "NAILIT_RECORDINGS": str(self.tmp / "rec")})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        voice._TTS_DOWN.clear()
        self.client = TestClient(self.api.app)
        self.addCleanup(self.client.close)

    def test_the_deck_is_missing_until_built_and_duplicate_ids_are_split(self):
        (self.tmp / "library" / "model_level" / "deck.json").unlink()
        self.assertEqual(self.client.get("/rehearse/deck").status_code, 404)
        (self.tmp / "library" / "model_level" / "deck.json").write_text(json.dumps({"cards": self.CARDS}))
        cards = self.client.get("/rehearse/deck").json()["cards"]
        self.assertEqual([c["id"] for c in cards], ["c1", "c1_2"])
        self.assertEqual(cards[0]["type"], "behavioural")
        self.assertEqual(cards[0]["variants"], ["A failure?"])  # the wording that repeats the question is hidden
        self.assertEqual(len(self.client.get("/rehearse/deck", params={"kind": "hard_skills"}).json()["cards"]), 1)

    def test_follow_up_cards_are_addressed_by_suffix(self):
        self.assertEqual(self.rehearse.card("c1__f0")["type"], "followup")
        with self.assertRaises(Exception):
            self.rehearse.card("c1__f9")
        with self.assertRaises(Exception):
            self.rehearse.card("nope")

    def test_speaking_a_card_caches_the_audio_and_serves_it(self):
        def fake_speak(text, mock_id, name, engine=None, voice_name=None, instructions=None):
            path = voice.recordings_dir(mock_id) / f"{name}.mp3"
            path.write_bytes(b"mp3")
            return path, "openai"
        with mock.patch.object(self.rehearse.voice, "speak", side_effect=fake_speak) as speak:
            first = self.client.post("/rehearse/speak", json={"card_id": "c1", "part": "question"}).json()
            second = self.client.post("/rehearse/speak", json={"card_id": "c1", "part": "question"}).json()
        self.assertEqual(first, second)
        self.assertEqual(speak.call_count, 1)  # the second request is served from the cache
        self.assertEqual(self.client.get(first["audio_url"]).content, b"mp3")
        self.assertEqual(self.client.get("/rehearse/audio/missing.mp3").status_code, 404)
        self.assertEqual(self.client.get("/rehearse/audio/bad%20name.mp3").status_code, 404)
        with mock.patch.object(self.rehearse.voice, "speak", return_value=(None, "none")):
            self.assertIsNone(self.client.post("/rehearse/speak", json={"card_id": "c1", "part": "answer", "engine": "none"}).json()["audio_url"])

    def test_a_spoken_attempt_is_transcribed_and_scored(self):
        upload = {"audio": ("a.webm", b"x", "audio/webm")}
        heard = {"text": "I missed the launch and fixed the estimate process.", "speech_s": 12.0, "filled_pauses": 1}
        scored = {"score": 7, "quality": 7.0, "fidelity": None, "verdict": "Hire", "one_fix": "Lead with the result.", "rules": []}
        with mock.patch.object(self.rehearse.voice, "transcribe", return_value=heard), mock.patch("nailit.scoring.score", return_value=scored):
            out = self.client.post("/rehearse/attempt", data={"card_id": "c1", "unaided": "true", "test": "true"}, files=upload).json()
        self.assertEqual(out["score"], 7)
        with mock.patch.object(self.rehearse.voice, "transcribe", side_effect=voice.VoiceUnavailable("no whisper")):
            self.assertEqual(self.client.post("/rehearse/attempt", data={"card_id": "c1"}, files=upload).status_code, 503)
        with mock.patch.object(self.rehearse.voice, "transcribe", return_value={"text": " ", "speech_s": 0, "filled_pauses": 0}):
            self.assertEqual(self.client.post("/rehearse/attempt", data={"card_id": "c1"}, files=upload).status_code, 422)

    def test_typed_attempts_trust_dictation_timing_only_at_a_human_pace(self):
        scored = {"score": 8, "quality": 8.0, "fidelity": None, "verdict": "Hire", "one_fix": "x", "rules": []}
        text = " ".join(["word"] * 150)
        with mock.patch("nailit.scoring.score", return_value=scored), mock.patch.object(self.rehearse, "append_progress"):
            paced = self.client.post("/rehearse/attempt_text", json={"card_id": "c1", "text": text, "seconds": 60}).json()
            burst = self.client.post("/rehearse/attempt_text", json={"card_id": "c1", "text": text, "seconds": 5}).json()
        self.assertEqual(paced["delivery"]["wpm"], 150)
        self.assertIsNone(burst["delivery"]["wpm"])
        with mock.patch("nailit.scoring.score", side_effect=RuntimeError("scorer down")):
            self.assertEqual(self.client.post("/rehearse/attempt_text", json={"card_id": "c1", "text": text}).status_code, 502)

    def test_the_streak_counts_consecutive_days(self):
        rows = [{"at": time.strftime("%Y-%m-%d 09:00:00", time.localtime(time.time() - 86400 * n)), "card_id": "c1", "score": 7} for n in (0, 1, 2, 4)]
        (self.tmp / "rehearse_progress.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        self.assertEqual(self.client.get("/rehearse/progress").json()["streak"], 3)


if __name__ == "__main__":
    unittest.main()
