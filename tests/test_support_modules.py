"""Storage, settings, command line, voice back-ends and the LLM engines: the paths the other tests do not reach."""
import os
import subprocess
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import numpy as np

from nailit import cli, config, guards, llm, paths, store
from nailit.interview import voice


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(store, "DB_PATH", self.tmp / "jobs.db")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_jobs_are_created_updated_and_read_back(self):
        job = store.create_job("j1", {"session_id": "s1", "module_name": "gap_map"})
        self.assertEqual((job["status"], job["progress"]), ("queued", 0))
        updated = store.update_job("j1", status="running", progress=40, product_json={"a": 1}, ignored="x", error=None)
        self.assertEqual((updated["status"], updated["product_json"]), ("running", {"a": 1}))
        self.assertEqual(store.update_job("j1")["job_id"], "j1")  # nothing to change
        self.assertIsNone(store.get_job("missing"))
        self.assertEqual(store.find_running_module_job("s1", "gap_map"), "j1")
        self.assertIsNone(store.find_running_module_job("s1", "other"))

    def test_corrupt_json_columns_do_not_break_a_read(self):
        store.create_job("j2", {})
        with store._connect() as con:
            con.execute("UPDATE jobs SET product_json = '{bad', input_payload = '{bad' WHERE job_id = 'j2'")
        job = store.get_job("j2")
        self.assertEqual((job["product_json"], job["input_payload"]), ({}, {}))

    def test_only_one_job_per_session_and_module_is_created(self):
        self.assertEqual(store.get_or_create_job("s1", "gap_map", "a"), ("a", True))
        self.assertEqual(store.get_or_create_job("s1", "gap_map", "b"), ("a", False))
        self.assertEqual(store.get_or_create_job("s1", "other", "c"), ("c", True))

    def test_a_failed_insert_rolls_back(self):
        with mock.patch.object(store, "_now", side_effect=RuntimeError("clock")), self.assertRaises(RuntimeError):
            store.get_or_create_job("s2", "m", "z")
        real_connect = store._connect

        def broken():
            con = real_connect()
            wrapper = mock.Mock(wraps=con)
            wrapper.execute.side_effect = lambda sql, *a: (_ for _ in ()).throw(RuntimeError("db")) if "INSERT" in sql else con.execute(sql, *a)
            return wrapper
        with mock.patch.object(store, "_connect", broken), self.assertRaises(RuntimeError):
            store.get_or_create_job("s3", "m", "y")

    def test_stale_jobs_are_failed_and_fresh_ones_kept(self):
        store.create_job("old", {})
        store.create_job("new", {})
        with store._connect() as con:
            con.execute("UPDATE jobs SET updated_at = ? WHERE job_id = 'old'", ((datetime.now() - timedelta(hours=3)).isoformat(),))
        self.assertEqual(store.fail_stale_jobs(30), 1)
        self.assertEqual((store.get_job("old")["status"], store.get_job("new")["status"]), ("failed", "queued"))

    def test_sessions_truncate_long_fields_and_hide_raw_text_by_default(self):
        payload = {"company_name": "A" * 300, "role_name": "SDM", "job_description": "jd", "cv": "cv", "answer_bank": "", "user_email": "e@x.io"}
        session = store.create_session("s1", payload)
        self.assertEqual(len(session["company_name"]), 200)
        self.assertEqual(session["raw_jd"], "jd")
        public = store.get_session("s1")
        self.assertNotIn("raw_jd", public)
        self.assertEqual((public["has_job_description"], public["has_answer_bank"], public["user_id"]), (True, False, "s1"))
        self.assertIsNone(store.get_session("nope"))
        self.assertEqual(store._truncate_session_fields(raw_jd="x" * 130000)["raw_jd"], "x" * 120000)

    def test_mocks_drills_and_voice_timings(self):
        store.save_mock({"id": "m1", "n": 1})
        store.save_mock({"id": "m1", "n": 2})
        self.assertEqual(store.load_mock("m1")["n"], 2)
        self.assertIsNone(store.load_mock("none"))
        start = datetime(2026, 1, 1)
        store.log_drill("d1", "freeze", 5, when=start)
        store.log_drill("d2", "voice", 8, when=start + timedelta(days=8))
        store.log_drill("d3", "voice", None, when=start + timedelta(days=9))
        progress = store.mode_c_progress()
        self.assertEqual((progress["freeze_drills"], progress["week2_average"]), (1, 8))
        store.log_voice("m1", 0, 0.5, 0.4, 0.3, "say")
        self.assertEqual(store.set_voice_latency("m1", 0, 1.2), 1)
        self.assertEqual(store.voice_latencies("m1")[0]["latency_s"], 1.2)
        self.assertEqual(len(store.voice_latencies()), 1)
        self.assertEqual(store.mode_c_progress.__name__, "mode_c_progress")

    def test_empty_drill_log_has_no_average(self):
        self.assertEqual(store.mode_c_progress(), {"freeze_drills": 0, "week2_average": None})


