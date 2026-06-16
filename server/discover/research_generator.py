"""
Research report generator for the Bob Digital Investigator.

After the robot analysis determines a verdict (real/likely/fake/suspicious/unconfirmed),
this module performs additional SearXNG searches and compiles a structured research report.

For FAKE/SUSPICIOUS verdicts: searches for the truth behind the claim
For REAL/LIKELY verdicts: searches for reinforcing evidence
For UNCONFIRMED verdicts: searches for any clarifying information
"""
import json
import logging
from django.conf import settings
from openai import OpenAI

from .searxng_client import search_general, search_images, search_videos
from .llm_research_prompt import build_research_prompt

logger = logging.getLogger(__name__)

# LLM config — reuse the same models as the robot analysis
RESEARCH_MODEL = "openai/gpt-4o-mini"
RESEARCH_FALLBACK_MODEL = "anthropic/claude-3-haiku"


def generate_research_queries(claim, verdict):
    """
    Generate search queries based on the claim and the analysis verdict.

    Args:
        claim: The original user claim / query text
        verdict: The analysis verdict (real, likely, fake, suspicious, unconfirmed)

    Returns:
        List of search query strings
    """
    if not claim or not claim.strip():
        return []

    claim = claim.strip()
    queries = []

    is_false = verdict in ('fake', 'suspicious')
    is_unconfirmed = verdict == 'unconfirmed'
    is_true = verdict in ('real', 'likely')

    if is_false:
        # Search for the truth — what actually happened
        queries.append(f"{claim} fact check")
        queries.append(f"{claim} debunked")
        queries.append(f"what actually happened {claim}")
    elif is_unconfirmed:
        # Search for any information that might clarify
        queries.append(f"{claim} fact check")
        queries.append(f"{claim} verification")
        queries.append(f"{claim} sources")
    else:
        # Search for additional confirming evidence
        queries.append(f"{claim}")
        queries.append(f"{claim} confirmed")
        queries.append(f"{claim} official statement")

    return queries


def run_searxng_searches(queries):
    """
    Execute multiple SearXNG searches and aggregate results.

    For the first query, we search general + images + videos.
    For additional queries, we only search general (to get diverse sources).

    Args:
        queries: List of search query strings

    Returns:
        Dict with aggregated 'general', 'images', 'videos' results
        and deduplication applied
    """
    all_general = []
    all_images = []
    all_videos = []
    seen_urls = set()

    for i, query in enumerate(queries):
        logger.info(f"SearXNG research query [{i+1}/{len(queries)}]: {query}")

        if i == 0:
            # First query: full search (general + images + videos)
            general = search_general(query)
            all_images = search_images(query)
            all_videos = search_videos(query)
        else:
            # Subsequent queries: general only for diverse sources
            general = search_general(query)

        # Deduplicate general results by URL
        for r in general:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_general.append(r)

    return {
        'general': all_general,
        'images': all_images,
        'videos': all_videos,
    }


def compile_research_with_llm(claim, verdict, confidence, explanation, search_results, generated_queries):
    """
    Use the LLM to compile a structured research report from SearXNG results.

    Args:
        claim: The original user claim
        verdict: The analysis verdict
        confidence: Confidence score
        explanation: Original analysis explanation
        search_results: Dict with 'general', 'images', 'videos' from SearXNG
        generated_queries: List of queries that were executed

    Returns:
        Dict with 'summary', 'key_findings', 'sources', 'images', 'videos'
        or a fallback report if LLM fails
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — cannot compile research with LLM")
        return _fallback_report(search_results, verdict)

    prompt = build_research_prompt(
        claim=claim,
        verdict=verdict,
        confidence=confidence,
        explanation=explanation,
        search_results=search_results,
        generated_queries=generated_queries,
    )

    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://bob-investigator.app",
                "X-Title": "Bob Digital Investigator - Research",
            }
        )

        response = client.chat.completions.create(
            model=RESEARCH_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content.strip()
        parsed = _parse_llm_response(raw_content)

        logger.info(
            f"LLM research compiled: {len(parsed.get('sources', []))} sources, "
            f"{len(parsed.get('images', []))} images, "
            f"{len(parsed.get('videos', []))} videos"
        )
        return parsed

    except Exception as e:
        logger.error(f"LLM research compilation failed with {RESEARCH_MODEL}: {str(e)}")

        # Try fallback model
        if RESEARCH_MODEL != RESEARCH_FALLBACK_MODEL:
            try:
                client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key,
                    default_headers={
                        "HTTP-Referer": "https://bob-investigator.app",
                        "X-Title": "Bob Digital Investigator - Research",
                    }
                )
                response = client.chat.completions.create(
                    model=RESEARCH_FALLBACK_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                raw_content = response.choices[0].message.content.strip()
                return _parse_llm_response(raw_content)
            except Exception as fallback_err:
                logger.error(f"LLM fallback also failed: {str(fallback_err)}")

        # Return fallback report
        return _fallback_report(search_results, verdict)


def _parse_llm_response(content):
    """Parse and clean the LLM JSON response."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        data = json.loads(content[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to parse LLM research response: {e}")
        return _empty_report()

    # Ensure all expected fields exist
    return {
        'summary': str(data.get('summary', '')),
        'key_findings': data.get('key_findings', []) if isinstance(data.get('key_findings'), list) else [],
        'sources': data.get('sources', []) if isinstance(data.get('sources'), list) else [],
        'images': data.get('images', []) if isinstance(data.get('images'), list) else [],
        'videos': data.get('videos', []) if isinstance(data.get('videos'), list) else [],
    }


