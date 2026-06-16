import logging
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Default timeout for all crawls
_DEFAULT_TIMEOUT = 12  # seconds

# Realistic browser User-Agent to reduce blocking
_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Paywall / login-wall / blocked-content indicators
_PAYWALL_TEXTS = [
    "subscribe to continue reading",
    "subscribe to read",
    "subscribe now",
    "this is a premium article",
    "premium content",
    "you have reached your free article limit",
    "log in to continue",
    "sign in to read",
    "unlock this article",
    "please subscribe",
    "access denied",
    "access restricted",
    "article is behind a paywall",
    "paywall",
    "subscriber only",
    "subscriber-exclusive",
    "register to read",
    "create a free account to continue",
    "this content is for members only",
    "members only",
    "you need a subscription",
    "limited access",
    "403 forbidden",
    "401 unauthorized",
]

# CSS selectors that often indicate paywall overlays
_PAYWALL_SELECTORS = [
    ".paywall",
    ".subscription-wall",
    ".premium-wall",
    ".meter-wall",
    "#paywall",
    ".access-wall",
    ".login-wall",
    ".gate",
    ".registration-wall",
    "[class*='paywall']",
    "[class*='gate']",
    "[class*='subscription']",
    "[data-testid='paywall']",
]

# Pre-compiled regex patterns for performance
_RE_WHITESPACE = re.compile(r'\s+')
_RE_SENSATIONAL = re.compile(r'(breaking!|shocking!|you won\'t believe|viral|must see|urgent)', re.IGNORECASE)
_RE_AI_MARKERS = re.compile(r'(as an ai|as a language model|i cannot|i don\'t have)', re.IGNORECASE)

# Shared requests Session with connection pooling
_http_session = None

def _get_http_session():
    """Get or create a shared requests Session with connection pooling.
    
    Reuses TCP connections across requests, which is significantly faster
    than creating a new connection for every request.
    """
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.headers.update({"User-Agent": _USER_AGENT})
        # Connection pool size: up to 20 concurrent connections
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=0,
        )
        _http_session.mount('https://', adapter)
        _http_session.mount('http://', adapter)
    return _http_session


def get_cached_or_fetch(cache_key, fetch_func, ttl=86400):
    """Get data from cache or fetch and cache it.
    
    Args:
        cache_key: Redis cache key string
        fetch_func: Callable that returns the data to cache
        ttl: Time-to-live in seconds (default 24h)
    
    Returns:
        The cached or freshly fetched data
    """
    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit: {cache_key}")
        return cached
    
    logger.debug(f"Cache miss: {cache_key} — fetching")
    data = fetch_func()
    if data is not None:
        cache.set(cache_key, data, timeout=ttl)
    return data


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