class ConfigCliPathsTest(unittest.TestCase):
    def test_keychain_reads_succeed_fail_and_are_skipped_off_mac(self):
        with mock.patch.object(config.sys, "platform", "darwin"), mock.patch.object(config.subprocess, "run", return_value=types.SimpleNamespace(returncode=0, stdout=" secret\n")):
            self.assertEqual(config.keychain_secret("X"), "secret")
        with mock.patch.object(config.sys, "platform", "darwin"), mock.patch.object(config.subprocess, "run", return_value=types.SimpleNamespace(returncode=44, stdout="")):
            self.assertEqual(config.keychain_secret("X"), "")
        with mock.patch.object(config.sys, "platform", "darwin"), mock.patch.object(config.subprocess, "run", side_effect=OSError("no security")):
            self.assertEqual(config.keychain_secret("X"), "")
        with mock.patch.object(config.sys, "platform", "linux"):
            self.assertEqual(config.keychain_secret("X"), "")

    def test_load_secrets_copies_keychain_values_into_the_environment(self):
        with mock.patch.object(config, "keychain_secret", side_effect=lambda name: "v1" if name == "TENSORX_API_KEY" else ""), \
                mock.patch.object(config, "load_dotenv"), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TENSORX_API_KEY", None)
            config.load_secrets(Path("/nonexistent/.env"))
            self.assertEqual(os.environ["TENSORX_API_KEY"], "v1")
            os.environ.pop("TENSORX_API_KEY", None)

    def test_prices_and_models_come_from_the_environment(self):
        self.assertEqual(config._price_pair("1.5, 2"), (1.5, 2.0))
        self.assertEqual(config._price_pair("bad"), (0.0, 0.0))
        self.assertEqual(config._price_pair(None), (0.0, 0.0))
        with mock.patch.dict(os.environ, {"NAILIT_MODEL_FAST": "f", "NAILIT_MODEL_STRONG": "s", "NAILIT_PRICE_FAST": "1,2"}):
            settings = config.llm_settings()
        self.assertEqual((settings["model_fast"], settings["model_strong"], settings["prices"]["fast"]), ("f", "s", (1.0, 2.0)))

    def test_data_paths_follow_the_data_dir(self):
        with mock.patch.dict(os.environ, {"DATA_DIR": "/data", "LUA_DB_BASE_DIR": ""}):
            self.assertEqual(paths.data_path("a.db"), Path("/data/a.db"))
            self.assertEqual(paths.lua_data_path("b.db"), Path("/data/b.db"))
        with mock.patch.dict(os.environ, {"DATA_DIR": "", "LUA_DB_BASE_DIR": "/lua"}):
            self.assertEqual(paths.data_path("a.db"), Path("a.db"))
            self.assertEqual(paths.lua_data_path("b.db"), Path("/lua/b.db"))

    def test_the_command_line_checks_the_library_or_serves(self):
        with mock.patch("nailit.library.load_library", return_value={}), mock.patch("nailit.library.summary", return_value="fine"), mock.patch("builtins.print"):
            self.assertEqual(cli.main(["check-library", "/x"]), 0)
        error = type("E", (Exception,), {})
        from nailit.library import LibraryError
        with mock.patch("nailit.library.load_library", side_effect=LibraryError(["bad one", "bad two"])), mock.patch("builtins.print"):
            self.assertEqual(cli.check_library("/x"), 1)
        fake_uvicorn = types.ModuleType("uvicorn")
        fake_uvicorn.run = mock.Mock()
        with mock.patch.dict(sys.modules, {"uvicorn": fake_uvicorn}), mock.patch("nailit.config.load_secrets"):
            self.assertEqual(cli.main(["--port", "9001", "--reload"]), 0)
        fake_uvicorn.run.assert_called_once_with("nailit.api:app", host="127.0.0.1", port=9001, reload=True)
        self.assertTrue(error)


