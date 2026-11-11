import importlib
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit.interview import voice

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"
WHISPER = {
    "language": "en",
    "segments": [{"words": [
        {"word": " Um,", "start": 1.4, "end": 1.6},
        {"word": " I", "start": 1.7, "end": 1.8},
        {"word": " led", "start": 1.8, "end": 2.0},
        {"word": " uh", "start": 2.1, "end": 2.3},
        {"word": " the", "start": 2.4, "end": 2.5},
        {"word": " like", "start": 2.5, "end": 2.7},
        {"word": " migration.", "start": 2.7, "end": 3.2},
    ]}],
}


class VoiceUnitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        patcher = mock.patch.dict(os.environ, {"NAILIT_RECORDINGS": self.tmp})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_words_keep_fillers_and_timings(self):
        result = voice.words_result(WHISPER, 4.0)
        self.assertEqual(result["text"], "Um, I led uh the like migration.")
        self.assertEqual(result["filled_pauses"], 2)
        self.assertEqual((result["first_word_s"], result["speech_s"], result["trailing_silence_s"]), (1.4, 1.8, 0.8))

    def test_transcribe_asks_whisper_for_word_timestamps_and_fillers(self):
        calls = {}
        fake = types.ModuleType("mlx_whisper")
        fake.transcribe = lambda audio, **kwargs: calls.update(kwargs) or WHISPER
        audio_mod = types.ModuleType("mlx_whisper.audio")
        audio_mod.load_audio = lambda path: [0.0] * (voice.SAMPLE_RATE * 4)
        with mock.patch.dict(sys.modules, {"mlx_whisper": fake, "mlx_whisper.audio": audio_mod}), \
                mock.patch.object(voice.shutil, "which", return_value="/usr/bin/ffmpeg"):
            result = voice.transcribe("x.webm")
        self.assertTrue(calls["word_timestamps"])
        self.assertIn("Um", calls["initial_prompt"])
        self.assertFalse(calls["condition_on_previous_text"])
        self.assertEqual(result["duration_s"], 4.0)

    def test_text_without_word_timings_is_kept(self):
        fake = types.ModuleType("mlx_whisper")
        fake.transcribe = lambda audio, **kwargs: {"text": " I led the migration.", "segments": [{"words": []}]}
        audio_mod = types.ModuleType("mlx_whisper.audio")
        audio_mod.load_audio = lambda path: [0.0] * (voice.SAMPLE_RATE * 4)
        with mock.patch.dict(sys.modules, {"mlx_whisper": fake, "mlx_whisper.audio": audio_mod}), \
                mock.patch.object(voice.shutil, "which", return_value="/usr/bin/ffmpeg"):
            result = voice.transcribe("x.webm")
        self.assertEqual(result["text"], "I led the migration.")
        self.assertIsNone(result["first_word_s"])

    def test_estimated_tail_keeps_the_measured_start(self):
        result = voice.words_result({"segments": [{"words": [{"word": "I", "start": 3.5, "end": 3.7},
                                                             {"word": "led", "start": 4.0, "end": 4.5, "estimated": True}]}]}, 5.0)
        self.assertEqual(result["first_word_s"], 3.5)

    def test_oversized_upload_is_rejected(self):
        with mock.patch.object(voice, "MAX_UPLOAD_BYTES", 10), self.assertRaises(ValueError):
            voice.save_upload("m1", "answer_001.webm", b"x" * 11)

    def test_strong_finish_never_picks_a_closing_question(self):
        from nailit.interview import interviewer
        questions = [{"id": "close_q", "type": "closing"}, {"id": "story_q", "type": "behavioural"}]
        with mock.patch.object(interviewer.library, "_questions", return_value=(questions, [])):
            picked = interviewer._strong_finish_question({"scores": []}, {"questions": []}, {})
        self.assertEqual(picked["id"], "story_q")

    def test_transcribe_without_mlx_is_unavailable(self):
        with mock.patch.dict(sys.modules, {"mlx_whisper": None}):
            with self.assertRaises(voice.VoiceUnavailable):
                voice.transcribe("x.webm")

    def test_say_engine_writes_wave(self):
        with mock.patch.object(voice.sys, "platform", "darwin"), \
                mock.patch.object(voice.shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(voice.subprocess, "run") as run:
            path, used = voice.speak("Tell me about a decision.", "m1", "interviewer_000", "say")
        self.assertEqual(used, "say")
        self.assertEqual(path.suffix, ".wav")
        self.assertIn("--file-format=WAVE", run.call_args[0][0])
        self.assertEqual(run.call_args[0][0][-1], "Tell me about a decision.")

    def test_openai_failure_falls_back_to_say_then_text(self):
        with mock.patch.object(voice, "_openai_tts", side_effect=RuntimeError("down")), \
                mock.patch.object(voice, "_say_tts", side_effect=voice.VoiceUnavailable("no say")):
            self.assertEqual(voice.speak("Hello.", "m1", "interviewer_001", "openai"), (None, "none"))

    def test_unsafe_names_are_rejected(self):
        for bad in ("../x", "a/b", "", "..", ".hidden"):
            with self.assertRaises(ValueError):
                voice.recordings_dir(bad)
        with self.assertRaises(ValueError):
            voice.save_upload("m1", "../evil", b"")


class VoiceApiTest(unittest.TestCase):
    def setUp(self):
        api = importlib.import_module("nailit.api")
        self.store = importlib.import_module("nailit.store")
        self.tmp = Path(tempfile.mkdtemp())
        self.patches = [
            mock.patch.object(self.store, "DB_PATH", self.tmp / "t.db"),
            mock.patch.object(api.interviewer, "ask_llm", return_value="Tell me more."),
            mock.patch.object(api.voice, "transcribe", return_value=voice.words_result(WHISPER, 4.0)),
            mock.patch.object(api.voice, "_openai_tts", side_effect=lambda text, path: Path(path).write_bytes(b"mp3")),
            mock.patch.dict(os.environ, {"NAILIT_HOME": str(EXAMPLE), "NAILIT_RECORDINGS": str(self.tmp / "rec")}),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(api.app)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_spoken_turn_round_trip(self):
        self.assertIn("vad-web", self.client.get("/mock").text)
        mock_id = self.client.post("/interview/start", json={"round_id": "behavioural"}).json()["mock_id"]
        first = self.client.post("/voice/say", json={"mock_id": mock_id, "engine": "openai"}).json()
        self.assertEqual(first["audio_url"], f"/voice/audio/{mock_id}/interviewer_000.mp3")
        self.assertEqual(self.client.get(first["audio_url"]).content, b"mp3")
        reply = self.client.post("/voice/answer", data={"mock_id": mock_id, "engine": "openai", "gap_before_record_s": "0.5"},
                                 files={"audio": ("answer.webm", b"webm-bytes", "audio/webm")}).json()
        self.assertEqual(reply["transcript"]["filled_pauses"], 2)
        self.assertEqual(set(reply["timings"]), {"stt_s", "llm_s", "tts_s"})
        self.assertTrue((self.tmp / "rec" / mock_id / "answer_001.webm").is_file())
        state = self.store.load_mock(mock_id)
        candidate = state["turns"][1]
        self.assertEqual((candidate["role"], candidate["audio"], candidate["pre_answer_silence_s"]), ("candidate", "answer_001.webm", 1.9))
        self.assertIn("answer_seconds", candidate["measure"]["metrics"])  # measured after the reply, not shown in the round
        self.assertNotIn("measure", reply["turn"])
        self.assertIn("structure_error", candidate["measure"])  # no API key in tests: structure skipped, rest kept
        self.assertIsInstance(self.client.get("/interview/get", params={"mock_id": mock_id}).json()["consistency"], list)
        self.client.post("/voice/latency", json={"mock_id": mock_id, "turn": reply["turn_index"], "latency_s": 1.2})
        self.assertEqual(self.client.get("/voice/latency", params={"mock_id": mock_id}).json()["median_s"], 1.2)
        self.assertEqual(self.client.get(f"/voice/audio/{mock_id}/..%2Ft.db").status_code, 404)

    def test_preview_needs_a_real_mock(self):
        r = self.client.post("/voice/preview", data={"mock_id": "nope"}, files={"audio": ("p.webm", b"x", "audio/webm")})
        self.assertEqual(r.status_code, 404)


if __name__ == "__main__":
    unittest.main()
