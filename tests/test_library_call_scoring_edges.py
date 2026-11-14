"""Library parsing errors, the call routes that fail, and the scorer's guard rails."""
import copy
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from nailit import library, llm, scoring
from nailit.answers import ai

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"


class StoriesParsingTest(unittest.TestCase):
    def test_duplicate_malformed_and_broken_story_blocks_are_reported(self):
        text = ("F1 | Led a team | confirmed | CV\nF1 | Again | confirmed | CV\nF2 | broken line\n\n"
                "## S1: First\n```yaml\nstages: {a: 1}\n```\n"
                "## S2: No block\ntext only\n"
                "## S3: Bad yaml\n```yaml\nkey: [unclosed\n```\n"
                "## S4: Not a mapping\n```yaml\n- a\n- b\n```\n")
        data, errors = library.parse_stories(text)
        joined = "\n".join(errors)
        for piece in ("duplicate fact F1", "malformed fact line", "S2 has no ```yaml block", "S3: invalid yaml", "S4: yaml block must be a mapping"):
            self.assertIn(piece, joined)
        self.assertEqual([s["id"] for s in data["stories"]], ["S1"])
        self.assertEqual(data["stories"][0]["title"], "First")

    def test_rubric_rule_sources_and_profile_people_are_split_out(self):
        rubric, errors = library.parse_rubric("- **R1.1.** Answer first (src: D1, D2)\n**R2.3:** No source here\nR9.9 not bold\n")
        self.assertEqual([r["src"] for r in rubric["rules"] if "src" in r], [["D1", "D2"]])
        self.assertEqual(len(rubric["rules"]), 2)
        self.assertTrue(any("must be bold" in e for e in errors))
        self.assertEqual(library._split_src("text (src: X"), ("text (src: X", None))
        profile = library.parse_profile("## People\n- Ana Cole: former manager\n- bad line\n## Target line\nSenior ops\n")
        self.assertEqual(profile["people"], {"Ana Cole": "former manager"})
        self.assertEqual(profile["target_line"], "Senior ops")


class LibraryFolderTest(unittest.TestCase):
    def copy_library(self):
        tmp = Path(tempfile.mkdtemp())
        import shutil
        shutil.copytree(EXAMPLE / "library", tmp / "library")
        return tmp / "library"

    def test_problems_in_a_library_folder_are_all_listed(self):
        lib_dir = self.copy_library()
        (lib_dir / "rubric.md").unlink()
        (lib_dir / "phrases.yaml").write_text("key: [unclosed")
        (lib_dir / "detectors.yaml").unlink()
        for path in (lib_dir / "drills").glob("*.yaml"):
            path.unlink()
        with self.assertRaises(library.LibraryError) as caught:
            library.load_library(lib_dir)
        text = "\n".join(caught.exception.errors)
        for piece in ("rubric.md: missing", "phrases.yaml: invalid yaml", "detectors.yaml: missing", "drills/: no .yaml files"):
            self.assertIn(piece, text)
        with self.assertRaises(library.LibraryError):
            library.load_library(lib_dir / "nowhere")

    def test_a_programme_gate_beyond_its_length_is_an_error(self):
        lib = copy.deepcopy(library.load_library(EXAMPLE / "library"))
        programme = next(iter(lib["programmes"].values()))
        programme["gates"] = [{"after_day": programme["days"] + 5}]
        errors = library._cross_reference_errors(lib)
        self.assertTrue(any("is beyond" in e for e in errors))

    def test_drill_items_accept_lists_and_grouped_dicts(self):
        self.assertEqual(library._drill_items([1, 2]), [1, 2])
        self.assertEqual(library._drill_items({"core": [1], "common_end": [9], "voice": [2], "x": "no"}), [1, 2])
        self.assertEqual(library._drill_items("junk"), [])

    def test_me_files_missing_or_unparsed_are_listed(self):
        tmp = Path(tempfile.mkdtemp())
        with self.assertRaises(library.LibraryError) as caught:
            library.load_me(tmp)
        self.assertIn("missing", "\n".join(caught.exception.errors))


