"""The prep-pack modules (common helpers, candidate profile, gap map, answer options, research, interview strategy)
with the search API and the models faked and every artifact written to a temporary working folder."""
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from nailit.prep import answers, common, me, questions, research, research_config

SESSION = {"session_id": "s1", "company_name": "Acme", "role_name": "Service Delivery Manager", "raw_jd": "Run delivery.",
           "raw_cv": "I cut the backlog by 40% in six weeks.", "raw_answer_bank": "", "raw_company_context": "", "raw_youtube_transcripts": ""}
WORDS = " ".join(["word"] * 210)


class InTempDir(unittest.TestCase):
    """The modules write under ./jobs, so each test runs in its own folder with a progress log set."""

    def setUp(self):
        self.old = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.token = common._current_progress_log.set([])
        self.addCleanup(common._current_progress_log.reset, self.token)
        self.addCleanup(os.chdir, self.old)
        printer = mock.patch("builtins.print")
        printer.start()
        self.addCleanup(printer.stop)


class CommonTest(InTempDir):
    def test_text_helpers(self):
        self.assertEqual(common.safe_path_part("a b/../c", "x"), "a_b_.._c")
        self.assertEqual(common.safe_path_part("///", "fallback"), "fallback")
        self.assertEqual(common.normalize_text("a \r\n\n\n\n\n b\t\tc "), "a \n\n\n b c")
        self.assertEqual(common.trim_text("short", 100), "short")
        self.assertIn("trimmed", common.trim_text("x" * 500, 100))
        self.assertEqual(common.as_list(None), [])
        self.assertEqual(common.as_list("a"), ["a"])
        self.assertEqual(common.count_words("one two, three"), 3)

    def test_jd_signals_are_deduplicated_across_keys(self):
        analysis = {"must_prove_signals": [{"signal": "Own SLAs"}, "Own SLAs"], "dangerous_gaps": [{"gap": "No cloud"}], "hidden_expectations": [None]}
        self.assertEqual(common.jd_signal_texts(analysis), ["Own SLAs", "No cloud"])
        self.assertEqual(common.jd_signal_texts(None), [])

    def test_progress_log_and_context_submission(self):
        common.log(3, "hello")
        self.assertEqual(common._active_progress_log()[0]["message"], "hello")
        seen = []
        common.report_progress(lambda stage, pct: seen.append((stage, pct)), "s", 5)
        common.report_progress(None, "s", 5)
        self.assertEqual(seen, [("s", 5)])
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(1) as pool:
            self.assertEqual(common.submit_with_context(pool, lambda x: len(common._active_progress_log()) + x, 10).result(), 11)
        token = common._current_progress_log.set(None)
        with self.assertRaises(RuntimeError):
            common.log(1, "no log")
        common._current_progress_log.reset(token)

    def test_artifacts_round_trip_and_bad_ones_are_reported(self):
        common.write_module_json("s1", "gap_map", {"a": 1})
        self.assertEqual(common.read_module_artifact("s1", "gap_map"), {"a": 1})
        common.write_module_markdown("s1", "prep_pack", "# pack")
        self.assertEqual(common.read_module_artifact("s1", "prep_pack"), "# pack")
        with self.assertRaises(FileNotFoundError):
            common.read_module_artifact("s1", "role_intelligence")
        common.module_artifact_path("s1", "company_intelligence").write_text("{broken")
        with self.assertRaises(ValueError):
            common.read_module_artifact("s1", "company_intelligence")

    def test_markdown_list_hides_internal_fields(self):
        text = common.markdown_list([{"id": "S1", "claim": "x", "source_id": "q", "empty": "", "story_name": "Backlog"}, "plain", {"id": "only"}])
        self.assertEqual(text, "- Claim: x; Story Name: Backlog\n- plain")


