"""
Tests for the robot app (models, serializers, analysis pipeline, LLM client).
"""
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from django.test import TestCase, SimpleTestCase
from django.utils import timezone as django_timezone

from authentication.models import CustomUser
from reversewebsearch.models import WebsearchResults
from .models import RobotAnalysis
from .serializers import RobotAnalysisSerializer
from .analysis_pipeline import (
    _compute_crawl_status,
    _rules_based_assessment,
    _rules_based_verdict,
)
from .llm_client import (
    _parse_llm_response,
    _default_verdict,
    _fix_overcautious_verdict,
    build_analysis_prompt,
    _load_trusted_domains,
    _get_credible_domains,
    _get_government_domains,
    _get_tier1_news_domains,
    _get_tier1_african_domains,
    _credible_source_cited_in_evidence,
    _detect_crawl_anomalies,
    get_openrouter_client,
    analyze_with_openrouter,
    VALID_VERDICTS,
)


# ═══════════════════════════════════════════════════════════════
#  Model & Serializer Tests
# ═══════════════════════════════════════════════════════════════

class RobotAnalysisModelTests(TestCase):
    """Tests for the RobotAnalysis model."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="test@example.com", password="pwd"
        )
        self.websearch = WebsearchResults.objects.create(
            user=self.user, query="test query", results={}
        )

    def test_create_robot_analysis(self):
        """Creating a RobotAnalysis with minimal fields should succeed."""
        analysis = RobotAnalysis.objects.create(
            websearch_result=self.websearch,
            verdict="real",
            confidence_score=0.85,
            short_summary="This is real news",
            explanation="Detailed reasoning here",
            key_evidence=["Evidence 1", "Evidence 2"],
        )
        self.assertIsNotNone(analysis.id)
        self.assertEqual(analysis.verdict, "real")
        self.assertEqual(analysis.confidence_score, 0.85)
        self.assertEqual(analysis.short_summary, "This is real news")
        self.assertEqual(analysis.key_evidence, ["Evidence 1", "Evidence 2"])
        self.assertIsNotNone(analysis.created_at)

    def test_all_verdict_choices_valid(self):
        """All 4 verdict choices are valid and storable."""
        verdicts = ["real", "fake", "suspicious", "unconfirmed"]
        for i, verdict in enumerate(verdicts):
            ws = WebsearchResults.objects.create(
                user=self.user, query=f"test {verdict}", results={}
            )
            analysis = RobotAnalysis.objects.create(
                websearch_result=ws,
                verdict=verdict,
                confidence_score=0.5,
                short_summary=f"Test {verdict}",
                explanation="Test explanation",
            )
            self.assertEqual(analysis.verdict, verdict)

    def test_str_method(self):
        """__str__ returns a formatted string with verdict, query, and confidence."""
        analysis = RobotAnalysis.objects.create(
            websearch_result=self.websearch,
            verdict="fake",
            confidence_score=0.75,
            short_summary="Fake news detected",
            explanation="Detailed reasoning",
        )
        result_str = str(analysis)
        self.assertIn("fake", result_str)
        self.assertIn("75%", result_str)  # 0.75 formatted as 75%

    def test_research_fields_defaults(self):
        """research_queries and research_report should default to [] and {}."""
        analysis = RobotAnalysis.objects.create(
            websearch_result=self.websearch,
            verdict="real",
            confidence_score=0.9,
            short_summary="Summary",
            explanation="Explanation",
        )
        self.assertEqual(analysis.research_queries, [])
        self.assertEqual(analysis.research_report, {})

    def test_one_to_one_relation(self):
        """RobotAnalysis has a OneToOneField to WebsearchResults."""
        analysis = RobotAnalysis.objects.create(
            websearch_result=self.websearch,
            verdict="real",
            confidence_score=0.9,
            short_summary="Summary",
            explanation="Explanation",
        )
        self.assertEqual(analysis.websearch_result, self.websearch)
        # Reverse relation should work
        self.assertEqual(self.websearch.robot_analysis, analysis)

    def test_confidence_score_range(self):
        """Confidence score can be 0.0 to 1.0."""
        analysis = RobotAnalysis.objects.create(
            websearch_result=self.websearch,
            verdict="unconfirmed",
            confidence_score=0.0,
            short_summary="Low confidence",
            explanation="No evidence",
        )
        self.assertEqual(analysis.confidence_score, 0.0)
        analysis.confidence_score = 1.0
        analysis.save()
        analysis.refresh_from_db()
        self.assertEqual(analysis.confidence_score, 1.0)


class RobotAnalysisSerializerTests(TestCase):
    """Tests for the RobotAnalysisSerializer."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="test@example.com", password="pwd"
        )
        self.websearch = WebsearchResults.objects.create(
            user=self.user, query="test", results={}
        )
        self.analysis = RobotAnalysis.objects.create(
            websearch_result=self.websearch,
            verdict="suspicious",
            confidence_score=0.65,
            short_summary="Suspicious content",
            explanation="Some red flags detected",
            key_evidence=["Flag 1", "Flag 2"],
        )

    def test_serializer_fields(self):
        """Serializer should include all expected fields."""
        serializer = RobotAnalysisSerializer(self.analysis)
        data = serializer.data
        expected_fields = [
            "id", "verdict", "confidence_score", "short_summary",
            "explanation", "key_evidence", "research_queries",
            "research_report", "created_at",
        ]
        for field in expected_fields:
            self.assertIn(field, data)

    def test_serializer_read_only_id(self):
        """ID should be included and be a string (UUID)."""
        serializer = RobotAnalysisSerializer(self.analysis)
        self.assertIsInstance(serializer.data["id"], str)


