# reversewebsearch/views.py
from django.conf import settings
from django.http import JsonResponse
from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from serpapi import GoogleSearch
from .serializers import ReverseImageSearchSerializer
import os
import uuid


class ReverseImageSearchView(GenericAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ReverseImageSearchSerializer

    def get(self, request, *args, **kwargs):
        # This makes DRF render the serializer form in browsable API
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

        if uploaded_image:
            image_url = self._get_temp_image_url(uploaded_image)

        try:
            results = self._perform_reverse_search(image_url)
            return JsonResponse({"results": results}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_temp_image_url(self, uploaded_image):
        from django.core.files.storage import default_storage
        ext = os.path.splitext(uploaded_image.name)[1]
        filename = f"temp_{uuid.uuid4()}{ext}"
        path = default_storage.save(f"reversewebsearch/temp/{filename}", uploaded_image)
        return default_storage.url(path)

    def _perform_reverse_search(self, image_url):
        params = {
            "engine": "google_reverse_image",
            "image_url": image_url,
            "api_key": settings.SERPAPI_KEY,
        }
        search = GoogleSearch(params)
        results = search.get_dict()
        formatted_results = []
        print(results)
        print("Image URL:", image_url)
        
        if "visual_matches" in results:
            for match in results["visual_matches"]:
                formatted_results.append({
                    "title": match.get("title", ""),
                    "url": match.get("link", ""),
                    "domain": match.get("source", ""),
                    "thumbnail": match.get("thumbnail", "")
                })
        elif "image_results" in results:
            for match in results["image_results"]:
                formatted_results.append({
                    "title": match.get("title", ""),
                    "url": match.get("link", ""),
                    "domain": match.get("source", ""),
                    "thumbnail": match.get("thumbnail", "")
                })

        return formatted_results