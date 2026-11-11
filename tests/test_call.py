import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit import api, llm

DECK = {"cards": [{"id": "tmay", "question": "Tell me about yourself", "answer": "x", "competency": "tmay", "frequency": 9},
                  {"id": "why_amazon", "question": "Why Amazon?", "answer": "x", "competency": "why_company", "company": "amazon"},
                  {"id": "why_google", "question": "Why Google?", "answer": "x", "competency": "why_company", "company": "google"},
                  {"id": "fail", "question": "Tell me about a time you failed.", "answer": "x", "competency": "failure",
                   "amazon": ["Ownership"], "frequency": 5}]}
LIB = {"personas": {"companies": [{"id": "amazon", "name": "Amazon", "probing_style": "What did YOU do?", "values": ["Ownership"]}],
                    "rounds": [{"id": "behavioural", "label": "Behavioural round"}]}}


class CallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "library" / "model_level").mkdir(parents=True)
        (self.tmp / "library" / "model_level" / "deck.json").write_text(json.dumps(DECK))
        for patcher in (mock.patch("nailit.library.home", return_value=self.tmp),
                        mock.patch("nailit.library.load_library", return_value=LIB),
                        mock.patch.dict("os.environ", {"NAILIT_PROVIDER": ""})):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(api.app)

    def test_pack_uses_the_company_card_and_asks_for_a_transcript(self):
        pack = self.client.get("/call/pack?company=amazon&n=5").json()
        self.assertEqual(pack["questions"][:2], ["Tell me about yourself", "Why Amazon?"])
        self.assertNotIn("Why Google?", pack["questions"])
        self.assertIn("What did YOU do?", pack["brief"])
        self.assertIn("CANDIDATE:", pack["brief"])

    def test_engine_choice_is_saved_and_refused_when_not_set_up(self):
        with mock.patch.dict("os.environ", {"TENSORX_API_KEY": "k", "LUA_API_KEY": "", "LUA_AGENT_ID": ""}):
            self.assertEqual(self.client.post("/settings", json={"engine": "lua"}).status_code, 409)
            self.assertEqual(self.client.post("/settings", json={"engine": "tensorx"}).json()["engine"], "tensorx")
        with mock.patch.dict("os.environ", {"LUA_API_KEY": "k", "LUA_AGENT_ID": "a"}):
            self.assertEqual(self.client.post("/settings", json={"engine": "lua"}).json()["engine"], "lua")
            self.assertEqual(llm.provider(), "lua")

    def test_lua_engine_sends_the_prompt_as_one_stateless_turn(self):
        reply = mock.Mock(status_code=201, headers={"content-type": "application/json"}, json=lambda: {"text": "Tell me more."})
        with mock.patch.dict("os.environ", {"NAILIT_PROVIDER": "lua", "LUA_API_KEY": "k", "LUA_AGENT_ID": "agent1"}), \
                mock.patch("httpx.post", return_value=reply) as post:
            self.assertEqual(llm.ask_llm("Ask a question", retries=1), "Tell me more.")
        self.assertIn("/chat/generate/agent1", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["json"]["messages"][0]["text"], "Ask a question")

    def test_transcript_is_split_and_scored(self):
        split = {"items": [{"question": "Tell me about a time you failed.", "answer": "I missed a date. " * 12, "competency": "failure"}]}
        scored = {"score": 6, "quality": 6.0, "fidelity": None, "rules": [{"id": "R1.1", "name": "Answer first", "verdict": "fail", "evidence": ""}],
                  "verdict": "Lean No Hire", "one_fix": "Lead with the result.", "best_line": "", "moves_hit": [], "moves_missed": [], "on_topic": True}
        with mock.patch("nailit.answers.ai.chat", return_value=split), mock.patch("nailit.scoring.score", return_value=scored):
            out = self.client.post("/call/import", json={"text": "INTERVIEWER: Tell me about a time you failed.\nCANDIDATE: I missed a date."}).json()
        self.assertEqual((out["overall"], out["count"], out["repeat_misses"][0][0]), (6.0, 1, "Answer first"))


if __name__ == "__main__":
    unittest.main()
