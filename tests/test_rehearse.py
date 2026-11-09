import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit import api, rehearse

DECK = {"cards": [{"id": "tmay", "question": "Tell me about yourself.", "answer": "I run delivery. Repeat contacts fell a third.",
                   "moves": ["Opens with the result", "Gives a number"], "hook": "I run delivery.", "frequency": 3,
                   "type": "opening", "why_it_won": ["specific"], "practice_only": True}], "built": "today"}


class FakeChoice:
    def __init__(self, content):
        self.message = mock.Mock(content=content)


class RehearseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "library" / "model_level").mkdir(parents=True)
        (self.tmp / "library" / "model_level" / "deck.json").write_text(json.dumps(DECK))
        self.home = mock.patch("nailit.library.home", return_value=self.tmp)
        self.home.start()
        self.client = TestClient(api.app)

    def tearDown(self):
        self.home.stop()

    def test_deck_and_page(self):
        data = self.client.get("/rehearse/deck").json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["cards"][0]["moves"], DECK["cards"][0]["moves"])
        self.assertIn("Rehearse", self.client.get("/rehearse").text)

    def test_typed_attempt_is_scored_and_logged(self):
        reply = json.dumps({"score": 8, "moves_hit": ["Opens with the result"], "moves_missed": ["Gives a number"],
                            "one_fix": "Say the number.", "best_line": "I run delivery.", "verdict": "Hire"})
        fake = mock.Mock()
        fake.chat.completions.create.return_value = mock.Mock(choices=[FakeChoice(reply)])
        with mock.patch("openai.OpenAI", return_value=fake):
            result = self.client.post("/rehearse/attempt_text", json={"card_id": "tmay", "text": "I run delivery, we like it."}).json()
        self.assertEqual(result["score"], 8)
        self.assertEqual(result["delivery"]["we"], 1)
        self.assertEqual(result["moves"], DECK["cards"][0]["moves"])
        progress = self.client.get("/rehearse/progress").json()
        self.assertEqual((progress["attempts"], progress["mastered"]), (1, 1))

    def test_unknown_card_is_404(self):
        self.assertEqual(self.client.post("/rehearse/attempt_text", json={"card_id": "nope", "text": "x"}).status_code, 404)


if __name__ == "__main__":
    unittest.main()
