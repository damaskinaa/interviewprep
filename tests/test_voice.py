import importlib
import json
import os
import sys
import tempfile
import time
import types
import unittest
import wave
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit.interview import voice

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"
WHISPER = {
    "language": "en",
    "segments": [{"words": [
        {"word": " Um,", "start": 0.1, "end": 0.2},
        {"word": " I", "start": 0.25, "end": 0.3},
        {"word": " led", "start": 0.3, "end": 0.4},
        {"word": " uh", "start": 0.45, "end": 0.5},
        {"word": " the", "start": 0.5, "end": 0.55},
        {"word": " like", "start": 0.55, "end": 0.6},
        {"word": " migration.", "start": 0.6, "end": 0.8},
    ]}],
}


class VoiceUnitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        patcher = mock.patch.dict(os.environ, {"NAILIT_RECORDINGS": self.tmp})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_words_keep_fillers_and_timings(self):
        result = voice.words_result(WHISPER, 1.5)
        self.assertEqual(result["text"], "Um, I led uh the like migration.")
        self.assertEqual(result["filled_pauses"], 2)
        self.assertEqual((result["first_word_s"], result["speech_s"], result["trailing_silence_s"]), (0.1, 0.7, 0.7))

    def test_transcribe_asks_whisper_for_word_timestamps_and_fillers(self):
        calls = {}
        fake = types.ModuleType("mlx_whisper")
        fake.transcribe = lambda audio, **kwargs: calls.update(kwargs) or WHISPER
        audio_mod = types.ModuleType("mlx_whisper.audio")
        audio_mod.load_audio = lambda path: [0.0] * (voice.SAMPLE_RATE * 4)
        with mock.patch.dict(sys.modules, {"mlx_whisper": fake, "mlx_whisper.audio": audio_mod}), \
                mock.patch.object(voice.shutil, "which", return_value="/usr/bin/ffmpeg"):
            result = voice.transcribe("x.wav")
        self.assertTrue(calls["word_timestamps"])
        self.assertIn("Um", calls["initial_prompt"])
        self.assertFalse(calls["condition_on_previous_text"])
        self.assertEqual(result["duration_s"], 4.0)

    def test_missing_local_models_are_unavailable(self):
        with mock.patch.dict(sys.modules, {"mlx_whisper": None}):
            with self.assertRaises(voice.VoiceUnavailable):
                voice.transcribe("x.wav")
        with mock.patch.dict(sys.modules, {"mlx_audio": None, "mlx_audio.tts": None, "mlx_audio.tts.utils": None}), \
                mock.patch.object(voice, "_KOKORO", None):
            with self.assertRaises(voice.VoiceUnavailable):
                voice.kokoro_model()

    def test_kokoro_yields_int16_chunks(self):
        import numpy as np
        model = mock.Mock()
        model.generate.return_value = [types.SimpleNamespace(audio=np.array([0.0, 0.5, -2.0]), sample_rate=24000)]
        with mock.patch.object(voice, "_KOKORO", model):
            (pcm, rate), = list(voice.kokoro_pcm("Tell me about a decision."))
        self.assertEqual(rate, 24000)
        self.assertEqual(list(np.frombuffer(pcm, dtype=np.int16)), [0, 16383, -32767])
        self.assertEqual(model.generate.call_args.kwargs["voice"], "af_heart")

    def test_say_returns_pcm(self):
        def fake_say(command, **_):
            with wave.open(command[2], "wb") as wav:
                wav.setnchannels(1), wav.setsampwidth(2), wav.setframerate(24000)
                wav.writeframes(b"\x01\x00" * 10)
        with mock.patch.object(voice.sys, "platform", "darwin"), \
                mock.patch.object(voice.shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(voice.subprocess, "run", side_effect=fake_say) as run:
            pcm = voice.say_pcm("Tell me about a decision.")
        self.assertEqual(len(pcm), 20)
        self.assertIn("--data-format=LEI16@24000", run.call_args[0][0])
        self.assertEqual(run.call_args[0][0][-1], "Tell me about a decision.")

    def test_unsafe_names_are_rejected(self):
        for bad in ("../x", "a/b", "", "..", ".hidden"):
            with self.assertRaises(ValueError):
                voice.recordings_dir(bad)
        with self.assertRaises(ValueError):
            voice.save_upload("m1", "../evil", b"")


class VoicePipelineTest(unittest.TestCase):
    """A push-to-talk turn through the real Pipecat pipeline over the websocket, with Whisper, Kokoro and the LLM mocked."""

    def setUp(self):
        api = importlib.import_module("nailit.api")
        self.store = importlib.import_module("nailit.store")
        self.tmp = Path(tempfile.mkdtemp())
        tone = b"\x00\x10" * 2400  # 0.1 s at 24 kHz
        self.patches = [
            mock.patch.object(self.store, "DB_PATH", self.tmp / "t.db"),
            mock.patch.object(api.interviewer, "ask_llm", return_value="Tell me more."),
            mock.patch.object(voice, "transcribe", return_value=voice.words_result(WHISPER, 1.5)),
            mock.patch.object(voice, "kokoro_pcm", side_effect=lambda text: iter([(tone, 24000)])),
            mock.patch.dict(os.environ, {"NAILIT_HOME": str(EXAMPLE), "NAILIT_RECORDINGS": str(self.tmp / "rec")}),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(api.app)

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _until(self, ws, kind):
        events, audio = [], 0
        for _ in range(500):
            message = ws.receive()
            if message.get("bytes"):
                audio += len(message["bytes"])
                continue
            event = json.loads(message["text"])
            events.append(event)
            if event["type"] == kind:
                return events, audio
        self.fail(f"no {kind} event: {events}")

    def test_push_to_talk_turn(self):
        self.assertIn("ptt", self.client.get("/mock").text)
        mock_id = self.client.post("/interview/start", json={"round_id": "behavioural"}).json()["mock_id"]
        with self.client.websocket_connect(f"/voice/ws/{mock_id}?input=ptt") as ws:
            ws.send_text(json.dumps({"type": "ready"}))
            events, audio = self._until(ws, "question")
            self.assertTrue(events[-1]["interviewer"])
            _, line_audio = self._until(ws, "tts_done")
            self.assertGreater(audio + line_audio, 0)  # tts_done arrives after the line's audio
            time.sleep(0.3)
            ws.send_text(json.dumps({"type": "played"}))
            time.sleep(0.4)
            ws.send_text(json.dumps({"type": "ptt", "down": True}))
            for _ in range(50):
                ws.send_bytes(b"\x00\x00" * 320)  # 20 ms frames at 16 kHz
            ws.send_text(json.dumps({"type": "ptt", "down": False}))
            events, audio = self._until(ws, "latency")
            ws.send_text(json.dumps({"type": "end"}))
            for _ in range(500):
                if ws.receive()["type"] == "websocket.close":
                    break
            from nailit.interview import pipeline
            for _ in range(100):
                if mock_id not in pipeline.ACTIVE:
                    break
                time.sleep(0.05)
        turn = next(e for e in events if e["type"] == "turn")
        self.assertEqual((turn["candidate"], turn["filled_pauses"]), ("Um, I led uh the like migration.", 2))
        self.assertGreater(audio, 0)
        latency = events[-1]
        for key in ("stt_s", "llm_s", "tts_s", "latency_s"):
            self.assertIsNotNone(latency[key], key)
        state = self.store.load_mock(mock_id)
        candidate = next(t for t in state["turns"] if t["role"] == "candidate")
        self.assertTrue((self.tmp / "rec" / mock_id / candidate["audio"]).is_file())
        self.assertEqual(candidate["filled_pauses"], 2)
        self.assertGreaterEqual(candidate["pre_answer_silence_s"], 0.3)
        rows = self.client.get("/voice/latency", params={"mock_id": mock_id}).json()
        self.assertEqual(rows["median_s"], latency["latency_s"])

    def test_unknown_mock_closes(self):
        with self.client.websocket_connect("/voice/ws/nope") as ws:
            self.assertEqual(ws.receive()["code"], 4404)


if __name__ == "__main__":
    unittest.main()
