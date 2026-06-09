# reversewebsearch/views.py
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.views import View  # Add this
from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from serpapi import GoogleSearch
from .serializers import ReverseImageSearchSerializer
from .models import WebsearchResults
from .tasks import run_reverse_search_pipeline
from .utils import fetch_image_metadata, rank_images, crawl_image
import uuid
import logging
import json
import time
from celery.result import AsyncResult

logger = logging.getLogger(__name__)


class ReverseImageSearchView(GenericAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ReverseImageSearchSerializer
    authentication_classes=[TokenAuthentication]
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

    def _perform_reverse_search(self, image_url):
        # ... keep existing implementation ...
        pass

    def _format_date_for_json(self, date_obj):
        # ... keep existing implementation ...
        pass

    def _extract_published_date(self, match):
        # ... keep existing implementation ...
        pass

    def _parse_date(self, date_value):
        # ... keep existing implementation ...
        pass

    def _parse_date_from_snippet(self, snippet):
        # ... keep existing implementation ...
        pass

    def _extract_domain(self, match):
        # ... keep existing implementation ...
        pass

    def _save_results(self, user, uploaded_image, cloudinary_public_id, image_url, query, results):
        image_value = cloudinary_public_id if cloudinary_public_id else uploaded_image
        
        WebsearchResults.objects.create(
            user=user,
            image=image_value,
            query=query or image_url,
            results=results
        )


# FIXED: Use Django's plain View instead of GenericAPIView to bypass DRF content negotiation
class ReverseSearchProgressView(View):
    """
    SSE endpoint for Celery task progress.
    Uses Django's plain View to avoid DRF's renderer negotiation that causes 406
    when Accept: text/event-stream is sent.
    """
    
    def get(self, request, task_id):
        # Manual authentication check since we're not using DRF's permission system
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Token '):
            return JsonResponse(
                {"error": "Authentication required"}, 
                status=401
            )
        
        token = auth_header.replace('Token ', '').strip()
        
        # Verify token manually
        from rest_framework.authtoken.models import Token
        try:
            Token.objects.get(key=token)
        except Token.DoesNotExist:
            return JsonResponse(
                {"error": "Invalid token"}, 
                status=401
            )

        def event_stream():
            while True:
                result = AsyncResult(task_id)

                if result.state == "PENDING":
                    yield _sse("queued", {"message": "Waiting for worker…"})

                elif result.state == "PROGRESS":
                    yield _sse("progress", result.info)

                elif result.state == "SUCCESS":
                    yield _sse("done", result.result)
                    break

                elif result.state == "FAILURE":
                    yield _sse("error", {"error": str(result.info)})
                    break

                time.sleep(1)

        return StreamingHttpResponse(
            event_stream(),
            content_type="text/event-stream"
        )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"