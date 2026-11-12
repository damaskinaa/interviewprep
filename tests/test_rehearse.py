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
        reply = {"on_topic": True, "rules": {"R1.1": {"verdict": "pass", "evidence": "I run delivery"},
                                              "R1.11": {"verdict": "pass", "evidence": "I run delivery"}},
                 "moves_hit": ["Opens with the result"], "moves_missed": ["Gives a number"],
                 "one_fix": "Say the number.", "best_line": "I run delivery."}
        with mock.patch("nailit.answers.ai.chat", return_value=reply):
            result = self.client.post("/rehearse/attempt_text", json={"card_id": "tmay", "text": "I run delivery, we like it. " * 6}).json()
        self.assertEqual((result["quality"], result["fidelity"], result["score"]), (10.0, 5.0, 8))
        self.assertEqual(result["delivery"]["we"], 6)
        self.assertEqual([r["verdict"] for r in result["rules"]], ["pass", "pass"])
        self.assertEqual(result["moves"], DECK["cards"][0]["moves"])
        progress = self.client.get("/rehearse/progress").json()
        self.assertEqual((progress["attempts"], progress["mastered"]), (1, 1))

    def test_unknown_card_is_404(self):
        self.assertEqual(self.client.post("/rehearse/attempt_text", json={"card_id": "nope", "text": "x"}).status_code, 404)

    REPLY = {"on_topic": True, "rules": {"R1.1": {"verdict": "pass", "evidence": "I run delivery"},
                                          "R1.11": {"verdict": "pass", "evidence": "I run delivery"}}}

    def timed(self, words, seconds):
        with mock.patch("nailit.answers.ai.chat", return_value=self.REPLY):
            return self.client.post("/rehearse/attempt_text", json={"card_id": "tmay", "text": "I run delivery well. " * (words // 4),
                                                                   "seconds": seconds})

    def test_typed_timing_is_kept_only_at_a_speaking_pace(self):
        self.assertEqual(self.timed(120, 60).json()["delivery"]["wpm"], 120)    # normal pace: kept
        self.assertEqual(self.timed(120, 120).json()["delivery"]["wpm"], 60)    # 60 wpm: lower edge kept
        self.assertEqual(self.timed(260, 60).json()["delivery"]["wpm"], 260)    # 260 wpm: upper edge kept
        self.assertIsNone(self.timed(120, 600).json()["delivery"]["seconds"])   # 12 wpm: a pause in dictation
        self.assertIsNone(self.timed(400, 60).json()["delivery"]["seconds"])    # 400 wpm: pasted, not spoken
        self.assertEqual(self.timed(120, 0.5).status_code, 422)
        self.assertEqual(self.timed(120, 1801).status_code, 422)

    def test_duplicate_deck_ids_are_made_unique(self):
        cards = [{**DECK["cards"][0], "id": "a"}, {**DECK["cards"][0], "id": "a"}, {**DECK["cards"][0], "id": "a_2"},
                 {**DECK["cards"][0], "id": "a"}]
        (self.tmp / "library" / "model_level" / "deck.json").write_text(json.dumps({"cards": cards}))
        ids = [c["id"] for c in rehearse.load_deck()["cards"]]
        self.assertEqual(len(set(ids)), 4, ids)
        self.assertEqual(ids[0], "a")

    def test_concurrent_progress_appends_never_interleave(self):
        import threading
        big = "x" * 20000  # bigger than the file buffer, so an unlocked write could be split
        threads = [threading.Thread(target=rehearse.append_progress, args=([{"card_id": f"c{n}", "score": n, "pad": big}],))
                   for n in range(24)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        rows = rehearse.history()
        self.assertEqual(sorted(r["score"] for r in rows), list(range(24)))


if __name__ == "__main__":
    unittest.main()
