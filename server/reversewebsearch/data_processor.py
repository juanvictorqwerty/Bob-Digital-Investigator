from urllib.parse import urlparse, urlunparse, parse_qs
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


# List of trusted domains (can be expanded)
TRUSTED_DOMAINS = {
    'reuters.com', 'apnews.com', 'bbc.com', 'nytimes.com', 'washingtonpost.com',
    'theguardian.com', 'wsj.com', 'bloomberg.com', 'cnn.com', 'nbcnews.com',
    'abcnews.go.com', 'cbsnews.com', 'time.com', 'theatlantic.com', 'politico.com',
    'npr.org', 'pbs.org', 'ft.com', 'economist.com', 'nature.com', 'science.org',
    'gov.uk', 'gov.au', 'canada.ca', 'europa.eu', 'un.org', 'who.int',
    'whitehouse.gov', 'state.gov', 'justice.gov', 'fbi.gov', 'nih.gov'
}


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
            ''  # remove fragment
        ))
        
        return normalized
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
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return None


def is_trusted_domain(domain):
    """
    Check if domain is in trusted list.
    """
    if not domain:
        return False
    return domain in TRUSTED_DOMAINS


def normalize_results(raw_results):
    """
    Normalize a list of results from reverse image search engines.
    
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


def score_result(result, engine_counts):
    """
    Score a result based on available metadata and domain trust.
    
    Scoring rules:
    +3 → has publish_date
    +3 → has image_metadata
    +2 → trusted domain
    +1 → high-resolution metadata (if available)
    +1 → appears across multiple engines
    
    Args:
        result: Result dict
        engine_counts: Dict mapping page_url to count of engines that found it
    
    Returns:
        Integer score
    """
    score = 0
    
    # +3 for publish_date
    if result.get('publish_date'):
        score += 3
    
    # +3 for image_metadata
    if result.get('image_metadata'):
        score += 3
    
    # +2 for trusted domain
    domain = result.get('domain')
    if is_trusted_domain(domain):
        score += 2
    
    # +1 for high-resolution metadata
    metadata = result.get('image_metadata')
    if metadata:
        width = metadata.get('width') or metadata.get('dimensions', {}).get('width')
        height = metadata.get('height') or metadata.get('dimensions', {}).get('height')
        if width and height and width >= 1000 and height >= 1000:
            score += 1
    
    # +1 for appearing across multiple engines
    page_url = result.get('page_url')
    if page_url and engine_counts.get(page_url, 0) > 1:
        score += 1
    
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
    Build timeline from ALL results that have publish_date.
    Sort chronologically (oldest → newest).
    
    Args:
        results: List of result dicts
    
    Returns:
        List of timeline entries with date, domain, url
    """
    timeline_entries = []
    
    for result in results:
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


def compute_statistics(results):
    """
    Compute statistics about the results.
    
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
    
    for result in results:
        domain = result.get('domain')
        if domain:
            unique_domains.add(domain)
            if is_trusted_domain(domain):
                trusted_domain_count += 1
    
    return {
        'total_sources': total_sources,
        'with_publish_date': with_publish_date,
        'with_image_metadata': with_image_metadata,
        'unique_domains': len(unique_domains),
        'trusted_domains': trusted_domain_count
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
    
    # Step 6: Build timeline
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