def crawl_image(url, attempt=1, max_retries=2):
    """
    Crawl the actual page URL to extract metadata and readable content.
    
    Retries up to `max_retries` times on transient failures (timeout,
    connection error, server 5xx). Does NOT retry on paywalls, 403s,
    404s, rate limits, or insufficient content.
    
    Replaces the previous RapidAPI-based approach with direct HTTP fetching
    using BeautifulSoup for content extraction. This allows us to:
    
    1. Get the actual page content, not just a domain scrape
    2. Extract metadata: title, publish date, author, domain
    3. Detect paywalls, access blocks, and thin content
    4. Return up to 1000 characters of clean article text
    
    Args:
        url: The page URL to crawl
        attempt: Current attempt number (1-based, internal)
        max_retries: Max attempts before giving up (default 2)
    
    Returns:
        Dict with:
            crawl_status: "success" or "failed"
            crawl_error: Error message or None
            crawled_at: ISO timestamp
            raw_snippet: Up to 1000 chars of clean text
            page_title: The page <title> text
            publish_date: Extracted publication date (ISO format or None)
            author: Extracted author name or None
            domain: Domain extracted from the URL
            paywall_detected: True/False whether a paywall was detected
            attempts: Number of attempts made
    """
    logger.info(f"Crawling page URL: {url} (attempt {attempt}/{max_retries})")

    if not url:
        logger.warning("No URL provided for crawling")
        return _failed_crawl("No URL provided")

    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    try:
        # Use the shared session with connection pooling
        session = _get_http_session()
        response = session.get(
            url,
            timeout=_DEFAULT_TIMEOUT,
            allow_redirects=True,
        )

        # Handle HTTP errors
        if response.status_code >= 400:
            error_msg = f"HTTP {response.status_code}"
            can_retry = False

            if response.status_code == 403:
                error_msg = "Blocked (HTTP 403)"
            elif response.status_code == 404:
                error_msg = "Page not found (HTTP 404)"
            elif response.status_code == 429:
                error_msg = "Rate limited (HTTP 429)"
                # Rate limit — wait 1s and retry if attempts left
                if attempt < max_retries:
                    import time as _time
                    _time.sleep(1)
                    result = crawl_image(url, attempt=attempt + 1, max_retries=max_retries)
                    result["attempts"] = attempt
                    return result
                error_msg = "Rate limited (HTTP 429) — exhausted retries"
            elif response.status_code >= 500:
                # Server error — wait 1s and retry if attempts left
                if attempt < max_retries:
                    import time as _time
                    _time.sleep(1)
                    result = crawl_image(url, attempt=attempt + 1, max_retries=max_retries)
                    result["attempts"] = attempt
                    return result
                error_msg = f"Server error (HTTP {response.status_code}) — exhausted retries"

            logger.warning(f"Crawl failed for {url}: {error_msg}")
            return {**_failed_crawl(error_msg, domain), "attempts": attempt}

        # Check content type — skip non-HTML responses
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            logger.warning(f"Non-HTML response for {url}: {content_type}")
            return {**_failed_crawl(f"Non-HTML content: {content_type}", domain), "attempts": attempt}

        # Parse HTML
        soup = BeautifulSoup(response.text, "html.parser")

        # ── Extract metadata ────────────────────────────────────────────────
        page_title = _extract_title(soup)
        publish_date = _extract_publish_date(soup)
        author = _extract_author(soup)

        # ── Check for paywall / access blocks ──────────────────────────────
        paywall_detected = _detect_paywall(soup, response.text)

        # ── Extract readable content (up to 1000 chars) ───────────────────
        raw_snippet = _extract_readable_content(soup, max_chars=1000)

        if not raw_snippet or len(raw_snippet.strip()) < 50:
            logger.warning(f"Very little content extracted from {url}: {len(raw_snippet) if raw_snippet else 0} chars")
            result = {
                "crawl_status": "failed",
                "crawl_error": "Insufficient content extracted",
                "crawled_at": datetime.utcnow().isoformat(),
                "raw_snippet": raw_snippet or "",
                "page_title": page_title,
                "publish_date": publish_date,
                "author": author,
                "domain": domain,
                "paywall_detected": paywall_detected,
                "attempts": attempt,
            }
            return result

        logger.info(
            f"Successfully crawled {url} (attempt {attempt}/{max_retries}): "
            f"title='{page_title[:60] if page_title else 'N/A'}', "
            f"date={publish_date or 'N/A'}, "
            f"author={author or 'N/A'}, "
            f"snippet={len(raw_snippet)} chars, "
            f"paywall={paywall_detected}"
        )

        result = {
            "crawl_status": "success",
            "crawl_error": None,
            "crawled_at": datetime.utcnow().isoformat(),
            "raw_snippet": raw_snippet[:1000],
            "page_title": page_title,
            "publish_date": publish_date,
            "author": author,
            "domain": domain,
            "paywall_detected": paywall_detected,
            "attempts": attempt,
        }

        return result

    except requests.exceptions.Timeout:
        logger.warning(f"Timeout crawling {url} (attempt {attempt}/{max_retries})")
        if attempt < max_retries:
            import time as _time
            _time.sleep(1)
            result = crawl_image(url, attempt=attempt + 1, max_retries=max_retries)
            result["attempts"] = attempt
            return result
        return {**_failed_crawl("Crawl timeout — exhausted retries", domain), "attempts": attempt}
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error crawling {url} (attempt {attempt}/{max_retries}): {str(e)[:80]}")
        if attempt < max_retries:
            import time as _time
            _time.sleep(1)
            result = crawl_image(url, attempt=attempt + 1, max_retries=max_retries)
            result["attempts"] = attempt
            return result
        return {**_failed_crawl(f"Connection error — exhausted retries", domain), "attempts": attempt}
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error crawling {url}: {str(e)[:100]}")
        return {**_failed_crawl(f"Request error: {str(e)[:80]}", domain), "attempts": attempt}
    except Exception as e:
        logger.error(f"Unexpected error crawling {url}: {str(e)[:200]}")
        return {**_failed_crawl(f"Unexpected error: {str(e)[:80]}", domain), "attempts": attempt}


def _failed_crawl(error_message, domain=None):
    """Return a standard failed-crawl response dict."""
    return {
        "crawl_status": "failed",
        "crawl_error": error_message,
        "crawled_at": datetime.utcnow().isoformat(),
        "raw_snippet": None,
        "page_title": None,
        "publish_date": None,
        "author": None,
        "domain": domain,
        "paywall_detected": None,
    }


def _extract_title(soup):
    """Extract page title from <title> tag, Open Graph, or Twitter card."""
    # OG title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return str(og_title["content"]).strip()

    # Twitter card title
    twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
    if twitter_title and twitter_title.get("content"):
        return str(twitter_title["content"]).strip()

    # Standard <title>
    if soup.title and soup.title.string:
        return soup.title.string.strip()

    # First <h1> as fallback
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:200]

    return None


