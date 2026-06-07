from celery import shared_task
from django.conf import settings
from serpapi import GoogleSearch
from .views import fetch_image_metadata, rank_images, crawl_image
from .models import WebsearchResults
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_reverse_search_pipeline(self, image_url, query, user_id, cloudinary_public_id):
    """
    Celery task that runs the reverse image search pipeline with progress updates.
    """
    try:
        # Step 1: Running reverse image search (5%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "searching",
                "message": "Running reverse image search…"
            }
        )

        # Perform reverse image search
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
                "title": match.get("title", ""),
                "url": match.get("link", ""),
                "domain": domain,
                "thumbnail": match.get("thumbnail", ""),
                "published_date": published_date_str,
            })

        # Step 2: Search done (20%)
        total_results = len(formatted_results)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "search_done",
                "message": f"Found {total_results} matches",
                "data": {"total": total_results}
            }
        )

        # Step 3: Fetch metadata for each result (20-60%)
        results_with_metadata = []
        for i, result in enumerate(formatted_results):
            image_url_result = result.get('url')
            if image_url_result:
                logger.info(f"Fetching metadata for image: {image_url_result}")
                metadata = fetch_image_metadata(image_url_result)
                result.update(metadata)
            results_with_metadata.append(result)
            
            # Update progress (20% to 60%)
            progress = 20 + int((i + 1) / total_results * 40)
            self.update_state(
                state="PROGRESS",
                meta={
                    "step": "metadata",
                    "message": f"Fetching metadata ({i + 1}/{total_results})…",
                    "data": {"current": i + 1, "total": total_results}
                }
            )

        # Step 4: Ranking results (65%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "ranking",
                "message": "Ranking results…"
            }
        )
        
        ranked_results = rank_images(results_with_metadata)

        # Step 5: Crawling top 5 sources (70%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "crawling",
                "message": "Crawling top sources (0/5)…",
                "data": {"current": 0, "total": 5}
            }
        )

        # Select top 5 images for crawling
        top_5_images = ranked_results[:5]
        logger.info(f"Selected top 5 images for crawling")

        # Crawl only the top 5 images (70-95%)
        for j, image in enumerate(top_5_images):
            image_url_result = image.get('url')
            if image_url_result:
                logger.info(f"Crawling image: {image_url_result}")
                crawl_data = crawl_image(image_url_result)
                image.update(crawl_data)
            
            # Update progress (70% to 95%)
            progress = 70 + int((j + 1) / 5 * 25)
            self.update_state(
                state="PROGRESS",
                meta={
                    "step": "crawling",
                    "message": f"Crawling source {j + 1}/5…",
                    "data": {
                        "current": j + 1,
                        "total": 5,
                        "url": image_url_result if image_url_result else ""
                    }
                }
            )

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

        # Save results to database
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                _save_results(user, None, cloudinary_public_id, image_url, query, enriched_results)
            except User.DoesNotExist:
                logger.warning(f"User with id {user_id} not found")

        # Return final payload (100%)
        return {
            "total": len(enriched_results),
            "results": enriched_results
        }

    except Exception as e:
        logger.error(f"Error in reverse search pipeline: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


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
