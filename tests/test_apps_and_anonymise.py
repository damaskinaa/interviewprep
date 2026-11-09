import os
import shutil
import tempfile
import types
import unittest
from pathlib import Path

from nailit import library, llm
from nailit.prep import apps

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "NailIt"
SESSION = {"session_id": "s1", "company_name": "Example Corp", "role_name": "Platform Engineer"}


class HomeMixin:
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        shutil.copytree(EXAMPLE / "me", self.home / "me")
        self._old = os.environ.get("NAILIT_HOME")
        os.environ["NAILIT_HOME"] = str(self.home)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("NAILIT_HOME", None)
        else:
            os.environ["NAILIT_HOME"] = self._old
        shutil.rmtree(self.home)


class AnonymiseTest(HomeMixin, unittest.TestCase):
    def test_names_become_roles(self):
        people = library.people_map()
        text = "Alex Sample asked me; later alex's plan clashed with Jordan Example."
        self.assertEqual(
            library.anonymise(text, people),
            "my engineering manager asked me; later my engineering manager's plan clashed with the support lead.",
        )

    def test_names_split_across_lines_and_short_first_names(self):
        people = {"Alex Sample": "my manager", "Jo Smith": "the analyst"}
        self.assertEqual(library.anonymise("Alex\nSample and Jo agreed.", people), "my manager and the analyst agreed.")

    def test_shared_first_name_is_left_alone(self):
        people = {"Sam One": "the PM", "Sam Two": "the designer"}
        with self.assertLogs("nailit.library", level="WARNING"):
            self.assertEqual(library.anonymise("Sam One and Sam", people), "the PM and Sam")

    def test_prompt_is_anonymised_before_the_llm(self):
        sent = []

        def create(**kwargs):
            sent.append(kwargs["messages"][-1]["content"])
            usage = types.SimpleNamespace(prompt_tokens=1, completion_tokens=1)
            message = types.SimpleNamespace(content="ok")
            return types.SimpleNamespace(usage=usage, choices=[types.SimpleNamespace(message=message)])

        old_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "test-key"
        llm._client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))
        try:
            llm.ask_llm("Rewrite: Jordan Example disagreed.")
        finally:
            llm._client = None
            if old_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old_key
        self.assertEqual(sent, ["Rewrite: the support lead disagreed."])


class AppFilesTest(HomeMixin, unittest.TestCase):
    def test_writes_the_three_files_under_apps(self):
        sources = [{"title": "About us", "url": "https://example.com/about", "fetched_at": "2026-01-02"}]
        apps.write_research(SESSION, {"official_company_signals": [{"signal": "Ships weekly", "confidence": "high"}]}, sources)
        stories = library.load_me()["stories"]["stories"]
        competency = stories[0]["competencies"][0]
        self.assertEqual(apps._story_for(competency[:2], stories), "no story yet (gap)")
        apps.write_jd_map(SESSION, {"question_seeds": [
            {"maps_to_jd_line_or_requirement": "Own reliability", "competency": competency},
            {"maps_to_jd_line_or_requirement": "Lead hiring", "competency": "zzz unmatched"},
        ]})
        apps.write_questions(SESSION, {"questions_by_round": [
            {"round_name": "Hiring manager", "questions": [{"question": "Tell me about a failure.", "assigned_story": stories[0]["id"]}]},
        ]})
        folder = self.home / "apps" / "example-corp-platform-engineer"
        research = (folder / "research.md").read_text()
        self.assertIn("Ships weekly (high)", research)
        self.assertIn("fetched 2026-01-02", research)
        jd_map = (folder / "jd_map.md").read_text()
        self.assertIn(f"| Own reliability | {competency} | {stories[0]['id']}", jd_map)
        self.assertIn("| Lead hiring | zzz unmatched | no story yet (gap) |", jd_map)
        self.assertIn(f"- Tell me about a failure. — story: {stories[0]['id']}", (folder / "questions.md").read_text())

    def test_export_failure_only_logs(self):
        (self.home / "apps").write_text("not a folder")
        with self.assertLogs("nailit.prep.apps", level="WARNING"):
            self.assertIsNone(apps.write_questions(SESSION, {"questions_by_round": []}))


if __name__ == "__main__":
    unittest.main()