def _fallback_report(search_results, verdict):
    """
    Generate a basic report without LLM when it's unavailable.
    Simply selects the top results from SearXNG.
    """
    general = search_results.get('general', [])
    images = search_results.get('images', [])
    videos = search_results.get('videos', [])

    # Pick top 5 general results as sources
    sources = []
    for r in general[:5]:
        sources.append({
            'title': r.get('title', ''),
            'url': r.get('url', ''),
            'snippet': r.get('snippet', ''),
            'domain': r.get('domain', ''),
        })

    # Pick top 5 images
    img_list = []
    for img in images[:5]:
        img_list.append({
            'thumbnail_url': img.get('thumbnail_url', ''),
            'source_url': img.get('source_url', ''),
            'title': img.get('title', ''),
        })

    # Pick top 3 videos
    vid_list = []
    for vid in videos[:3]:
        vid_list.append({
            'url': vid.get('url', ''),
            'thumbnail_url': vid.get('thumbnail_url', ''),
            'title': vid.get('title', ''),
            'source': vid.get('source', ''),
            'duration': vid.get('duration'),
        })

    summary = (
        f"Automated research results for a claim assessed as '{verdict}'. "
        f"Found {len(sources)} relevant sources, {len(img_list)} related images, "
        f"and {len(vid_list)} related videos."
    )

    return {
        'summary': summary,
        'key_findings': [],
        'sources': sources,
        'images': img_list,
        'videos': vid_list,
    }


def _empty_report():
    """Return an empty report structure."""
    return {
        'summary': '',
        'key_findings': [],
        'sources': [],
        'images': [],
        'videos': [],
    }


def generate_research_report(websearch_result, robot_analysis, processed_data):
    """
    Main entry point — generate a full research report after the robot analysis.

    Args:
        websearch_result: WebsearchResults model instance
        robot_analysis: Dict with verdict, confidence, explanation, key_evidence
        processed_data: The full processed results dict

    Returns:
        Tuple of (research_queries, research_report) for storage in RobotAnalysis
    """
    claim = websearch_result.query or ""
    verdict = robot_analysis.get('verdict', 'unconfirmed')
    confidence = robot_analysis.get('confidence', 0.0)
    explanation = robot_analysis.get('explanation', '')

    # Step 1: Generate search queries based on verdict
    queries = generate_research_queries(claim, verdict)
    if not queries:
        logger.info("No research queries generated (empty claim)")
        return [], _empty_report()

    logger.info(f"Generated {len(queries)} research queries for verdict '{verdict}'")

    # Step 2: Execute SearXNG searches
    search_results = run_searxng_searches(queries)
    total_results = (
        len(search_results.get('general', []))
        + len(search_results.get('images', []))
        + len(search_results.get('videos', []))
    )
    logger.info(f"SearXNG returned {total_results} total results")

    # Step 3: Compile research report with LLM
    report = compile_research_with_llm(
        claim=claim,
        verdict=verdict,
        confidence=confidence,
        explanation=explanation,
        search_results=search_results,
        generated_queries=queries,
    )

    logger.info(
        f"Research report generated: summary={len(report.get('summary', ''))} chars, "
        f"sources={len(report.get('sources', []))}, "
        f"images={len(report.get('images', []))}, "
        f"videos={len(report.get('videos', []))}"
    )

    return queries, report