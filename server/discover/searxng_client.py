"""
SearXNG API client for performing metasearch queries.
Queries a self-hosted SearXNG instance via its JSON API.
Results are cached in Redis to avoid redundant requests.
"""
import logging
import requests
from urllib.parse import urljoin, quote_plus
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Default cache TTL for SearXNG results (24 hours)
_CACHE_TTL = getattr(settings, 'CACHE_EXTERNAL_API_TTL', 86400)

# Request timeout
_TIMEOUT = 15  # seconds


def _get_base_url():
    """Return the SearXNG base URL from Django settings."""
    return getattr(settings, 'SEARXNG_BASE_URL', 'http://localhost:8888').rstrip('/')


def _search(query, categories=None, page=1, language='auto'):
    """
    Execute a search query against SearXNG.

    Args:
        query: Search query string
        categories: List of category strings (e.g. ['general'], ['images'], ['videos'])
        page: Result page number (1-based)
        language: Language code or 'auto'

    Returns:
        Dict with 'results', 'number_of_results', etc. or None on failure
    """
    if not query or not query.strip():
        logger.warning("Empty query provided to SearXNG search")
        return None

    base_url = _get_base_url()
    cache_key = f"searxng:{':'.join(categories or ['general'])}:{query}:{page}"

    # Check cache
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"SearXNG cache hit: {query[:50]} ({':'.join(categories or ['general'])})")
        return cached

    params = {
        'q': query.strip(),
        'format': 'json',
        'language': language,
        'pageno': page,
    }
    if categories:
        params['categories'] = ','.join(categories)

    try:
        url = f"{base_url}/search"
        response = requests.get(url, params=params, timeout=_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        result = {
            'results': data.get('results', []),
            'number_of_results': data.get('number_of_results', 0),
            'query': query,
            'categories': categories or ['general'],
        }

        # Cache the result
        cache.set(cache_key, result, timeout=_CACHE_TTL)
        logger.info(
            f"SearXNG search: '{query[:50]}' ({':'.join(categories or ['general'])}) "
            f"→ {len(result['results'])} results"
        )
        return result

    except requests.exceptions.Timeout:
        logger.error(f"SearXNG search timed out for query: {query[:50]}")
        return None
    except requests.exceptions.ConnectionError:
        logger.error(f"SearXNG connection failed. Is the service running at {base_url}?")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"SearXNG request failed: {str(e)}")
        return None
    except (ValueError, KeyError) as e:
        logger.error(f"SearXNG response parse error: {str(e)}")
        return None


def search_general(query, page=1, language='auto'):
    """
    Search for general web results.

    Args:
        query: Search query string
        page: Result page number (1-based)
        language: Language code or 'auto'

    Returns:
        List of result dicts with: title, url, snippet, engine, domain, score
    """
    data = _search(query, categories=['general'], page=page, language=language)
    if not data:
        return []

    results = []
    for item in data.get('results', []):
        url = item.get('url', '')
        domain = _extract_domain(url)
        results.append({
            'title': item.get('title', ''),
            'url': url,
            'snippet': item.get('content', ''),
            'engine': ', '.join(item.get('engines', [])),
            'domain': domain,
            'score': item.get('score', 0),
            'published_date': item.get('publishedDate'),
            'thumbnail': item.get('thumbnail', ''),
        })

    return results


def search_images(query, page=1, language='auto'):
    """
    Search for image results.

    Args:
        query: Search query string
        page: Result page number (1-based)
        language: Language code or 'auto'

    Returns:
        List of image result dicts with: thumbnail_url, source_url, title, width, height
    """
    data = _search(query, categories=['images'], page=page, language=language)
    if not data:
        return []

    results = []
    for item in data.get('results', []):
        results.append({
            'thumbnail_url': item.get('thumbnail', ''),
            'source_url': item.get('img_src', '') or item.get('url', ''),
            'page_url': item.get('url', ''),
            'title': item.get('title', ''),
            'engine': ', '.join(item.get('engines', [])),
            'width': item.get('width'),
            'height': item.get('height'),
            'filesize': item.get('filesize'),
            'domain': _extract_domain(item.get('url', '')),
        })

    return results


def search_videos(query, page=1, language='auto'):
    """
    Search for video results.

    Args:
        query: Search query string
        page: Result page number (1-based)
        language: Language code or 'auto'

    Returns:
        List of video result dicts with: thumbnail_url, url, title, source, duration
    """
    data = _search(query, categories=['videos'], page=page, language=language)
    if not data:
        return []

    results = []
    for item in data.get('results', []):
        results.append({
            'thumbnail_url': item.get('thumbnail', ''),
            'url': item.get('url', ''),
            'title': item.get('title', ''),
            'source': item.get('engine', ''),
            'duration': item.get('length'),
            'description': item.get('content', ''),
            'domain': _extract_domain(item.get('url', '')),
            'published_date': item.get('publishedDate'),
        })

    return results


def search_all(query, language='auto'):
    """
    Execute a comprehensive search: general + images + videos.

    Args:
        query: Search query string
        language: Language code or 'auto'

    Returns:
        Dict with 'general', 'images', 'videos' lists
    """
    general = search_general(query, language=language)
    images = search_images(query, language=language)
    videos = search_videos(query, language=language)

    return {
        'general': general,
        'images': images,
        'videos': videos,
    }


def _extract_domain(url):
    """Extract domain from URL."""
    from urllib.parse import urlparse
    if not url:
        return ''
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ''