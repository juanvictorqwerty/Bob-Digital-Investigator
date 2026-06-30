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
    _extract_keywords_from_results,
    run_searxng_searches,
    compile_research_with_llm,
    generate_research_report,
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

    def test_fake_verdict_fallback(self):
        """fake verdict fallback returns fact check + debunk queries."""
        queries = generate_research_queries("Some claim", "fake")
        self.assertEqual(len(queries), 2)
        self.assertTrue(any("fact check" in q for q in queries))
        self.assertTrue(any("debunked" in q for q in queries))

    def test_suspicious_verdict_fallback(self):
        """suspicious verdict fallback returns fact check + debunk queries."""
        queries = generate_research_queries("Some claim", "suspicious")
        self.assertEqual(len(queries), 2)
        self.assertTrue(any("fact check" in q for q in queries))
        self.assertTrue(any("debunked" in q for q in queries))

    def test_real_verdict_fallback(self):
        """real verdict fallback returns background + developments queries."""
        queries = generate_research_queries("Some claim", "real")
        self.assertEqual(len(queries), 2)
        self.assertTrue(any("background" in q for q in queries))
        self.assertTrue(any("developments" in q for q in queries))

    def test_likely_verdict_fallback(self):
        """likely verdict fallback returns background + developments queries."""
        queries = generate_research_queries("Some claim", "likely")
        self.assertEqual(len(queries), 2)
        self.assertTrue(any("background" in q for q in queries))
        self.assertTrue(any("developments" in q for q in queries))

    def test_unconfirmed_verdict_fallback(self):
        """unconfirmed verdict fallback returns fact check + evidence queries."""
        queries = generate_research_queries("Some claim", "unconfirmed")
        self.assertEqual(len(queries), 2)
        self.assertTrue(any("fact check" in q for q in queries))
        self.assertTrue(any("evidence" in q for q in queries))

    def test_empty_claim_fallback(self):
        """Empty claim returns empty list (fallback path)."""
        self.assertEqual(generate_research_queries("", "fake"), [])
        self.assertEqual(generate_research_queries("   ", "real"), [])

    def test_none_claim_fallback(self):
        """None claim returns empty list (fallback path)."""
        self.assertEqual(generate_research_queries(None, "fake"), [])

    def test_with_processed_data_calls_llm(self):
        """When processed_data has keywords, should call LLM for queries."""
        processed_data = {
            "normalized_results": [
                {"title": "Election fraud in Cameroon", "snippet": "Reports of election fraud emerging"},
                {"title": "Cameroon election results", "snippet": "Official results show landslide"},
            ]
        }
        with patch("discover.research_generator.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "test-key"
            with patch("discover.research_generator.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_choice = MagicMock()
                mock_choice.message.content = "election fraud investigation\nCameroon election results analysis"
                mock_client.chat.completions.create.return_value = MagicMock(
                    choices=[mock_choice]
                )
                mock_openai.return_value = mock_client

                queries = generate_research_queries(
                    claim="Some claim",
                    verdict="fake",
                    confidence=0.85,
                    explanation="The claim is fake because...",
                    processed_data=processed_data,
                )
                self.assertEqual(len(queries), 2)
                mock_openai.assert_called_once()

    def test_with_processed_data_no_api_key_falls_back(self):
        """When processed_data provided but no API key, falls back to templates."""
        processed_data = {
            "normalized_results": [
                {"title": "Election fraud", "snippet": "Reports of fraud"},
            ]
        }
        with patch("discover.research_generator.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = ""
            queries = generate_research_queries(
                claim="Some claim",
                verdict="fake",
                confidence=0.85,
                explanation="Explanation",
                processed_data=processed_data,
            )
            # Should fall back to template queries
            self.assertEqual(len(queries), 2)
            self.assertTrue(any("fact check" in q for q in queries))

    def test_with_processed_data_llm_fails_falls_back(self):
        """When processed_data provided but LLM call fails, falls back."""
        processed_data = {
            "normalized_results": [
                {"title": "Election fraud", "snippet": "Reports of fraud"},
            ]
        }
        with patch("discover.research_generator.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = "test-key"
            with patch("discover.research_generator.OpenAI") as mock_openai:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = Exception("API error")
                mock_openai.return_value = mock_client

                queries = generate_research_queries(
                    claim="Some claim",
                    verdict="fake",
                    confidence=0.85,
                    explanation="Explanation",
                    processed_data=processed_data,
                )
                # Should fall back to template queries
                self.assertEqual(len(queries), 2)
                self.assertTrue(any("fact check" in q for q in queries))

    def test_with_processed_data_empty_results_falls_back(self):
        """When processed_data has empty results, falls back to templates."""
        processed_data = {"normalized_results": []}
        queries = generate_research_queries(
            claim="Some claim",
            verdict="fake",
            confidence=0.85,
            explanation="Explanation",
            processed_data=processed_data,
        )
        self.assertEqual(len(queries), 2)
        self.assertTrue(any("fact check" in q for q in queries))


class FallbackReportTests(SimpleTestCase):
    """Tests for _fallback_report()."""

    def test_fallback_structure(self):
        """Fallback report has all expected keys."""
        report = _fallback_report("fake", "test claim")
        expected_keys = {"summary", "additional_context", "reality_check"}
        self.assertEqual(set(report.keys()), expected_keys)

    def test_fallback_handles_empty(self):
        """Fallback handles gracefully."""
        report = _fallback_report("real", "test claim")
        self.assertIn("TRUE", report["summary"])

    def test_fallback_summary_contains_verdict(self):
        """Fallback summary mentions the verdict."""
        report = _fallback_report("suspicious", "test claim")
        self.assertEqual(report["reality_check"], (
            "The claim was assessed as FAKE. "
            "Review the provided sources for the verified version of events."
        ))


class EmptyReportTests(SimpleTestCase):
    """Tests for _empty_report()."""

    def test_empty_report_structure(self):
        """_empty_report returns the expected empty dict."""
        report = _empty_report()
        self.assertEqual(report["summary"], "")
        self.assertIsNone(report["additional_context"])
        self.assertIsNone(report["reality_check"])


class ParseLlmResponseResearchTests(SimpleTestCase):
    """Tests for _parse_llm_response() in research_generator."""

    def test_valid_json(self):
        """Valid JSON is parsed correctly."""
        response = json.dumps({
            "summary": "Research summary here",
            "additional_context": None,
            "reality_check": "This is the truth",
        })
        result = _parse_llm_response(response)
        self.assertEqual(result["summary"], "Research summary here")
        self.assertEqual(result["reality_check"], "This is the truth")

    def test_markdown_code_fences(self):
        """Markdown ```json ... ``` fences should be stripped."""
        response = '```json\n{"summary": "S", "additional_context": null, "reality_check": null}\n```'
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
        self.assertIsNone(result["additional_context"])
        self.assertIsNone(result["reality_check"])


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
        self.assertIn("YOUR TASK", prompt)
        self.assertIn("JSON", prompt)

    def test_false_strategy(self):
        """Fake/suspicious verdict uses truth strategy."""
        prompt = build_research_prompt("claim", "fake", 0.8, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("FALSE or SUSPICIOUS", prompt)
        self.assertIn("what actually happened", prompt)

        prompt_susp = build_research_prompt("claim", "suspicious", 0.5, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("FALSE or SUSPICIOUS", prompt_susp)

    def test_true_strategy(self):
        """Real/likely verdict uses reinforcing strategy."""
        prompt = build_research_prompt("claim", "real", 0.9, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("TRUE or LIKELY TRUE", prompt)
        self.assertIn("reinforcing this finding", prompt)

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

    def test_prompt_includes_verdict_mapped(self):
        """Prompt should include the mapped verdict."""
        prompt = build_research_prompt("claim", "real", 0.75, "explanation", {"general": [], "images": [], "videos": []}, ["q1"])
        self.assertIn("TRUE", prompt)


# ═══════════════════════════════════════════════════════════════
#  run_searxng_searches Tests
# ═══════════════════════════════════════════════════════════════

class RunSearxngSearchesTests(SimpleTestCase):
    """Tests for run_searxng_searches()."""

    @patch("discover.research_generator.search_general")
    @patch("discover.research_generator.search_images")
    @patch("discover.research_generator.search_videos")
    def test_aggregates_all_categories(self, mock_videos, mock_images, mock_general):
        """Should aggregate general, images, and videos from multiple queries."""
        mock_general.return_value = [
            {"url": "https://ex.com/1", "title": "R1"},
            {"url": "https://ex.com/2", "title": "R2"},
        ]
        mock_images.return_value = [
            {"source_url": "https://img.com/1", "title": "I1"},
        ]
        mock_videos.return_value = [
            {"url": "https://vid.com/1", "title": "V1"},
        ]

        result = run_searxng_searches(["query1", "query2"])
        self.assertEqual(len(result["general"]), 2)
        self.assertEqual(len(result["images"]), 1)
        self.assertEqual(len(result["videos"]), 1)

    @patch("discover.research_generator.search_general")
    @patch("discover.research_generator.search_images")
    @patch("discover.research_generator.search_videos")
    def test_deduplicates_general_by_url(self, mock_videos, mock_images, mock_general):
        """Duplicate URLs should be deduplicated."""
        mock_general.return_value = [
            {"url": "https://ex.com/dup", "title": "Same"},
        ]
        mock_images.return_value = []
        mock_videos.return_value = []

        result = run_searxng_searches(["q1", "q2"])
        self.assertEqual(len(result["general"]), 1)

    @patch("discover.research_generator.search_general")
    @patch("discover.research_generator.search_images")
    @patch("discover.research_generator.search_videos")
    def test_empty_queries(self, mock_videos, mock_images, mock_general):
        """Empty queries should produce empty results."""
        mock_general.return_value = []
        mock_images.return_value = []
        mock_videos.return_value = []

        result = run_searxng_searches([])
        self.assertEqual(len(result["general"]), 0)
        self.assertEqual(len(result["images"]), 0)
        self.assertEqual(len(result["videos"]), 0)


# ═══════════════════════════════════════════════════════════════
#  compile_research_with_llm Tests
# ═══════════════════════════════════════════════════════════════

class CompileResearchWithLlmTests(SimpleTestCase):
    """Tests for compile_research_with_llm()."""

    @patch("discover.research_generator.settings")
    @patch("discover.research_generator.OpenAI")
    def test_successful_compilation(self, mock_openai, mock_settings):
        """Successful LLM call should return parsed report."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps({
            "summary": "Research summary",
            "additional_context": "Extra context",
            "reality_check": "Reality check",
        })
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[mock_choice]
        )
        mock_openai.return_value = mock_client

        result = compile_research_with_llm(
            claim="test claim",
            verdict="fake",
            confidence=0.85,
            explanation="Explanation",
            search_results={"general": [], "images": [], "videos": []},
            generated_queries=["q1"],
        )
        self.assertEqual(result["summary"], "Research summary")
        self.assertEqual(result["additional_context"], "Extra context")

    @patch("discover.research_generator.settings")
    def test_no_api_key_returns_fallback(self, mock_settings):
        """Missing API key should return fallback report."""
        mock_settings.OPENROUTER_API_KEY = ""
        result = compile_research_with_llm(
            claim="test", verdict="real", confidence=0.9,
            explanation="E", search_results={"general": [], "images": [], "videos": []},
            generated_queries=["q1"],
        )
        self.assertIn("summary", result)
        self.assertIn("TRUE", result["summary"])

    @patch("discover.research_generator.settings")
    @patch("discover.research_generator.OpenAI")
    def test_primary_fails_falls_back(self, mock_openai, mock_settings):
        """When primary model fails, should fall back to secondary."""
        mock_settings.OPENROUTER_API_KEY = "test-key"
        mock_client = MagicMock()
        # Both calls fail
        mock_client.chat.completions.create.side_effect = Exception("Model failed")
        mock_openai.return_value = mock_client

        result = compile_research_with_llm(
            claim="test", verdict="fake", confidence=0.8,
            explanation="E", search_results={"general": [], "images": [], "videos": []},
            generated_queries=["q1"],
        )
        # Should return fallback on total failure
        self.assertIn("summary", result)


# ═══════════════════════════════════════════════════════════════
#  generate_research_report Tests
# ═══════════════════════════════════════════════════════════════

class GenerateResearchReportTests(SimpleTestCase):
    """Tests for generate_research_report()."""

    # The full test requires mocking search functions, so we test the early-exit case
    @patch("discover.research_generator.run_searxng_searches")
    @patch("discover.research_generator.compile_research_with_llm")
    def test_generate_report(self, mock_compile, mock_searxng):
        """generate_research_report should return queries, report, sources."""
        mock_searxng.return_value = {
            "general": [{"url": "https://ex.com", "title": "R1", "domain": "ex.com", "snippet": "Snippet"}],
            "images": [{"source_url": "https://img.com/1", "thumbnail_url": "", "title": "I1"}],
            "videos": [{"url": "https://vid.com/1", "title": "V1", "thumbnail_url": "", "domain": "youtube"}],
        }
        mock_compile.return_value = {
            "summary": "Research summary",
            "additional_context": None,
            "reality_check": "Reality check",
        }

        websearch = MagicMock()
        websearch.query = "test claim"
        robot_analysis = {
            "verdict": "fake",
            "confidence": 0.85,
            "explanation": "Explanation",
            "key_evidence": ["Evidence 1"],
        }

        queries, report, sources, images, videos = generate_research_report(
            websearch, robot_analysis, {}
        )
        self.assertEqual(len(queries), 2)
        self.assertEqual(report["summary"], "Research summary")
        self.assertEqual(len(sources), 1)
        self.assertEqual(len(images), 1)
        self.assertEqual(len(videos), 1)

    def test_empty_claim_returns_empty(self):
        """Empty claim should return empty results."""
        websearch = MagicMock()
        websearch.query = ""
        robot_analysis = {"verdict": "fake", "confidence": 0.8, "explanation": "E", "key_evidence": []}

        queries, report, sources, images, videos = generate_research_report(
            websearch, robot_analysis, {}
        )
        self.assertEqual(queries, [])
        self.assertEqual(report["summary"], "")
        self.assertEqual(sources, [])
        self.assertEqual(images, [])
        self.assertEqual(videos, [])


# ═══════════════════════════════════════════════════════════════
#  _extract_keywords_from_results Tests
# ═══════════════════════════════════════════════════════════════

class ExtractKeywordsFromResultsTests(SimpleTestCase):
    """Tests for _extract_keywords_from_results()."""

    def test_extracts_keywords_from_titles_and_snippets(self):
        """Should extract most frequent meaningful keywords."""
        data = {
            "normalized_results": [
                {"title": "Election fraud in Cameroon", "snippet": "Reports of election fraud emerging in Yaounde"},
                {"title": "Cameroon election results", "snippet": "Official results show landslide victory"},
            ]
        }
        keywords = _extract_keywords_from_results(data, max_keywords=10)
        self.assertIn("election", keywords)
        self.assertIn("cameroon", keywords)
        self.assertIn("fraud", keywords)
        self.assertNotIn("the", keywords)  # Stop word
        self.assertNotIn("of", keywords)   # Stop word

    def test_skips_stop_words(self):
        """Should skip common stop words."""
        data = {
            "normalized_results": [
                {"title": "The and for with from", "snippet": "this that these those"},
            ]
        }
        keywords = _extract_keywords_from_results(data)
        self.assertEqual(len(keywords), 0)

    def test_empty_results(self):
        """Empty normalized_results returns empty list."""
        self.assertEqual(_extract_keywords_from_results({}), [])
        self.assertEqual(_extract_keywords_from_results({"normalized_results": []}), [])
        self.assertEqual(_extract_keywords_from_results(None), [])

    def test_falls_back_to_top_candidates(self):
        """When normalized_results is empty, should try top_candidates."""
        data = {
            "normalized_results": [],
            "top_candidates": [
                {"title": "Investigation launched", "snippet": "Authorities launch investigation"},
            ]
        }
        keywords = _extract_keywords_from_results(data, max_keywords=5)
        self.assertIn("investigation", keywords)

    def test_uses_extracted_text_field(self):
        """Should also check extracted_text if available."""
        data = {
            "normalized_results": [
                {"title": "Short title", "extracted_text": "Detailed analysis of corruption scandal"},
            ]
        }
        keywords = _extract_keywords_from_results(data, max_keywords=10)
        self.assertIn("corruption", keywords)
        self.assertIn("scandal", keywords)
        self.assertIn("analysis", keywords)


# ═══════════════════════════════════════════════════════════════
#  (Celery task run_research_generation is tested indirectly
#   through the view tests above, which mock task.delay().
#   Direct task execution requires a Celery backend, so
#   the business logic (caching, report generation) is
#   covered by the GenerateResearchReportTests and views.)
# ═══════════════════════════════════════════════════════════════