def _extract_publish_date(soup):
    """Extract publication date from meta tags or <time> elements.

    Returns ISO-formatted date string or None.
    """
    date_str = None

    # Priority 1: article:published_time (OG)
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        date_str = meta["content"]

    # Priority 2: <meta name="date" content="...">
    if not date_str:
        meta = soup.find("meta", attrs={"name": "date"})
        if meta and meta.get("content"):
            date_str = meta["content"]

    # Priority 3: <meta name="DC.date" content="...">
    if not date_str:
        meta = soup.find("meta", attrs={"name": "DC.date"})
        if meta and meta.get("content"):
            date_str = meta["content"]

    # Priority 4: <time> element with datetime attribute
    if not date_str:
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            date_str = time_tag["datetime"]

    # Priority 5: <meta itemprop="datePublished">
    if not date_str:
        meta = soup.find("meta", itemprop="datePublished")
        if meta and meta.get("content"):
            date_str = meta["content"]

    if not date_str:
        return None

    # Attempt to parse and normalize the date
    try:
        parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return parsed.isoformat()
    except (ValueError, AttributeError):
        pass

    # Try common formats
    for fmt in [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%B %d, %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%d %b %Y",
    ]:
        try:
            parsed = datetime.strptime(date_str.strip(), fmt)
            return parsed.isoformat()
        except (ValueError, AttributeError):
            continue

    # Return raw date string if we can't parse but have it
    return date_str.strip() if date_str.strip() else None


def _extract_author(soup):
    """Extract author name from meta tags or byline elements."""
    # Priority 1: <meta name="author">
    meta = soup.find("meta", attrs={"name": "author"})
    if meta and meta.get("content"):
        return str(meta["content"]).strip()

    # Priority 2: article:author (OG)
    meta = soup.find("meta", property="article:author")
    if meta and meta.get("content"):
        return str(meta["content"]).strip()

    # Priority 3: <meta itemprop="author">
    meta = soup.find("meta", itemprop="author")
    if meta and meta.get("content"):
        return str(meta["content"]).strip()

    # Priority 4: Twitter card creator
    meta = soup.find("meta", attrs={"name": "twitter:creator"})
    if meta and meta.get("content"):
        return str(meta["content"]).strip()

    # Priority 5: Look for common byline selectors in HTML
    byline_selectors = [
        ".byline", ".author", ".article-author", ".post-author",
        "[class*='byline']", "[class*='author']",
        "[rel='author']", "span.author", "a.author",
    ]
    for selector in byline_selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(strip=True)
            if text and len(text) < 200:
                return text

    return None


def _detect_paywall(soup, raw_html):
    """Detect whether the page has a paywall or login wall."""
    # Check 1: Paywall CSS selectors
    for selector in _PAYWALL_SELECTORS:
        if soup.select_one(selector):
            logger.debug(f"Paywall detected via CSS selector: {selector}")
            return True

    # Check 2: Paywall keywords in visible text
    body_text = soup.get_text().lower() if soup.body else raw_html.lower()
    for phrase in _PAYWALL_TEXTS:
        if phrase in body_text:
            logger.debug(f"Paywall detected via text: '{phrase}'")
            return True

    # Check 3: Meta robots noindex (often used for gated content)
    meta_robots = soup.find("meta", attrs={"name": "robots"})
    if meta_robots and meta_robots.get("content"):
        content = meta_robots["content"].lower()
        if "noindex" in content and "nofollow" in content:
            logger.debug("Paywall suspected via meta robots: noindex, nofollow")
            return True

    return False


def _extract_readable_content(soup, max_chars=1000):
    """
    Extract readable text content from the page, up to max_chars.

    Strategy:
    1. Remove script, style, nav, footer, header, aside elements
    2. Look for <article> tag first (best signal)
    3. Fall back to <main> or <body>
    4. Extract text, clean whitespace, truncate to max_chars
    """
    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                      "noscript", "iframe", "form", "button", "svg",
                      "[role='navigation']", "[role='banner']",
                      "[role='contentinfo']"]):
        tag.decompose()

    # Try to find the main content area
    content = None

    # Priority 1: <article>
    article = soup.find("article")
    if article:
        content = article

    # Priority 2: <main>
    if not content:
        main_tag = soup.find("main")
        if main_tag:
            content = main_tag

    # Priority 3: <div class="content" ...> or similar common selectors
    if not content:
        for selector in [
            ".content", ".article-body", ".post-content", ".entry-content",
            ".story-body", "#content", "#article", "#main-content",
            "[class*='content']", "[class*='article-body']",
        ]:
            element = soup.select_one(selector)
            if element:
                content = element
                break

    # Priority 4: <body> as last resort
    if not content:
        content = soup.body

    if not content:
        # No body tag at all — use the whole soup
        content = soup

    # Extract text
    text = content.get_text(separator=" ", strip=True)

    # Clean excessive whitespace using pre-compiled regex
    text = _RE_WHITESPACE.sub(' ', text).strip()

    return text[:max_chars]


def extract_raw_snippet(crawl_data):
    """
    Extract the first 300 characters from the crawl response.
    Handles various response formats from RapidAPI.

    NOTE: This function is kept for backward compatibility but is no longer
    used by the new `crawl_image()` function which returns `raw_snippet` directly.
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