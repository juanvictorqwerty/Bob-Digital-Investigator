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
import uuid
import requests
import logging
from urllib.parse import urlparse
from datetime import datetime
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_image_metadata(url):
    """
    Fetch image metadata (file size, dimensions) using SERP API image search.
    Returns a dict with file_size_bytes and dimensions.
    """
    logger.info(f"Fetching metadata for image URL: {url}")
    
    try:
        params = {
            "engine": "google_images",
            "q": url,
            "api_key": settings.SERPAPI_KEY,
            "ijn": 0
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        metadata = {
            "file_size_bytes": None,
            "dimensions": None
        }
        
        # Extract metadata from image results
        if "images_results" in results:
            images = results["images_results"]
            if images:
                first_image = images[0]
                
                # Extract file size
                if "file_size" in first_image:
                    try:
                        file_size = first_image["file_size"]
                        # Handle various formats (e.g., "200 KB", "1.5 MB")
                        if isinstance(file_size, str):
                            if "KB" in file_size:
                                metadata["file_size_bytes"] = int(float(file_size.replace("KB", "").strip()) * 1024)
                            elif "MB" in file_size:
                                metadata["file_size_bytes"] = int(float(file_size.replace("MB", "").strip()) * 1024 * 1024)
                            elif "GB" in file_size:
                                metadata["file_size_bytes"] = int(float(file_size.replace("GB", "").strip()) * 1024 * 1024 * 1024)
                        elif isinstance(file_size, (int, float)):
                            metadata["file_size_bytes"] = int(file_size)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing file size for {url}: {str(e)}")
                
                # Extract dimensions
                if "width" in first_image and "height" in first_image:
                    try:
                        metadata["dimensions"] = {
                            "width": int(first_image["width"]),
                            "height": int(first_image["height"])
                        }
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing dimensions for {url}: {str(e)}")
        
        logger.info(f"Successfully fetched metadata for {url}: {metadata}")
        return metadata
        
    except Exception as e:
        logger.error(f"Error fetching metadata for {url}: {str(e)}")
        return {
            "file_size_bytes": None,
            "dimensions": None
        }


def rank_images(results):
    """
    Rank images by file size (largest first) or by oldest published_date if size unavailable.
    Returns sorted list of results.
    """
    logger.info(f"Ranking {len(results)} images")
    
    def sort_key(result):
        file_size = result.get("file_size_bytes")
        published_date = result.get("published_date")
        
        # Primary sort: file_size_bytes descending (largest first)
        if file_size is not None:
            return (-file_size, datetime.max)  # Use datetime.max as secondary key to prioritize size
        # Secondary sort: published_date ascending (oldest first)
        elif published_date:
            try:
                return (0, datetime.fromisoformat(published_date))
            except (ValueError, TypeError):
                return (0, datetime.max)
        else:
            return (0, datetime.max)
    
    sorted_results = sorted(results, key=sort_key)
    
    logger.info(f"Ranked images - top result: {sorted_results[0].get('url') if sorted_results else 'None'}")
    return sorted_results


def crawl_image(url):
    """
    Crawl an image URL using RapidAPI scraping endpoint with 10-second timeout.
    Returns a dict with crawl_status, crawl_error, crawled_at, and raw_snippet.
    """
    logger.info(f"Crawling image URL: {url}")
    
    rapidapi_host = "scrapey-link-scraper.p.rapidapi.com"
    
    try:
        # Parse domain from URL for RapidAPI
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Make request to RapidAPI
        rapidapi_url = f"https://{rapidapi_host}/v1/scrapelinks/"
        params = {
            "url": domain,
            "maxlinks": 10,
            "includequery": "true"
        }
        headers = {
            "Content-Type": "application/json",
            "x-rapidapi-host": rapidapi_host,
            "x-rapidapi-key": settings.RAPIDAPI_KEY
        }
        
        response = requests.get(
            rapidapi_url,
            params=params,
            headers=headers,
            timeout=10
        )
        
        # Handle rate limiting
        if response.status_code == 429:
            logger.warning(f"Rate limited by RapidAPI for URL: {url}")
            return {
                "crawl_status": "failed",
                "crawl_error": "Rate limit exceeded",
                "crawled_at": datetime.utcnow().isoformat(),
                "raw_snippet": None
            }
        
        # Parse RapidAPI response
        if response.status_code == 200:
            crawl_data = response.json()
            logger.info(f"Successfully crawled URL: {url}")
            
            # Extract raw snippet (first 300 chars)
            raw_snippet = extract_raw_snippet(crawl_data)
            
            return {
                "crawl_status": "success",
                "crawl_error": None,
                "crawled_at": datetime.utcnow().isoformat(),
                "raw_snippet": raw_snippet
            }
        else:
            logger.warning(f"RapidAPI returned status {response.status_code} for URL: {url}")
            return {
                "crawl_status": "failed",
                "crawl_error": f"RapidAPI returned status {response.status_code}",
                "crawled_at": datetime.utcnow().isoformat(),
                "raw_snippet": None
            }
            
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout crawling URL: {url}")
        return {
            "crawl_status": "failed",
            "crawl_error": "Crawl timeout",
            "crawled_at": datetime.utcnow().isoformat(),
            "raw_snippet": None
        }
    except Exception as e:
        logger.error(f"Error crawling URL {url}: {str(e)}")
        return {
            "crawl_status": "failed",
            "crawl_error": str(e),
            "crawled_at": datetime.utcnow().isoformat(),
            "raw_snippet": None
        }


def extract_raw_snippet(crawl_data):
    """
    Extract the first 300 characters from the crawl response.
    Handles various response formats from RapidAPI.
    """
    try:
        # Try to get HTML content
        if "html" in crawl_data:
            html_content = crawl_data["html"]
            if isinstance(html_content, str):
                # Strip HTML tags for snippet
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text()
                return text[:300]
            return str(html_content)[:300]
        
        # Try to get content field
        if "content" in crawl_data:
            content = crawl_data["content"]
            if isinstance(content, str):
                return content[:300]
            return str(content)[:300]
        
        # Try to get text field
        if "text" in crawl_data:
            text = crawl_data["text"]
            if isinstance(text, str):
                return text[:300]
            return str(text)[:300]
        
        # Fallback: return first 300 chars of entire response
        return str(crawl_data)[:300]
        
    except Exception as e:
        logger.warning(f"Error extracting raw snippet: {str(e)}")
        return None


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
            # Perform reverse image search to get initial results
            results = self._perform_reverse_search(image_url)
            
            # Fetch image metadata (file size, dimensions) for each result
            results_with_metadata = []
            for result in results:
                image_url_result = result.get('url')
                if image_url_result:
                    logger.info(f"Fetching metadata for image: {image_url_result}")
                    metadata = fetch_image_metadata(image_url_result)
                    result.update(metadata)
                results_with_metadata.append(result)
            
            # Rank images by file size (largest first) or by oldest published_date if size unavailable
            ranked_results = rank_images(results_with_metadata)
            
            # Select top 5 images for crawling
            top_5_images = ranked_results[:5]
            logger.info(f"Selected top 5 images for crawling")
            
            # Crawl only the top 5 images
            for image in top_5_images:
                image_url_result = image.get('url')
                if image_url_result:
                    logger.info(f"Crawling image: {image_url_result}")
                    crawl_data = crawl_image(image_url_result)
                    image.update(crawl_data)
            
            # Prepare response with ALL results (not just crawled ones)
            enriched_results = []
            for result in ranked_results:
                is_crawled = result.get("crawl_status") is not None
                enriched_results.append({
                    "url": result.get("url", ""),
                    "domain": result.get("domain", ""),
                    "title": result.get("title", ""),
                    "published_date": result.get("published_date"),
                    "file_size_bytes": result.get("file_size_bytes"),
                    "dimensions": result.get("dimensions"),
                    "is_crawled": is_crawled,
                    "crawl_status": result.get("crawl_status"),
                    "crawl_error": result.get("crawl_error"),
                    "crawled_at": result.get("crawled_at"),
                    "raw_snippet": result.get("raw_snippet")
                })
            
            if request.user and request.user.is_authenticated:
                self._save_results(request.user, uploaded_image, cloudinary_public_id, image_url, query, enriched_results)
            
            return JsonResponse({
                "total": len(enriched_results),
                "results": enriched_results
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error in reverse image search: {str(e)}")
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

