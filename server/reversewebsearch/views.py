# reversewebsearch/views.py
from django.conf import settings
from django.http import JsonResponse
from rest_framework.generics import GenericAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from serpapi import GoogleSearch
from .serializers import ReverseImageSearchSerializer
from .models import WebsearchResults
import os
import uuid
import random
import requests
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup


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

        # If an image file is uploaded, upload to Cloudinary first to get URL
        cloudinary_public_id = None
        if uploaded_image and not image_url:
            image_url, cloudinary_public_id = self._upload_to_cloudinary(uploaded_image)

        try:
            results = self._perform_reverse_search(image_url)
            
            # Select pages to crawl based on priority logic
            pages_to_crawl = self._select_pages_to_crawl(results)
            
            # Crawl selected pages and extract data
            crawled_data = self._crawl_pages(pages_to_crawl)
            
            # Merge crawled data with results
            enriched_results = self._merge_crawled_data(results, crawled_data)
            
            if request.user and request.user.is_authenticated:
                self._save_results(request.user, uploaded_image, cloudinary_public_id, image_url, query, enriched_results)
            
            return JsonResponse({"results": enriched_results}, status=status.HTTP_200_OK)
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

    def _select_pages_to_crawl(self, results):
        """
        Select pages to crawl using priority logic:
        - Sort results by published_date ascending, take the 3 oldest with a non-null date
        - If fewer than 3 have a date, fill the remaining slots by randomly picking from null-date results until you have 2 total (not 3)
        """
        # Separate results with and without dates
        with_dates = [r for r in results if r.get('published_date')]
        without_dates = [r for r in results if not r.get('published_date')]
        
        # Sort with_dates by published_date ascending
        with_dates_sorted = sorted(with_dates, key=lambda x: datetime.fromisoformat(x['published_date']))
        
        # Take up to 3 oldest with dates
        selected = with_dates_sorted[:3]
        
        # If we have fewer than 3 with dates, fill from null-date results until we have 2 total
        if len(selected) < 3 and without_dates:
            needed = min(2 - len(selected), len(without_dates))
            if needed > 0:
                selected.extend(random.sample(without_dates, needed))
        
        return selected

    def _crawl_pages(self, pages):
        """
        Crawl selected pages and extract data.
        Skip pages requiring login or returning 4xx/5xx.
        """
        crawled_data = {}
        
        for page in pages:
            url = page.get('url')
            if not url:
                continue
            
            try:
                data = self._crawl_single_page(url)
                crawled_data[url] = data
            except Exception as e:
                # Skip pages that fail to crawl
                crawled_data[url] = {'error': str(e)}
        
        return crawled_data

    def _crawl_single_page(self, url):
        """
        Crawl a single page and extract required data.
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Skip pages with 4xx/5xx responses
        if response.status_code >= 400:
            raise Exception(f"HTTP {response.status_code}")
        
        # Check for login requirement (basic heuristic)
        if 'login' in response.text.lower() or 'sign in' in response.text.lower():
            raise Exception("Login required")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract page title
        page_title = soup.title.string if soup.title else ''
        
        # Extract page description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        page_description = meta_desc.get('content', '') if meta_desc else ''
        
        # Extract image data (find the image that matches the thumbnail)
        img_alt = ''
        img_caption = ''
        surrounding_text = ''
        
        # Try to find the main image - this is a simplified approach
        # In a real implementation, you'd match against the thumbnail URL
        images = soup.find_all('img')
        if images:
            main_img = images[0]  # Take first image as fallback
            img_alt = main_img.get('alt', '')
            
            # Find nearest figcaption or .caption
            caption = main_img.find_parent('figure')
            if caption:
                figcaption = caption.find('figcaption')
                if figcaption:
                    img_caption = figcaption.get_text(strip=True)
                else:
                    caption_div = caption.find(class_='caption')
                    if caption_div:
                        img_caption = caption_div.get_text(strip=True)
            
            # Extract surrounding text (up to 300 chars before and after)
            img_text = str(main_img)
            img_index = response.text.find(img_text)
            if img_index > 0:
                start = max(0, img_index - 300)
                end = min(len(response.text), img_index + len(img_text) + 300)
                surrounding_text = response.text[start:end]
        
        return {
            'img_alt': img_alt,
            'img_caption': img_caption,
            'surrounding_text': surrounding_text,
            'page_description': page_description,
            'page_title': page_title
        }

    def _merge_crawled_data(self, results, crawled_data):
        """
        Merge crawled data with the original results.
        For pages that failed to crawl, fall back to Google snippet text.
        """
        enriched_results = []
        
        for result in results:
            url = result.get('url')
            crawled = crawled_data.get(url, {})
            
            if 'error' in crawled:
                # Fall back to Google snippet
                enriched_result = result.copy()
                enriched_result['crawl_status'] = 'failed'
                enriched_result['crawl_error'] = crawled['error']
            else:
                enriched_result = result.copy()
                enriched_result.update(crawled)
                enriched_result['crawl_status'] = 'success'
            
            enriched_results.append(enriched_result)
        
        return enriched_results