# ═══════════════════════════════════════════════════════════════
#  Analysis Pipeline Unit Tests (SimpleTestCase — no DB)
# ═══════════════════════════════════════════════════════════════

class ComputeCrawlStatusTests(SimpleTestCase):
    """Tests for _compute_crawl_status()."""

    def test_all_successful(self):
        """All 10 candidates successfully crawled."""
        candidates = [
            {"crawl_data": {"crawl_status": "success"}, "domain": f"site{i}.com"}
            for i in range(10)
        ]
        result = _compute_crawl_status(candidates)
        self.assertEqual(result["results_crawled"], 10)
        self.assertEqual(result["successful_crawls"], 10)
        self.assertEqual(result["failed_crawls"], 0)
        self.assertEqual(result["failed_domains"], [])

    def test_mixed_success_failure(self):
        """Mixed crawl results should count correctly."""
        candidates = [
            {"crawl_data": {"crawl_status": "success"}, "domain": "good.com"},
            {"crawl_data": {"crawl_status": "success"}, "domain": "good2.com"},
            {"crawl_data": {"crawl_status": "failed"}, "domain": "bad.com"},
            {"crawl_data": {"crawl_status": "failed"}, "domain": "bad2.com"},
            {"crawl_data": {}, "domain": "no-data.com"},
        ]
        result = _compute_crawl_status(candidates)
        self.assertEqual(result["results_crawled"], 4)  # 4 have status
        self.assertEqual(result["successful_crawls"], 2)
        self.assertEqual(result["failed_crawls"], 2)
        self.assertIn("bad.com", result["failed_domains"])

    def test_paywall_success(self):
        """Paywall-detected success still counts as successful."""
        candidates = [
            {"crawl_data": {"crawl_status": "success", "paywall_detected": True}, "domain": "paywalled.com"},
        ]
        result = _compute_crawl_status(candidates)
        self.assertEqual(result["successful_crawls"], 1)
        self.assertIn("paywalled.com (paywall)", result["failed_domains"])

    def test_no_crawl_data(self):
        """Candidates without crawl_data are skipped."""
        candidates = [{"domain": "no-crawl.com"}]
        result = _compute_crawl_status(candidates)
        self.assertEqual(result["results_crawled"], 0)

    def test_no_failed_domains_when_none_fail(self):
        """When all succeed, failed_domains should be empty."""
        candidates = [
            {"crawl_data": {"crawl_status": "success"}, "domain": "a.com"}
            for _ in range(5)
        ]
        result = _compute_crawl_status(candidates)
        self.assertEqual(result["failed_domains"], [])


