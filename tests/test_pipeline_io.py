"""Model access (ai), the harvest and extra-source fetchers, curation and repair, with every network call faked."""
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from nailit.answers import ai, curate, extra_sources, harvest, repair


def reply(text, finish="stop"):
    return types.SimpleNamespace(usage=types.SimpleNamespace(prompt_tokens=10, completion_tokens=5, input_tokens=10, output_tokens=5),
                                 choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=text), finish_reason=finish)],
                                 stop_reason="end_turn", content=[types.SimpleNamespace(type="text", text=text)])


class AiTest(unittest.TestCase):
    def setUp(self):
        for name in ("USAGE",):
            patcher = mock.patch.dict(ai.USAGE, clear=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        sleep = mock.patch.object(ai.time, "sleep")
        sleep.start()
        self.addCleanup(sleep.stop)
        self.addCleanup(ai.set_cap, 0)

    def test_cost_tracking_and_the_spending_cap(self):
        ai._track("claude-opus-5-5", 1_000_000, 100_000)
        self.assertAlmostEqual(ai.spent(), 4 + 2)
        ai.set_cap(5)
        with self.assertRaises(ai.BudgetExceeded):
            ai.chat("claude-opus-5-5", "hi")
        ai.set_cap(0)
        ai._track("tx:model", 5, 5)
        with mock.patch.object(ai, "BACKEND", "api"):
            self.assertIn("total (Claude)", ai.usage_report())
        with mock.patch.object(ai, "BACKEND", "cli"):
            self.assertIn("Claude plan", ai.usage_report())

    def test_the_tensorx_backend_parses_json_and_retries_truncated_replies(self):
        client = mock.Mock()
        client.chat.completions.create.side_effect = [reply("{", finish="length"), reply("<think>x</think>{\"ok\": true}")]
        with mock.patch.object(ai, "_tx", return_value=client):
            self.assertEqual(ai.chat("tx:some/model", "hi", json_mode=True, timeout=9), {"ok": True})
        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertGreater(client.chat.completions.create.call_args.kwargs["max_tokens"], 16000)
        client.chat.completions.create.side_effect = [reply("plain text")]
        with mock.patch.object(ai, "_tx", return_value=client):
            self.assertEqual(ai.chat("tx:some/model", "hi"), "plain text")

    def test_the_sdk_backends_pass_thinking_options_and_stop_on_refusal(self):
        claude = mock.Mock()
        claude.messages.create.return_value = reply("answer")
        with mock.patch.object(ai, "BACKEND", "api"), mock.patch.object(ai, "_claude", return_value=claude):
            self.assertEqual(ai.chat("claude-haiku-5-5", "hi", thinking=False), "answer")
            self.assertEqual(claude.messages.create.call_args.kwargs["thinking"], {"type": "disabled"})
            ai.chat("claude-sonnet-5-5", "hi", thinking=False)
            self.assertEqual(claude.messages.create.call_args.kwargs["thinking"], {"type": "between_tools"})
            refusal = reply("")
            refusal.stop_reason = "refusal"
            claude.messages.create.return_value = refusal
            self.assertEqual(ai.chat("claude-opus-5-5", "hi", json_mode=True), {})
            self.assertEqual(ai.chat("claude-opus-5-5", "hi"), "")
        gpt = mock.Mock()
        gpt.chat.completions.create.return_value = reply("from gpt")
        with mock.patch.object(ai, "_gpt", return_value=gpt):
            self.assertEqual(ai.chat("gpt-x", "hi", json_mode=True) or "empty", "empty")  # not JSON: parsed to {}
            self.assertEqual(ai.chat("gpt-x", "hi"), "from gpt")

    def test_authentication_errors_are_raised_and_other_errors_end_in_an_empty_reply(self):
        client = mock.Mock()
        client.chat.completions.create.side_effect = RuntimeError("authentication failed")
        with mock.patch.object(ai, "_tx", return_value=client), self.assertRaises(RuntimeError):
            ai.chat("tx:m", "hi")
        client.chat.completions.create.side_effect = RuntimeError("boom")
        with mock.patch.object(ai, "_tx", return_value=client):
            self.assertEqual(ai.chat("tx:m", "hi", retries=2), "")
            self.assertEqual(ai.chat("tx:m", "hi", json_mode=True, retries=1), {})

    def test_claude_code_backend_checks_the_served_model_and_reports_errors(self):
        def run(payload, code=0):
            return types.SimpleNamespace(stdout=payload if isinstance(payload, str) else json.dumps(payload), stderr="err", returncode=code)
        good = {"result": " hi ", "modelUsage": {"claude-fable-5-2": {}}, "usage": {"input_tokens": 3, "output_tokens": 2}}
        with mock.patch.object(subprocess, "run", return_value=run(good)):
            self.assertEqual(ai._cli("claude-fable-5-2", "prompt", "high"), "hi")
        with mock.patch.object(subprocess, "run", return_value=run(dict(good, modelUsage={"claude-fable-5-1": {}}))), \
                self.assertRaises(ai.CLIError):
            ai._cli("claude-fable-5-2", "p", "high")
        with mock.patch.object(subprocess, "run", return_value=run("not json")), self.assertRaises(ai.CLIError):
            ai._cli("claude-fable-5-2", "p", "high")
        with mock.patch.object(subprocess, "run", return_value=run({"is_error": True, "result": "You've reached your limit"})), \
                self.assertRaises(PermissionError):
            ai._cli("claude-fable-5-2", "p", "high")
        with mock.patch.object(subprocess, "run", return_value=run({"is_error": True, "result": "weird"})), self.assertRaises(ai.CLIError):
            ai._cli("claude-fable-5-2", "p", "high")
        with mock.patch.object(ai, "BACKEND", "cli"), mock.patch.object(ai, "_cli", return_value='{"a": 1}'):
            self.assertEqual(ai.chat("claude-opus-5-5", "hi", json_mode=True), {"a": 1})

    def test_clients_and_embeddings_are_built_lazily(self):
        fake_openai = types.ModuleType("openai")
        fake_openai.OpenAI = mock.Mock(return_value="client")
        fake_anthropic = types.ModuleType("anthropic")
        fake_anthropic.Anthropic = mock.Mock(return_value="claude-client")
        fake_st = types.ModuleType("sentence_transformers")
        encoder = mock.Mock()
        encoder.encode.return_value = np.array([[1.0, 0.0]])
        fake_st.SentenceTransformer = mock.Mock(return_value=encoder)
        with mock.patch.dict(sys.modules, {"openai": fake_openai, "anthropic": fake_anthropic, "sentence_transformers": fake_st}), \
                mock.patch.object(ai, "_tensorx", None), mock.patch.object(ai, "_openai", None), mock.patch.object(ai, "_anthropic", None), \
                mock.patch.object(ai, "_embedder", None), mock.patch.dict("os.environ", {"TENSORX_API_KEY": "k"}):
            self.assertEqual((ai._tx(), ai._gpt(), ai._claude()), ("client", "client", "claude-client"))
            self.assertEqual(ai.embed(["a"]), [[1.0, 0.0]])


class HarvestFetchTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(harvest, "OUT", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)
        env = mock.patch.dict("os.environ", {"TAVILY_API_KEY": "t", "EXA_API_KEY": "e", "FIRECRAWL_API_KEY": "f", "JINA_API_KEY": "j"})
        env.start()
        self.addCleanup(env.stop)

    def http(self, **payloads):
        client = mock.Mock()
        response = mock.Mock(status_code=200, text="x" * 900, headers={})
        response.json.return_value = payloads
        client.post.return_value = response
        client.get.return_value = response
        return client, response

    def test_budget_and_cache(self):
        budget = harvest.Budget(10)
        self.assertEqual((budget.take(6), budget.take(6), budget.left), (True, False, 4))
        calls = []
        self.assertEqual(harvest.cached("page", "k", lambda: calls.append(1) or {"a": 1}), {"a": 1})
        self.assertEqual(harvest.cached("page", "k", lambda: calls.append(1) or {"a": 2}), {"a": 1})
        self.assertEqual(len(calls), 1)
        with mock.patch.dict(harvest.OFFLINE, {"on": True}):
            self.assertIsNone(harvest.cached("page", "other", lambda: {"a": 3}))
            self.assertEqual(harvest.cached("extract", "other", lambda: {"a": 3}), {"a": 3})
        self.assertIsNone(harvest.cached("page", "none", lambda: None))

    def test_query_lists_cover_roles_and_companies(self):
        self.assertGreater(len(harvest.web_queries()), 80)
        self.assertTrue(any("Pfizer" in q for q in harvest.web_queries()))
        self.assertGreater(len(harvest.video_queries()), 10)
        self.assertGreater(len(harvest.yt_free_queries()), 100)

    def test_search_engines_return_url_title_snippet(self):
        client, response = self.http(results=[{"url": "https://a", "title": "T", "content": "C", "highlights": ["h1", "h2"]}])
        self.assertEqual(harvest.tavily(client, "q"), [{"url": "https://a", "title": "T", "snippet": "C"}])
        self.assertEqual(harvest.exa(client, "q")[0]["snippet"], "h1 h2")

    def test_firecrawl_retries_rate_limits_then_fails_loudly(self):
        client = mock.Mock()
        limited = mock.Mock(status_code=429, headers={"retry-after": "0"})
        ok = mock.Mock(status_code=200, headers={})
        ok.json.return_value = {"data": {"markdown": "m"}}
        client.post.side_effect = [limited, ok]
        with mock.patch.object(harvest.time, "sleep"):
            self.assertEqual(harvest.firecrawl(client, {"url": "u"}), {"markdown": "m"})
            client.post.side_effect = [limited] * 3
            limited.raise_for_status.side_effect = RuntimeError("429")
            with self.assertRaises(RuntimeError):
                harvest.firecrawl(client, {}, attempts=3)

    def test_pages_try_jina_then_firecrawl(self):
        client, response = self.http()
        page = harvest.scrape_page(client, "https://x")
        self.assertEqual((page["via"], len(page["text"])), ("jina", 900))
        response.text = "short"
        with mock.patch.object(harvest, "firecrawl", return_value={"markdown": "md", "metadata": {"title": "T"}}):
            page = harvest.scrape_page(client, "https://x")
        self.assertEqual((page["via"], page["title"]), ("firecrawl", "T"))
        client.get.side_effect = RuntimeError("down")
        with mock.patch.object(harvest, "firecrawl", return_value={}):
            self.assertEqual(harvest.scrape_page(client, "https://x")["text"], "")

    def test_youtube_through_firecrawl_and_free_tools(self):
        videos = {"alexandria": [{"data": {"records": [{"video_id": "abc", "title": "T", "channel": {"name": "C"}}, {"title": "no id"}, "junk"]}}]}
        with mock.patch.object(harvest, "firecrawl", return_value=videos):
            self.assertEqual(harvest.yt_search(None, "q"), [{"video_id": "abc", "title": "T", "channel": "C"}])
        with mock.patch.object(harvest, "firecrawl", return_value={"alexandria": [{"data": {"full_text": "words", "title": "T"}}]}):
            self.assertEqual(harvest.yt_transcript(None, "abc")["text"], "words")
        lines = json.dumps({"id": "v1", "title": "A", "channel": "C", "duration": 600, "view_count": 5}) + "\nnot json\n"
        with mock.patch.object(subprocess, "run", return_value=types.SimpleNamespace(stdout=lines)):
            self.assertEqual(harvest.yt_free_search("q")[0]["video_id"], "v1")
        module = types.ModuleType("youtube_transcript_api")
        module.YouTubeTranscriptApi = lambda: types.SimpleNamespace(fetch=lambda vid, languages: [types.SimpleNamespace(text="a"), types.SimpleNamespace(text="b")])
        with mock.patch.dict(sys.modules, {"youtube_transcript_api": module}):
            self.assertEqual(harvest.yt_free_transcript("v1")["text"], "a b")

    def test_extract_chunks_the_text_and_returns_none_when_every_call_failed(self):
        with mock.patch.object(ai, "chat", return_value={"questions": [{"q": "Q?"}], "answers": [{"q": "Q?", "answer": "A"}]}):
            out = harvest.extract("x" * 20000, "title")
        self.assertEqual((len(out["questions"]), len(out["answers"])), (2, 2))
        with mock.patch.object(ai, "chat", return_value=None):
            self.assertIsNone(harvest.extract("x" * 400, "title"))

    def test_cluster_groups_near_identical_questions_and_counts_sources(self):
        def embed(texts):
            return [[1.0, 0.0] if t.startswith("a") else [0.0, 1.0] for t in texts]
        items = [{"q": "a one?", "source": "s1", "company": "Google", "role": "PM", "kind": "asked"},
                 {"q": "a two?", "source": "s2", "company": "", "role": "", "kind": "asked"},
                 {"q": "b one?", "source": "s1"}]
        with mock.patch.object(harvest, "embed", side_effect=embed):
            canon = harvest.cluster(items)
        self.assertEqual((canon[0]["frequency"], canon[0]["companies"]), (2, ["Google"]))
        self.assertEqual(len(canon), 2)

    def test_cached_docs_skip_duplicates_and_library_seed_reads_the_bank(self):
        for kind, name, doc in (("page", "a", {"url": "u1", "text": "word " * 200}), ("page", "b", {"url": "u1", "text": "other " * 200}),
                                ("video", "c", {"url": "u3", "text": "word " * 200}), ("video", "d", {"url": "u4", "text": "tiny"})):
            path = self.tmp / "raw" / kind
            path.mkdir(parents=True, exist_ok=True)
            (path / f"{name}.json").write_text(json.dumps(doc))
        self.assertEqual([d["url"] for d in harvest.cached_docs()], ["u1"])
        home = self.tmp / "home"
        (home / "library" / "model_level").mkdir(parents=True)
        (home / "library" / "model_level" / "03_master_question_bank.md").write_text("| Tell me about a time you failed? | x |\n| short? | y |\nplain\n")
        lib = {"questions": 1}
        qs = [{"text": "Why us?", "variants": ["Why here?"]}]
        with mock.patch.object(harvest.library, "home", return_value=home), mock.patch.object(harvest.library, "load_library", return_value=lib), \
                mock.patch.object(harvest.library, "_questions", return_value=(qs, [{"text": "Ask me?"}])):
            rows = harvest.library_seed()
        self.assertEqual(sorted({r["source"] for r in rows}), ["library", "model_level_03"])
        self.assertIn("ask_them", {r["kind"] for r in rows})


class HarvestMainTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(harvest.OFFLINE)  # main() switches it on for --offline runs
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_a_full_run_with_faked_sources_writes_the_outputs(self):
        tmp = Path(tempfile.mkdtemp())

        def tavily(http, query):
            return [{"url": "https://example.com/a", "title": "A", "snippet": "s"},
                    {"url": "https://www.youtube.com/watch?v=abcdefghijk", "title": "Mock interview"},
                    {"url": "https://www.glassdoor.com/x", "title": "G", "snippet": "S" * 100}]

        def exa(http, query):
            raise RuntimeError("exa down")
        doc = {"url": "https://example.com/a", "text": "word " * 200, "title": "A"}
        data = {"questions": [{"q": "Tell me about a time you failed?", "kind": "asked"}, {"q": "What do you ask us?", "kind": "ask_them"}],
                "answers": [{"q": "Q?", "answer": "A"}]}
        out = []
        with mock.patch.object(harvest, "OUT", tmp), mock.patch.object(harvest, "tavily", tavily), mock.patch.object(harvest, "exa", exa), \
                mock.patch.object(harvest, "web_queries", return_value=["q1"]), mock.patch.object(harvest, "video_queries", return_value=["v1"]), \
                mock.patch.object(harvest, "scrape_page", return_value=doc), mock.patch.object(harvest, "yt_search", return_value=[]), \
                mock.patch.object(harvest, "yt_transcript", return_value={"url": "https://www.youtube.com/watch?v=abcdefghijk", "text": "t " * 400, "title": "Mock interview"}), \
                mock.patch.object(harvest, "extract", return_value=data), mock.patch.object(harvest, "library_seed", return_value=[]), \
                mock.patch.object(harvest, "embed", side_effect=lambda t: [[1.0, 0.0]] * len(t)), \
                mock.patch.object(ai, "usage_report", return_value="usage"), mock.patch("nailit.config.load_secrets"), \
                mock.patch("builtins.print", side_effect=lambda *a, **k: out.append(" ".join(map(str, a)))), \
                mock.patch("sys.argv", ["harvest", "--budget", "50"]):
            harvest.main()
        self.assertTrue((tmp / "canonical.json").exists() and (tmp / "ask_them.json").exists())
        self.assertIn("exa down", (tmp / "report.md").read_text())
        self.assertTrue(json.loads((tmp / "canonical.json").read_text()))

    def test_the_free_youtube_mode_and_offline_mode(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "raw" / "page").mkdir(parents=True)
        (tmp / "raw" / "page" / "a.json").write_text(json.dumps({"url": "https://example.com/z", "text": "word " * 200}))
        data = {"questions": [{"q": "How do you prioritise work?", "kind": "asked"}], "answers": []}
        videos = [{"video_id": "vid00000001", "title": "Great interview mock", "duration": 900, "views": 5}]
        with mock.patch.object(harvest, "OUT", tmp), mock.patch.object(harvest, "web_queries", return_value=[]), \
                mock.patch.object(harvest, "yt_free_queries", return_value=["q"]), mock.patch.object(harvest, "yt_free_search", return_value=videos), \
                mock.patch.object(harvest, "yt_free_transcript", side_effect=type("RequestBlocked", (Exception,), {})("blocked")), \
                mock.patch.object(harvest.time, "sleep"), mock.patch.object(harvest, "extract", return_value=data), \
                mock.patch.object(harvest, "library_seed", return_value=[{"q": "Seed question here?", "kind": "asked", "source": "library", "company": "", "role": ""}]), mock.patch.object(harvest, "embed", side_effect=lambda t: [[1.0, 0.0]] * len(t)), \
                mock.patch.object(ai, "usage_report", return_value=""), mock.patch("nailit.config.load_secrets"), mock.patch("builtins.print"), \
                mock.patch("sys.argv", ["harvest", "--youtube", "--yt-delay", "0"]):
            harvest.main()
            self.assertIn("transcript failed", (tmp / "report.md").read_text())
        with mock.patch.object(harvest, "OUT", tmp), mock.patch.object(harvest, "web_queries", return_value=[]), \
                mock.patch.object(harvest, "video_queries", return_value=[]), mock.patch.object(harvest, "extract", return_value=data), \
                mock.patch.object(harvest, "library_seed", return_value=[{"q": "Seed question here?", "kind": "asked", "source": "library", "company": "", "role": ""}]), mock.patch.object(harvest, "embed", side_effect=lambda t: [[1.0, 0.0]] * len(t)), \
                mock.patch.object(ai, "usage_report", return_value=""), mock.patch("nailit.config.load_secrets"), mock.patch("builtins.print"), \
                mock.patch("sys.argv", ["harvest", "--offline"]):
            harvest.main()
        self.assertTrue(json.loads((tmp / "canonical.json").read_text()))


class ExtraSourcesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        patcher = mock.patch.object(harvest, "OUT", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_url_lists_keep_behavioural_and_role_pages(self):
        http = mock.Mock()
        http.get.return_value = mock.Mock(text="<loc>https://interviewing-io.agentsite.network/content/behavioral-guide</loc>"
                                               "<loc>https://interviewing-io.agentsite.network/content/css-tricks</loc>")
        self.assertEqual(len(extra_sources.agentsite_urls(http)), 1)
        http.get.return_value = mock.Mock(text="https://www.aced.io/questions?type=behavioral https://www.aced.io/other "
                                               "https://www.aced.io/questions?company=amazon&role=tpm")
        urls = extra_sources.aced_urls(http)
        self.assertEqual(len(urls), 2)

    def test_read_cleans_html_and_waits_politely_for_the_reader(self):
        http = mock.Mock()
        http.get.return_value = mock.Mock(text="<p>Hello   there</p>")
        page = extra_sources.read(http, extra_sources.AGENTSITE + "/content/x")
        self.assertEqual(page["text"].strip(), "Hello there")
        with mock.patch.object(extra_sources.time, "sleep") as sleep:
            extra_sources.read(http, "https://www.aced.io/q")
        self.assertTrue(sleep.called)

    def test_hacker_news_threads_are_walked_and_cached(self):
        http = mock.Mock()
        search = mock.Mock()
        search.json.return_value = {"hits": [{"objectID": "1", "num_comments": 50, "title": "Loop"}, {"objectID": "2", "num_comments": 1, "title": "Few"}]}
        item = mock.Mock()
        long_text = "word " * 200
        item.json.return_value = {"text": long_text, "children": [{"text": long_text, "children": [{"text": "short"}]}, {"text": long_text * 2}]}
        http.get.side_effect = lambda url, **k: search if "search" in url else item
        with mock.patch.object(extra_sources, "HN_QUERIES", ["q"]), mock.patch.object(extra_sources.time, "sleep"):
            docs = extra_sources.hn_threads(http)
            self.assertEqual(docs, ["https://news.ycombinator.com/item?id=1"])
            self.assertEqual(extra_sources.hn_threads(http), [])  # already cached

    def test_main_counts_pages_added_per_source(self):
        client = mock.Mock()
        with mock.patch.object(extra_sources.httpx, "Client", return_value=client), \
                mock.patch.object(extra_sources, "agentsite_urls", return_value=["https://a/1", "https://a/2"]), \
                mock.patch.object(extra_sources, "aced_urls", return_value=["https://b/1"]), \
                mock.patch.object(extra_sources, "read", side_effect=[{"url": "u", "text": "x" * 900}, RuntimeError("blocked"), {"url": "v", "text": "short"}]), \
                mock.patch.object(extra_sources, "hn_threads", return_value=[]), mock.patch("builtins.print") as printed:
            extra_sources.main()
        self.assertTrue(any("interviewing.io pages added: 1 of 2" in " ".join(map(str, c.args)) for c in printed.call_args_list))


class CurateAndRepairTest(unittest.TestCase):
    def test_apply_drops_merges_and_filters_off_topic(self):
        deck = {"cards": [{"question": "Keep me please?", "answer": "a", "frequency": 2}, {"question": "Dup wording?", "answer": "b", "frequency": 1},
                          {"question": "Design a url shortener?", "answer": "c"}, {"question": "Tight Deadlines", "answer": "d"},
                          {"question": "Drop this one?", "answer": "e"}]}
        dropped, merged = curate.apply(deck, {"drop": ["Drop this one?"], "merge": {"Dup wording?": "Keep me please?", "Ghost?": "Keep me please?"}})
        self.assertEqual(merged, 1)
        self.assertEqual(len(dropped), 3)
        self.assertEqual(deck["cards"][0]["variants"], ["Dup wording?"])
        self.assertEqual(deck["cards"][0]["frequency"], 3)

    def test_curate_main_writes_a_backup_unless_checking(self):
        tmp = Path(tempfile.mkdtemp())
        deck = tmp / "deck.json"
        deck.write_text(json.dumps({"cards": [{"question": "Keep me please?", "answer": "a"}, {"question": "Drop me please?", "answer": "b"}]}))
        rules = tmp / "curation.json"
        rules.write_text(json.dumps({"drop": ["Drop me please?"], "merge": {}}))
        with mock.patch.object(curate, "DECK", deck), mock.patch.object(curate, "CURATION", rules), mock.patch("builtins.print"):
            with mock.patch("sys.argv", ["curate", "--check"]):
                curate.main()
            self.assertEqual(len(json.loads(deck.read_text())["cards"]), 2)
            with mock.patch("sys.argv", ["curate"]):
                curate.main()
        self.assertEqual(len(json.loads(deck.read_text())["cards"]), 1)
        self.assertTrue(list(tmp.glob("deck_before_curate_*.json")))
        self.assertTrue(curate.is_fragment("Tell me about a time when..."))

    def test_repair_rewrite_edge_cases(self):
        card = {"question": "Q?", "answer": "old", "story": "M1", "rules": [{"id": "R1", "name": "Rule", "verdict": "fail", "evidence": "e" * 100}]}
        with mock.patch.object(repair, "judge", return_value=(5.0, ["Rule (fail)"])), mock.patch.object(repair, "rules_text", return_value=([], "- r")), \
                mock.patch.object(ai, "chat", return_value={"answer": "too short"}):
            self.assertIsNone(repair.rewrite(card, {"M1": "story"}))
        with mock.patch.object(repair, "judge", return_value=(5.0, [])), mock.patch.object(repair, "rules_text", return_value=([], "- r")), \
                mock.patch.object(ai, "chat", return_value=None):
            self.assertIsNone(repair.rewrite(dict(card, rules=[]), {}))

    def test_repair_main_replaces_improved_cards_and_notes_failures(self):
        tmp = Path(tempfile.mkdtemp())
        deck = tmp / "deck.json"
        cards = [{"question": f"Weak {n}?", "generation": 2, "quality": 4.0 + n, "answer": "old", "story": "M1"} for n in range(4)]
        deck.write_text(json.dumps({"cards": cards}))
        results = {"Weak 0?": {"before": 4.0, "after": 9.0, "answer": "new", "leftover": []},
                   "Weak 1?": {"before": 5.0, "remarked": True}, "Weak 2?": None, "Weak 3?": RuntimeError("fable limit")}

        def fake_rewrite(card, stories, writer=None, threshold=8.0):
            value = results[card["question"]]
            if isinstance(value, Exception):
                raise value
            return value
        out = []
        with mock.patch.object(repair, "DECK", deck), mock.patch.object(repair, "story_bank", return_value={}), mock.patch.object(repair, "rewrite", fake_rewrite), \
                mock.patch.object(repair, "apply", side_effect=lambda d, c, r: c.update(answer=r["answer"])), mock.patch("nailit.config.load_secrets"), \
                mock.patch("builtins.print", side_effect=lambda *a, **k: out.append(" ".join(map(str, a)))), mock.patch("sys.argv", ["repair"]):
            repair.main()
        text = "\n".join(out)
        self.assertIn("1 of 4 cards replaced", text)
        self.assertIn("fable limit", text)
        self.assertIn("fine as is", text)
        saved = {c["question"]: c for c in json.loads(deck.read_text())["cards"]}
        self.assertEqual(saved["Weak 0?"]["answer"], "new")
        self.assertEqual(saved["Weak 1?"]["judged_by"], 2)
        with mock.patch.object(repair, "DECK", deck), mock.patch.object(repair, "story_bank", return_value={}), mock.patch.object(repair, "rewrite", fake_rewrite), \
                mock.patch("nailit.config.load_secrets"), mock.patch("builtins.print"), mock.patch("sys.argv", ["repair", "--dry", "--limit", "1"]):
            repair.main()


if __name__ == "__main__":
    unittest.main()
