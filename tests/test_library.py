import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from nailit import cli, library

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"


class LibraryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        shutil.copytree(EXAMPLE, self.tmp / "NailIt")
        self.root = self.tmp / "NailIt"
        self.lib = self.root / "library"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def edit_yaml(self, name, change):
        path = self.lib / name
        data = yaml.safe_load(path.read_text())
        change(data)
        path.write_text(yaml.safe_dump(data, sort_keys=False))

    def errors(self):
        with self.assertRaises(library.LibraryError) as ctx:
            library.load_library(self.lib)
        return ctx.exception.errors

    def test_example_library_and_me_are_valid(self):
        lib = library.load_library(self.lib)
        self.assertEqual([r["id"] for r in lib["rubric"]["rules"]], ["R1.1", "R1.2", "R2.1", "R5.1"])
        self.assertEqual(lib["rubric"]["rules"][1]["src"], ["D01", "D02"])
        self.assertIn("3 questions, 1 candidate questions", library.summary(lib))
        me = library.load_me(self.root)
        self.assertEqual(me["stories"]["facts"]["F2"]["status"], "approximate")
        self.assertEqual(me["stories"]["stories"][0]["id"], "S1")
        self.assertEqual(library.people_map(self.root)["Alex Sample"], "my engineering manager")
        self.assertEqual(set(me["tmay"]["versions"]), {"lift", "short", "classic", "interview"})

    def test_root_folder_is_accepted(self):
        self.assertIn("rubric rules", library.summary(library.load_library(self.root)))

    def test_unknown_cross_references_are_reported(self):
        self.edit_yaml("detectors.yaml", lambda d: d["structure_checks"][0].update(rubric_rule="R8.9"))
        self.edit_yaml("personas.yaml", lambda d: (d["companies"][0]["followup_banks"].append("nope"),
                                                   d["rounds"][0]["flow"].append("missing_question")))
        self.edit_yaml("followups.yaml", lambda d: d["banks"][2].update(trigger="company:ghost"))
        self.edit_yaml("programmes/14day.yaml", lambda d: (d["schedule"][0]["drills"].append("ghost_drill"),
                                                           d["schedule"][1]["questions"].extend(["round:ghost", "mode:D", "zzz"])))
        errors = "\n".join(self.errors())
        for expected in ("unknown rubric rule R8.9", "unknown followup bank nope", "unknown question or round missing_question",
                         "unknown company in trigger company:ghost", "unknown drill ghost_drill",
                         "unknown question entry round:ghost", "unknown question entry mode:D", "unknown question entry zzz"):
            self.assertIn(expected, errors)

    def test_schema_errors_are_reported(self):
        self.edit_yaml("detectors.yaml", lambda d: (d["measured_detectors"][0].update(metric="made_up_metric"),
                                                    d["phrase_detectors"][0].pop("patterns")))
        self.edit_yaml("questions.yaml", lambda d: d["questions"][0].update(type="riddle"))
        errors = "\n".join(self.errors())
        self.assertIn("'made_up_metric' is not one of", errors)
        self.assertIn("'patterns' is a required property", errors)
        self.assertIn("'riddle' is not one of", errors)

    def test_duplicate_ids_and_unbold_rubric_rules(self):
        self.edit_yaml("phrases.yaml", lambda d: d["joining"][0].update(id="buy_time"))
        (self.lib / "rubric.md").write_text("**R1.1** Result first.\nR1.2 Not bold.\n")
        errors = "\n".join(self.errors())
        self.assertIn("line 2: rule ID must be bold", errors)
        (self.lib / "rubric.md").write_text("**R1.1** Result first.\n**R1.1** Again.\n**R2.1** x\n**R5.1** y\n")
        self.assertIn("rubric.md: duplicate id R1.1", "\n".join(self.errors()))

    def test_bare_question_list_is_accepted(self):
        self.edit_yaml("questions.yaml", lambda d: (d.clear(), None))
        path = self.lib / "questions.yaml"
        data = yaml.safe_load((EXAMPLE / "library" / "questions.yaml").read_text())["questions"]
        path.write_text(yaml.safe_dump(data))
        library.load_library(self.lib)

    def test_stories_errors(self):
        stories = self.root / "me" / "stories.md"
        text = stories.read_text().replace("facts: [F1, F2, F3]", "facts: [F1, F7]").replace("F3 | Team of 4 engineers | confirmed", "F3 | Team | maybe")
        stories.write_text(text.replace("plot_type:", "fallback_story: S9\nplot_type:"))
        with self.assertRaises(library.LibraryError) as ctx:
            library.load_me(self.root)
        errors = "\n".join(ctx.exception.errors)
        self.assertIn("malformed fact line: F3 | Team | maybe", errors)
        self.assertIn("S1 references unknown fact F7", errors)
        self.assertIn("S1 references unknown fact F3", errors)
        self.assertIn("fallback_story S9 does not exist", errors)

    def test_check_library_cli_exit_codes(self):
        self.assertEqual(cli.main(["check-library", str(self.lib)]), 0)
        (self.lib / "personas.yaml").unlink()
        self.assertEqual(cli.main(["check-library", str(self.lib)]), 1)


if __name__ == "__main__":
    unittest.main()
