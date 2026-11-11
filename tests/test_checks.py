"""N4c: structure checks (one mocked LLM call per answer) and consistency checks (E8), synthetic only."""
import unittest
from pathlib import Path

from nailit import library
from nailit.measure import consistency, structure

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"


def _ids(hits):
    return [h["id"] for h in hits]


class StructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = library.load_library(EXAMPLE / "library")

    def test_one_call_with_applicable_rubric_rules(self):
        calls = []

        def ask(prompt, **_):
            calls.append(prompt)
            return {"checks": {"result_first": {"pass": False, "reason": "Opens with context."},
                               "trade_off_named": {"pass": True, "reason": "Names the patch option."}}}

        hits = structure.check(self.lib, "The old queue was slow. I migrated it.", "behavioural", ask=ask)
        self.assertEqual(len(calls), 1)
        self.assertIn("Lead with the result in the first sentence.", calls[0])
        self.assertIn("R2.1", calls[0])
        self.assertEqual([(h["id"], h["rubric_rule"], h["severity"]) for h in hits], [("result_first", "R1.1", "fail")])

    def test_applies_to_filters_and_skips_the_call(self):
        prompts = []
        structure.check(self.lib, "I want this role.", "motivation", ask=lambda p, **_: prompts.append(p) or {})
        self.assertNotIn("trade_off_named", prompts[0])
        self.lib_without = {**self.lib, "detectors": {**self.lib["detectors"], "structure_checks": []}}
        self.assertEqual(structure.check(self.lib_without, "x", "behavioural", ask=lambda *a, **k: 1 / 0), [])

    def test_applies_to_is_optional(self):
        checks = [{"id": "c", "label": "C", "rubric_rule": "R1.1", "severity": "warn"}]
        self.assertEqual(structure.applicable(checks, "behavioural"), checks)

    def test_missing_or_malformed_verdicts_are_not_failures(self):
        self.assertEqual(structure.check(self.lib, "x", "behavioural", ask=lambda p, **_: {"checks": "?"}), [])


class E8ConsistencyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.me = library.load_me(EXAMPLE)
        cls.lib = library.load_library(EXAMPLE / "library")

    def test_conflicting_team_sizes_across_answers(self):
        answers = [{"text": "I led a team of 4 engineers through the migration."},
                   {"text": "With my team of 6, I owned the launch."}]
        hits = consistency.check(answers, self.me, self.lib)
        conflict = next(h for h in hits if h["id"] == "conflicting_numbers")
        self.assertEqual((conflict["thing"], conflict["label"]), ("team", "Team size changed between answers"))
        self.assertIn("number_not_in_facts", _ids(hits))  # 6 is in no fact

    def test_before_and_after_numbers_do_not_conflict(self):
        answers = [{"text": "Failed payments went from about 9 to 3 per week."},
                   {"text": "We ended at 3 per week, with a team of 4."}]
        self.assertNotIn("conflicting_numbers", _ids(consistency.check(answers, self.me)))

    def test_numbers_vs_fact_status(self):
        hits = consistency.check([{"text": "My team of 4 cut failures to 3 a week, and cost fell 40 percent."}], self.me)
        by_number = {h["number"]: h["id"] for h in hits if "number" in h}
        self.assertEqual(by_number, {3.0: "unconfirmed_fact", 40.0: "number_not_in_facts"})

    def test_cv_number_missing_from_stories(self):
        hits = consistency.check([], self.me, cv_text="Grew the platform team to 12 engineers. Team of 4 on billing.")
        missing = [h for h in hits if h["id"] == "cv_number_missing"]
        self.assertEqual([(h["number"], h["thing"]) for h in missing], [(12.0, "engineer")])

    def test_years_ignored_and_story_reuse(self):
        hits = consistency.check([{"text": "In 2021 I joined."}], self.me, stories_used={"S1": ["q1", "q2"], "S2": ["q3"]})
        self.assertEqual(_ids(hits), ["story_reused"])

    def test_library_warnings_for_unknown_ids(self):
        self.assertEqual(consistency.library_warnings(self.lib["detectors"]), [])
        warn = consistency.library_warnings({"consistency_checks": [{"id": "made_up"}]})
        self.assertEqual(len(warn), 1)


if __name__ == "__main__":
    unittest.main()
