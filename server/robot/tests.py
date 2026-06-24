"""
Tests for the robot app (models, serializers, analysis pipeline, LLM client).
"""
import json
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

    def test_unconfirmed_no_source_count_no_upgrade(self):
        """unconfirmed with no source count in prompt stays unchanged."""
        verdict = {"verdict": "unconfirmed", "confidence": 0.55, "explanation": "Some evidence"}
        prompt = "Some prompt"
        result = _fix_overcautious_verdict(verdict, prompt)
        self.assertEqual(result["verdict"], "unconfirmed")

    def test_govt_source_present_upgraded(self):
        """govt source + overcautious verdict → upgrade to 'real'."""
        prompt = "✓ Official government/presidential source present"
        verdict = {"verdict": "unconfirmed", "confidence": 0.70, "explanation": "Some explanation"}
        result = _fix_overcautious_verdict(verdict, prompt)
        self.assertEqual(result["verdict"], "real")

    def test_govt_plus_tier1_upgraded_to_real(self):
        """Govt + tier1 + confidence >= 0.70 → upgrade to 'real'."""
        prompt = (
            "✓ Official government/presidential source present\n"
            "✓ Tier-1 international news agency present"
        )
        verdict = {"verdict": "likely", "confidence": 0.75, "explanation": "Good sources"}
        result = _fix_overcautious_verdict(verdict, prompt)
        self.assertEqual(result["verdict"], "real")

    def test_self_contradicting_explanation_upgraded(self):
        """Explanation with positive signals but no source count stays unchanged."""
        verdict = {
            "verdict": "unconfirmed",
            "confidence": 0.60,
            "explanation": "The claim is supported by credible sources. Multiple sources confirm it.",
        }
        prompt = "prompt"
        result = _fix_overcautious_verdict(verdict, prompt)
        self.assertEqual(result["verdict"], "unconfirmed")

    def test_suspicious_no_source_count_no_upgrade(self):
        """suspicious with no source count in prompt stays unchanged."""
        verdict = {"verdict": "suspicious", "confidence": 0.75, "explanation": "Some evidence"}
        result = _fix_overcautious_verdict(verdict, "prompt")
        self.assertEqual(result["verdict"], "suspicious")

    def test_no_change_when_no_issues(self):
        """Correct verdicts should remain unchanged."""
        verdict = {"verdict": "real", "confidence": 0.85, "explanation": "All good"}
        result = _fix_overcautious_verdict(verdict, "prompt")
        self.assertEqual(result["verdict"], "real")
        self.assertEqual(result["confidence"], 0.85)


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