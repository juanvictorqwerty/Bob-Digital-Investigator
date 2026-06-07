from celery import shared_task
from django.conf import settings
from serpapi import GoogleSearch
from .views import fetch_image_metadata, rank_images, crawl_image
from .models import WebsearchResults
from .data_processor import process_reverse_search_results
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_reverse_search_pipeline(self, image_url, query, user_id, cloudinary_public_id):
    """
    Celery task that runs the reverse image search pipeline with progress updates.
    Searches both Google and Yandex, then processes results through the data pipeline.
    """
    try:
        # Step 1: Running reverse image search (5%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "searching",
                "message": "Running reverse image search on Google…"
            }
        )

        # Perform Google reverse image search
        google_results = _perform_google_search(image_url)
        
        # Step 1b: Running Yandex reverse image search (10%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "searching",
                "message": "Running reverse image search on Yandex…"
            }
        )
        
        # Perform Yandex reverse image search
        yandex_results = _perform_yandex_search(image_url)
        
        # Combine results from both engines
        all_raw_results = google_results + yandex_results
        logger.info(f"Combined {len(google_results)} Google results and {len(yandex_results)} Yandex results")

        # Step 2: Search done (20%)
        total_results = len(all_raw_results)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "search_done",
                "message": f"Found {total_results} matches across engines",
                "data": {"total": total_results}
            }
        )

        # Step 3: Process results through data pipeline (20-80%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "processing",
                "message": "Processing and normalizing results…"
            }
        )
        
        # Process through the data pipeline (normalize, deduplicate, enrich, score, rank)
        processed_data = process_reverse_search_results(all_raw_results)
        
        # Step 4: Fetch metadata for top candidates (80-90%)
        top_candidates = processed_data['top_candidates']
        enriched_candidates = []
        for i, result in enumerate(top_candidates):
            image_url_result = result.get('image_url') or result.get('page_url')
            if image_url_result:
                logger.info(f"Fetching metadata for image: {image_url_result}")
                metadata = fetch_image_metadata(image_url_result)
                # Merge metadata into result
                result['image_metadata'] = metadata
            enriched_candidates.append(result)
            
            # Update progress (80% to 90%)
            progress = 80 + int((i + 1) / len(top_candidates) * 10)
            self.update_state(
                state="PROGRESS",
                meta={
                    "step": "metadata",
                    "message": f"Fetching metadata for top candidates ({i + 1}/{len(top_candidates)})…",
                    "data": {"current": i + 1, "total": len(top_candidates)}
                }
            )

        # Step 5: Crawling top 5 sources (90-95%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "crawling",
                "message": "Crawling top sources (0/5)…",
                "data": {"current": 0, "total": 5}
            }
        )

        # Select top 5 images for crawling
        top_5_for_crawling = enriched_candidates[:5]
        logger.info(f"Selected top 5 candidates for crawling")

        # Crawl only the top 5 images (90-95%)
        for j, result in enumerate(top_5_for_crawling):
            page_url = result.get('page_url') or result.get('image_url')
            if page_url:
                logger.info(f"Crawling URL: {page_url}")
                crawl_data = crawl_image(page_url)
                result['crawl_data'] = crawl_data
            
            # Update progress (90% to 95%)
            progress = 90 + int((j + 1) / 5 * 5)
            self.update_state(
                state="PROGRESS",
                meta={
                    "step": "crawling",
                    "message": f"Crawling source {j + 1}/5…",
                    "data": {
                        "current": j + 1,
                        "total": 5,
                        "url": page_url if page_url else ""
                    }
                }
            )

        # Update processed data with enriched candidates
        processed_data['top_candidates'] = enriched_candidates

        # Save results to database
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                _save_results(user, None, cloudinary_public_id, image_url, query, processed_data)
            except User.DoesNotExist:
                logger.warning(f"User with id {user_id} not found")

        # Return final payload (100%)
        return processed_data

    except Exception as e:
        logger.error(f"Error in reverse search pipeline: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


def _perform_google_search(image_url):
    """
    Perform Google reverse image search using SerpAPI.
    Returns list of results with engine field set to 'google'.
    """
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
        published_date = _extract_published_date(match)
        published_date_str = _format_date_for_json(published_date)
        domain = _extract_domain(match)
        
        formatted_results.append({
            "page_url": match.get("link", ""),
            "image_url": match.get("thumbnail", ""),
            "title": match.get("title", ""),
            "domain": domain,
            "thumbnail": match.get("thumbnail", ""),
            "publish_date": published_date_str,
            "engine": "google",
            "image_metadata": None,
            "extracted_text": match.get("snippet", "")
        })
    
    return formatted_results


def _perform_yandex_search(image_url):
    """
    Perform Yandex reverse image search using SerpAPI.
    Returns list of results with engine field set to 'yandex'.
    """
    try:
        params = {
            "engine": "yandex_images",
            "image_url": image_url,
            "api_key": settings.SERPAPI_KEY
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        formatted_results = []
        
        raw_results = []
        if "images_results" in results:
            raw_results = results["images_results"]
        elif "visual_matches" in results:
            raw_results = results["visual_matches"]
        
        for match in raw_results:
            published_date = _extract_published_date(match)
            published_date_str = _format_date_for_json(published_date)
            domain = _extract_domain(match)
            
            formatted_results.append({
                "page_url": match.get("link", ""),
                "image_url": match.get("thumbnail", ""),
                "title": match.get("title", ""),
                "domain": domain,
                "thumbnail": match.get("thumbnail", ""),
                "publish_date": published_date_str,
                "engine": "yandex",
                "image_metadata": None,
                "extracted_text": match.get("snippet", "")
            })
        
        return formatted_results
    except Exception as e:
        logger.warning(f"Yandex search failed: {str(e)}")
        return []


def _extract_published_date(match):
    """Extract published date from match data."""
    from datetime import datetime
    
    for field in ["date", "published_date"]:
        if field in match and match[field]:
            return _parse_date(match[field])
    
    snippet = match.get("snippet", "")
    if snippet:
        parsed = _parse_date_from_snippet(snippet)
        if parsed:
            return parsed
    
    source_info = match.get("source_info", {})
    if isinstance(source_info, dict):
        for field in ["date", "published_date"]:
            if field in source_info and source_info[field]:
                return _parse_date(source_info[field])
    
    return None


def _format_date_for_json(date_obj):
    """Format date object for JSON serialization."""
    from datetime import datetime
    
    if date_obj is None:
        return None
    if isinstance(date_obj, datetime):
        return date_obj.isoformat()
    if isinstance(date_obj, str):
        parsed = _parse_date(date_obj)
        if parsed:
            return parsed.isoformat()
    return None


def _parse_date(date_value):
    """Parse date string into datetime object."""
    from datetime import datetime
    
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


def _parse_date_from_snippet(snippet):
    """Parse date from snippet text."""
    import re
    from datetime import datetime
    
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


def _extract_domain(match):
    """Extract domain from match data."""
    from urllib.parse import urlparse
    
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


def _save_results(user, uploaded_image, cloudinary_public_id, image_url, query, results):
    """Save search results to database."""
    image_value = cloudinary_public_id if cloudinary_public_id else uploaded_image
    
    WebsearchResults.objects.create(
        user=user,
        image=image_value,
        query=query or image_url,
        results=results
    )
