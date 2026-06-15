from celery import shared_task
from django.conf import settings
import requests
import logging
from .utils import fetch_image_metadata, crawl_image
from .models import WebsearchResults
from .data_processor import process_reverse_search_results
from robot.analysis_pipeline import run_robot_analysis

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def run_reverse_search_pipeline(self, image_url, query, user_id, cloudinary_public_id):
    """
    Celery task that runs the reverse image search pipeline with progress updates.
    Searches using OpenWebNinja, then processes results through the data pipeline.
    """
    try:
        # Step 1: Running reverse image search (5%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "searching",
                "message": "Running reverse image search via OpenWebNinja…"
            }
        )

        # Perform OpenWebNinja reverse image search
        all_raw_results = _perform_openwebninja_search(image_url)
        logger.info(f"Found {len(all_raw_results)} results from OpenWebNinja")

        # Step 2: Search done (20%)
        total_results = len(all_raw_results)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "search_done",
                "message": f"Found {total_results} matches",
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

        # Step 5: Crawling top 10 sources (85-95%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "crawling",
                "message": "Crawling top sources (0/10)…",
                "data": {"current": 0, "total": 10}
            }
        )

        # Import miniature/sublink detection
        from reversewebsearch.data_processor import is_miniature_or_sublink

        # We have 20 enriched candidates — crawl up to 10 successful sources,
        # skipping miniatures/sublinks and paywalled content, pulling replacements
        # from deeper in the candidate pool.
        logger.info(f"Starting crawl of top sources (pool size: {len(enriched_candidates)})")

        # Track crawl results for status summary
        successful_crawls = 0
        failed_crawls = 0
        skipped_paywall = 0
        failed_domains = []
        attempted_count = 0
        max_attempts = min(15, len(enriched_candidates))  # try up to 15 candidates to get 10 good ones
        target_successful = 10

        # Crawl sources, skip paywalled ones, pull replacements from pool
        for j in range(max_attempts):
            result = enriched_candidates[j]
            skip_reason = None

            # Check 1: Miniature or sublink — crawl the page_url instead
            if is_miniature_or_sublink(result):
                target_url = result.get('page_url')
                skip_reason = "miniature/sublink"
                logger.info(f"Candidate {j+1} is a miniature/sublink — using page URL: {target_url}")
            else:
                target_url = result.get('page_url') or result.get('image_url')

            if target_url:
                logger.info(f"Crawling candidate {j+1}/{max_attempts}: {target_url}")
                crawl_data = crawl_image(target_url)
                result['crawl_data'] = crawl_data

                # Check 2: Paywall detected — skip this result, try next candidate
                if crawl_data.get("paywall_detected") and crawl_data.get("crawl_status") == "success":
                    skipped_paywall += 1
                    failed_crawls += 1
                    domain = crawl_data.get("domain") or result.get("domain", "unknown")
                    failed_domains.append(domain)
                    logger.info(f"Paywall detected on {domain} — skipping, will try next candidate")
                    self.update_state(
                        state="PROGRESS",
                        meta={
                            "step": "crawling",
                            "message": f"Paywall on {domain}, trying next source…",
                            "data": {
                                "current": successful_crawls,
                                "total": target_successful,
                                "url": target_url,
                                "successful": successful_crawls,
                                "failed": failed_crawls,
                                "paywall_skipped": skipped_paywall,
                            }
                        }
                    )
                    continue  # try next candidate

                if crawl_data.get("crawl_status") == "success":
                    successful_crawls += 1
                else:
                    failed_crawls += 1
                    domain = crawl_data.get("domain") or result.get("domain", "unknown")
                    failed_domains.append(domain)
            else:
                logger.warning(f"Candidate {j+1} has no URL to crawl — marking as failed")
                result['crawl_data'] = {
                    "crawl_status": "failed",
                    "crawl_error": "No URL available",
                    "crawled_at": None,
                    "raw_snippet": None,
                }
                failed_crawls += 1

            attempted_count += 1
            
            # Update progress
            progress = 85 + int(min(attempted_count, target_successful) / target_successful * 10)
            self.update_state(
                state="PROGRESS",
                meta={
                    "step": "crawling",
                    "message": f"Crawl progress: {successful_crawls} successful, {failed_crawls} failed, {skipped_paywall} paywall-skipped",
                    "data": {
                        "current": successful_crawls,
                        "total": target_successful,
                        "url": target_url if target_url else "",
                        "successful": successful_crawls,
                        "failed": failed_crawls,
                        "paywall_skipped": skipped_paywall,
                    }
                }
            )

            # Stop early if we have enough successful (non-paywalled) crawls
            if successful_crawls >= target_successful:
                logger.info(f"Reached target of {target_successful} successful crawls after {attempted_count} attempts")
                break

        # Log crawl summary
        logger.info(
            f"Crawl summary: {successful_crawls}/10 successful, "
            f"{failed_crawls} failed. "
            f"Failed domains: {failed_domains if failed_domains else 'none'}"
        )

        # Update processed data with enriched candidates
        processed_data['top_candidates'] = enriched_candidates

        # Save results to database
        saved_obj = None
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                user = User.objects.get(id=user_id)
                saved_obj = _save_results(user, None, cloudinary_public_id, image_url, query, processed_data)
            except User.DoesNotExist:
                logger.warning(f"User with id {user_id} not found")

        # Step 6: Robot AI analysis (96-98%)
        self.update_state(
            state="PROGRESS",
            meta={
                "step": "analyzing",
                "message": "Running AI fake-news analysis…"
            }
        )

        robot_analysis = None
        if saved_obj:
            try:
                robot_analysis = run_robot_analysis(saved_obj, processed_data)
                processed_data['robot_analysis'] = robot_analysis
                logger.info(f"Robot analysis complete: {robot_analysis.get('verdict')} @ {robot_analysis.get('confidence', 0):.0%}")
            except Exception as e:
                logger.error(f"Robot analysis failed: {str(e)}")
                processed_data['robot_analysis'] = {
                    "verdict": "unconfirmed",
                    "confidence": 0.0,
                    "explanation": f"AI analysis error: {str(e)}",
                    "key_evidence": [],
                    "llm_used": False
                }

        # Return final payload (100%)
        return processed_data

    except Exception as e:
        logger.error(f"Error in reverse search pipeline: {str(e)}")
        self.update_state(
            state="FAILURE",
            meta={"error": str(e)}
        )
        raise


