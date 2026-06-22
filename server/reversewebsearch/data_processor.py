from urllib.parse import urlparse, urlunparse, parse_qs
from datetime import datetime
from collections import defaultdict
import re
import logging

from reversewebsearch.trusted_domains_loader import (
    is_trusted_domain,
    is_certified_facebook_page,
    has_trusted_suffix,
    has_cameroon_keyword,
    has_government_tld,
    is_official_presidential_domain,
    is_tier1_news_agency,
    is_tier1_african_news,
)


logger = logging.getLogger(__name__)


def normalize_url(url):
    """
    Normalize URL by removing tracking parameters and standardizing format.
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)

        # Remove tracking parameters
        query_params = parse_qs(parsed.query)
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'msclkid', '_ga', '_gid', 'ref', 'source'
        }

        clean_params = {
            k: v for k, v in query_params.items() 
            if k.lower() not in tracking_params
        }

        # Rebuild query string
        clean_query = '&'.join(f"{k}={v[0]}" for k, v in clean_params.items())

        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),  # lowercase domain
            parsed.path,
            parsed.params,
            clean_query,
            parsed.fragment
        ))

        return normalized or None

    except Exception as e:
        logger.warning(f"Error normalizing URL {url}: {str(e)}")
        return url


def extract_domain(url):
    """
    Extract domain from URL.
    """
    if not url:
        return None

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]

        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]

        return domain if domain else None

    except Exception:
        return None


def normalize_results(raw_results):
    """
    Normalize raw results into a consistent format.

    Args:
        raw_results: List of dicts with page_url, image_url, title, engine, etc.

    Returns:
        List of normalized result dicts
    """
    normalized = []

    for result in raw_results:
        page_url = result.get('page_url') or result.get('url')
        image_url = result.get('image_url')

        normalized_result = {
            'page_url': normalize_url(page_url),
            'image_url': normalize_url(image_url),
            'title': result.get('title', ''),
            'domain': extract_domain(page_url),
            'engine': result.get('engine', 'unknown'),
            'publish_date': result.get('publish_date'),
            'image_metadata': result.get('image_metadata'),
            'extracted_text': result.get('extracted_text'),
            'thumbnail': result.get('thumbnail', ''),
        }

        normalized.append(normalized_result)

    return normalized


def deduplicate_results(results):
    """
    Remove duplicate entries based on normalized page_url OR identical image_url.
    Keep the richest version (the one with more metadata).

    Args:
        results: List of normalized result dicts

    Returns:
        Deduplicated list of results
    """
    seen_page_urls = {}
    seen_image_urls = {}
    deduplicated = []

    for result in results:
        page_url = result.get('page_url')
        image_url = result.get('image_url')

        # Calculate metadata richness score
        metadata_score = 0
        if result.get('publish_date'):
            metadata_score += 1
        if result.get('image_metadata'):
            metadata_score += 1
        if result.get('extracted_text'):
            metadata_score += 1
        if result.get('title'):
            metadata_score += 1

        # Check for page_url duplicates
        if page_url and page_url in seen_page_urls:
            existing = seen_page_urls[page_url]
            existing_score = seen_page_urls[f"{page_url}_score"]
            if metadata_score > existing_score:
                # Replace with richer version
                idx = deduplicated.index(existing)
                deduplicated[idx] = result
                seen_page_urls[page_url] = result
                seen_page_urls[f"{page_url}_score"] = metadata_score
            continue

        # Check for image_url duplicates
        if image_url and image_url in seen_image_urls:
            existing = seen_image_urls[image_url]
            existing_score = seen_image_urls[f"{image_url}_score"]
            if metadata_score > existing_score:
                # Replace with richer version
                idx = deduplicated.index(existing)
                deduplicated[idx] = result
                seen_image_urls[image_url] = result
                seen_image_urls[f"{image_url}_score"] = metadata_score
            continue

        # Add to results
        deduplicated.append(result)
        if page_url:
            seen_page_urls[page_url] = result
            seen_page_urls[f"{page_url}_score"] = metadata_score
        if image_url:
            seen_image_urls[image_url] = result
            seen_image_urls[f"{image_url}_score"] = metadata_score

    return deduplicated


def enrich_results(results):
    """
    Enrich results by ensuring domain is extracted and keeping available metadata.
    Does NOT invent missing values.

    Args:
        results: List of result dicts

    Returns:
        Enriched list of results
    """
    enriched = []

    for result in results:
        enriched_result = result.copy()

        # Ensure domain is extracted
        if not enriched_result.get('domain'):
            page_url = enriched_result.get('page_url')
            enriched_result['domain'] = extract_domain(page_url)

        # Keep existing fields as-is (do not invent values)
        enriched.append(enriched_result)

    return enriched


def is_miniature_or_sublink(result):
    """
    Detect if an image result is a miniature (thumbnail) or a sublink on a page.

    Checks multiple signals:
    - Image metadata shows very small dimensions (< 200px in either axis)
    - File size is tiny (< 20 KB)
    - Image URL path contains thumbnail indicators (thumb, thumbnail, small, mini, tn)
    - URL query params request small dimensions (w, width, s, size < 300)
    - The 'thumbnail' field points to the same URL as 'image_url' (it's just a thumbnail ref)
    - URL contains Google/Bing image serving size notation (=s<small number>, =w<small number>)

    Args:
        result: Result dict with image_url, image_metadata, etc.

    Returns:
        True if the result appears to be a miniature or sublink
    """
    # Check 1: Image metadata shows very small dimensions
    metadata = result.get('image_metadata')
    if metadata:
        width = metadata.get('width') or (metadata.get('dimensions') or {}).get('width')
        height = metadata.get('height') or (metadata.get('dimensions') or {}).get('height')
        if width is not None and height is not None:
            try:
                w = int(width)
                h = int(height)
                if w < 200 or h < 200:
                    logger.debug(f"Miniature detected: small dimensions {w}x{h}")
                    return True
            except (ValueError, TypeError):
                pass

        # Also check if file_size_bytes in metadata indicates tiny file
        file_size = metadata.get('file_size_bytes')
        if file_size is not None and isinstance(file_size, (int, float)) and file_size < 20 * 1024:
            logger.debug(f"Miniature detected: tiny file size {file_size} bytes")
            return True

    # Check 2: Direct file_size_bytes on the result (may come from fetch_image_metadata merge)
    file_size = result.get('file_size_bytes')
    if file_size is not None and isinstance(file_size, (int, float)) and file_size < 20 * 1024:
        logger.debug(f"Miniature detected: tiny file_size_bytes {file_size}")
        return True

    # Check 3: Image URL contains thumbnail indicators in path
    image_url = result.get('image_url', '') or ''
    if image_url:
        url_lower = image_url.lower()
        thumbnail_path_patterns = [
            '/thumb/', '/thumbnail/', '/small/', '/mini/',
            '/tiny/', '/icon/', '/icons/', '/tn/',
        ]
        for pattern in thumbnail_path_patterns:
            if pattern in url_lower:
                logger.debug(f"Miniature detected: URL path '{pattern}' in {image_url}")
                return True

        # Check filename patterns
        filename_patterns = [
            '_thumb', '-thumb', '.thumb',
            '_tn', '-tn',
            '_small', '-small',
            '_mini', '-mini',
            '_icon', '-icon',
        ]
        # Extract filename from URL
        path_part = urlparse(image_url).path
        for pattern in filename_patterns:
            if pattern in path_part.lower():
                logger.debug(f"Miniature detected: filename pattern '{pattern}' in {path_part}")
                return True

    # Check 4: URL query params suggesting small requested size
    if image_url:
        try:
            parsed = urlparse(image_url)
            if parsed.query:
                qs = parse_qs(parsed.query)
                for param in ['w', 'width', 's', 'size']:
                    if param in qs:
                        try:
                            val = int(qs[param][0])
                            if val < 300:
                                logger.debug(f"Miniature detected: {param}={val} in {image_url}")
                                return True
                        except (ValueError, IndexError):
                            pass
        except Exception:
            pass

    # Check 5: Google/Bing style size notation (=sNNN, =wNNN-hNNN) in URL
    if image_url:
        size_notation = re.findall(r'[=/]s\d{2,3}[=/]?', image_url, re.IGNORECASE)
        if size_notation:
            logger.debug(f"Miniature detected: size notation in {image_url}")
            return True

    # Check 6: The 'thumbnail' field matches 'image_url' — it's just a thumbnail reference
    thumbnail = result.get('thumbnail', '') or ''
    if thumbnail and thumbnail == result.get('image_url', ''):
        logger.debug(f"Miniature detected: image_url matches thumbnail field")
        return True

    return False



# ── URL quality heuristics ──────────────────────────────────────
_JUNK_URL_RE = re.compile(
    r'(thumb|thumbnail|mini|small|preview|cache|proxy|cdn[0-9]|resize|w=\d{1,2}[^0-9])',
    re.IGNORECASE,
)
_CLEAN_IMAGE_URL_RE = re.compile(r'\.(jpg|jpeg|png|webp)(\?.*)?$', re.IGNORECASE)

# ── Date-in-URL ──────────────────────────────
_DATE_IN_URL_RE = re.compile(r'/20[1-3][0-9]/')  # covers 2010–2039


def _is_official_government_source(domain: str, page_url: str) -> bool:
    """Check if domain is an official government or presidential source."""
    if not domain:
        return False
    domain_lower = domain.lower()
    if is_official_presidential_domain(domain_lower):
        return True
    if has_government_tld(domain_lower):
        return True
    # Check URL path patterns for official press releases
    if '/presidence' in page_url.lower() or '/presidency' in page_url.lower():
        return True
    return False

def _is_tier1_news_source(domain: str) -> bool:
    """Check if domain is a tier-1 news agency or major outlet."""
    if not domain:
        return False
    domain_lower = domain.lower()
    return is_tier1_news_agency(domain_lower) or is_tier1_african_news(domain_lower)


def score_result(result: dict, engine_counts: dict, user_query: str = "") -> int:
    """
    Merged ranking algorithm optimised for Cameroon / low-metadata environments.

    KEY CHANGE: Authoritative primary sources (govt press releases, official 
    presidential sites, major news agencies) get heavy bonuses. This prevents
    the system from demanding excessive corroboration when a primary source
    already confirms the claim with specificity.

    Scoring is structured in four tiers so the function produces useful
    rankings even when trust signals and image metadata are entirely absent.

    Tier 1 — universal signals (always available)
        +4   found by 2+ engines
        +2   found by 3+ engines (bonus on top of the +4)
        +2   clean image URL (.jpg/.png/.webp with no junk pattern)

    Tier 2 — local context signals
        +3   .cm domain  (high-confidence Cameroonian source)
        +2   Cameroon keyword in snippet or title
        +2   year detected in page URL (e.g. /2024/)

    Tier 2b — AUTHORITATIVE SOURCE BONUSES (NEW)
        +6   Official government / presidential domain (e.g. prc.cm, kremlin.ru)
        +4   Tier-1 international news agency (Reuters, AFP, AP, BBC, etc.)
        +3   Major verified African news outlet (Jeune Afrique, CRTV, etc.)
        +2   Trusted domain (from trusted_domains.json)
        +1   Trusted suffix in domain (e.g. .org, .gov, .edu in .org.cm, .gov.ru)
        +2   Certified Facebook page (stacked on top of domain trust)

    Tier 3 — soft metadata bonuses (present = great, absent = neutral)
        +2   has publish_date in metadata
        +2   has image_metadata
        +1   image is ≥ 800×600  (lowered from 1000×1000 for mobile-first content)

    Tier 4 — graduated penalties (not a single binary gate)
        -3   junk URL pattern (thumbnails, cache, proxy, resize)
        -4   miniature image
        -6   sublink / non-canonical URL
        -2   no signal at all (floor nudge)

    Max possible score  : 24 pts (with govt source)
    Without trust/meta  : 4–9 pts  (still useful for ranking)
    """
    score = 0
    page_url   = (result.get('page_url') or '').lower()
    image_url  = (result.get('image_url') or '').lower()
    snippet    = (result.get('snippet') or '').lower()
    title      = (result.get('title') or '').lower()
    domain     = (result.get('domain') or '').lower()

    # ── Tier 1: Universal signals ─────────────────────────────────────────────
    engine_count = engine_counts.get(page_url, 0)
    if engine_count >= 2:
        score += 4
    if engine_count >= 3:
        score += 2  # bonus tier — not double-counting, genuine extra confidence

    if image_url:
        if _CLEAN_IMAGE_URL_RE.search(image_url) and not _JUNK_URL_RE.search(image_url):
            score += 2
        elif _JUNK_URL_RE.search(image_url):
            score -= 3  # catches thumbnails the penalty block might miss

    # ── Tier 2: Local context signals ────────────────────────────────────────
    # .cm TLD is a strong proxy for Cameroonian origin — no trust list needed.
    is_cm_domain = domain.endswith('.cm') or '.cm/' in page_url
    if is_cm_domain:
        score += 3

    # Geo-keywords in snippet or title surface locally relevant content
    # even when the domain isn't .cm (e.g. diaspora blogs, regional portals).
    has_local_keyword = has_cameroon_keyword(snippet) or has_cameroon_keyword(title)
    if has_local_keyword and not is_cm_domain:  # avoid stacking with .cm bonus
        score += 2

    # Date in URL is a lightweight freshness proxy used by many African CMS.
    if _DATE_IN_URL_RE.search(page_url):
        score += 2

    # ── Tier 2b: AUTHORITATIVE SOURCE BONUSES (NEW) ─────────────────────────
    # Government / official sources get the highest bonus — they are PRIMARY sources
    if _is_official_government_source(domain, page_url):
        score += 6
        logger.debug(f"Authoritative govt source bonus: {domain}")

    # Tier-1 news agencies are strong secondary corroboration
    elif _is_tier1_news_source(domain):
        score += 4
        logger.debug(f"Tier-1 news bonus: {domain}")

    # Legacy trust bonuses (kept for backward compatibility)
    if is_trusted_domain(domain):
        score += 2
    if has_trusted_suffix(domain):
        score += 1
    if is_certified_facebook_page(page_url):
        score += 2

    # ── Tier 3: Soft metadata bonuses ────────────────────────────────────────
    if result.get('publish_date'):
        score += 2  # still rewarded, but no longer a gate signal

    metadata = result.get('image_metadata')
    if metadata:
        score += 2

        # Lowered resolution threshold: 800×600 covers most mobile-shot images
        # common on Cameroonian social-media reposts and local news sites.
        width  = metadata.get('width')  or metadata.get('dimensions', {}).get('width',  0)
        height = metadata.get('height') or metadata.get('dimensions', {}).get('height', 0)
        if width and height and int(width) >= 800 and int(height) >= 600:
            score += 1

    # ── Tier 4: Graduated penalties ──────────────────────────────────────────
    # Split miniature vs sublink so you can tune them independently in the future.
    if is_miniature_or_sublink(result):
        if is_sublink(result):
            score -= 6
            logger.debug(f"Sublink penalty: {image_url[:80]}")
        else:
            score -= 4
            logger.debug(f"Miniature penalty: {image_url[:80]}")

    # Gentle floor-nudge for results with zero positive signal of any kind.
    has_any_signal = (
        engine_count >= 2
        or result.get('publish_date')
        or metadata
        or is_cm_domain
        or has_local_keyword
        or is_trusted_domain(domain)
        or _is_official_government_source(domain, page_url)
        or _is_tier1_news_source(domain)
    )
    if not has_any_signal:
        score -= 2

    return score

def rank_results(results):
    """
    Rank results by score (highest first).

    Args:
        results: List of result dicts

    Returns:
        List of results with 'score' field added, sorted by score descending
    """
    # Count how many engines found each page_url
    engine_counts = defaultdict(int)
    for result in results:
        page_url = result.get('page_url')
        if page_url:
            engine_counts[page_url] += 1

    # Score each result
    scored_results = []
    for result in results:
        scored_result = result.copy()
        scored_result['score'] = score_result(result, engine_counts)
        scored_results.append(scored_result)

    # Sort by score descending
    ranked = sorted(scored_results, key=lambda x: x['score'], reverse=True)

    return ranked


def select_top_candidates(results, limit=20):
    """
    Select top N candidates from ranked results.

    Args:
        results: List of ranked result dicts
        limit: Maximum number of candidates to return

    Returns:
        List of top N results
    """
    return results[:limit]


def build_timeline(results):
    """
    Build timeline from results that have publish_date AND are not miniatures/sublinks.
    Sort chronologically (oldest → newest).

    Args:
        results: List of result dicts

    Returns:
        List of timeline entries with date, domain, url
    """
    timeline_entries = []

    for result in results:
        # Skip miniatures and sublinks — they should not appear in the timeline
        if is_miniature_or_sublink(result):
            logger.debug(f"Skipping miniature/sublink in timeline: {(result.get('image_url') or '')[:80]}")
            continue

        publish_date = result.get('publish_date')
        if publish_date:
            # Parse date if it's a string
            if isinstance(publish_date, str):
                try:
                    parsed_date = datetime.fromisoformat(publish_date.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    try:
                        # Try other common formats
                        for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%B %d, %Y']:
                            try:
                                parsed_date = datetime.strptime(publish_date, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            continue
                    except Exception:
                        continue
            elif isinstance(publish_date, datetime):
                parsed_date = publish_date
            else:
                continue

            timeline_entries.append({
                'date': parsed_date.isoformat(),
                'domain': result.get('domain'),
                'url': result.get('page_url')
            })

    # Sort chronologically (oldest first)
    timeline_entries.sort(key=lambda x: x['date'])

    return timeline_entries


# is_trusted_domain is imported from trusted_domains_loader
# It checks against the JSON config file (trusted_domains.json)
# See: trusted_domains_loader.is_trusted_domain()


def compute_statistics(results):
    """
    Compute basic statistics from ranked results.

    Args:
        results: List of result dicts

    Returns:
        Dict with statistics
    """
    total_sources = len(results)
    with_publish_date = sum(1 for r in results if r.get('publish_date'))
    with_image_metadata = sum(1 for r in results if r.get('image_metadata'))
    unique_domains = set()
    trusted_domain_count = 0
    govt_source_count = 0
    tier1_news_count = 0
    credible_local_news_count = 0

    for r in results:
        domain = r.get('domain')
        page_url = r.get('page_url', '')
        if domain:
            unique_domains.add(domain)
            if is_trusted_domain(domain):
                trusted_domain_count += 1
            if _is_official_government_source(domain, page_url):
                govt_source_count += 1
            if _is_tier1_news_source(domain):
                tier1_news_count += 1
            # Count credible local news outlets (tier-1 African news)
            if is_tier1_african_news(domain):
                credible_local_news_count += 1

    # Count certified Facebook pages
    certified_fb_count = sum(1 for r in results if is_certified_facebook_page(r.get('page_url')))

    return {
        'total_sources': total_sources,
        'with_publish_date': with_publish_date,
        'with_image_metadata': with_image_metadata,
        'unique_domains': len(unique_domains),
        'trusted_domains': trusted_domain_count,
        'certified_facebook_pages': certified_fb_count,
        'government_sources': govt_source_count,
        'tier1_news_sources': tier1_news_count,
        'credible_local_news_sources': credible_local_news_count,
    }


def process_reverse_search_results(raw_results):
    """
    Main processing pipeline for reverse image search results.

    Args:
        raw_results: List of raw result dicts from search engines

    Returns:
        Dict with normalized_results, top_candidates, timeline, statistics
    """
    logger.info(f"Processing {len(raw_results)} raw results")

    # Step 1: Normalize
    normalized = normalize_results(raw_results)
    logger.info(f"Normalized {len(normalized)} results")

    # Step 2: Deduplicate
    deduplicated = deduplicate_results(normalized)
    logger.info(f"Deduplicated to {len(deduplicated)} results")

    # Step 3: Enrich
    enriched = enrich_results(deduplicated)

    # Step 4: Score
    ranked = rank_results(enriched)
    logger.info(f"Ranked {len(ranked)} results")

    # Step 5: Select top candidates
    top_candidates = select_top_candidates(ranked, limit=20)
    logger.info(f"Selected top {len(top_candidates)} candidates")

    # Step 6: Build timeline (excludes miniatures/sublinks)
    timeline = build_timeline(ranked)
    logger.info(f"Built timeline with {len(timeline)} entries")

    # Step 7: Compute statistics
    statistics = compute_statistics(ranked)
    logger.info(f"Computed statistics: {statistics}")

    return {
        'normalized_results': ranked,
        'top_candidates': top_candidates,
        'timeline': timeline,
        'statistics': statistics
    }