class RulesBasedVerdictTests(SimpleTestCase):
    """Tests for _rules_based_verdict()."""

    def test_strong_negative_signals_fake(self):
        """3+ negative signals, 0-1 positive → fake."""
        assessment = {
            "date_anomaly": "All dated sources published within 24 hours — possible coordinated push",
            "trust_anomaly": "4+ of top 5 sources are from untrusted domains — credibility concern",
            "top_5_untrusted_count": 4,
            "corroboration": "Results from only one engine — limited cross-validation",
            "source_quality": "Only 3 sources found — limited evidence",
            "trusted_domain_ratio": "10%",
        }
        verdict = _rules_based_verdict(assessment)
        self.assertEqual(verdict["verdict"], "fake")
        self.assertGreaterEqual(verdict["confidence"], 0.55)

    def test_strong_positive_signals_real(self):
        """3+ positive signals → real."""
        assessment = {
            "date_anomaly": "Sources span 5 days — natural spread",
            "trust_anomaly": "Top sources are from reasonably trusted domains",
            "corroboration": "Results corroborated by multiple search engines",
            "source_quality": "30 sources — robust evidence",
            "trusted_domain_ratio": "70%",
            "top_5_untrusted_count": 0,
        }
        verdict = _rules_based_verdict(assessment)
        self.assertEqual(verdict["verdict"], "real")
        self.assertGreaterEqual(verdict["confidence"], 0.6)

    def test_neutral_signals_unconfirmed(self):
        """No strong signals → unconfirmed."""
        assessment = {
            "date_anomaly": "Too few parseable dates to analyze",
            "trust_anomaly": "2 of top 5 sources are from untrusted domains",
            "corroboration": "Results from only one engine — limited cross-validation",
            "source_quality": "Only 3 sources found — limited evidence",
            "trusted_domain_ratio": "0%",
            "top_5_untrusted_count": 2,
        }
        verdict = _rules_based_verdict(assessment)
        self.assertEqual(verdict["verdict"], "unconfirmed")
        self.assertLessEqual(verdict["confidence"], 0.4)

    def test_verdict_has_explanation(self):
        """Verdict dict should have explanation mentioning 'Rules-based'."""
        assessment = {
            "date_anomaly": "Too few parseable dates to analyze",
            "trust_anomaly": "2 of top 5 sources are from untrusted domains",
            "corroboration": "Results from only one engine",
            "source_quality": "Only 3 sources found",
            "trusted_domain_ratio": "0%",
            "top_5_untrusted_count": 2,
        }
        verdict = _rules_based_verdict(assessment)
        self.assertIn("explanation", verdict)
        self.assertIn("Rules-based", verdict["explanation"])


class DefaultVerdictTests(SimpleTestCase):
    """Tests for _default_verdict()."""

    def test_default_verdict_structure(self):
        """_default_verdict returns the expected dict structure."""
        verdict = _default_verdict()
        expected_keys = {"verdict", "confidence", "short_summary", "explanation", "key_evidence"}
        self.assertEqual(set(verdict.keys()), expected_keys)
        self.assertEqual(verdict["verdict"], "unconfirmed")
        self.assertEqual(verdict["confidence"], 0.0)
        self.assertIsInstance(verdict["key_evidence"], list)
        self.assertEqual(verdict["key_evidence"], [])


# ═══════════════════════════════════════════════════════════════
#  LLM Client Tests (SimpleTestCase — no DB)
# ═══════════════════════════════════════════════════════════════

