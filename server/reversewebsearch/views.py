# reversewebsearch/views.py
from django.conf import settings
from django.http import JsonResponse
from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from serpapi import GoogleSearch
from .serializers import ReverseImageSearchSerializer
from .models import WebsearchResults
import os
import uuid
from urllib.parse import urlparse
from datetime import datetime


class ReverseImageSearchView(GenericAPIView):
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = ReverseImageSearchSerializer
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

        # If an image file is uploaded, upload to Cloudinary first to get URL
        cloudinary_public_id = None
        if uploaded_image and not image_url:
            image_url, cloudinary_public_id = self._upload_to_cloudinary(uploaded_image)

        try:
            results = self._perform_reverse_search(image_url)
            
            if request.user and request.user.is_authenticated:
                self._save_results(request.user, uploaded_image, cloudinary_public_id, image_url, query, results)
            
            return JsonResponse({"results": results}, status=status.HTTP_200_OK)
        except Exception as e:
            return JsonResponse(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _upload_to_cloudinary(self, uploaded_image):
        """
        Upload image to Cloudinary and return a public HTTPS URL and public_id.
        Cloudinary URLs are globally accessible and fast for SerpAPI.
        """
        import cloudinary
        import cloudinary.uploader
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
        
        # Upload the image
        # Use a unique public_id to avoid collisions
        public_id = f"reverse_search/{uuid.uuid4().hex}"
        
        result = cloudinary.uploader.upload(
            uploaded_image,
            public_id=public_id,
            folder="bob_investigator",
            overwrite=False,
            resource_type="image"
        )
        
        # Return the secure HTTPS URL and public_id
        return result["secure_url"], result["public_id"]

    def _perform_reverse_search(self, image_url):
        params = {
            "engine": "google_reverse_image",
            "image_url": image_url,
            "api_key": settings.SERPAPI_KEY,
            "tbs": "imgo:1,qdr:y"
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        formatted_results = []
        
        raw_results = []
        if "visual_matches" in results:
            raw_results = results["visual_matches"]
        elif "image_results" in results:
            raw_results = results["image_results"]
        
        for match in raw_results:
            published_date = self._extract_published_date(match)
            published_date_str = self._format_date_for_json(published_date)
            domain = self._extract_domain(match)
            
            formatted_results.append({
                "title": match.get("title", ""),
                "url": match.get("link", ""),
                "domain": domain,
                "thumbnail": match.get("thumbnail", ""),
                "published_date": published_date_str,
            })
        
        formatted_results.sort(
            key=lambda x: datetime.fromisoformat(x["published_date"]) 
            if x["published_date"] else datetime.max
        )
        
        return formatted_results

    def _format_date_for_json(self, date_obj):
        if date_obj is None:
            return None
        if isinstance(date_obj, datetime):
            return date_obj.isoformat()
        if isinstance(date_obj, str):
            parsed = self._parse_date(date_obj)
            if parsed:
                return parsed.isoformat()
        return None

    def _extract_published_date(self, match):
        for field in ["date", "published_date"]:
            if field in match and match[field]:
                return self._parse_date(match[field])
        
        snippet = match.get("snippet", "")
        if snippet:
            parsed = self._parse_date_from_snippet(snippet)
            if parsed:
                return parsed
        
        source_info = match.get("source_info", {})
        if isinstance(source_info, dict):
            for field in ["date", "published_date"]:
                if field in source_info and source_info[field]:
                    return self._parse_date(source_info[field])
        
        return None

    def _parse_date(self, date_value):
        if isinstance(date_value, datetime):
            return date_value
        
        if not date_value or not isinstance(date_value, str):
            return None
        
        date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_value, fmt)
            except ValueError:
                continue
        
        return None

    def _parse_date_from_snippet(self, snippet):
        import re
        
        relative_pattern = r'(\d+)\s+(day|week|month|year)s?\s+ago'
        match = re.search(relative_pattern, snippet, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            now = datetime.now()
            
            if unit == "day":
                return now.replace(day=max(1, now.day - num))
            elif unit == "week":
                return now.replace(day=max(1, now.day - (num * 7)))
            elif unit == "month":
                month = max(1, now.month - num)
                return now.replace(month=month)
            elif unit == "year":
                return now.replace(year=now.year - num)
        
        date_patterns = [
            r'([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, snippet)
            if match:
                try:
                    date_str = match.group(0)
                    for fmt in ["%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"]:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except ValueError:
                    continue
        
        return None

    def _extract_domain(self, match):
        source = match.get("source", "")
        if source:
            return source
        
        url = match.get("link", "")
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc
                if domain.startswith("www."):
                    domain = domain[4:]
                return domain
            except Exception:
                pass
        
        return ""

    def _save_results(self, user, uploaded_image, cloudinary_public_id, image_url, query, results):
        # If we have a cloudinary_public_id, use it to reference the already-uploaded image
        # Otherwise, use the uploaded_image file (which will trigger Cloudinary upload via CloudinaryField)
        image_value = cloudinary_public_id if cloudinary_public_id else uploaded_image
        
        WebsearchResults.objects.create(
            user=user,
            image=image_value,
            query=query or image_url,
            results=results
        )