def _perform_openwebninja_search(image_url):
    """
    Perform reverse image search using OpenWebNinja API.
    Returns list of results with engine field set to 'openwebninja'.
    """
    api_key = settings.REVERSE_IMAGE_API_KEY
    if not api_key:
        logger.error("OpenWebNinja API key not configured (REVERSE_IMAGE)")
        return []

    try:
        headers = {
            "X-API-Key": api_key
        }
        
        url = "https://api.openwebninja.com/reverse-image-search/reverse-image-search"
        params = {"url": image_url}
        
        logger.info(f"Calling OpenWebNinja reverse image search for: {image_url}")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        raw_results = result.get("data", [])
        
        formatted_results = []
        for match in raw_results:
            published_date_str = match.get("date", None)
            domain = _extract_domain_from_link(match.get("link", ""))
            
            formatted_results.append({
                "page_url": match.get("link", ""),
                "image_url": match.get("image", ""),
                "title": match.get("title", ""),
                "domain": domain,
                "thumbnail": match.get("image", ""),
                "publish_date": published_date_str,
                "engine": "openwebninja",
                "image_metadata": None,
                "extracted_text": ""
            })
        
        return formatted_results
        
    except requests.exceptions.Timeout:
        logger.error("OpenWebNinja search timed out")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenWebNinja search failed: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in OpenWebNinja search: {str(e)}")
        return []


def _extract_domain_from_link(url):
    """Extract domain from URL."""
    from urllib.parse import urlparse
    
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


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
    """Save search results to database and return the created instance."""
    image_value = cloudinary_public_id if cloudinary_public_id else uploaded_image
    
    return WebsearchResults.objects.create(
        user=user,
        image=image_value,
        query=query or image_url,
        results=results
    )