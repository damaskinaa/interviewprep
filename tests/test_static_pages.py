"""Deck text, transcripts and model replies must reach the pages through textContent, never as HTML."""
import re
import unittest
from pathlib import Path

PAGES = sorted((Path(__file__).resolve().parents[1] / "nailit" / "static").glob("*.html"))
COUNTERS = re.compile(r"p\.(streak|today|mastered|due|total|average)\b")  # numbers the server counts, not text anyone wrote


class InnerHtmlTest(unittest.TestCase):
    def test_html_sinks_only_take_fixed_markup_or_counters(self):
        self.assertTrue(PAGES)
        for page in PAGES:
            source = page.read_text()
            self.assertNotRegex(source, r"insertAdjacentHTML|outerHTML\s*=|document\.write")
            for line in (l for l in source.splitlines() if re.search(r"innerHTML\s*=", l)):
                for expr in re.findall(r"\$\{([^}]*)\}", line):
                    with self.subTest(page=page.name, expr=expr):
                        self.assertRegex(expr, COUNTERS)


if __name__ == "__main__":
    unittest.main()
