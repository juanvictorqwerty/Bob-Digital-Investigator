import logging
import requests
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from django.conf import settings

logger = logging.getLogger(__name__)


def fetch_image_metadata(url):
    """
    Fetch image metadata (file size, dimensions) using SERP API image search.
    Returns a dict with file_size_bytes and dimensions.
    """
    logger.info(f"Fetching metadata for image URL: {url}")
    
    try:
        from serpapi import GoogleSearch
        
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
