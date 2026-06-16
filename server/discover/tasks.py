"""
Celery tasks for the Discover (SearXNG Research) functionality.
Runs on-demand when the user clicks to generate a research report.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_research_generation(self, analysis_id):
    """
    Celery task that generates a SearXNG research report for a RobotAnalysis.

    Args:
        analysis_id: UUID of the RobotAnalysis record

    Returns:
        Dict with the research report data
    """
    from robot.models import RobotAnalysis
    from .research_generator import generate_research_report

    try:
        # Step 1: Fetch the analysis record (5%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "loading",
                "message": "Loading analysis data…"
            }
        )

        try:
            analysis = RobotAnalysis.objects.select_related('websearch_result').get(id=analysis_id)
        except RobotAnalysis.DoesNotExist:
            raise ValueError(f"RobotAnalysis with id {analysis_id} not found")

        websearch_result = analysis.websearch_result
        verdict_dict = {
            'verdict': analysis.verdict,
            'confidence': analysis.confidence_score,
            'explanation': analysis.explanation,
            'key_evidence': analysis.key_evidence,
            'short_summary': analysis.short_summary,
        }

        # Check if research already exists
        if analysis.research_report and analysis.research_report.get('summary'):
            self.update_state(
                state="PROGRESS",
                meta={
                    "step": "cached",
                    "message": "Research report already exists, returning cached version…"
                }
            )
            return {
                'research_queries': analysis.research_queries,
                'research_report': analysis.research_report,
                'cached': True,
            }

        # Step 2: Generate research queries (15%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "generating_queries",
                "message": "Generating search queries…"
            }
        )

        from .research_generator import generate_research_queries
        queries = generate_research_queries(websearch_result.query, analysis.verdict)

        # Step 3: Execute SearXNG searches (20-70%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "searching",
                "message": f"Running {len(queries)} SearXNG searches…",
                "data": {"current": 0, "total": len(queries)}
            }
        )

        from .research_generator import run_searxng_searches
        search_results = run_searxng_searches(queries)

        total_general = len(search_results.get('general', []))
        total_images = len(search_results.get('images', []))
        total_videos = len(search_results.get('videos', []))

        self.update_state(
            state="PROGRESS",
            meta={
                "step": "search_done",
                "message": f"Found {total_general} web results, {total_images} images, {total_videos} videos",
                "data": {
                    "general": total_general,
                    "images": total_images,
                    "videos": total_videos,
                }
            }
        )

        # Step 4: Compile research with LLM (70-95%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "compiling",
                "message": "Compiling research report with AI…"
            }
        )

        from .research_generator import compile_research_with_llm
        report = compile_research_with_llm(
            claim=websearch_result.query,
            verdict=analysis.verdict,
            confidence=analysis.confidence_score,
            explanation=analysis.explanation,
            search_results=search_results,
            generated_queries=queries,
        )

        # Step 5: Save to DB (95-100%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "saving",
                "message": "Saving research report…"
            }
        )

        analysis.research_queries = queries
        analysis.research_report = report
        analysis.save(update_fields=['research_queries', 'research_report'])

        logger.info(
            f"Research report saved for analysis {analysis_id}: "
            f"{len(report.get('sources', []))} sources, "
            f"{len(report.get('images', []))} images, "
            f"{len(report.get('videos', []))} videos"
        )

        return {
            'research_queries': queries,
            'research_report': report,
            'cached': False,
        }

    except Exception as e:
        logger.error(f"Research generation failed for analysis {analysis_id}: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise