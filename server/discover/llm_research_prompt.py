"""
LLM prompt builder for research report compilation.
Takes SearXNG search results and the original analysis verdict,
then builds a prompt for the LLM to compile a structured research report.
"""
import json
from io import StringIO


def build_research_prompt(claim, verdict, confidence, explanation, search_results, generated_queries):
    """
    Build a prompt for the LLM to compile a research report from SearXNG results.

    Args:
        claim: The original user claim / query
        verdict: The analysis verdict (real, likely, fake, suspicious, unconfirmed)
        confidence: The confidence score (0.0 - 1.0)
        explanation: The original analysis explanation
        search_results: Dict with 'general', 'images', 'videos' lists from SearXNG
        generated_queries: List of search queries that were executed

    Returns:
        String prompt for the LLM
    """
    # Determine research strategy based on verdict
    is_false = verdict in ('fake', 'suspicious')
    is_unconfirmed = verdict == 'unconfirmed'
    is_true = verdict in ('real', 'likely')

    if is_false:
        strategy = (
            "The claim has been assessed as FALSE or SUSPICIOUS. "
            "Your task is to research what ACTUALLY happened — find the truth behind this claim, "
            "identify the real source or origin of the misinformation, and provide the correct "
            "information that contradicts the false claim."
        )
    elif is_unconfirmed:
        strategy = (
            "The claim could not be confirmed due to insufficient or contradictory evidence. "
            "Your task is to do further research to determine the truth — search for any "
            "related credible information, fact-checks, or debunking efforts that might help "
            "clarify whether this claim is true or false."
        )
    else:
        strategy = (
            "The claim has been assessed as TRUE or LIKELY TRUE. "
            "Your task is to reinforce this finding with additional supporting evidence — "
            "find more credible sources that confirm the claim, related images, videos, "
            "and any additional context that strengthens the verification."
        )

    # Build general results section
    general_results = search_results.get('general', [])
    general_buffer = StringIO()
    for i, r in enumerate(general_results[:10], 1):
        general_buffer.write(
            f"  [{i}] {r.get('title', 'No title')}\n"
            f"      URL: {r.get('url', '')}\n"
            f"      Domain: {r.get('domain', '')}\n"
            f"      Snippet: {r.get('snippet', '')[:300]}\n\n"
        )

    # Build images section
    image_results = search_results.get('images', [])
    image_buffer = StringIO()
    for i, img in enumerate(image_results[:8], 1):
        image_buffer.write(
            f"  [{i}] {img.get('title', 'No title')}\n"
            f"      Thumbnail: {img.get('thumbnail_url', '')}\n"
            f"      Source: {img.get('source_url', '')}\n"
            f"      Page: {img.get('page_url', '')}\n\n"
        )

    # Build videos section
    video_results = search_results.get('videos', [])
    video_buffer = StringIO()
    for i, vid in enumerate(video_results[:5], 1):
        video_buffer.write(
            f"  [{i}] {vid.get('title', 'No title')}\n"
            f"      URL: {vid.get('url', '')}\n"
            f"      Thumbnail: {vid.get('thumbnail_url', '')}\n"
            f"      Duration: {vid.get('duration', 'N/A')}\n"
            f"      Description: {vid.get('description', '')[:200]}\n\n"
        )

    queries_text = '\n'.join(f"  - {q}" for q in generated_queries)

    return f"""You are a digital forensics and fact-checking research assistant. You have been given
the results of additional web searches performed to deepen the investigation of a claim.

## ORIGINAL CLAIM
{claim or "(No additional claim provided by the user)"}

## PREVIOUS ANALYSIS VERDICT
- Verdict: {verdict.upper()}
- Confidence: {confidence:.0%}
- Explanation: {explanation}

## RESEARCH STRATEGY
{strategy}

## SEARCH QUERIES USED
{queries_text}

## WEB SEARCH RESULTS
{general_buffer.getvalue() or "  (No general web results found)"}

## IMAGE SEARCH RESULTS
{image_buffer.getvalue() or "  (No image results found)"}

## VIDEO SEARCH RESULTS
{video_buffer.getvalue() or "  (No video results found)"}

## YOUR TASK

Based on all the search results above, compile a research report. You must:

1. **Write a concise summary** (3-5 sentences) that:
   - If verdict is FAKE/SUSPICIOUS: Explains what actually happened and debunks the false claim
   - If verdict is UNCONFIRMED: Presents what is known and what remains uncertain
   - If verdict is REAL/LIKELY: Provides additional context and reinforcing evidence

2. **Extract the most relevant sources** (up to 5) — pick the most credible and informative web results.

3. **Extract the most relevant images** (up to 5) — pick images that are most related to the claim.

4. **Extract the most relevant videos** (up to 3) — pick videos that help verify or debunk the claim.

Respond with a strict JSON object matching this exact schema:
{{
  "summary": "3-5 sentence research summary in the same language as the claim",
  "key_findings": [
    "First key finding",
    "Second key finding"
  ],
  "sources": [
    {{
      "title": "Article title",
      "url": "https://...",
      "snippet": "Relevant excerpt from the search result",
      "domain": "example.com"
    }}
  ],
  "images": [
    {{
      "thumbnail_url": "https://...",
      "source_url": "https://...",
      "title": "Image description"
    }}
  ],
  "videos": [
    {{
      "url": "https://...",
      "thumbnail_url": "https://...",
      "title": "Video title",
      "source": "youtube.com",
      "duration": "5:30"
    }}
  ]
}}

**IMPORTANT RULES:**
- Write the summary in the SAME LANGUAGE as the original claim (French if the claim is in French, English if in English).
- Only include sources, images, and videos that are genuinely relevant to the claim.
- Do NOT fabricate URLs or titles — use only what appears in the search results above.
- Keep the summary factual, neutral, and informative.
"""