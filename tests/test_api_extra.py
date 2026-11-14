"""API routes the journey tests do not reach: module jobs, coach, mock errors, debrief, voice errors, video and audio."""
import importlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit.interview import voice

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"


class ApiExtraTest(unittest.TestCase):
    def setUp(self):
        voice._TTS_DOWN.clear()
        self.api = importlib.import_module("nailit.api")
        self.store = importlib.import_module("nailit.store")
        self.tmp = Path(tempfile.mkdtemp())
        self.cwd = os.getcwd()
        os.chdir(self.tmp)  # module jobs read and write ./jobs
        patches = [mock.patch.object(self.store, "DB_PATH", self.tmp / "t.db"),
                   mock.patch.dict(os.environ, {"NAILIT_HOME": str(EXAMPLE), "NAILIT_RECORDINGS": str(self.tmp / "rec")})]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(os.chdir, self.cwd)
        self.client = TestClient(self.api.app)
        self.addCleanup(self.client.close)

    def session(self):
        return self.client.post("/session/create", json={"company_name": "Acme", "role_name": "SDM", "job_description": "jd", "cv": "cv"}).json()["session_id"]

    def mock_id(self, round_id="behavioural"):
        return self.client.post("/interview/start", json={"round_id": round_id}).json()["mock_id"]

    # ---- module jobs, answers, coach ----
    def test_startup_marks_leftover_jobs_failed(self):
        self.store.create_job("old", {})
        with TestClient(self.api.app):  # entering the client runs the startup hook
            pass
        self.assertEqual(self.store.get_job("old")["status"], "failed")

    def test_a_module_job_runs_to_done_or_failed(self):
        sid = self.session()
        job_id, _ = self.store.get_or_create_job(sid, "role_intelligence", "j1")
        with mock.patch.object(self.api, "run_session_module", return_value={"stage": "ok", "markdown": "m", "product_json": {"a": 1}, "output_file": "f"}):
            self.api._run_module_job(job_id, sid, "role_intelligence")
        self.assertEqual((self.store.get_job(job_id)["status"], self.store.get_job(job_id)["output_file"]), ("done", "f"))
        job2, _ = self.store.get_or_create_job(sid, "company_intelligence", "j2")
        with mock.patch.object(self.api, "run_session_module", side_effect=RuntimeError("model down")):
            self.api._run_module_job(job2, sid, "company_intelligence")
        self.assertIn("model down", self.store.get_job(job2)["error"])

    def test_running_a_module_creates_one_job_and_dispatches_it(self):
        sid = self.session()
        with mock.patch.object(self.api, "dispatch_job") as dispatch:
            first = self.client.post("/module/run", json={"session_id": sid, "module_name": "role_intelligence"}).json()
            again = self.client.post("/module/run", json={"session_id": sid, "module_name": "role_intelligence"}).json()
        self.assertEqual(first["job_id"], again["job_id"])
        self.assertEqual(dispatch.call_count, 1)
        self.assertEqual(self.client.get("/module/status", params={"job_id": first["job_id"]}).status_code, 200)
        self.assertEqual(self.client.get("/module/status", params={"job_id": "nope"}).status_code, 404)

    def test_dispatch_starts_a_daemon_thread(self):
        ran = []
        with mock.patch.object(self.api.threading, "Thread") as thread:
            self.api.dispatch_job(ran.append, 1)
        self.assertTrue(thread.return_value.start.called)

    def test_answer_options_errors_map_to_400_and_500(self):
        sid = self.session()
        body = {"session_id": sid, "question": "Q?"}
        self.assertEqual(self.client.post("/answers/generate", json=body).status_code, 400)  # no candidate profile yet
        with mock.patch.object(self.api, "generate_answer_options", side_effect=RuntimeError("boom")):
            self.assertEqual(self.client.post("/answers/generate", json=body).status_code, 500)
        with mock.patch.object(self.api, "generate_answer_options", return_value={"answers": []}):
            self.assertEqual(self.client.post("/answers/generate", json=body).json(), {"answers": []})

    def test_the_lua_coach_route_validates_the_session(self):
        self.assertEqual(self.client.post("/lua-coach", json={}).status_code, 400)
        self.assertEqual(self.client.post("/lua-coach", json={"session_id": "nope"}).status_code, 404)
        sid = self.session()
        with mock.patch.object(self.api, "build_lua_coach_response", return_value={"status": "coaching", "score_out_of_10": 8}):
            out = self.client.post("/lua-coach", json={"session_id": sid, "question": "Q?", "candidate_answer": "A"}).json()
        self.assertEqual(out["structure_score"], 8)

    # ---- mock interview ----
    def test_options_start_and_answer_errors(self):
        options = self.client.get("/interview/options").json()
        self.assertTrue(options["rounds"] and options["modes"])
        self.assertEqual(self.client.post("/interview/start", json={"round_id": "no_such_round"}).status_code, 400)
        with mock.patch.object(self.api.interviewer, "start_mock", side_effect=PermissionError("locked")):
            self.assertEqual(self.client.post("/interview/start", json={"round_id": "behavioural", "mode": "C"}).status_code, 403)
        self.assertEqual(self.client.post("/interview/answer", json={"mock_id": "nope", "text": "hi"}).status_code, 404)
        self.assertEqual(self.client.get("/interview/get", params={"mock_id": "nope"}).status_code, 404)
        self.assertEqual(self.client.post("/interview/end", json={"mock_id": "nope"}).status_code, 404)
        mid = self.mock_id()
        with mock.patch.object(self.api.interviewer, "answer", side_effect=ValueError("finished")):
            self.assertEqual(self.client.post("/interview/answer", json={"mock_id": mid, "text": "hi"}).status_code, 409)
        self.assertIn("turns", self.client.get("/interview/get", params={"mock_id": mid}).json())

    def test_invalid_library_is_reported_as_a_server_error(self):
        with mock.patch.object(self.api.library, "load_library", side_effect=self.api.library.LibraryError(["bad file"])):
            response = self.client.get("/interview/options")
        self.assertEqual(response.status_code, 500)

    def test_ending_a_mock_twice_returns_the_summary(self):
        mid = self.mock_id()
        with mock.patch.object(self.api.interviewer, "ask_llm", return_value="ok"):
            first = self.client.post("/interview/end", json={"mock_id": mid}).json()
            second = self.client.post("/interview/end", json={"mock_id": mid}).json()
        self.assertEqual((first["phase"], second["phase"]), ("done", "done"))

    def test_pairs_group_answers_under_their_questions(self):
        state = {"turns": [{"role": "interviewer", "kind": "question", "question_id": "q1", "say": "Q one?", "question_text": "Q one text?"},
                           {"role": "candidate", "say": "answer a"}, {"role": "interviewer", "kind": "followup", "say": "why?"},
                           {"role": "candidate", "say": "answer b"}, {"role": "interviewer", "kind": "question", "question_id": "q2", "say": "Q two?"},
                           {"role": "interviewer", "kind": "closing", "say": "bye"}, {"role": "candidate", "say": "late"}]}
        pairs = self.api.mock_pairs(state)
        self.assertEqual(len(pairs), 1)
        self.assertEqual((pairs[0]["question"], pairs[0]["followups"], pairs[0]["answers"]), ("Q one text?", ["why?"], ["answer a", "answer b"]))

    def test_debrief_scores_once_logs_progress_and_caches(self):
        mid = self.mock_id()
        state = self.store.load_mock(mid)
        state["phase"] = "done"
        state["turns"] = [{"role": "interviewer", "kind": "question", "question_id": "q1", "say": "Tell me about a failure."},
                          {"role": "candidate", "say": "I missed a deadline and fixed the process afterwards."},
                          {"role": "interviewer", "kind": "question", "question_id": "q2", "say": "Why us?"},
                          {"role": "candidate", "say": "Because of the scale."}]
        self.store.save_mock(state)
        results = iter([{"score": 9, "quality": 9.0, "verdict": "Hire", "rules": [{"id": "R1", "name": "Answer first", "verdict": "fail"}]},
                        RuntimeError("scorer down")])

        def fake_score(card, text, level=2):
            value = next(results)
            if isinstance(value, Exception):
                raise value
            return value
        with mock.patch("nailit.scoring.score", side_effect=fake_score), mock.patch("nailit.rehearse.append_progress") as progress:
            debrief = self.client.get("/interview/debrief", params={"mock_id": mid}).json()
            cached = self.client.get("/interview/debrief", params={"mock_id": mid}).json()
        self.assertEqual((debrief["overall"], debrief["verdict"], debrief["count"]), (9.0, "Strong Hire", 1))
        self.assertEqual(debrief["repeat_misses"], [["Answer first", 1]])
        self.assertTrue(any("error" in a for a in debrief["answers"]))
        self.assertEqual(cached, debrief)
        self.assertEqual(progress.call_count, 1)
        self.assertEqual(self.client.get("/interview/debrief", params={"mock_id": "nope"}).status_code, 404)

    def test_debrief_verdict_bands_and_unfinished_mocks(self):
        mid = self.mock_id()
        state = self.store.load_mock(mid)
        state["turns"] = [{"role": "interviewer", "kind": "question", "question_id": "q1", "say": "Q?"}, {"role": "candidate", "say": "an answer"}]
        self.store.save_mock(state)
        with mock.patch("nailit.scoring.score", return_value={"score": 4, "quality": 4.0, "verdict": "No Hire", "rules": []}):
            debrief = self.client.get("/interview/debrief", params={"mock_id": mid}).json()
        self.assertEqual(debrief["verdict"], "No Hire")
        self.assertNotIn("debrief", self.store.load_mock(mid))  # an unfinished mock is not recorded
        empty = self.mock_id()
        self.assertIsNone(self.client.get("/interview/debrief", params={"mock_id": empty}).json()["overall"])

    # ---- voice ----
    def test_preview_errors_map_to_status_codes(self):
        mid = self.mock_id()
        upload = {"audio": ("a.webm", b"x", "audio/webm")}
        with mock.patch.object(self.api.voice, "live_update", side_effect=voice.VoiceUnavailable("no whisper")):
            self.assertEqual(self.client.post("/voice/preview", data={"mock_id": mid}, files=upload).status_code, 503)
        with mock.patch.object(self.api.voice, "live_update", side_effect=ValueError("bad")):
            self.assertEqual(self.client.post("/voice/preview", data={"mock_id": mid}, files=upload).status_code, 400)
        with mock.patch.object(self.api.voice, "live_update", side_effect=RuntimeError("cut mid-frame")):
            self.assertEqual(self.client.post("/voice/preview", data={"mock_id": mid}, files=upload).json(), {"text": ""})
        with mock.patch.object(self.api.voice, "live_update", return_value="partial words"):
            self.assertEqual(self.client.post("/voice/preview", data={"mock_id": mid}, files=upload).json(), {"text": "partial words"})

    def test_saying_a_line_needs_a_mock_and_a_known_engine(self):
        self.assertEqual(self.client.post("/voice/say", json={"mock_id": "nope"}).status_code, 404)
        mid = self.mock_id()
        self.assertEqual(self.client.post("/voice/say", json={"mock_id": mid, "engine": "bogus"}).status_code, 400)
        self.assertIsNone(self.client.post("/voice/say", json={"mock_id": mid, "engine": "none"}).json()["audio_url"])

    def test_spoken_answers_report_each_failure_separately(self):
        upload = {"audio": ("answer.wav", b"x", "audio/wav")}
        self.assertEqual(self.client.post("/voice/answer", data={"mock_id": "m", "engine": "bogus"}, files=upload).status_code, 400)
        self.assertEqual(self.client.post("/voice/answer", data={"mock_id": "nope"}, files=upload).status_code, 404)
        mid = self.mock_id()
        with mock.patch.object(self.api.voice, "transcribe", side_effect=voice.VoiceUnavailable("no whisper")):
            self.assertEqual(self.client.post("/voice/answer", data={"mock_id": mid}, files=upload).status_code, 503)
        with mock.patch.object(self.api.voice, "transcribe", side_effect=ValueError("bad")):
            self.assertEqual(self.client.post("/voice/answer", data={"mock_id": mid}, files=upload).status_code, 400)
        silent = {"text": "", "first_word_s": None, "speech_s": 0, "words": [], "filled_pauses": 0}
        with mock.patch.object(self.api.voice, "transcribe", return_value=silent):
            self.assertEqual(self.client.post("/voice/answer", data={"mock_id": mid}, files=upload).status_code, 422)
        heard = {"text": "I led it", "first_word_s": 0.5, "speech_s": 2.0, "words": [], "filled_pauses": 0}
        with mock.patch.object(self.api.voice, "transcribe", return_value=heard), \
                mock.patch.object(self.api.interviewer, "answer", side_effect=ValueError("not your turn")):
            self.assertEqual(self.client.post("/voice/answer", data={"mock_id": mid}, files=upload).status_code, 409)

    def test_latency_rows_without_measurements_have_no_median(self):
        self.assertEqual(self.client.get("/voice/latency").json(), {"rows": [], "median_s": None})

    def test_webcam_chunks_are_appended_until_the_size_limit(self):
        self.assertEqual(self.client.post("/voice/video", data={"mock_id": "nope"}, files={"video": ("v.webm", b"x", "video/webm")}).status_code, 404)
        mid = self.mock_id()
        for _ in range(2):
            self.assertEqual(self.client.post("/voice/video", data={"mock_id": mid}, files={"video": ("v.webm", b"chunk", "video/webm")}).status_code, 200)
        self.assertEqual((self.tmp / "rec" / mid / "webcam.webm").read_bytes(), b"chunkchunk")
        with mock.patch.object(self.api, "MAX_VIDEO", 4):
            self.assertEqual(self.client.post("/voice/video", data={"mock_id": mid}, files={"video": ("v.webm", b"chunk", "video/webm")}).status_code, 413)

    def test_audio_files_are_served_only_from_safe_paths(self):
        mid = self.mock_id()
        voice.save_upload(mid, "line.mp3", b"mp3")
        self.assertEqual(self.client.get(f"/voice/audio/{mid}/line.mp3").content, b"mp3")
        self.assertEqual(self.client.get(f"/voice/audio/{mid}/missing.mp3").status_code, 404)
        self.assertEqual(self.client.get(f"/voice/audio/{mid}/a..b.mp3").status_code, 400)


if __name__ == "__main__":
    unittest.main()