class GuardsEdgeTest(unittest.TestCase):
    def test_empty_why_company_text_counts_as_generic(self):
        self.assertTrue(guards.why_company_is_generic(""))
        self.assertFalse(guards.why_company_is_generic("Acme runs a six week onboarding for operations leads."))

    def test_stripping_uses_qualitative_words_by_unit(self):
        cleaned, stripped = guards.strip_hallucinated_metrics("We saved 40 percent, 12 hours, $5 million and 9 people.", "I did things", "")
        self.assertIn("significantly", cleaned)
        self.assertIn("meaningfully faster", cleaned)
        self.assertEqual(len(stripped), 4)
        kept, none = guards.strip_hallucinated_metrics("I cut it by 40%.", "cut 40%", "")
        self.assertEqual((kept, none), ("I cut it by 40%.", []))


class LlmEngineTest(unittest.TestCase):
    def reply(self, text="hello", status=200, body=None):
        response = mock.Mock(status_code=status, text=text, headers={"content-type": "application/json"})
        response.json.return_value = body if body is not None else {"text": text}
        return response

    def test_the_lua_engine_returns_text_and_raises_on_errors(self):
        env = {"LUA_API_KEY": "k" * 10, "LUA_AGENT_ID": "agent"}
        with mock.patch.dict(os.environ, env), mock.patch("httpx.post", return_value=self.reply(" hi ")):
            self.assertEqual(llm._lua("prompt", 100), "hi")
            self.assertEqual(llm._other_engine("lua", "prompt", 100), "hi")
        with mock.patch.dict(os.environ, env), mock.patch("httpx.post", return_value=self.reply(status=500, body={"error": "down"})), \
                self.assertRaises(llm.LLMError):
            llm._lua("prompt", 100)
        blocked = self.reply(body={"type": "governance_blocked", "message": "no"})
        with mock.patch.dict(os.environ, env), mock.patch("httpx.post", return_value=blocked), self.assertRaises(llm.LLMError):
            llm._lua("prompt", 100)
        plain = types.SimpleNamespace(status_code=200, text="x", headers={"content-type": "text/plain"}, json=lambda: {})
        with mock.patch.dict(os.environ, env), mock.patch("httpx.post", return_value=plain):
            self.assertEqual(llm._lua("prompt", 100), "")

    def test_the_claude_and_gemini_engines_and_unknown_names(self):
        with mock.patch("nailit.answers.ai._cli", return_value="from claude") as cli_call:
            self.assertEqual(llm._other_engine("claude", "p", 10), "from claude")
        self.assertIn("p", cli_call.call_args.args[1])
        completion = mock.Mock()
        completion.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content=" from gemini "))]
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "g" * 12}), mock.patch.object(llm, "OpenAI") as client:
            client.return_value.chat.completions.create.return_value = completion
            self.assertEqual(llm._other_engine("gemini", "p", 10), "from gemini")
        with self.assertRaises(llm.LLMError):
            llm._other_engine("nope", "p", 10)

    def test_engine_readiness(self):
        with mock.patch("shutil.which", return_value="/usr/bin/claude"):
            self.assertTrue(llm.engine_ready("claude"))
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            self.assertFalse(llm.engine_ready("gemini"))

    def test_ask_llm_through_other_engines_retries_then_gives_up(self):
        with mock.patch.object(llm, "provider", return_value="lua"), mock.patch.object(llm, "engine_ready", return_value=False):
            with self.assertRaisesRegex(llm.LLMError, "not set up"):
                llm.ask_llm("hi")
        with mock.patch.object(llm, "provider", return_value="lua"), mock.patch.object(llm, "engine_ready", return_value=True), \
                mock.patch.object(llm, "people_map", return_value={}):
            with mock.patch.object(llm, "_other_engine", return_value="spoken"):
                self.assertEqual(llm.ask_llm("hi"), "spoken")
            with mock.patch.object(llm, "_other_engine", return_value=""), self.assertRaisesRegex(llm.LLMError, "empty reply"):
                llm.ask_llm("hi", retries=2)
            with mock.patch.object(llm, "_other_engine", side_effect=PermissionError("limit")) as engine, self.assertRaises(llm.LLMError):
                llm.ask_llm("hi", retries=3)
            self.assertEqual(engine.call_count, 1)  # a usage limit is not retried

    def test_ask_llm_through_tensorx_and_without_any_key(self):
        completion = mock.Mock()
        completion.usage = types.SimpleNamespace(prompt_tokens=1, completion_tokens=1)
        completion.choices = [types.SimpleNamespace(message=types.SimpleNamespace(content="<think>x</think> the reply "))]
        fake = mock.Mock()
        fake.chat.completions.create.return_value = completion
        with mock.patch.object(llm, "provider", return_value="tensorx"), mock.patch.object(llm, "people_map", return_value={}), \
                mock.patch.object(llm, "_tx_client", fake), mock.patch.object(llm, "record_call"):
            self.assertEqual(llm.ask_llm("hi", model=llm.MODEL_STRONG, max_tokens=100), "the reply")
            self.assertGreaterEqual(fake.chat.completions.create.call_args.kwargs["max_tokens"], 1200)
        with mock.patch.object(llm, "provider", return_value="openai"), mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            with self.assertRaisesRegex(llm.LLMError, "No model key"):
                llm.ask_llm("hi")
        empty = mock.Mock()
        empty.chat.completions.create.side_effect = RuntimeError("down")
        with mock.patch.object(llm, "provider", return_value="tensorx"), mock.patch.object(llm, "people_map", return_value={}), \
                mock.patch.object(llm, "_tx_client", empty), mock.patch.object(llm.time, "sleep"):
            with self.assertRaisesRegex(llm.LLMError, "after 2 attempts"):
                llm.ask_llm("hi", retries=2)

    def test_the_tensorx_client_is_created_on_first_use(self):
        made = mock.Mock()
        made.chat.completions.create.side_effect = RuntimeError("stop")
        with mock.patch.object(llm, "provider", return_value="tensorx"), mock.patch.object(llm, "people_map", return_value={}), \
                mock.patch.object(llm, "_tx_client", None), mock.patch.object(llm, "OpenAI", return_value=made) as factory, \
                mock.patch.dict(os.environ, {"TENSORX_API_KEY": "t" * 12}), mock.patch.object(llm.time, "sleep"):
            with self.assertRaises(llm.LLMError):
                llm.ask_llm("hi", retries=1)
        self.assertTrue(factory.called)

    def test_json_helpers_recover_from_fences_and_junk(self):
        self.assertEqual(llm.parse_json_object('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(llm.parse_json_object("not json", {"x": 1}), {"x": 1})
        self.assertEqual(llm.parse_json_object("[1, 2]"), [1, 2])
        with mock.patch.object(llm, "ask_llm", return_value='{"ok": true}'):
            self.assertEqual(llm.ask_json("p"), {"ok": True})
        with mock.patch.object(llm, "ask_llm", return_value="junk"):
            self.assertEqual(llm.ask_json("p", fallback={"f": 1}), {"f": 1})
        self.assertEqual(llm.json_dumps(None), "{}")
        self.assertIn("raw_output", llm.extract_json(None) + "raw_output")


class VoiceInternalsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patcher = mock.patch.dict(os.environ, {"NAILIT_RECORDINGS": str(self.tmp)})
        patcher.start()
        self.addCleanup(patcher.stop)
        voice._TTS_DOWN.clear()
        self.addCleanup(voice._TTS_DOWN.clear)
        voice.LIVE.clear()
        self.addCleanup(voice.LIVE.clear)

    def words(self, spoken, start=0.0, step=0.5):
        return [{"word": w, "start": start + i * step, "end": start + i * step + 0.4} for i, w in enumerate(spoken.split())]

    def test_a_repetition_loop_or_sparse_transcript_looks_broken(self):
        self.assertTrue(voice._looks_broken(self.words("I I I I I I I"), 20))
        self.assertTrue(voice._looks_broken(self.words("hello there"), 20))
        self.assertFalse(voice._looks_broken(self.words("we ran the weekly review with every region"), 4))

    def test_words_retry_without_the_filler_prompt_and_keep_the_better_attempt(self):
        audio = np.zeros(16000 * 10, dtype="float32")
        broken = {"segments": [{"words": [{"word": " a", "start": 0, "end": 0.1}]}]}
        good = {"segments": [{"words": [{"word": f" w{i}", "start": i * 0.3, "end": i * 0.3 + 0.2} for i in range(30)]}]}
        fake = types.ModuleType("mlx_whisper")
        fake.transcribe = mock.Mock(side_effect=[broken, good])
        with mock.patch.dict(sys.modules, {"mlx_whisper": fake}):
            out = voice._words(audio, offset_s=1.0)
        self.assertEqual(len(out), 30)
        self.assertEqual(out[0]["start"], 1.0)
        fake.transcribe = mock.Mock(return_value=broken)
        with mock.patch.dict(sys.modules, {"mlx_whisper": fake}):
            self.assertEqual(len(voice._words(audio)), 1)  # both attempts broken: the longer one is kept
            self.assertEqual(voice._words(np.zeros(100, dtype="float32")), [])  # too short to transcribe

    def test_the_quietest_point_is_chosen_for_chunk_boundaries(self):
        audio = np.ones(16000 * 6, dtype="float32")
        audio[16000 * 3:int(16000 * 3.2)] = 0.0
        cut = voice._quiet_cut(audio, 2.0, 4.0)
        self.assertGreaterEqual(cut, 3.0)
        self.assertLessEqual(cut, 3.2)
        self.assertEqual(voice._quiet_cut(audio, 2.0, 2.05), 2.05)

    def test_loading_audio_reports_missing_dependencies(self):
        with mock.patch.dict(sys.modules, {"mlx_whisper": None, "mlx_whisper.audio": None}), self.assertRaises(voice.VoiceUnavailable):
            voice._load("x.wav")
        fake_audio = types.ModuleType("mlx_whisper.audio")
        fake_audio.load_audio = lambda path: np.zeros(16000, dtype="float32")
        with mock.patch.dict(sys.modules, {"mlx_whisper": types.ModuleType("mlx_whisper"), "mlx_whisper.audio": fake_audio}):
            with mock.patch.object(voice.shutil, "which", return_value=None), self.assertRaises(voice.VoiceUnavailable):
                voice._load("x.wav")
            with mock.patch.object(voice.shutil, "which", return_value="/usr/bin/ffmpeg"):
                self.assertEqual(len(voice._load("x.wav")), 16000)

    def test_live_captions_commit_finished_chunks_and_transcribe_reuses_them(self):
        audio = np.zeros(16000 * 25, dtype="float32")
        with mock.patch.object(voice, "_load", return_value=audio), \
                mock.patch.object(voice, "_words", side_effect=lambda a, start=0.0, model=None: [{"word": f"w{int(start)}", "start": start, "end": start + 1}]):
            text = voice.live_update("m1", "t1", "x.wav")
            self.assertIn("w0", text)
            self.assertGreater(voice.LIVE["m1"]["committed_s"], 0)
            result = voice.transcribe("x.wav", mock_id="m1", take="t1")
            self.assertGreaterEqual(len(result["words"]), 2)
            self.assertNotIn("m1", voice.LIVE)
            fresh = voice.transcribe("x.wav", mock_id="m2", take="t2")
            self.assertEqual(len(fresh["words"]), 1)
            voice.live_update("m3", "a", "x.wav")
            voice.live_update("m3", "b", "x.wav")  # a new take starts a new state
            self.assertEqual(voice.LIVE["m3"]["take"], "b")

    def test_openai_and_tensorx_speech(self):
        with mock.patch.dict(os.environ, {"OPENAI_TTS_API_KEY": "", "OPENAI_API_KEY": ""}), self.assertRaises(voice.VoiceUnavailable):
            voice._openai_tts("hi", self.tmp / "a.mp3")
        stream = mock.MagicMock()
        client = mock.Mock()
        client.audio.speech.with_streaming_response.create.return_value = stream
        stream.__enter__.return_value = stream
        fake_openai = types.ModuleType("openai")
        fake_openai.OpenAI = mock.Mock(return_value=client)
        with mock.patch.dict(sys.modules, {"openai": fake_openai}), mock.patch.dict(os.environ, {"OPENAI_API_KEY": "k"}):
            voice._openai_tts("hi", self.tmp / "a.mp3", voice_name="nova", instructions="calm")
        stream.stream_to_file.assert_called_once()
        with mock.patch.dict(os.environ, {"TENSORX_API_KEY": ""}), self.assertRaises(voice.VoiceUnavailable):
            voice._tensorx_tts("hi", self.tmp / "b.mp3")
        ok = types.SimpleNamespace(status_code=200, content=b"x" * 2000, text="")
        with mock.patch.dict(os.environ, {"TENSORX_API_KEY": "k"}), mock.patch("httpx.post", return_value=ok):
            voice._tensorx_tts("hi", self.tmp / "b.mp3")
        self.assertEqual((self.tmp / "b.mp3").stat().st_size, 2000)
        bad = types.SimpleNamespace(status_code=500, content=b"", text="boom")
        with mock.patch.dict(os.environ, {"TENSORX_API_KEY": "k"}), mock.patch("httpx.post", return_value=bad), self.assertRaises(voice.VoiceUnavailable):
            voice._tensorx_tts("hi", self.tmp / "c.mp3")

    def test_say_speech_and_error_descriptions(self):
        with mock.patch.object(voice.sys, "platform", "linux"), self.assertRaises(voice.VoiceUnavailable):
            voice._say_tts("hi", self.tmp / "a.wav")
        with mock.patch.object(voice.sys, "platform", "darwin"), mock.patch.object(voice.shutil, "which", return_value="/usr/bin/say"), \
                mock.patch.object(voice.subprocess, "run") as run, mock.patch.dict(os.environ, {"NAILIT_SAY_VOICE": "Samantha"}):
            voice._say_tts("secret words", self.tmp / "a.wav")
        self.assertIn("Samantha", run.call_args.args[0])
        called = subprocess.CalledProcessError(2, ["/usr/bin/say", "secret words"])
        timed = subprocess.TimeoutExpired(["/usr/bin/say", "secret words"], 60)
        self.assertNotIn("secret", voice._describe(called))
        self.assertIn("timed out", voice._describe(timed))
        self.assertIn("RuntimeError", voice._describe(RuntimeError("x")))

    def test_speak_falls_back_through_the_engines_and_skips_failed_ones(self):
        def fail(text, path, voice_name=None, instructions=None):
            raise voice.VoiceUnavailable("down")

        def say(text, path, voice_name=None, instructions=None):
            Path(path).write_bytes(b"wav")
        with mock.patch.object(voice, "_openai_tts", fail), mock.patch.object(voice, "_tensorx_tts", fail), mock.patch.object(voice, "_say_tts", say):
            path, engine = voice.speak("hi", "mock1", "line1", engine="openai")
            self.assertEqual((engine, path.suffix), ("say", ".wav"))
            self.assertEqual(set(voice._TTS_DOWN), {"openai", "tensorx"})
            self.assertEqual(voice.speak("hi", "mock1", "line2", engine="openai")[1], "say")  # failed engines skipped for ten minutes
            self.assertEqual(voice.speak("hi", "mock1", "line3", engine="none"), (None, "none"))
        with self.assertRaises(ValueError):
            voice.speak("hi", "mock1", "line4", engine="bogus")
        with mock.patch.object(voice, "_say_tts", fail):
            self.assertEqual(voice.speak("hi", "mock1", "line5", engine="say"), (None, "none"))

    def test_recordings_reject_unsafe_names(self):
        with self.assertRaises(ValueError):
            voice.recordings_dir("../etc")
        with self.assertRaises(ValueError):
            voice.save_upload("mock1", "bad/name.wav", b"x")
        self.assertTrue(voice.save_upload("mock1", "ok.wav", b"x").exists())


if __name__ == "__main__":
    unittest.main()