class CallRoutesTest(unittest.TestCase):
    def setUp(self):
        self.api = importlib.import_module("nailit.api")
        self.tmp = Path(tempfile.mkdtemp())
        for patcher in (mock.patch("nailit.library.home", return_value=self.tmp), mock.patch.dict("os.environ", {"NAILIT_PROVIDER": ""})):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(self.api.app)
        self.addCleanup(self.client.close)

    def test_settings_list_engines_and_refuse_unknown_or_unready_ones(self):
        self.assertTrue(self.client.get("/settings").json()["engines"])
        self.assertEqual(self.client.post("/settings", json={"engine": "nonsense"}).status_code, 422)
        with mock.patch.object(llm, "engine_ready", return_value=False):
            self.assertEqual(self.client.post("/settings", json={"engine": "lua"}).status_code, 409)
            self.assertEqual(self.client.post("/settings", json={"engine": "claude"}).status_code, 409)
        with mock.patch.object(llm, "engine_ready", return_value=True):
            self.assertEqual(self.client.post("/settings", json={"engine": "gemini"}).json()["engine"], "gemini")

    def test_the_engine_test_button_reports_success_and_failure(self):
        with mock.patch.object(llm, "ask_llm", return_value="Tell me about conflict."):
            self.assertEqual(self.client.post("/settings/test").json()["reply"], "Tell me about conflict.")
        with mock.patch.object(llm, "ask_llm", side_effect=llm.LLMError("down")):
            self.assertEqual(self.client.post("/settings/test").status_code, 502)

    def test_transcript_import_failures_have_specific_messages(self):
        text = "INTERVIEWER: Tell me about a failure.\nCANDIDATE: I missed a deadline and then rebuilt the process."
        with mock.patch.object(ai, "chat", side_effect=RuntimeError("no model")):
            self.assertEqual(self.client.post("/call/import", json={"text": text}).status_code, 502)
        with mock.patch.object(ai, "chat", return_value={"items": []}):
            self.assertEqual(self.client.post("/call/import", json={"text": text}).status_code, 422)
        invented = {"items": [{"question": "Q?", "answer": "I single-handedly saved the company and won an award.", "competency": "failure"}]}
        with mock.patch.object(ai, "chat", return_value=invented):
            self.assertEqual(self.client.post("/call/import", json={"text": text}).status_code, 422)

    def test_an_item_the_scorer_cannot_mark_is_reported_not_dropped(self):
        text = "INTERVIEWER: Tell me about a failure.\nCANDIDATE: I missed a deadline and then rebuilt the whole process."
        split = {"items": [{"question": "Tell me about a failure.", "answer": "I missed a deadline and then rebuilt the whole process.", "competency": "failure"}]}
        with mock.patch.object(ai, "chat", return_value=split), mock.patch("nailit.scoring.score", side_effect=RuntimeError("scorer down")), \
                mock.patch("nailit.rehearse.append_progress"):
            out = self.client.post("/call/import", json={"text": text}).json()
        self.assertTrue(any("error" in a for a in out["answers"]))

    def test_the_call_page_is_served(self):
        self.assertIn("transcript", self.client.get("/call").text)


class ScoringGuardTest(unittest.TestCase):
    def test_no_verdicts_from_the_model_is_an_error_not_a_zero(self):
        card = {"question": "Q?", "type": "behavioural", "answer": "", "moves": []}
        with mock.patch.object(ai, "chat", return_value={"rules": []}), self.assertRaisesRegex(RuntimeError, "no rule verdicts"):
            scoring.score(card, "I did it.")

    def test_phrase_checks_never_stop_scoring(self):
        with mock.patch("nailit.manuals.phrase_hits", side_effect=RuntimeError("broken yaml")):
            self.assertEqual(scoring._phrases("text", {}), [])

    def test_rule_sets_depend_on_competency_and_type(self):
        story = scoring.rule_set({"competency": None, "type": "behavioural"})
        direct = scoring.rule_set({"competency": None, "type": "motivation"})
        self.assertNotEqual(set(story), set(direct))
        self.assertTrue(scoring.rule_set({"competency": "failure", "type": "behavioural"}))


if __name__ == "__main__":
    unittest.main()