class MeModulesTest(InTempDir):
    def test_story_helpers(self):
        self.assertEqual(me.story_metric_text({"metrics": ["40%", " 6 weeks "]}), "40%, 6 weeks")
        self.assertIn("verified metrics", me.story_metric_text({}))
        self.assertEqual(me.story_title({"story_name": "Backlog"}), "Backlog")
        self.assertEqual(me.story_title("nope"), "")
        profile = {"story_inventory": [{"title": f"S{n}", "metrics": ["m"]} for n in range(6)] + ["junk"]}
        self.assertEqual(me.candidate_bridge_summary(profile).count(";"), 3)
        self.assertIn("operations leadership", me.candidate_bridge_summary({}))

    def test_profile_and_gap_map_modules_write_their_artifacts(self):
        common.write_module_json("s1", "role_intelligence", {"a": 1})
        common.write_module_json("s1", "company_intelligence", {"b": 1})
        seen = []
        with mock.patch.object(me, "ask_json", return_value={"positioning_statement": "p"}):
            self.assertEqual(me.run_candidate_profile_module(SESSION, lambda s, p: seen.append(p))["positioning_statement"], "p")
        with mock.patch.object(me, "ask_json", return_value={"strength_matches": []}):
            self.assertIn("strength_matches", me.run_gap_map_module(SESSION))
        self.assertEqual(common.read_module_artifact("s1", "gap_map"), {"strength_matches": []})
        self.assertEqual(seen[-1], 100)


class AnswerOptionsTest(InTempDir):
    PROFILE = {"story_inventory": [{"story_id": "S1", "title": "Backlog", "result": "faster", "metrics": ["40%"]}, "junk"]}

    def test_story_lookup_by_id_then_title(self):
        self.assertEqual(answers._story_lookup(self.PROFILE, "S1", "")["title"], "Backlog")
        self.assertEqual(answers._story_lookup(self.PROFILE, "", "backlog")["title"], "Backlog")
        self.assertIsNone(answers._story_lookup(self.PROFILE, "S9", "other"))
        self.assertIsNone(answers._story_lookup(None, "", ""))

    def test_options_outside_the_word_range_are_replaced_by_a_grounded_fallback(self):
        good = {"full_answer": " ".join(["spoken"] * 200), "why_it_wins": "", "metric_used": ""}
        out = answers.normalize_answer_options({"answers": [good, {"full_answer": "too short"}, "junk"]}, "Q?", self.PROFILE, None)
        self.assertEqual([a["label"] for a in out["answers"]], answers.ANSWER_LABELS)
        self.assertNotIn("Fallback", out["answers"][0]["full_answer"])
        self.assertIn("Fallback/manual review", out["answers"][1]["full_answer"])
        self.assertIn("Backlog", answers._fallback_answer("Q?", "A", self.PROFILE, None)["full_answer"])
        self.assertIn("Fallback", answers._fallback_answer("Q?", "A", {}, None)["full_answer"])
        self.assertEqual(answers.normalize_answer_options(None, "Q?", {}, None)["answers"][0]["label"], answers.ANSWER_LABELS[0])

    def test_generate_reads_the_stored_profile_and_validates_the_question(self):
        with self.assertRaises(FileNotFoundError):
            answers.generate_answer_options(SESSION, {"question": "Q?"})
        profile_dir = Path("jobs") / "s1" / "candidate_profile"
        profile_dir.mkdir(parents=True)
        (profile_dir / "candidate_profile.json").write_text(json.dumps(self.PROFILE))
        with self.assertRaises(ValueError):
            answers.generate_answer_options(SESSION, {"question": " "})
        with mock.patch.object(answers, "ask_json", return_value={"answers": []}):
            out = answers.generate_answer_options(SESSION, {"question": "Tell me about a launch", "assigned_story_id": "S1", "round_name": "HM"})
        self.assertEqual((out["session_id"], out["round_name"], len(out["answers"])), ("s1", "HM", 3))


class ResearchConfigTest(unittest.TestCase):
    def test_tiers_and_credit_estimates(self):
        self.assertEqual(research_config.get_config()["search_depth"], "advanced")
        self.assertEqual(research_config.get_credit_estimate(2), 8 + 2 * (3 + 6))


