# reversewebsearch/views.py
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from .serializers import (
    ReverseImageSearchSerializer,
    WebsearchResultListSerializer,
    WebsearchResultDetailSerializer,
    WebsearchResultAliasSerializer,
)
from .models import WebsearchResults
from .tasks import run_reverse_search_pipeline
from .utils import fetch_image_metadata, crawl_image
import uuid
import logging
import json
import time
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


def _resolve_user_from_token(request):
    """
    Resolve the authenticated user from a token in the request header.
    Uses select_related to avoid N+1 queries on Token->User.
    Returns (user, error_response) tuple.
    If error_response is None, user is valid.
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
        # select_related('user') eliminates the extra query to fetch the User row
        token_obj = Token.objects.select_related('user').get(key=token)
    except Token.DoesNotExist:
        return None, JsonResponse(
            {"error": "Invalid token"},
            status=401
        )
    
    return token_obj.user, None


class ReverseImageSearchView(GenericAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ReverseImageSearchSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer()
        return Response({
            "message": "Send a POST request with image_url or image file",
            "form": serializer.data
        })

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return JsonResponse(
                {"error": serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        image_url = serializer.validated_data.get('image_url')
        uploaded_image = serializer.validated_data.get('image')
        query = serializer.validated_data.get('query', '')

        cloudinary_public_id = None
        if uploaded_image and not image_url:
            # We upload inline, but this could be moved to the Celery task
            image_url, cloudinary_public_id = self._upload_to_cloudinary(uploaded_image)

        try:
            user_id = request.user.id if request.user and request.user.is_authenticated else None
            task = run_reverse_search_pipeline.delay(
                image_url=image_url,
                query=query,
                user_id=user_id,
                cloudinary_public_id=cloudinary_public_id
            )
            
            return JsonResponse({
                "task_id": task.id,
                "status": "queued"
            }, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Error enqueuing reverse search task: {str(e)}")
            return JsonResponse(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _upload_to_cloudinary(self, uploaded_image):
        import cloudinary
        import cloudinary.uploader
        
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        
        public_id = f"reverse_search/{uuid.uuid4().hex}"
        
        result = cloudinary.uploader.upload(
            uploaded_image,
            public_id=public_id,
            folder="bob_investigator",
            overwrite=False,
            resource_type="image"
        )
        
        return result["secure_url"], result["public_id"]


# FIXED: Use Django's plain View instead of GenericAPIView to bypass DRF content negotiation
class ReverseSearchProgressView(View):
    """
    SSE endpoint for Celery task progress.
    Uses Django's plain View to avoid DRF's renderer negotiation that causes 406
    when Accept: text/event-stream is sent.
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

                # Exponential backoff sleep
                time.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)

        return StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream"
        )


class HistoryListView(View):
    """
    List all reverse search history items (lightweight) for the authenticated user.
    Results are paginated with ?page=1&page_size=20 query params.
    """
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100

    def get(self, request):
        user, error = _resolve_user_from_token(request)
        if error:
            return error

        # Parse pagination params
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        try:
            page_size = min(
                self.MAX_PAGE_SIZE,
                max(1, int(request.GET.get('page_size', self.DEFAULT_PAGE_SIZE)))
            )
        except (ValueError, TypeError):
            page_size = self.DEFAULT_PAGE_SIZE

        offset = (page - 1) * page_size

        queryset = WebsearchResults.objects.filter(user=user).only(
            'id', 'alias', 'query', 'created_at'
        )[offset:offset + page_size]
        serializer = WebsearchResultListSerializer(queryset, many=True)
        return JsonResponse(serializer.data, safe=False)


class HistoryDetailView(View):
    """
    Retrieve full details of a single search result by its UUID.
    """
    def get(self, request, pk):
        user, error = _resolve_user_from_token(request)
        if error:
            return error

        try:
            obj = WebsearchResults.objects.get(pk=pk, user=user)
        except WebsearchResults.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        serializer = WebsearchResultDetailSerializer(obj)
        return JsonResponse(serializer.data)


@method_decorator(csrf_exempt, name='dispatch')
class HistoryAliasUpdateView(View):
    """
    Update the alias (editable name) of a search result.
    Uses csrf_exempt because authentication is via token, not session cookies.
    """
    def options(self, request, *args, **kwargs):
        """Handle CORS preflight requests."""
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS, PATCH"
        response["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return response

    def patch(self, request, pk):
        user, error = _resolve_user_from_token(request)
        if error:
            return error

        try:
            obj = WebsearchResults.objects.get(pk=pk, user=user)
        except WebsearchResults.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        # Parse request body
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        serializer = WebsearchResultAliasSerializer(obj, data=body, partial=True)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"