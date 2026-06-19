"""
Tests for the discover app (views, research generator, LLM prompt builder).
"""
import json
import uuid
from unittest.mock import patch, MagicMock

from django.test import TestCase, SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token

from authentication.models import CustomUser
from reversewebsearch.models import WebsearchResults
from robot.models import RobotAnalysis
from .research_generator import (
    generate_research_queries,
    _fallback_report,
    _empty_report,
    _parse_llm_response,
)
from .llm_research_prompt import build_research_prompt


# ═══════════════════════════════════════════════════════════════
#  Views Tests
# ═══════════════════════════════════════════════════════════════

class GenerateResearchViewTests(TestCase):
    """Tests for GenerateResearchView (POST /api/discover/generate/)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com", password="pwd"
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_header = f"Token {self.token.key}"
        self.url = reverse("discover-generate")

        # Create a WebsearchResult + RobotAnalysis
        self.websearch = WebsearchResults.objects.create(
            user=self.user, query="test claim", results={}
        )
        self.analysis = RobotAnalysis.objects.create(
            websearch_result=self.websearch,
            verdict="fake",
            confidence_score=0.85,
            short_summary="This is fake",
            explanation="Detailed reasoning",
        )

    def test_generate_post_success(self):
        """POST with valid analysis_id returns 202 + task_id."""
        with patch("discover.views.run_research_generation.delay") as mock_delay:
            mock_delay.return_value = MagicMock(id="task-abc-123")
            response = self.client.post(
                self.url,
                data=json.dumps({"analysis_id": str(self.analysis.id)}),
                content_type="application/json",
                HTTP_AUTHORIZATION=self.auth_header,
            )
            self.assertEqual(response.status_code, 202)
            data = response.json()
            self.assertEqual(data["status"], "queued")
            self.assertEqual(data["task_id"], "task-abc-123")

    def test_generate_no_auth(self):
        """POST without token returns 401."""
        response = self.client.post(
            self.url,
            data=json.dumps({"analysis_id": str(self.analysis.id)}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_generate_invalid_json(self):
        """POST with malformed JSON returns 400."""
        response = self.client.post(
            self.url,
            data="not json",
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 400)

    def test_generate_missing_analysis_id(self):
        """POST without analysis_id returns 400."""
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 400)

    def test_generate_not_found(self):
        """POST with non-existent analysis_id returns 404."""
        fake_id = str(uuid.uuid4())
        response = self.client.post(
            self.url,
            data=json.dumps({"analysis_id": fake_id}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 404)

    def test_generate_other_users_analysis_not_found(self):
        """POST with analysis belonging to another user returns 404."""
        other_user = CustomUser.objects.create_user(
            email="other@example.com", password="pwd"
        )
        other_ws = WebsearchResults.objects.create(
            user=other_user, query="other", results={}
        )
        other_analysis = RobotAnalysis.objects.create(
            websearch_result=other_ws,
            verdict="real",
            confidence_score=0.9,
            short_summary="Real",
            explanation="Reasoning",
        )
        response = self.client.post(
            self.url,
            data=json.dumps({"analysis_id": str(other_analysis.id)}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 404)

    def test_generate_already_exists(self):
        """POST when research_report already exists returns 200 with cached data."""
        self.analysis.research_report = {"summary": "Existing research summary"}
        self.analysis.save()

        response = self.client.post(
            self.url,
            data=json.dumps({"analysis_id": str(self.analysis.id)}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth_header,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "already_exists")
        self.assertIn("research_report", data)

    def test_generate_task_enqueue_failure(self):
        """POST when Celery enqueue fails returns 500."""
        with patch("discover.views.run_research_generation.delay") as mock_delay:
            mock_delay.side_effect = Exception("Broker connection error")
            response = self.client.post(
                self.url,
                data=json.dumps({"analysis_id": str(self.analysis.id)}),
                content_type="application/json",
                HTTP_AUTHORIZATION=self.auth_header,
            )
            self.assertEqual(response.status_code, 500)


class ResearchProgressViewTests(TestCase):
    """Tests for ResearchProgressView (GET /api/discover/progress/<task_id>/)."""

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com", password="pwd"
        )
        self.token = Token.objects.create(user=self.user)
        self.auth_header = f"Token {self.token.key}"

    def test_progress_no_auth(self):
        """GET without token returns 401."""
        url = reverse("discover-progress", args=["some-task-id"])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)


# ═══════════════════════════════════════════════════════════════
#  Research Generator Unit Tests (SimpleTestCase — no DB)
# ═══════════════════════════════════════════════════════════════

class GenerateResearchQueriesTests(SimpleTestCase):
    """Tests for generate_research_queries()."""

    def test_fake_verdict(self):
        """fake verdict returns truth/debunk queries."""
        queries = generate_research_queries("Some claim", "fake")
        self.assertGreater(len(queries), 0)
        self.assertTrue(any("fact check" in q for q in queries))
        self.assertTrue(any("debunked" in q for q in queries))
        self.assertTrue(any("what actually happened" in q for q in queries))

    def test_suspicious_verdict(self):
        """suspicious verdict returns truth/debunk queries (same as fake)."""
        queries = generate_research_queries("Some claim", "suspicious")
        self.assertGreater(len(queries), 0)
        self.assertTrue(any("fact check" in q for q in queries))

    def test_real_verdict(self):
        """real verdict returns confirming queries."""
        queries = generate_research_queries("Some claim", "real")
        self.assertGreater(len(queries), 0)
        self.assertTrue(any("confirmed" in q for q in queries))
        self.assertTrue(any("official statement" in q for q in queries))

    def test_likely_verdict(self):
        """likely verdict returns confirming queries."""
        queries = generate_research_queries("Some claim", "likely")
        self.assertGreater(len(queries), 0)
        self.assertTrue(any("confirmed" in q for q in queries))

    def test_unconfirmed_verdict(self):
        """unconfirmed verdict returns clarification queries."""
        queries = generate_research_queries("Some claim", "unconfirmed")
        self.assertGreater(len(queries), 0)
        self.assertTrue(any("fact check" in q for q in queries))
        self.assertTrue(any("verification" in q for q in queries))
        self.assertTrue(any("sources" in q for q in queries))

    def test_empty_claim(self):
        """Empty claim returns empty list."""
        self.assertEqual(generate_research_queries("", "fake"), [])
        self.assertEqual(generate_research_queries("   ", "real"), [])

    def test_none_claim(self):
        """None claim returns empty list."""
        self.assertEqual(generate_research_queries(None, "fake"), [])


class FallbackReportTests(SimpleTestCase):
    """Tests for _fallback_report()."""

    def test_fallback_structure(self):
        """Fallback report has all expected keys."""
        search_results = {"general": [], "images": [], "videos": []}
        report = _fallback_report(search_results, "fake")
        expected_keys = {"summary", "key_findings", "sources", "images", "videos"}
        self.assertEqual(set(report.keys()), expected_keys)

    def test_fallback_selects_top_results(self):
        """Fallback selects top 5 general, 5 images, 3 videos."""
        general = [{"title": f"Result {i}", "url": f"https://example{i}.com", "snippet": "Snippet", "domain": f"example{i}.com"} for i in range(10)]
        images = [{"thumbnail_url": f"https://img{i}.com", "source_url": f"https://src{i}.com", "title": f"Img {i}"} for i in range(10)]
        videos = [{"url": f"https://vid{i}.com", "thumbnail_url": "", "title": f"Vid {i}", "source": "youtube", "duration": "1:00"} for i in range(10)]

        report = _fallback_report({"general": general, "images": images, "videos": videos}, "fake")
        self.assertEqual(len(report["sources"]), 5)
        self.assertEqual(len(report["images"]), 5)
        self.assertEqual(len(report["videos"]), 3)

    def test_fallback_handles_empty(self):
        """Fallback handles empty search results gracefully."""
        report = _fallback_report({"general": [], "images": [], "videos": []}, "real")
        self.assertEqual(report["sources"], [])
        self.assertEqual(report["images"], [])
        self.assertEqual(report["videos"], [])
        self.assertIn("real", report["summary"])  # verdict in summary

    def test_fallback_summary_contains_verdict(self):
        """Fallback summary mentions the verdict."""
        report = _fallback_report({"general": [], "images": [], "videos": []}, "suspicious")
        self.assertIn("suspicious", report["summary"])


class EmptyReportTests(SimpleTestCase):
    """Tests for _empty_report()."""

    def test_empty_report_structure(self):
        """_empty_report returns the expected empty dict."""
        report = _empty_report()
        self.assertEqual(report["summary"], "")
        self.assertEqual(report["key_findings"], [])
        self.assertEqual(report["sources"], [])
        self.assertEqual(report["images"], [])
        self.assertEqual(report["videos"], [])


class ParseLlmResponseResearchTests(SimpleTestCase):
    """Tests for _parse_llm_response() in research_generator."""

    def test_valid_json(self):
        """Valid JSON is parsed correctly."""
        response = json.dumps({
            "summary": "Research summary here",
            "key_findings": ["Finding 1", "Finding 2"],
            "sources": [{"title": "Source 1", "url": "https://example.com", "snippet": "Snippet", "domain": "example.com"}],
            "images": [{"thumbnail_url": "https://img.com", "source_url": "https://src.com", "title": "Image 1"}],
            "videos": [{"url": "https://vid.com", "thumbnail_url": "", "title": "Video 1", "source": "youtube", "duration": "1:00"}],
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["summary"], "Research summary here")
        self.assertEqual(len(result["key_findings"]), 2)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(len(result["images"]), 1)
        self.assertEqual(len(result["videos"]), 1)

    def test_markdown_code_fences(self):
        """Markdown ```json ... ``` fences should be stripped."""
        response = '```json\n{"summary": "S", "key_findings": [], "sources": [], "images": [], "videos": []}\n```'
        result = _parse_llm_response(response)
        self.assertEqual(result["summary"], "S")

    def test_invalid_json_returns_empty(self):
        """Invalid JSON returns empty report."""
        result = _parse_llm_response("not json")
        self.assertEqual(result["summary"], "")

    def test_missing_fields_default(self):
        """Missing fields use empty defaults."""
        response = json.dumps({"summary": "Only summary"})
        result = _parse_llm_response(response)
        self.assertEqual(result["summary"], "Only summary")
        self.assertEqual(result["key_findings"], [])
        self.assertEqual(result["sources"], [])

    def test_non_list_fields_default_to_empty(self):
        """Non-list key_findings/sources/images/videos default to []."""
        response = json.dumps({
            "summary": "S",
            "key_findings": "not a list",
            "sources": "not a list",
            "images": "not a list",
            "videos": "not a list",
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["key_findings"], [])
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["images"], [])
        self.assertEqual(result["videos"], [])


# ═══════════════════════════════════════════════════════════════
#  LLM Research Prompt Tests (SimpleTestCase — no DB)
# ═══════════════════════════════════════════════════════════════

class BuildResearchPromptTests(SimpleTestCase):
    """Tests for build_research_prompt()."""

    def test_prompt_contains_expected_sections(self):
        """Prompt should contain claim, verdict, and search results."""
        prompt = build_research_prompt(
            claim="Some test claim",
            verdict="fake",
            confidence=0.85,
            explanation="Explanation text",
            search_results={
                "general": [{"title": "Result 1", "url": "https://ex.com", "snippet": "Snippet", "domain": "ex.com"}],
                "images": [{"thumbnail_url": "https://img.com", "source_url": "https://src.com", "title": "Img"}],
                "videos": [{"url": "https://vid.com", "thumbnail_url": "", "title": "Vid", "source": "youtube", "duration": "1:00"}],
            },
            generated_queries=["query 1", "query 2"],
        )
        self.assertIn("ORIGINAL CLAIM", prompt)
        self.assertIn("Some test claim", prompt)
        self.assertIn("PREVIOUS ANALYSIS VERDICT", prompt)
        self.assertIn("FAKE", prompt)
        self.assertIn("RESEARCH STRATEGY", prompt)
        self.assertIn("SEARCH QUERIES USED", prompt)
        self.assertIn("WEB SEARCH RESULTS", prompt)
        self.assertIn("IMAGE SEARCH RESULTS", prompt)
        self.assertIn("VIDEO SEARCH RESULTS", prompt)
        self.assertIn("YOUR TASK", prompt)
        self.assertIn("JSON", prompt)

    def test_false_strategy(self):
        """Fake/suspicious verdict uses truth strategy."""
        prompt = build_research_prompt("claim", "fake", 0.8, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("FALSE or SUSPICIOUS", prompt)
        self.assertIn("what ACTUALLY happened", prompt)

        prompt_susp = build_research_prompt("claim", "suspicious", 0.5, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("FALSE or SUSPICIOUS", prompt_susp)

    def test_true_strategy(self):
        """Real/likely verdict uses reinforcing strategy."""
        prompt = build_research_prompt("claim", "real", 0.9, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("TRUE or LIKELY TRUE", prompt)
        self.assertIn("additional supporting evidence", prompt)

        prompt_likely = build_research_prompt("claim", "likely", 0.7, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("TRUE or LIKELY TRUE", prompt_likely)

    def test_unconfirmed_strategy(self):
        """Unconfirmed verdict uses clarification strategy."""
        prompt = build_research_prompt("claim", "unconfirmed", 0.3, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("could not be confirmed", prompt)

    def test_empty_search_results(self):
        """Prompt handles empty search results gracefully."""
        prompt = build_research_prompt("claim", "fake", 0.8, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("(No general web results found)", prompt)
        self.assertIn("(No image results found)", prompt)
        self.assertIn("(No video results found)", prompt)

    def test_prompt_includes_confidence_percentage(self):
        """Confidence should appear as a percentage in the prompt."""
        prompt = build_research_prompt("claim", "real", 0.75, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("75%", prompt)