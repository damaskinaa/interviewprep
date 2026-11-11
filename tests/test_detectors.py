"""N4b detector runner (E7) and measured-rule evaluation, on the synthetic example library."""
import unittest
from pathlib import Path

import yaml

from nailit import library
from nailit.measure import detectors

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "NailIt"
FIXTURES = yaml.safe_load((ROOT / "tests" / "fixtures" / "e7_answers.yaml").read_text())


def _words(text, start=0.0, step=0.4):
    return [{"word": w, "start": round(start + i * step, 2), "end": round(start + i * step + 0.3, 2)}
            for i, w in enumerate(text.split())]


class E7PhraseDetectorsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = library.load_library(EXAMPLE / "library")
        cls.people = library.people_map(EXAMPLE)

    def _ids(self, case, key, timed):
        kwargs = {"words": _words(case[key])} if timed else {"text": case[key]}
        hits = detectors.phrase_hits(self.lib["detectors"]["phrase_detectors"], question_type=case["type"],
                                     people=self.people, **kwargs)
        return {h["id"] for h in hits}

    def test_every_phrase_detector_has_a_fixture(self):
        self.assertEqual({d["id"] for d in self.lib["detectors"]["phrase_detectors"]}, set(FIXTURES))

    def test_raw_answers_trigger_and_polished_answers_do_not(self):
        for detector_id, case in FIXTURES.items():
            for timed in (False, True):
                with self.subTest(detector=detector_id, timed=timed):
                    self.assertIn(detector_id, self._ids(case, "raw", timed))
                    self.assertEqual(self._ids(case, "polished", timed), set())

    def test_scopes_threshold_and_except_context(self):
        phrase = {d["id"]: d for d in self.lib["detectors"]["phrase_detectors"]}
        once = detectors.phrase_hits([phrase["hedge_words"]], text="It was kind of hard.")
        self.assertEqual(once, [], "threshold per_answer: 2")
        late = "I own the roadmap. I ship monthly. Sorry, one more thing: I hire well."
        self.assertEqual(detectors.phrase_hits([phrase["apology_opening"]], text=late), [], "answer_start only")
        with_i = "In the end we decided to cut 20 percent and I wrote the plan."
        self.assertEqual(detectors.phrase_hits([phrase["we_without_i"]], text=with_i), [], "except_context")
        blame = FIXTURES["blame_in_failure"]["raw"]
        self.assertEqual(detectors.phrase_hits([phrase["blame_in_failure"]], text=blame, question_type="behavioural"), [])

    def test_hit_carries_fix_replacement_and_timestamp(self):
        hit = detectors.phrase_hits(self.lib["detectors"]["phrase_detectors"], words=_words(FIXTURES["trailing_off"]["raw"]))
        hit = next(h for h in hit if h["id"] == "trailing_off")
        self.assertEqual(hit["replacement"], "The result was [result].")
        self.assertEqual(hit["matches"][0]["start"], 4.8)


class MeasuredRulesTest(unittest.TestCase):
    def test_rule_forms(self):
        self.assertTrue(detectors.evaluate_rule("> baseline * 1.2", 190, 150))
        self.assertFalse(detectors.evaluate_rule("> baseline * 1.2", 170, 150))
        self.assertTrue(detectors.evaluate_rule("< baseline * 0.7 or > baseline * 1.5", 0.5, 1.0))
        self.assertFalse(detectors.evaluate_rule("< 1 or > 3", 2.0))
        self.assertTrue(detectors.evaluate_rule("value >= 20 and value < 600", 25))
        self.assertIsNone(detectors.evaluate_rule("> baseline * 1.2", 190, None))
        self.assertIsNone(detectors.evaluate_rule("> 120", None))

    def test_unsafe_or_unknown_rules_are_library_errors(self):
        for rule in ("> __import__('os')", "> open", "value", "> 'x'"):
            with self.subTest(rule=rule), self.assertRaises(ValueError):
                detectors.compile_rule(rule)
        errors = detectors.library_errors({"measured_detectors": [
            {"id": "a", "metric": "made_up_metric", "rule": "> 1"}, {"id": "b", "metric": "answer_seconds", "rule": "> x"}]})
        self.assertEqual(len(errors), 2)

    def test_run_flags_measured_detectors(self):
        lib = library.load_library(EXAMPLE / "library")
        words = _words(" ".join(["word"] * 330), step=0.4)  # 132 s, no pause > 0.5 s
        result = detectors.run(lib, words=words, question_type="behavioural", pre_answer_silence_s=4.2,
                               baseline={"wpm": 120})
        hit_ids = {h["id"] for h in result["hits"]}
        self.assertTrue({"long_answer", "thinking_pause", "rush", "too_fast"} <= hit_ids, hit_ids)
        self.assertNotIn("flat_or_frantic", hit_ids)


if __name__ == "__main__":
    unittest.main()