class ResearchHelpersTest(InTempDir):
    def test_sources_are_classified_scored_and_deduplicated(self):
        c = research.classify_source
        self.assertEqual(c("Acme", "https://www.acme.com/careers", "", ""), "Official company source")
        self.assertEqual(c("Acme", "https://reddit.com/r/x", "", ""), "Reddit directional theme")
        self.assertEqual(c("Acme", "https://teamblind.com/x", "", ""), "Blind directional theme")
        self.assertEqual(c("Acme", "https://youtu.be/x", "", ""), "YouTube public theme")
        self.assertEqual(c("Acme", "https://medium.com/x", "", ""), "Public prep or candidate experience")
        self.assertEqual(c("Acme", "https://x.com/y", "Interview tips", ""), "High signal public source")
        self.assertEqual(c("Acme", "https://x.com/careers", "", ""), "High signal public source")
        self.assertEqual(c("Acme", "https://x.com/y", "", ""), "Weak or background source")
        self.assertEqual(c("Acme", "", "", ""), "Search summary")
        self.assertEqual(c("Acme", "https://x.com", "", "", "directional_reddit"), "Reddit directional theme")
        self.assertEqual([research.source_score(t, "") for t in ("Official company source", "High signal public source", "Reddit directional theme",
                                                                 "Search summary", "Weak or background source")], [5, 4, 3, 2, 1])
        self.assertEqual(research.source_score("Weak or background source", "x" * 600), 2)
        self.assertEqual(research.canonical_source_key("HTTPS://A.com/x/?q=1#top"), "https://a.com/x")
        self.assertTrue(research.is_blocked_source("https://www.linkedin.com/in/x"))
        self.assertFalse(research.is_blocked_source("https://example.com"))
        self.assertEqual(research.source_host(None), "")
        self.assertEqual(research.company_domain_hint("Google Cloud"), "google.com")
        self.assertEqual(research.company_domain_hint("Tiny Co!"), "tinyco.com")
        self.assertEqual(research.company_domain_hint(""), "")
        record = research.source_record({"content": "x" * 900, "url": "u"}, 3)
        self.assertEqual((record["id"], len(record["excerpt"]) < 900), ("S3", True))

    def test_tavily_post_and_retry_logic(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"results": [{"url": "https://a.com", "title": "T", "content": "C"},
                                                                                     {"url": "https://linkedin.com/x"}, {"url": ""}]}).encode()
        with mock.patch.object(research, "TAVILY_API_KEY", None):
            self.assertEqual(research.tavily_post("search", {}), {})
            self.assertEqual(research.tavily_with_retry("q"), [])
        with mock.patch.object(research, "TAVILY_API_KEY", "k"), mock.patch.object(research.urllib.request, "urlopen", return_value=response):
            self.assertEqual(research.tavily_post("search", {})["results"][0]["url"], "https://a.com")
            self.assertEqual([r["url"] for r in research.tavily_with_retry("q")], ["https://a.com"])
            self.assertEqual(research.tavily_search("q")[0]["query"], "q")

    def test_rate_limits_are_retried_and_other_errors_end_quietly(self):
        error = lambda code: urllib.error.HTTPError("u", code, "x", {}, None)  # noqa: E731
        with mock.patch.object(research, "TAVILY_API_KEY", "k"), mock.patch.object(research.time, "sleep"):
            with mock.patch.object(research.urllib.request, "urlopen", side_effect=error(429)) as opened:
                self.assertEqual(research.tavily_with_retry("q"), [])
                self.assertEqual(opened.call_count, 3)
            with mock.patch.object(research.urllib.request, "urlopen", side_effect=error(500)):
                self.assertEqual(research.tavily_with_retry("q"), [])
            with mock.patch.object(research.urllib.request, "urlopen", side_effect=RuntimeError("down")):
                self.assertEqual(research.tavily_with_retry("q"), [])
                self.assertEqual(research.tavily_post("extract", {}), {})
            with mock.patch.object(research.urllib.request, "urlopen", side_effect=error(500)):
                with self.assertRaises(urllib.error.HTTPError):
                    research.tavily_post("extract", {})
                self.assertEqual(research.tavily_extract(["https://a.com"]), [])

    def test_extract_filters_blocked_hosts_and_trims(self):
        with mock.patch.object(research, "tavily_post", return_value={"results": [{"url": "https://a.com", "raw_content": "x" * 6000, "title": "T"}, {"url": "b"}]}) as post:
            rows = research.tavily_extract(["https://a.com", "https://glassdoor.com/x"])
        self.assertEqual(post.call_args.args[1]["urls"], ["https://a.com"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(research.tavily_extract([]), [])

    def test_company_research_dedupes_ranks_and_drops_blocked_pages(self):
        rows = [{"url": "https://acme.com/careers", "title": "Careers", "content": "official"}, {"url": "https://acme.com/careers/", "title": "dupe", "content": "d"},
                {"url": "https://reddit.com/r/x", "title": "R", "content": "Just a moment"}, {"url": "https://youtu.be/z", "title": "Y", "content": "video"},
                {"url": "", "title": "no url", "content": ""}]
        with mock.patch.object(research, "tavily_search", return_value=rows), \
                mock.patch.object(research, "tavily_extract", return_value=[{"url": "https://acme.com/careers", "content": "full text", "title": "Full"}]):
            out = research.collect_company_research("Acme", "SDM")
        urls = [r["url"] for r in out]
        self.assertEqual(urls[0], "https://acme.com/careers")
        self.assertEqual(out[0]["content"], "full text")
        self.assertNotIn("https://reddit.com/r/x", urls)  # a bot-wall page is dropped

    def test_round_discovery_uses_artifacts_then_defaults(self):
        role = {"interview_round_map": [{"round_name": "HM Screen", "what_it_tests": "fit"}, {"round_name": ""}, "junk", {"round_name": "hm screen"}]}
        company = {"interview_process_signals": [{"signal": "Onsite loop", "what_it_tests": "depth"}, {"signal": "a very long signal that has more than eight words in it"}, "junk"]}
        names = [r["round_name"] for r in research.discover_interview_rounds(company, role, "Acme", "SDM")]
        self.assertEqual(names, ["HM Screen", "Onsite loop"])
        self.assertEqual(len(research.discover_interview_rounds({}, {}, "Acme", "SDM")), 6)

    def test_round_queries_depend_on_the_round_type(self):
        for kind, marker in (("behavioral", "tell me about a time"), ("technical", "technical interview"), ("cross stakeholder", "stakeholder"),
                             ("values culture", "googliness"), ("other", "what to expect")):
            queries = research.build_round_queries("Acme", "SDM", "Round", kind, "tests things")
            self.assertTrue(any(marker in q.lower() for q in queries), kind)
            self.assertLessEqual(len(queries), 25)
        self.assertTrue(research.build_round_queries("Acme", "SDM", "Round", "other", ""))

    def test_reported_questions_come_only_from_community_sources(self):
        text = "1. How do you handle a missed SLA with a client?\n- Tell me about a time you led a team through change\nWhat is your salary expectation here today?\nSign in to read more questions now?"
        sources = [{"source_type": "Reddit directional theme", "content": text, "url": "u"}, {"source_type": "Official company source", "content": text},
                   {"source_type": "Blind directional theme", "content": ""}]
        out = research.extract_round_reported_questions(sources)
        questions_ = [r["question"] for r in out]
        self.assertIn("How do you handle a missed SLA with a client?", questions_)
        self.assertTrue(any(q.startswith("Tell me about a time") for q in questions_))
        self.assertFalse(any("salary" in q.lower() or "sign in" in q.lower() for q in questions_))

    def test_per_round_research_and_the_parallel_runner(self):
        rows = [{"url": "https://reddit.com/r/a", "title": "R", "content": "How do you handle a missed SLA with a client?"}]
        with mock.patch.object(research, "tavily_with_retry", return_value=rows), mock.patch.object(research, "tavily_extract", return_value=[]):
            result = research.collect_per_round_research("Acme", "SDM", "HM", "behavioral", "fit")
        self.assertEqual(result["round_name"], "HM")
        self.assertTrue(result["reported_questions"])
        rounds = [{"round_name": "A", "round_type": "x", "what_it_tests": ""}, {"round_name": "B", "round_type": "x", "what_it_tests": ""}]

        def fake(company, role, name, kind, tests):
            if name == "B":
                raise RuntimeError("boom")
            return {"round_name": name, "sources": [], "reported_questions": []}
        with mock.patch.object(research, "collect_per_round_research", side_effect=fake):
            out = research.run_all_rounds_research("Acme", "SDM", rounds)
        self.assertEqual(sorted(r["round_name"] for r in out), ["A", "B"])

    def test_company_and_role_intelligence_modules(self):
        sources = [{"url": "https://acme.com/a", "title": "A", "content": "c", "source_type": "Official company source", "source_confidence": "high"}]
        reply = {"official_company_signals": [{"signal": "s", "source_url": "https://other.com"}, {"signal": "t", "source_url": "https://acme.com/a"}, "junk"]}
        with mock.patch.object(research, "collect_company_research", return_value=sources), mock.patch.object(research, "ask_json", return_value=reply), \
                mock.patch.object(research.apps, "write_research") as written:
            result = research.run_company_intelligence_module(SESSION)
        self.assertEqual(result["official_company_signals"][0]["source_url"], "")
        self.assertEqual(result["official_company_signals"][1]["source_url"], "https://acme.com/a")
        self.assertEqual(len(result["source_manifest"]), 1)
        self.assertTrue(written.called)
        with mock.patch.object(research, "ask_json", return_value={"role_domain": "ops"}), mock.patch.object(research.apps, "write_jd_map") as jd:
            self.assertEqual(research.run_role_intelligence_module(SESSION)["role_domain"], "ops")
        self.assertTrue(jd.called)

    def test_company_signals(self):
        self.assertEqual(research.company_signal_text({"theme": " growth  focus "}), "growth focus")
        self.assertEqual(research.company_signal_text("plain"), "plain")
        self.assertTrue(research.company_signal_has_source({"source_url": "u"}))
        self.assertFalse(research.company_signal_has_source("x"))
        specific = {"official_company_signals": [{"signal": "Acme runs a six week onboarding programme for new operations leads", "source_url": "https://acme.com"}]}
        self.assertTrue(research.has_specific_company_signal(specific))
        self.assertFalse(research.has_specific_company_signal({"official_company_signals": [{"signal": "short", "source_url": "u"}], "directional_themes": ["x"]}))
        self.assertFalse(research.has_specific_company_signal({}))


class StrategyHelpersTest(InTempDir):
    PROFILE = {"story_inventory": [{"story_name": "Backlog", "metrics": ["40%"]}], "positioning_statement": "ops leader"}

    def test_the_first_sentence_is_replaced(self):
        self.assertEqual(questions.replace_first_sentence("Old one. Keep this.", "New opening"), "New opening. Keep this.")
        self.assertEqual(questions.replace_first_sentence("No terminator here", "Open."), "Open. No terminator here")

    def test_opening_repair_falls_back_when_the_model_breaks_the_rules(self):
        with mock.patch.object(questions, "ask_llm", return_value="In my previous role I did it"):
            out = questions.repair_answer_opening("Q?", "Old start. Rest of it.", "Backlog", SESSION, self.PROFILE)
        self.assertTrue(out.startswith("The operating problem was specific"))
        with mock.patch.object(questions, "ask_llm", return_value="The backlog hit 40 percent"):
            self.assertTrue(questions.repair_answer_opening("Q?", "Old start. Rest.", "S", SESSION, self.PROFILE).startswith("The backlog hit"))

    def test_modular_answers_are_kept_when_good_and_rewritten_when_not(self):
        good = "The backlog had hit forty percent. " + WORDS
        self.assertEqual(questions.ensure_modular_answer("Q?", good, "S", SESSION, self.PROFILE, {}), good)
        bad = "In my previous role, I did a thing. Short answer."
        with mock.patch.object(questions, "ask_llm", return_value="In my previous role, " + WORDS) as ask:
            out = questions.ensure_modular_answer("Q?", bad, "S", SESSION, self.PROFILE, {})
        self.assertTrue(out.startswith("The stake was clear"))
        self.assertEqual(ask.call_count, 1)
        with mock.patch.object(questions, "ask_llm", return_value="tiny"):
            padded = questions.ensure_modular_answer("Q?", "Short.", "S", SESSION, self.PROFILE, {})
        self.assertIn("overclaim", padded)
        with mock.patch.object(questions, "ask_llm", side_effect=["Recognizing the need " + WORDS, "The backlog was the problem"]):
            repaired = questions.ensure_modular_answer("Q?", "Short.", "S", SESSION, self.PROFILE, {})
        self.assertTrue(repaired.startswith("The backlog was the problem"))

    def test_extra_questions_are_generated_only_when_needed(self):
        self.assertEqual(questions.generate_additional_round_questions(SESSION, {}, 0, {}, {}, {}, {}), [])
        reply = {"questions": [{"question": "Q1?", "complete_written_answer": WORDS}, "junk", {"question": "Q2?", "complete_written_answer": WORDS}]}
        with mock.patch.object(questions, "ask_json", return_value=reply):
            rows = questions.generate_additional_round_questions(SESSION, {"round_name": "HM"}, 2, {}, {}, self.PROFILE, {})
        self.assertEqual([r["question"] for r in rows], ["Q1?"])  # junk consumed a slot
        with mock.patch.object(questions, "ask_json", return_value={}):
            self.assertEqual(questions.generate_additional_round_questions(SESSION, "round", 3, {}, {}, {}, {}), [])

    def test_why_company_and_why_role_answers(self):
        self.assertIn("Acme", questions.insufficient_why_company_answer({}, "Acme"))
        thin = questions.insufficient_why_company_answer({"official_company_signals": [{"signal": "runs ops"}], "directional_themes": ["x"]}, "Acme", self.PROFILE)
        self.assertIn("Backlog", thin)
        specific = {"official_company_signals": [{"signal": "Acme runs a six week onboarding programme for new operations leads", "source_url": "https://acme.com"}]}
        self.assertIn("Acme", questions.repair_why_company_answer({}, SESSION, {}, self.PROFILE))  # no signal: the minimal answer
        keep = "Acme runs a distinctive six week onboarding programme and my queue work fits it directly."
        self.assertEqual(questions.repair_why_company_answer({"why_this_company_answer": keep}, SESSION, specific, self.PROFILE), keep)
        with mock.patch.object(questions, "ask_llm", return_value="Acme is a leader in innovation and culture"):
            self.assertIn("What draws me to Acme", questions.repair_why_company_answer({}, SESSION, specific, self.PROFILE))
        with mock.patch.object(questions, "ask_llm", return_value="Acme's onboarding programme matches my record of cutting a backlog quickly."):
            self.assertIn("onboarding programme matches", questions.repair_why_company_answer({}, SESSION, specific, self.PROFILE))
        long = " ".join(["role"] * 90)
        self.assertEqual(questions.repair_why_role_answer({"why_this_role_answer": long}, SESSION, {}, self.PROFILE), long)
        with mock.patch.object(questions, "ask_llm", return_value=""):
            self.assertIn("This role makes sense", questions.repair_why_role_answer({}, SESSION, {"must_prove_signals": ["Own SLAs"]}, self.PROFILE))
        with mock.patch.object(questions, "ask_llm", return_value=" ".join(["fit"] * 60)):
            self.assertEqual(len(questions.repair_why_role_answer({}, SESSION, {}, {}).split()), 60)

    def test_normalising_a_strategy_fills_rounds_and_repairs_answers(self):
        strategy = {"round_by_round_plan": [{"round_name": "HM"}, {"round_name": ""}, "junk"], "questions_by_round": [
            {"round_name": "Loop", "questions": [{"question": "Q?", "complete_written_answer": "In my previous role " + WORDS, "assigned_story": "S"}, "junk"]}, "junk"]}
        with mock.patch.object(questions, "ask_llm", return_value="The backlog hit 40% of volume. " + WORDS), \
                mock.patch.object(questions, "ask_json", return_value={"questions": []}), \
                mock.patch.object(questions, "repair_why_company_answer", return_value="why company"), \
                mock.patch.object(questions, "repair_why_role_answer", return_value="why role"):
            out = questions.normalize_modular_strategy(strategy, SESSION, {}, {}, self.PROFILE, {})
        self.assertEqual({r["round_name"] for r in out["questions_by_round"] if isinstance(r, dict)}, {"Loop", "HM"})
        self.assertEqual((out["why_this_company_answer"], out["why_this_role_answer"]), ("why company", "why role"))


class StrategyModuleTest(InTempDir):
    def seed(self, **overrides):
        artifacts = {"company_intelligence": {"a": 1, "b": 2, "c": 3}, "role_intelligence": {"a": 1, "b": 2, "c": 3},
                     "candidate_profile": {"story_inventory": [{"story_name": "Backlog"}], "positioning_statement": "ops", "forbidden_claims": [{"claim": "x"}],
                                           "confirmed_evidence": [{"claim": "c", "story": "s"}]},
                     "gap_map": {"a": 1, "b": 2, "c": 3, "repair_scripts": [{"gap": "g"}]}}
        artifacts.update(overrides)
        for name, data in artifacts.items():
            common.write_module_json("s1", name, data)

    def test_missing_or_thin_inputs_stop_the_strategy_early(self):
        with self.assertRaisesRegex(ValueError, "role_intelligence module must complete"):
            questions.run_interview_strategy_module(SESSION)
        self.seed(gap_map={"only": 1})
        with self.assertRaisesRegex(ValueError, "empty or incomplete"):
            questions.run_interview_strategy_module(SESSION)

    def test_the_strategy_is_built_validated_and_saved(self):
        self.seed()
        research_rows = [{"round_name": "HM", "reported_questions": [{"question": "Q reported?", "source_type": "Reddit"}],
                          "sources": [{"url": "https://glassdoor.com/x"}, {"url": "https://reddit.com/x"}, {"url": "https://teamblind.com/x"}]}, {"round_name": "Empty"}]
        strategy = {"executive_win_strategy": "win", "round_by_round_plan": [{"round_name": "HM"}], "questions_by_round": [{"round_name": "HM", "questions": [{"question": "Q?"}]}]}
        with mock.patch.object(questions, "discover_interview_rounds", return_value=[{"round_name": "HM"}]), \
                mock.patch.object(questions, "run_all_rounds_research", return_value=research_rows), \
                mock.patch.object(questions, "ask_json", return_value=strategy), \
                mock.patch.object(questions, "normalize_modular_strategy", side_effect=lambda s, *a: s), \
                mock.patch.object(questions.apps, "write_questions") as write:
            result = questions.run_interview_strategy_module(SESSION)
        self.assertEqual(result["executive_win_strategy"], "win")
        self.assertTrue(write.called)
        with mock.patch.object(questions, "discover_interview_rounds", return_value=[]), mock.patch.object(questions, "run_all_rounds_research", return_value=[]), \
                mock.patch.object(questions, "ask_json", return_value={}), self.assertRaisesRegex(ValueError, "no usable output"):
            questions.run_interview_strategy_module(SESSION)
        with mock.patch.object(questions, "discover_interview_rounds", return_value=[]), mock.patch.object(questions, "run_all_rounds_research", return_value=[]), \
                mock.patch.object(questions, "ask_json", return_value=strategy), mock.patch.object(questions, "normalize_modular_strategy", return_value={"questions_by_round": [{}]}), \
                self.assertRaisesRegex(ValueError, "no usable questions"):
            questions.run_interview_strategy_module(SESSION)

    def full_strategy(self, **overrides):
        answer = " ".join(["The backlog was cut sharply."] * 40)
        strategy = {"executive_win_strategy": " ".join(["win"] * 30), "why_this_company_answer": " ".join(["company"] * 30), "why_this_role_answer": " ".join(["role"] * 90),
                    "round_by_round_plan": [{"round_name": "HM", "what_this_round_tests": "fit", "specific_preparation_actions": []}, "junk"],
                    "questions_by_round": [{"round_name": "HM", "questions": [{"question": "Q?", "complete_written_answer": answer}, "junk"]}, "junk"],
                    "dangerous_questions": [{"question": "d"}], "do_not_say": [{"item": "x"}], "thirty_sixty_ninety": {"30_days": ["a"], "60_days": ["b"], "90_days": ["c"]},
                    "questions_to_ask": ["q"], "seven_day_plan": [{"day": "1", "actions": ["a"]}]}
        strategy.update(overrides)
        return strategy

    def test_the_prep_pack_is_assembled_and_checked(self):
        self.seed(company_intelligence={"official_company_signals": [{"signal": "s", "confidence": "high", "source_url": "u"}, "junk"], "interview_process_signals": [{"signal": "p"}]},
                  role_intelligence={"must_prove": [{"signal": "m", "why_it_matters": "w"}]})
        common.write_module_json("s1", "interview_strategy", self.full_strategy())
        with mock.patch.object(questions, "repair_why_company_answer", side_effect=lambda s, *a: s["why_this_company_answer"]), \
                mock.patch.object(questions, "repair_why_role_answer", side_effect=lambda s, *a: s["why_this_role_answer"]):
            pack = questions.run_prep_pack_module(SESSION)
        self.assertIn("# Interview Prep Pack", pack["markdown"])
        self.assertIn("## EVIDENCE LEDGER", pack["markdown"])
        self.assertTrue(Path(pack["path"]).exists())

    def test_a_prep_pack_with_missing_parts_or_template_text_is_refused(self):
        self.seed()
        patches = (mock.patch.object(questions, "repair_why_company_answer", side_effect=lambda s, *a: s.get("why_this_company_answer", "")),
                   mock.patch.object(questions, "repair_why_role_answer", side_effect=lambda s, *a: s.get("why_this_role_answer", "")))
        with patches[0], patches[1]:
            common.write_module_json("s1", "interview_strategy", self.full_strategy(executive_win_strategy="", round_by_round_plan=[]))
            with self.assertRaisesRegex(ValueError, "required-field check"):
                questions.run_prep_pack_module(SESSION)
            short = self.full_strategy(questions_by_round=[{"round_name": "HM", "questions": [{"question": "Q?", "complete_written_answer": "too short"}]}])
            common.write_module_json("s1", "interview_strategy", short)
            with self.assertRaisesRegex(ValueError, "under 180 words"):
                questions.run_prep_pack_module(SESSION)
            common.write_module_json("s1", "interview_strategy", self.full_strategy(do_not_say=[{"item": "Research insufficient"}], thirty_sixty_ninety="junk"))
            with self.assertRaisesRegex(ValueError, "assembly validation"):
                questions.run_prep_pack_module(SESSION)

    def test_run_session_module_routes_to_the_right_module_and_logs_cost(self):
        for name, target in (("company_intelligence", "run_company_intelligence_module"), ("role_intelligence", "run_role_intelligence_module"),
                             ("candidate_profile", "run_candidate_profile_module"), ("gap_map", "run_gap_map_module"),
                             ("interview_strategy", "run_interview_strategy_module")):
            with mock.patch.object(questions, target, return_value={"ok": name}):
                out = questions.run_session_module(SESSION, name)
            self.assertEqual(out["product_json"], {"ok": name})
            self.assertTrue(out["output_file"].endswith(f"{name}.json"))
        with mock.patch.object(questions, "run_prep_pack_module", return_value={"markdown": "# m", "path": "p"}):
            self.assertEqual(questions.run_session_module(SESSION, "prep_pack")["markdown"], "# m")
        with self.assertRaisesRegex(ValueError, "Unknown module"):
            questions.run_session_module(SESSION, "nonsense")


if __name__ == "__main__":
    unittest.main()
