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

        if uploaded_image:
            image_url = self._get_temp_image_url(uploaded_image)

        try:
            results = self._perform_reverse_search(image_url)
            
            # Only save if user is authenticated
            if request.user and request.user.is_authenticated:
                self._save_results(request.user, uploaded_image, image_url, query, results)
            
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
        # Build tbs parameter: combine exact match (imgo:1) and date filter (qdr:y)
        tbs_filters = ["imgo:1", "qdr:y"]
        tbs_value = ",".join(tbs_filters)
        
        params = {
            "engine": "google_reverse_image",
            "image_url": image_url,
            "api_key": settings.SERPAPI_KEY,
            "tbs": tbs_value,
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        formatted_results = []
        
        # Process results from both possible response structures
        raw_results = []
        if "visual_matches" in results:
            raw_results = results["visual_matches"]
        elif "image_results" in results:
            raw_results = results["image_results"]
        
        for match in raw_results:
            # Extract published_date from various possible fields
            published_date = self._extract_published_date(match)
            
            # Convert datetime to ISO string for JSON serialization
            published_date_str = self._format_date_for_json(published_date)
            
            # Extract domain from source or URL
            domain = self._extract_domain(match)
            
            formatted_results.append({
                "title": match.get("title", ""),
                "url": match.get("link", ""),
                "domain": domain,
                "thumbnail": match.get("thumbnail", ""),
                "published_date": published_date_str,
            })
        
        # Sort by published_date ascending (oldest first)
        # Use the datetime object for sorting, then convert to string
        formatted_results.sort(
            key=lambda x: datetime.fromisoformat(x["published_date"]) 
            if x["published_date"] else datetime.max
        )
        
        return formatted_results

    def _format_date_for_json(self, date_obj):
        """Convert datetime object to ISO format string for JSON serialization."""
        if date_obj is None:
            return None
        if isinstance(date_obj, datetime):
            return date_obj.isoformat()
        if isinstance(date_obj, str):
            # Try to parse and re-format
            parsed = self._parse_date(date_obj)
            if parsed:
                return parsed.isoformat()
        return None

    def _extract_published_date(self, match):
        """
        Extract published date from various possible fields in SerpAPI response.
        """
        # Check direct date fields
        for field in ["date", "published_date"]:
            if field in match and match[field]:
                return self._parse_date(match[field])
        
        # Try to extract from snippet
        snippet = match.get("snippet", "")
        if snippet:
            parsed = self._parse_date_from_snippet(snippet)
            if parsed:
                return parsed
        
        # Try to extract from source info
        source_info = match.get("source_info", {})
        if isinstance(source_info, dict):
            for field in ["date", "published_date"]:
                if field in source_info and source_info[field]:
                    return self._parse_date(source_info[field])
        
        return None

    def _parse_date(self, date_value):
        """Parse various date formats into a datetime object."""
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
        """Try to extract date from snippet text."""
        import re
        
        # Pattern for "X days/weeks/months/years ago"
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
        
        # Pattern for date like "Jan 15, 2023"
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
        """Extract domain from source field or URL."""
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

    def _save_results(self, user, uploaded_image, image_url, query, results):
        """Save search results to the database."""
        image_file = uploaded_image if uploaded_image else None
        
        WebsearchResults.objects.create(
            user=user,
            image=image_file,
            query=query or image_url,
            results=results
        )