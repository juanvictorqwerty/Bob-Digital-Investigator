"""
Views for the Discover (SearXNG Research) functionality.

Provides an endpoint to trigger on-demand research generation
and an SSE endpoint to stream progress updates.
"""
import json
import time
import logging
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from celery.result import AsyncResult

from .tasks import run_research_generation

logger = logging.getLogger(__name__)


def _resolve_user_from_token(request):
    """
    Resolve the authenticated user from a token in the request header.
    Returns (user, error_response) tuple.
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Token '):
        return None, JsonResponse(
            {"error": "Authentication required"},
            status=401
        )

    token = auth_header.replace('Token ', '').strip()
    from rest_framework.authtoken.models import Token
    try:
        token_obj = Token.objects.select_related('user').get(key=token)
    except Token.DoesNotExist:
        return None, JsonResponse(
            {"error": "Invalid token"},
            status=401
        )

    return token_obj.user, None


@method_decorator(csrf_exempt, name='dispatch')
class GenerateResearchView(View):
    """
    POST endpoint to trigger on-demand research generation for a RobotAnalysis.

    Accepts:
        POST /api/discover/generate/
        Body: {"analysis_id": "<uuid>"}

    Returns:
        202 Accepted with {"task_id": "...", "status": "queued"}
    """

    def post(self, request):
        user, error = _resolve_user_from_token(request)
        if error:
            return error

        # Parse request body
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        analysis_id = body.get('analysis_id')
        if not analysis_id:
            return JsonResponse(
                {"error": "analysis_id is required"},
                status=400
            )

        # Verify the analysis exists and belongs to the user
        from robot.models import RobotAnalysis
        try:
            analysis = RobotAnalysis.objects.select_related('websearch_result').get(
                id=analysis_id,
                websearch_result__user=user
            )
        except RobotAnalysis.DoesNotExist:
            return JsonResponse(
                {"error": "Analysis not found or access denied"},
                status=404
            )

        # Check if research already exists
        if analysis.research_report and analysis.research_report.get('summary'):
            return JsonResponse({
                "status": "already_exists",
                "research_queries": analysis.research_queries,
                "research_report": analysis.research_report,
            })

        # Dispatch Celery task
        try:
            task = run_research_generation.delay(str(analysis_id))
            return JsonResponse({
                "task_id": task.id,
                "status": "queued"
            }, status=202)
        except Exception as e:
            logger.error(f"Error enqueuing research task: {str(e)}")
            return JsonResponse(
                {"error": str(e)},
                status=500
            )


class ResearchProgressView(View):
    """
    SSE endpoint for research generation progress.

    GET /api/discover/progress/<task_id>/
    """

    def get(self, request, task_id):
        user, error = _resolve_user_from_token(request)
        if error:
            return error

        def event_stream():
            # Exponential backoff: start at 0.5s, cap at 4s
            delay = 0.5
            max_delay = 4.0
            backoff_factor = 1.5

            while True:
                result = AsyncResult(task_id)
                state = result.state

                if state == "PENDING":
                    yield _sse("queued", {"message": "Waiting for worker…"})

                elif state == "PROGRESS":
                    yield _sse("progress", result.info)

                elif state == "SUCCESS":
                    yield _sse("done", result.result)
                    break

                elif state == "FAILURE":
                    yield _sse("error", {"error": str(result.info)})
                    break

                time.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)

        return StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream"
        )


def _sse(event, data):
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"