class ParseLlmResponseTests(SimpleTestCase):
    """Tests for _parse_llm_response()."""

    def test_valid_json(self):
        """Valid JSON response is parsed correctly."""
        response = json.dumps({
            "verdict": "real",
            "confidence": 0.85,
            "short_summary": "This is true",
            "explanation": "Multiple credible sources confirm",
            "key_evidence": ["Source A says X"],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["verdict"], "real")
        self.assertEqual(result["confidence"], 0.85)
        self.assertEqual(result["short_summary"], "This is true")
        self.assertEqual(result["explanation"], "Multiple credible sources confirm")
        self.assertEqual(result["key_evidence"], ["Source A says X"])

    def test_markdown_code_fences(self):
        """Markdown ```json ... ``` fences should be stripped."""
        response = '```json\n{"verdict": "fake", "confidence": 0.9, "short_summary": "F", "explanation": "E", "key_evidence": []}\n```'
        result = _parse_llm_response(response)
        self.assertEqual(result["verdict"], "fake")
        self.assertEqual(result["confidence"], 0.9)

    def test_invalid_json(self):
        """Invalid JSON returns default verdict."""
        response = "not json at all"
        result = _parse_llm_response(response)
        self.assertEqual(result["verdict"], "unconfirmed")
        self.assertEqual(result["confidence"], 0.0)

    def test_verdict_normalization(self):
        """Verdict should be lowercased and trimmed."""
        response = json.dumps({
            "verdict": " REAL ",
            "confidence": 0.8,
            "short_summary": "S",
            "explanation": "E",
            "key_evidence": [],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["verdict"], "real")

    def test_invalid_verdict_falls_back(self):
        """Unknown verdict value falls back to 'unconfirmed'."""
        response = json.dumps({
            "verdict": "maybe",
            "confidence": 0.5,
            "short_summary": "S",
            "explanation": "E",
            "key_evidence": [],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["verdict"], "unconfirmed")

    def test_confidence_clamping_low(self):
        """Confidence below 0.0 is clamped to 0.0."""
        response = json.dumps({
            "verdict": "fake", "confidence": -0.5,
            "short_summary": "S", "explanation": "E", "key_evidence": [],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["confidence"], 0.0)

    def test_confidence_clamping_high(self):
        """Confidence above 1.0 is clamped to 1.0."""
        response = json.dumps({
            "verdict": "real", "confidence": 1.5,
            "short_summary": "S", "explanation": "E", "key_evidence": [],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["confidence"], 1.0)

    def test_confidence_non_numeric(self):
        """Non-numeric confidence defaults to 0.0."""
        response = json.dumps({
            "verdict": "real", "confidence": "high",
            "short_summary": "S", "explanation": "E", "key_evidence": [],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["confidence"], 0.0)

    def test_missing_short_summary(self):
        """Missing short_summary defaults to empty string."""
        response = json.dumps({
            "verdict": "real", "confidence": 0.9,
            "explanation": "E", "key_evidence": [],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["short_summary"], "")

    def test_missing_explanation(self):
        """Missing explanation defaults to 'No explanation provided.'"""
        response = json.dumps({
            "verdict": "real", "confidence": 0.9,
            "short_summary": "S", "key_evidence": [],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["explanation"], "No explanation provided.")

    def test_key_evidence_not_a_list(self):
        """Non-list key_evidence defaults to []."""
        response = json.dumps({
            "verdict": "real", "confidence": 0.9,
            "short_summary": "S", "explanation": "E",
            "key_evidence": "string not list",
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["key_evidence"], [])


class FixOvercautiousVerdictTests(SimpleTestCase):
    """Tests for _fix_overcautious_verdict()."""

    def test_unconfirmed_no_credible_source_no_upgrade(self):
        """unconfirmed with no credible source in stats stays unchanged."""
        verdict = {"verdict": "unconfirmed", "confidence": 0.55, "explanation": "Some evidence", "key_evidence": []}
        statistics = {"government_sources": 0, "tier1_news_sources": 0, "credible_local_news_sources": 0, "total_sources": 1}
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "unconfirmed")

    def test_govt_source_present_upgraded(self):
        """govt source present + evidence cites credible domain → upgrade to 'real'."""
        # reuters.com is in the default credible domains list
        statistics = {"government_sources": 1, "tier1_news_sources": 0, "credible_local_news_sources": 0, "total_sources": 5}
        verdict = {
            "verdict": "unconfirmed",
            "confidence": 0.70,
            "explanation": "Confirmed by reuters.com",
            "key_evidence": ["reuters.com reported on this"],
        }
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "real")

    def test_govt_plus_tier1_upgraded_to_real(self):
        """Govt + tier1 in stats + credible source cited in evidence → upgrade 'likely' to 'real'."""
        # Note: 'likely' is NOT in the upgrade targets (only unconfirmed/suspicious)
        # This test verifies 'likely' stays unchanged since it's intentionally cautious
        statistics = {"government_sources": 1, "tier1_news_sources": 2, "credible_local_news_sources": 0, "total_sources": 5}
        verdict = {"verdict": "likely", "confidence": 0.75, "explanation": "bbc.com confirms this story", "key_evidence": []}
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "likely")

    def test_self_contradicting_explanation_no_upgrade(self):
        """Explanation with positive language but no credible source cited stays unchanged."""
        verdict = {
            "verdict": "unconfirmed",
            "confidence": 0.60,
            "explanation": "The claim is supported by credible sources. Multiple sources confirm it.",
            "key_evidence": [],
        }
        # total_sources < 3 so Rule 2 (many sources upgrade) does NOT trigger
        statistics = {"government_sources": 0, "tier1_news_sources": 0, "credible_local_news_sources": 0, "total_sources": 2}
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "unconfirmed")

    def test_suspicious_no_credible_source_no_upgrade(self):
        """suspicious with no credible source in stats stays unchanged."""
        verdict = {"verdict": "suspicious", "confidence": 0.75, "explanation": "Some evidence", "key_evidence": []}
        statistics = {"government_sources": 0, "tier1_news_sources": 0, "credible_local_news_sources": 0, "total_sources": 1}
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "suspicious")

    def test_no_change_when_no_issues(self):
        """Correct verdicts should remain unchanged."""
        verdict = {"verdict": "real", "confidence": 0.85, "explanation": "All good", "key_evidence": []}
        statistics = {"government_sources": 0, "tier1_news_sources": 0, "credible_local_news_sources": 0, "total_sources": 1}
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "real")
        self.assertEqual(result["confidence"], 0.85)

    def test_no_credible_source_but_many_sources_upgraded_to_likely(self):
        """No authoritative source but >=3 sources → upgrade to 'likely'."""
        verdict = {"verdict": "unconfirmed", "confidence": 0.50, "explanation": "Some sources found", "key_evidence": ["source1", "source2"]}
        statistics = {"government_sources": 0, "tier1_news_sources": 0, "credible_local_news_sources": 0, "total_sources": 3}
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "likely")

    def test_credible_source_cited_with_key_evidence(self):
        """Credible domain cited in key_evidence triggers upgrade."""
        statistics = {"government_sources": 0, "tier1_news_sources": 1, "credible_local_news_sources": 0, "total_sources": 5}
        verdict = {
            "verdict": "suspicious",
            "confidence": 0.60,
            "explanation": "Some concerns",
            "key_evidence": ["reuters.com published a detailed article"],
        }
        result = _fix_overcautious_verdict(verdict, statistics)
        self.assertEqual(result["verdict"], "real")


class BuildAnalysisPromptTests(SimpleTestCase):
    """Tests for build_analysis_prompt()."""

    def test_prompt_contains_expected_sections(self):
        """The prompt should contain key sections."""
        prompt = build_analysis_prompt(
            query="Is this claim true?",
            top_candidates=[
                {
                    "domain": "example.com",
                    "title": "Example Article",
                    "score": 10,
                    "engine": "openwebninja",
                    "publish_date": "2024-01-15",
                    "crawl_data": {"crawl_status": "success", "raw_snippet": "Some content here"},
                }
            ],
            timeline=[{"date": "2024-01-15", "domain": "example.com", "url": "https://example.com"}],
            statistics={"total_sources": 10, "trusted_domains": 5, "government_sources": 1,
                        "tier1_news_sources": 2, "unique_domains": 8, "with_publish_date": 5},
            rules_assessment={"date_anomaly": "Natural spread", "trust_anomaly": "Good domains"},
        )
        self.assertIn("THE USER'S CLAIM TO FACT-CHECK", prompt)
        self.assertIn("Is this claim true?", prompt)
        self.assertIn("SOURCE CREDIBILITY", prompt)
        self.assertIn("Source Quality Summary", prompt)
        self.assertIn("Crawl Status", prompt)
        self.assertIn("Ranked Search Results", prompt)
        self.assertIn("Publication Timeline", prompt)
        self.assertIn("Statistics", prompt)
        self.assertIn("Output Format", prompt)

    def test_prompt_includes_crawl_failures_note(self):
        """When crawl failures exist, a note about not penalizing is included."""
        prompt = build_analysis_prompt(
            query="test",
            top_candidates=[
                {
                    "domain": "blocked.com",
                    "title": "Blocked Article",
                    "score": 5,
                    "engine": "openwebninja",
                    "crawl_data": {"crawl_status": "failed", "crawl_error": "403"},
                }
            ],
            timeline=[],
            statistics={
                "total_sources": 1, "trusted_domains": 0, "government_sources": 0,
                "tier1_news_sources": 0, "unique_domains": 1, "with_publish_date": 0,
                "crawl_status": {
                    "results_crawled": 1,
                    "successful_crawls": 0,
                    "failed_crawls": 1,
                    "failed_domains": ["blocked.com"],
                },
            },
            rules_assessment={"key": "value"},
        )
        self.assertIn("Do NOT downgrade the verdict", prompt)

    def test_prompt_empty_query(self):
        """Empty query should produce appropriate fallback text."""
        prompt = build_analysis_prompt(
            query="",
            top_candidates=[],
            timeline=[],
            statistics={"total_sources": 0, "trusted_domains": 0, "government_sources": 0,
                        "tier1_news_sources": 0, "unique_domains": 0, "with_publish_date": 0},
            rules_assessment={"key": "value"},
        )
        self.assertIn("No additional claim provided", prompt)


# ═══════════════════════════════════════════════════════════════
#  Trusted Domains Tests
# ═══════════════════════════════════════════════════════════════

class LoadTrustedDomainsTests(SimpleTestCase):
    """Tests for _load_trusted_domains() and related helpers."""

    def tearDown(self):
        # Reset the cache after each test
        from robot.llm_client import _trusted_domains_cache
        import robot.llm_client as llm
        llm._trusted_domains_cache = None

    @patch("robot.llm_client._TRUSTED_DOMAINS_JSON_PATH", "/nonexistent/path.json")
    def test_load_missing_file_uses_defaults(self):
        """When JSON file is missing, should return default domains."""
        domains = _load_trusted_domains()
        self.assertIn("reuters.com", domains.get("domains", []))
        self.assertIn(".gov", domains.get("trusted_suffixes", []))

    def test_get_credible_domains_returns_deduplicated_list(self):
        """_get_credible_domains should return unique domains from all sources."""
        domains = _get_credible_domains()
        self.assertIsInstance(domains, list)
        self.assertGreater(len(domains), 0)
        # Should include domains from various categories
        self.assertIn("reuters.com", domains)

    def test_get_government_domains_returns_list(self):
        """_get_government_domains should return a list."""
        domains = _get_government_domains()
        self.assertIsInstance(domains, list)

    def test_get_tier1_news_domains_returns_list(self):
        """_get_tier1_news_domains should return a list."""
        domains = _get_tier1_news_domains()
        self.assertIsInstance(domains, list)
        self.assertIn("reuters.com", domains)

    def test_get_tier1_african_domains_returns_list(self):
        """_get_tier1_african_domains should return a list."""
        domains = _get_tier1_african_domains()
        self.assertIsInstance(domains, list)
        self.assertIn("cameroon-tribune.cm", domains)


class CredibleSourceCitedTests(SimpleTestCase):
    """Tests for _credible_source_cited_in_evidence()."""

    def test_credible_domain_in_explanation(self):
        """Credible domain mentioned in explanation should return True."""
        parsed = {
            "explanation": "According to reuters.com the claim is verified",
            "key_evidence": [],
        }
        self.assertTrue(_credible_source_cited_in_evidence(parsed))

    def test_credible_domain_in_key_evidence(self):
        """Credible domain mentioned in key_evidence should return True."""
        parsed = {
            "explanation": "Some reasoning here",
            "key_evidence": ["bbc.com reported on this event"],
        }
        self.assertTrue(_credible_source_cited_in_evidence(parsed))

    def test_no_credible_domain_returns_false(self):
        """No credible domain mentioned should return False."""
        parsed = {
            "explanation": "Some random reasoning without credible sources",
            "key_evidence": ["unknownblog.com says something"],
        }
        self.assertFalse(_credible_source_cited_in_evidence(parsed))

    def test_empty_evidence_returns_false(self):
        """Empty explanation and evidence should return False."""
        parsed = {
            "explanation": "",
            "key_evidence": [],
        }
        self.assertFalse(_credible_source_cited_in_evidence(parsed))

    def test_case_insensitive_matching(self):
        """Domain matching should be case-insensitive."""
        parsed = {
            "explanation": "Associated Press (AP) citing Reuters.com",
            "key_evidence": [],
        }
        self.assertTrue(_credible_source_cited_in_evidence(parsed))


# ═══════════════════════════════════════════════════════════════
#  Crawl Anomaly Detection Tests
# ═══════════════════════════════════════════════════════════════

class DetectCrawlAnomaliesTests(SimpleTestCase):
    """Tests for _detect_crawl_anomalies()."""

    def test_ai_marker_detected(self):
        """AI disclaimer markers should be detected."""
        candidates = [
            {
                "domain": "ai-site.com",
                "crawl_data": {
                    "crawl_status": "success",
                    "raw_snippet": "As an AI language model, I cannot verify this claim",
                },
            }
        ]
        anomalies = _detect_crawl_anomalies(candidates)
        self.assertTrue(any("AI disclaimer" in a for a in anomalies))

    def test_sensational_language_detected(self):
        """Sensational language markers should be detected (snippet > 50 chars)."""
        candidates = [
            {
                "domain": "clickbait.com",
                "crawl_data": {
                    "crawl_status": "success",
                    "raw_snippet": "BREAKING! You won't believe what happened next! This is truly shocking news that everyone is talking about!",
                },
            }
        ]
        anomalies = _detect_crawl_anomalies(candidates)
        self.assertTrue(any("Sensational" in a for a in anomalies))

    def test_very_little_content_detected(self):
        """Very short content should be flagged."""
        candidates = [
            {
                "domain": "thin.com",
                "crawl_data": {
                    "crawl_status": "success",
                    "raw_snippet": "Short.",
                },
            }
        ]
        anomalies = _detect_crawl_anomalies(candidates)
        self.assertTrue(any("very little content" in a for a in anomalies))

    def test_failed_crawl_skipped(self):
        """Failed crawl entries should be skipped."""
        candidates = [
            {
                "domain": "blocked.com",
                "crawl_data": {"crawl_status": "failed", "crawl_error": "403"},
            }
        ]
        anomalies = _detect_crawl_anomalies(candidates)
        self.assertEqual(len(anomalies), 0)

    def test_no_crawl_data_skipped(self):
        """Entries without crawl_data should be skipped."""
        candidates = [
            {"domain": "no-data.com"},
        ]
        anomalies = _detect_crawl_anomalies(candidates)
        self.assertEqual(len(anomalies), 0)

    def test_clean_content_no_anomalies(self):
        """Clean content should produce no anomalies (>= 30 words, >= 50 chars)."""
        candidates = [
            {
                "domain": "normal.com",
                "crawl_data": {
                    "crawl_status": "success",
                    "raw_snippet": "This is a normal article with substantial content about a real event. It contains multiple sentences and paragraphs of useful information for detailed analysis purposes. The overall text length provides enough content to be meaningful and useful for evaluation.",
                },
            }
        ]
        anomalies = _detect_crawl_anomalies(candidates)
        # No AI markers, no sensational language, enough content
        self.assertEqual(len(anomalies), 0)

    def test_thin_word_count_detected(self):
        """Very few words (< 30) should be flagged as thin content."""
        candidates = [
            {
                "domain": "spam.com",
                "crawl_data": {
                    "crawl_status": "success",
                    "raw_snippet": "Just a few words here for testing. Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod tempor incididunt ut labore.",
                },
            }
        ]
        anomalies = _detect_crawl_anomalies(candidates)
        self.assertTrue(any("thin page content" in a for a in anomalies))


# ═══════════════════════════════════════════════════════════════
#  get_openrouter_client Tests
# ═══════════════════════════════════════════════════════════════

class GetOpenRouterClientTests(SimpleTestCase):
    """Tests for get_openrouter_client()."""

    @patch("robot.llm_client.settings")
    def test_client_created_with_api_key(self, mock_settings):
        """get_openrouter_client should return OpenAI client when key is set."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        client = get_openrouter_client()
        self.assertEqual(client.api_key, "test-key")
        self.assertIn("openrouter.ai", str(client.base_url))

    @patch("robot.llm_client.settings")
    def test_missing_api_key_raises_error(self, mock_settings):
        """get_openrouter_client should raise ValueError when key is missing."""
        mock_settings.OPENROUTER_API_KEY = ""
        with self.assertRaises(ValueError):
            get_openrouter_client()


# ═══════════════════════════════════════════════════════════════
#  analyze_with_openrouter Tests
# ═══════════════════════════════════════════════════════════════

class AnalyzeWithOpenRouterTests(SimpleTestCase):
    """Tests for analyze_with_openrouter()."""

    @patch("robot.llm_client.get_openrouter_client")
    def test_successful_analysis(self, mock_get_client):
        """Successful LLM call should return parsed verdict."""
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps({
            "verdict": "real",
            "confidence": 0.85,
            "short_summary": "Summary",
            "explanation": "Explanation",
            "key_evidence": ["Ev"],
        })
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        )
        mock_get_client.return_value = mock_client

        result, raw = analyze_with_openrouter("test prompt", {"total_sources": 5})
        self.assertEqual(result["verdict"], "real")
        self.assertEqual(result["confidence"], 0.85)
        self.assertIn("model", raw)
        self.assertIn("usage", raw)

    @patch("robot.llm_client.get_openrouter_client")
    def test_primary_fails_falls_back(self, mock_get_client):
        """When primary model fails, should fall back to secondary."""
        mock_client = MagicMock()
        # First call fails, second succeeds
        mock_client.chat.completions.create.side_effect = [
            Exception("Primary model failed"),
            MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps({
                    "verdict": "fake",
                    "confidence": 0.9,
                    "short_summary": "Fake",
                    "explanation": "E",
                    "key_evidence": [],
                })))],
                usage=MagicMock(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            ),
        ]
        mock_get_client.return_value = mock_client

        result, raw = analyze_with_openrouter("test prompt")
        self.assertEqual(result["verdict"], "fake")

    @patch("robot.llm_client.get_openrouter_client")
    def test_both_fail_returns_default(self, mock_get_client):
        """When both models fail, should return default verdict."""
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("All models failed")
        mock_get_client.return_value = mock_client

        result, raw = analyze_with_openrouter("test prompt")
        self.assertEqual(result["verdict"], "unconfirmed")
        self.assertEqual(result["confidence"], 0.0)
        self.assertIn("error", raw)


# ═══════════════════════════════════════════════════════════════
#  Rules-based Assessment Tests
# ═══════════════════════════════════════════════════════════════

class RulesBasedAssessmentTests(SimpleTestCase):
    """Tests for _rules_based_assessment()."""

    def test_date_anomaly_coordinated_push(self):
        """Sources within 24h should flag coordinated push."""
        websearch = MagicMock()
        websearch.query = "test claim"
        candidates = [
            {"publish_date": "2024-01-15T10:00:00Z", "domain": "a.com", "engine": "google"},
            {"publish_date": "2024-01-15T12:00:00Z", "domain": "b.com", "engine": "google"},
            {"publish_date": "2024-01-15T14:00:00Z", "domain": "c.com", "engine": "google"},
        ]
        assessment = _rules_based_assessment(websearch, candidates, [], {"total_sources": 3, "trusted_domains": 0})
        self.assertIn("24 hours", assessment.get("date_anomaly", ""))

    def test_natural_spread(self):
        """Sources spanning multiple days should show natural spread."""
        websearch = MagicMock()
        websearch.query = "test claim"
        candidates = [
            {"publish_date": "2024-01-10T10:00:00Z", "domain": "a.com", "engine": "google"},
            {"publish_date": "2024-01-12T10:00:00Z", "domain": "b.com", "engine": "google"},
            {"publish_date": "2024-01-15T10:00:00Z", "domain": "c.com", "engine": "google"},
        ]
        assessment = _rules_based_assessment(websearch, candidates, [], {"total_sources": 3, "trusted_domains": 1})
        self.assertIn("days", assessment.get("date_anomaly", ""))

    def test_few_dates_limited_temporal(self):
        """Fewer than 3 dated sources should show limited temporal data."""
        websearch = MagicMock()
        websearch.query = "test"
        candidates = [
            {"publish_date": "2024-01-15T10:00:00Z", "domain": "a.com", "engine": "google"},
            {"publish_date": "", "domain": "b.com", "engine": "google"},
        ]
        assessment = _rules_based_assessment(websearch, candidates, [], {"total_sources": 2, "trusted_domains": 0})
        self.assertIn("limited temporal", assessment.get("date_anomaly", ""))

    def test_trust_anomaly_high_untrusted(self):
        """4+ of top 5 untrusted should flag credibility concern."""
        websearch = MagicMock()
        websearch.query = "test"
        candidates = [
            {"domain": f"untrusted{i}.com", "engine": "google"} for i in range(5)
        ]
        assessment = _rules_based_assessment(websearch, candidates, [], {"total_sources": 5, "trusted_domains": 0})
        self.assertIn("credibility concern", assessment.get("trust_anomaly", ""))

    def test_multiple_engines_corroboration(self):
        """Multiple engines should show corroboration."""
        websearch = MagicMock()
        websearch.query = "test"
        candidates = [
            {"domain": "a.com", "engine": "google"},
            {"domain": "b.com", "engine": "yandex"},
        ]
        assessment = _rules_based_assessment(websearch, candidates, [], {"total_sources": 2, "trusted_domains": 1})
        self.assertIn("multiple", assessment.get("corroboration", "").lower())

    def test_source_quality_counts(self):
        """Source quality should reflect total sources count."""
        websearch = MagicMock()
        websearch.query = "test"
        assessment = _rules_based_assessment(websearch, [], [], {"total_sources": 20, "trusted_domains": 5})
        self.assertIn("robust", assessment.get("source_quality", ""))

    def test_user_query_provided(self):
        """User query presence should be reflected."""
        websearch = MagicMock()
        websearch.query = "real query"
        assessment = _rules_based_assessment(websearch, [], [], {"total_sources": 0, "trusted_domains": 0})
        self.assertTrue(assessment.get("user_query_provided"))