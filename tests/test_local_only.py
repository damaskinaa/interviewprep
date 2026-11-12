"""The request guard, upload caps and file-name checks. Synthetic data only."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit import api
from nailit.interview import voice


class HostnameTest(unittest.TestCase):
    def test_parsing(self):
        cases = {"127.0.0.1": "127.0.0.1", "localhost:8000": "localhost", "LOCALHOST": "localhost", "[::1]:8000": "::1",
                 "[::1]": "::1", "http://[::1]:3000": "::1", "http://localhost:3000": "localhost", "": None, None: None,
                 "localhost:abc": None, "[::1]evil": None, "localhost@evil.example": None, "localhost/x": None,
                 "127.0.0.1.evil.example": "127.0.0.1.evil.example", "null": "null", "http://user@localhost": None}
        for value, want in cases.items():
            with self.subTest(value):
                self.assertEqual(api._hostname(value), want)


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def status(self, method="get", path="/health", **kw):
        return getattr(self.client, method)(path, **kw).status_code

    def test_loopback_names_and_ipv6_are_served(self):
        for host in ("127.0.0.1:8000", "localhost", "[::1]:8000", "LocalHost:8000"):
            with self.subTest(host):
                self.assertEqual(self.status(headers={"host": host}), 200)

    def test_other_and_malformed_hosts_are_refused(self):
        for host in ("evil.example", "127.0.0.1.evil.example", "[::1]evil", "localhost:abc", "localhost@evil.example",
                     "0.0.0.0", "[::ffff:7f00:1]", "", "192.168.1.5:8000"):
            with self.subTest(host):
                self.assertEqual(self.status(headers={"host": host}), 403)

    def test_testserver_only_while_pytest_runs(self):
        with mock.patch.dict("os.environ", {"PYTEST_CURRENT_TEST": ""}):
            self.assertEqual(self.status(), 403)

    def test_cross_site_writes_are_refused(self):
        post = lambda headers: self.status("post", "/voice/latency", json={"mock_id": "m", "turn": 0, "latency_s": 1},
                                           headers=headers)
        self.assertEqual(post({"origin": "https://evil.example"}), 403)
        self.assertEqual(post({"origin": "null"}), 403)  # sandboxed iframes and file:// pages
        self.assertEqual(post({"origin": "http://localhost.evil.example:3000"}), 403)
        self.assertEqual(post({"origin": ""}), 403)
        self.assertEqual(post({"sec-fetch-site": "cross-site"}), 403)
        self.assertNotEqual(post({"origin": "http://[::1]:3000"}), 403)
        self.assertNotEqual(post({"origin": "http://localhost:3000", "sec-fetch-site": "same-site"}), 403)
        self.assertNotEqual(post({}), 403)  # curl and scripts on this Mac send no Origin

    def test_declared_and_chunked_bodies_are_capped(self):
        with mock.patch.object(api, "MAX_UPLOAD", 1000):
            self.assertEqual(self.status("post", "/rehearse/attempt_text", content=b"{}", headers={"content-length": "1001"}), 413)
            self.assertEqual(self.status("post", "/rehearse/attempt_text", content=b"{}", headers={"content-length": "-1"}), 413)
            chunks = (b"x" * 400 for _ in range(4))  # a generator body is sent chunked, with no Content-Length
            reply = self.client.post("/rehearse/attempt_text", content=chunks, headers={"content-type": "application/json"})
            self.assertEqual(reply.status_code, 413)
            files = {"audio": ("a.webm", b"x" * 3000, "audio/webm")}
            for path in ("/rehearse/attempt", "/voice/answer", "/voice/preview", "/voice/video"):
                with self.subTest(path):
                    field = "video" if path == "/voice/video" else "audio"
                    reply = self.client.post(path, data={"mock_id": "m1", "card_id": "c"}, files={field: files["audio"]})
                    self.assertEqual(reply.status_code, 413)


class PathTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        patcher = mock.patch.dict("os.environ", {"NAILIT_RECORDINGS": str(self.root / "rec")})
        patcher.start()
        self.addCleanup(patcher.stop)
        (self.root / "secret.txt").write_text("not for the browser")
        self.client = TestClient(api.app)

    def test_safe_name_rejects_traversal_and_newlines(self):
        for bad in ("..", ".hidden", "../x", "a/b", "a\\b", "x\n", "", "a" * 200, "%2e%2e"):
            with self.subTest(bad):
                self.assertIsNone(voice.SAFE_NAME.match(bad))
        self.assertTrue(voice.SAFE_NAME.match("answer_001.webm"))

    def test_recordings_dir_and_save_upload_stay_inside_the_root(self):
        for bad in ("..", "../rec2", "x\n", "/tmp"):
            with self.subTest(bad), self.assertRaises(ValueError):
                voice.recordings_dir(bad)
        for bad in ("../secret.txt", "..", "x\n.webm"):
            with self.subTest(bad), self.assertRaises(ValueError):
                voice.save_upload("m1", bad, b"x")
        saved = voice.save_upload("m1", "answer_000.webm", b"x")
        self.assertEqual(saved.parent, self.root / "rec" / "m1")

    def test_audio_routes_do_not_serve_files_outside_recordings(self):
        voice.save_upload("rehearse", "ok.mp3", b"ID3")
        voice.save_upload("m1", "ok.mp3", b"ID3")
        self.assertEqual(self.client.get("/rehearse/audio/ok.mp3").status_code, 200)
        self.assertEqual(self.client.get("/voice/audio/m1/ok.mp3").status_code, 200)
        for url in ("/rehearse/audio/..%2F..%2Fsecret.txt", "/rehearse/audio/%2e%2e", "/rehearse/audio/ok.mp3%0A",
                    "/voice/audio/..%2F..%2F/secret.txt", "/voice/audio/m1/..%2F..%2Fsecret.txt", "/voice/audio/%2e%2e/secret.txt",
                    "/voice/audio/m1%0A/ok.mp3"):
            with self.subTest(url):
                reply = self.client.get(url)
                self.assertIn(reply.status_code, (400, 404))
                self.assertNotIn(b"not for the browser", reply.content)

    def test_webcam_file_is_capped_across_chunks(self):
        with mock.patch.object(api, "load_mock", return_value={"id": "m1"}), mock.patch.object(api, "MAX_VIDEO", 20):
            send = lambda: self.client.post("/voice/video", data={"mock_id": "m1"}, files={"video": ("v.webm", b"x" * 8, "video/webm")})
            self.assertEqual(send().status_code, 200)
            self.assertEqual(send().status_code, 200)  # 16 bytes: at most the cap
            self.assertEqual(send().status_code, 413)
        self.assertEqual((self.root / "rec" / "m1" / "webcam.webm").stat().st_size, 16)


if __name__ == "__main__":
    unittest.main()


class LogLeakTest(unittest.TestCase):
    def test_failed_say_does_not_log_the_spoken_text(self):
        import subprocess
        secret = "My synthetic story about Project Bluebird"
        tmp = tempfile.mkdtemp()

        def fail(*args, **kwargs):
            raise subprocess.CalledProcessError(1, ["say", "-v", "Daniel", "--", secret])

        with mock.patch.dict("os.environ", {"NAILIT_RECORDINGS": tmp}), mock.patch("subprocess.run", side_effect=fail), \
                mock.patch("shutil.which", return_value="/usr/bin/say"), mock.patch.object(voice.sys, "platform", "darwin"), \
                self.assertLogs("nailit.voice", "WARNING") as logs:
            self.assertEqual(voice.speak(secret, "m1", "line", engine="say"), (None, "none"))
        self.assertTrue(logs.output)
        self.assertNotIn("Bluebird", "\n".join(logs.output))
        timeout = voice._describe(subprocess.TimeoutExpired(["say", "--", secret], 60))
        self.assertEqual(timeout, "say timed out after 60s")


class StoryLogTest(unittest.TestCase):
    def test_broken_stories_file_is_logged_without_the_candidates_lines(self):
        from nailit import library
        from nailit.interview import interviewer
        problem = library.LibraryError(["stories.md: s1/result: 'We grew Project Bluebird revenue' is not of type 'array'",
                                        "stories.md: malformed fact line: synthetic Bluebird fact"])
        with mock.patch.object(library, "load_me", side_effect=problem), self.assertLogs("nailit", "WARNING") as logs:
            self.assertEqual(interviewer._load_me(), {})
        self.assertNotIn("Bluebird", "\n".join(logs.output))
        self.assertIn("2 problem(s) in stories.md", "\n".join(logs.output))
