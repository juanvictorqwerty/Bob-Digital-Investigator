"""
Research report generator for the Bob Digital Investigator.

After the robot analysis determines a verdict (real/likely/fake/suspicious/unconfirmed),
this module performs additional SearXNG searches and compiles a structured research report.
"""
import json
import logging
from django.conf import settings
from openai import OpenAI

from .searxng_client import search_general, search_images, search_videos

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
        queries.append(f"{claim} origin debunked misinformation")
        queries.append(f"what actually happened {claim} verified truth")
    elif is_unconfirmed:
        # Search for any information that might clarify
        queries.append(f"{claim} fact check verification")
        queries.append(f"{claim} evidence sources")
        queries.append(f"{claim} what is the truth")
    else:
        # Search for additional confirming evidence
        queries.append(f"{claim} background history")
        queries.append(f"{claim} recent developments")
        queries.append(f"{claim} expert analysis official statement")

    return queries


def run_searxng_searches(queries):
    """
    Execute multiple SearXNG searches and aggregate results.

    Every query searches general + images + videos to collect
    rich results with images and source URLs.

    Args:
        queries: List of search query strings

    Returns:
        Dict with aggregated 'general', 'images', 'videos' results
    """
    all_general = []
    all_images = []
    all_videos = []
    seen_urls = set()
    seen_image_urls = set()
    seen_video_urls = set()

    for i, query in enumerate(queries):
        logger.info(f"SearXNG research query [{i+1}/{len(queries)}]: {query}")

        # Every query searches all categories
        general = search_general(query)
        images = search_images(query)
        videos = search_videos(query)

        # Deduplicate general results by URL
        for r in general:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_general.append(r)

        # Deduplicate images by source_url
        for img in images:
            src = img.get('source_url', '')
            if src and src not in seen_image_urls:
                seen_image_urls.add(src)
                all_images.append(img)

        # Deduplicate videos by URL
        for vid in videos:
            url = vid.get('url', '')
            if url and url not in seen_video_urls:
                seen_video_urls.add(url)
                all_videos.append(vid)

    return {
        'general': all_general,
        'images': all_images,
        'videos': all_videos,
    }


def compile_research_with_llm(claim, verdict, confidence, explanation, search_results, generated_queries):
    """
    Use the LLM to compile a structured research summary from SearXNG results.

    Args:
        claim: The original user claim
        verdict: The analysis verdict
        confidence: Confidence score
        explanation: Original analysis explanation
        search_results: Dict with 'general', 'images', 'videos' from SearXNG
        generated_queries: List of queries that were executed

    Returns:
        Dict with the new report schema or a fallback report if LLM fails
    """
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — cannot compile research with LLM")
        return _fallback_report(verdict, claim)

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
            max_tokens=1500,
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content.strip()
        parsed = _parse_llm_response(raw_content)

        logger.info(
            f"LLM research compiled: summary={len(parsed.get('summary', ''))} chars"
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
                    max_tokens=1500,
                    response_format={"type": "json_object"}
                )
                raw_content = response.choices[0].message.content.strip()
                return _parse_llm_response(raw_content)
            except Exception as fallback_err:
                logger.error(f"LLM fallback also failed: {str(fallback_err)}")

        # Return fallback report
        return _fallback_report(verdict, claim)


def build_research_prompt(claim, verdict, confidence, explanation, search_results, generated_queries):
    """
    Build a prompt for the LLM to compile a research summary from SearXNG results.
    """
    # Map verdict to the three-tier system
    if verdict in ('real', 'likely'):
        verdict_mapped = "TRUE"
    elif verdict in ('fake', 'suspicious'):
        verdict_mapped = "FAKE"
    else:
        verdict_mapped = "UNCERTAIN"

    # Determine strategy
    if verdict_mapped == "TRUE":
        strategy = (
            "The claim has been assessed as TRUE or LIKELY TRUE. "
            "Your task is to write a brief summary reinforcing this finding with "
            "additional context and supporting evidence from the search results."
        )
    elif verdict_mapped == "FAKE":
        strategy = (
            "The claim has been assessed as FALSE or SUSPICIOUS. "
            "Your task is to write a brief summary explaining what actually happened, "
            "debunking the false claim using evidence from the search results."
        )
    else:
        strategy = (
            "The claim could not be confirmed due to insufficient or contradictory evidence. "
            "Your task is to write a brief summary presenting what is known and what "
            "remains uncertain based on the search results."
        )

    # Build general results section (used for context only)
    general_results = search_results.get('general', [])
    general_lines = []
    for i, r in enumerate(general_results[:12], 1):
        general_lines.append(
            f"  [{i}] {r.get('title', 'No title')}\n"
            f"      URL: {r.get('url', '')}\n"
            f"      Domain: {r.get('domain', '')}\n"
            f"      Snippet: {r.get('snippet', '')[:400]}\n"
        )
    general_text = '\n'.join(general_lines) if general_lines else "  (No general web results found)"

    # Build image results section
    images_results = search_results.get('images', [])
    images_lines = []
    for i, img in enumerate(images_results[:10], 1):
        images_lines.append(
            f"  [{i}] {img.get('title', 'No title')}\n"
            f"      Source URL: {img.get('source_url', '')}\n"
            f"      Thumbnail: {img.get('thumbnail_url', '')}\n"
            f"      Domain: {img.get('domain', '')}\n"
            f"      Size: {img.get('width', 'N/A')}x{img.get('height', 'N/A')}\n"
        )
    images_text = '\n'.join(images_lines) if images_lines else "  (No image results found)"

    # Build video results section
    videos_results = search_results.get('videos', [])
    videos_lines = []
    for i, vid in enumerate(videos_results[:10], 1):
        videos_lines.append(
            f"  [{i}] {vid.get('title', 'No title')}\n"
            f"      URL: {vid.get('url', '')}\n"
            f"      Duration: {vid.get('duration', 'N/A')}\n"
            f"      Domain: {vid.get('domain', '')}\n"
            f"      Description: {vid.get('description', '')[:200]}\n"
        )
    videos_text = '\n'.join(videos_lines) if videos_lines else "  (No video results found)"

    queries_text = '\n'.join(f"  - {q}" for q in generated_queries)

    return f"""You are a digital forensics and fact-checking research assistant. You have been given
the results of additional web searches performed to deepen the investigation of a claim.

## ORIGINAL CLAIM
{claim or "(No additional claim provided by the user)"}

## PREVIOUS ANALYSIS VERDICT
- Verdict: {verdict.upper()}
- Mapped Verdict: {verdict_mapped}
- Explanation: {explanation}

## RESEARCH STRATEGY
{strategy}

## SEARCH QUERIES USED
{queries_text}

## WEB SEARCH RESULTS
{general_text}

## IMAGE SEARCH RESULTS
{images_text}

## VIDEO SEARCH RESULTS
{videos_text}

## YOUR TASK

Based on all the search results above, write a concise factual summary (3-5 sentences) that:
- If verdict is TRUE: Provides additional context and reinforcing evidence from the search results
- If verdict is FAKE: Explains what actually happened and debunks the false claim
- If verdict is UNCERTAIN: Presents what is known and what remains uncertain

Write the summary in the SAME LANGUAGE as the original claim (French if the claim is in French, English if in English).

Respond with a strict JSON object matching this exact schema:
{{
  "summary": "Your 3-5 sentence research summary here. Keep it factual, neutral, and informative.",
  "additional_context": "string or null — additional enriching context if verdict is TRUE. Set to null otherwise.",
  "reality_check": "string or null — what is actually true based on sources if verdict is FAKE or UNCERTAIN. Set to null otherwise."
}}

**IMPORTANT RULES:**
- Write the summary in the SAME LANGUAGE as the original claim (French if the claim is in French, English if in English).
- Keep the summary factual, neutral, and informative.
- Do NOT fabricate facts — use only what appears in the search results above.
- The summary is the most important part — focus on clarity and accuracy.
- You may reference images or videos found in the search results if they provide relevant evidence.
"""
    # Note: The raw SearXNG results (sources, images, videos) will be passed separately to the frontend
    # so users can click through to the source articles and view media themselves.


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

    # Ensure all expected fields exist with correct types
    return {
        'summary': str(data.get('summary', '')),
        'additional_context': data.get('additional_context') if data.get('additional_context') else None,
        'reality_check': data.get('reality_check') if data.get('reality_check') else None,
    }


def _fallback_report(verdict, claim):
    """
    Generate a basic report without LLM when it's unavailable.
    Uses the same schema as the LLM-generated report.
    """
    # Map verdict
    if verdict in ('real', 'likely'):
        verdict_mapped = "TRUE"
    elif verdict in ('fake', 'suspicious'):
        verdict_mapped = "FAKE"
    else:
        verdict_mapped = "UNCERTAIN"

    summary = (
        f"The claim was assessed as {verdict_mapped}. "
        f"Additional research sources were found — review the provided links for details."
    )

    additional_context = None
    reality_check = None
    if verdict_mapped == "TRUE":
        additional_context = (
            f"The claim was assessed as TRUE. Review the provided sources for supporting evidence."
        )
    else:
        reality_check = (
            f"The claim was assessed as {verdict_mapped}. "
            f"Review the provided sources for the verified version of events."
        )

    return {
        'summary': summary,
        'additional_context': additional_context,
        'reality_check': reality_check,
    }


def _empty_report():
    """Return an empty report structure."""
    return {
        'summary': '',
        'additional_context': None,
        'reality_check': None,
    }


def generate_research_report(websearch_result, robot_analysis, processed_data):
    """
    Main entry point — generate a full research report after the robot analysis.

    Args:
        websearch_result: WebsearchResults model instance
        robot_analysis: Dict with verdict, confidence, explanation, key_evidence
        processed_data: The full processed results dict

    Returns:
        Tuple of (research_queries, research_report, additional_sources, images, videos)
        where additional_sources is a list of source dicts with title, url, domain, snippet
    """
    claim = websearch_result.query or ""
    verdict = robot_analysis.get('verdict', 'unconfirmed')
    confidence = robot_analysis.get('confidence', 0.0)
    explanation = robot_analysis.get('explanation', '')

    # Step 1: Generate search queries based on verdict
    queries = generate_research_queries(claim, verdict)
    if not queries:
        logger.info("No research queries generated (empty claim)")
        return [], _empty_report(), [], [], []

    logger.info(f"Generated {len(queries)} research queries for verdict '{verdict}'")

    # Step 2: Execute SearXNG searches (all queries get images+videos)
    search_results = run_searxng_searches(queries)
    total_results = (
        len(search_results.get('general', []))
        + len(search_results.get('images', []))
        + len(search_results.get('videos', []))
    )
    logger.info(f"SearXNG returned {total_results} total results")

    # Extract additional sources from SearXNG results for the frontend
    additional_sources = []
    for r in search_results.get('general', [])[:15]:
        additional_sources.append({
            'title': r.get('title', ''),
            'url': r.get('url', ''),
            'domain': r.get('domain', ''),
            'snippet': r.get('snippet', '')[:300] if r.get('snippet') else '',
        })

    # Extract images and videos for the frontend
    images = search_results.get('images', [])[:20]
    videos = search_results.get('videos', [])[:20]

    # Step 3: Compile research summary with LLM
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
        f"sources={len(additional_sources)}, images={len(images)}, videos={len(videos)}"
    )

    return queries, report, additional_sources, images, videos