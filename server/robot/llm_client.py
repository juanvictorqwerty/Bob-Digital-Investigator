"""
OpenRouter LLM client for the robot analysis.
Uses openai-compatible API to send prompts to OpenRouter.
"""
import json
import logging
from io import StringIO
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

# Default model — good balance of quality/price
DEFAULT_MODEL = "openai/gpt-4o-mini"

# Fallback model if the primary is unavailable
FALLBACK_MODEL = "anthropic/claude-3-haiku"

# Valid system verdicts for validation
VALID_VERDICTS = {"real", "likely", "fake", "suspicious", "unconfirmed"}


def get_openrouter_client() -> OpenAI:
    """Return an OpenAI client configured to point at OpenRouter."""
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set in environment / settings")
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://bob-investigator.app",
            "X-Title": "Bob Digital Investigator",
        }
    )


def build_analysis_prompt(query, top_candidates, timeline, statistics, rules_assessment) -> str:
    """
    Build a structured prompt for the LLM.

    Args:
        query: User's optional text query / the claim to fact-check
        top_candidates: List of ranked result dicts with scores, domains, dates, crawl_data
        timeline: List of timeline entries [{date, domain, url}]
        statistics: Dict with total_sources, trusted_domains, etc.
        rules_assessment: Dict with heuristic findings

    Returns:
        String prompt
    """
    # Build candidates section using StringIO for efficient string concatenation
    candidates_buffer = StringIO()
    for i, c in enumerate(top_candidates[:10], 1):
        publish_date = c.get("publish_date") or "N/A"
        score = c.get("score", "N/A")
        domain = c.get("domain", "unknown")
        title = c.get("title", "No title")
        engine = c.get("engine", "unknown")

        crawl_data = c.get("crawl_data") or {}
        snippet = ""
        if crawl_data.get("crawl_status") == "success":
            raw = crawl_data.get("raw_snippet", "")
            if raw:
                snippet = raw[:1000]

        candidates_buffer.write(
            f"  [{i}] Score: {score} | Domain: {domain} | Engine: {engine}\n"
            f"      Title: {title}\n"
            f"      Published: {publish_date}\n"
            f"      Crawled page content:\n{snippet}\n\n"
        )

    # Build timeline entries
    timeline_lines = [f"  {e.get('date', '?')} — {e.get('domain', '?')}" for e in timeline]
    timeline_text = "\n".join(timeline_lines) if timeline_lines else "  (No timeline data available)"
    
    # Build rules entries
    rules_text = "\n".join([f"  - {k}: {v}" for k, v in rules_assessment.items()])

    # Detect crawl anomalies dynamically
    crawl_anomalies = _detect_crawl_anomalies(top_candidates)
    crawl_text = "\n".join(crawl_anomalies) if crawl_anomalies else "  None detected."

    return f"""You are a digital forensics and misinformation analysis expert. Your job is to analyze reverse image search results to verify or debunk a specific claim made by the user.

## THE USER'S CLAIM TO FACT-CHECK
{query or "(No additional claim provided by the user)"}

**Focus your analysis on this specific claim.** Determine if the search results confirm the claim, contradict it, or are inconclusive.

## Ranked Search Results (top 10 by relevance score)
Each result includes crawled page content from the source.
{candidates_buffer.getvalue()}

## Publication Timeline
(Chronological spread of sources found)
{timeline_text}

## Statistics
- Total sources found: {statistics.get('total_sources', 'N/A')}
- Sources with publication dates: {statistics.get('with_publish_date', 'N/A')}
- Sources from trusted domains: {statistics.get('trusted_domains', 'N/A')}
- Unique domains: {statistics.get('unique_domains', 'N/A')}

## Crawl Data Anomalies
{crawl_text}

## Rules-based Preliminary Assessment
{rules_text}

## Analysis Instructions
1. **Evaluate the user's claim** — Does the crawled page content support or contradict what the user suspects?
2. **Check date consistency** — Are all sources from the same narrow timeframe (suggesting a coordinated push)? Or is there a natural chronological spread?
3. **Evaluate source credibility** — Are the top sources from known reputable/trusted domains? Or from obscure/untrustworthy domains?
4. **Examine crawl data** — Do the crawled snippets contain sensational language, contradictory claims, lack of factual reporting, or AI-generated text?

## Output Format
Respond with a strict JSON object that matches this exact schema:
{{
  "verdict": "real|likely|fake|suspicious|unconfirmed",
  "confidence": 0.0 to 1.0,
  "short_summary": "One short sentence explaining the verdict",
  "explanation": "Detailed 3-6 sentence explanation of your reasoning, referencing the user's claim and the crawled content",
  "key_evidence": [
    "Specific evidence item 1 from crawled content",
    "Specific evidence item 2 from crawled content"
  ]
}}

**Verdict meanings:**
- "real" — Strong evidence the content is authentic/genuine news; the user's claim is supported by highly trusted/authoritative domains.
- "likely" — Multiple independent, non-trusted or secondary sources clearly corroborate and confirm the user's claim, though high-authority trusted domains haven't verified it yet.
- "fake" — Strong evidence of misinformation, manipulation, or false claims; the user's claim is contradicted.
- "suspicious" — Some red flags but not conclusive.
- "unconfirmed" — Insufficient data to make a determination.
"""


def _detect_crawl_anomalies(top_candidates) -> list:
    """
    Detect suspicious patterns in crawled page content.

    Args:
        top_candidates: List of result dicts with crawl_data

    Returns:
        List of anomaly description strings
    """
    anomalies = []
    ai_markers = ["as an ai", "as a language model", "i cannot", "i don't have"]
    sensational = ["breaking!", "shocking!", "you won't believe", "viral", "must see", "urgent"]

    for c in top_candidates[:5]:
        crawl_data = c.get("crawl_data") or {}
        if crawl_data.get("crawl_status") != "success":
            continue

        snippet = (crawl_data.get("raw_snippet") or "").strip()
        domain = c.get('domain', '?')

        if not snippet or len(snippet) < 50:
            anomalies.append(f"  - {domain}: Crawled page has very little content ({len(snippet)} chars) — may be low-quality.")
            continue

        snippet_lower = snippet.lower()
        for marker in ai_markers:
            if marker in snippet_lower:
                anomalies.append(f"  - {domain}: Page content contains AI disclaimer ('{marker}') — possible AI placeholder.")
                break

        sensational_found = [w for w in sensational if w in snippet_lower]
        if sensational_found:
            anomalies.append(f"  - {domain}: Sensational language detected: {sensational_found}")

        word_count = len(snippet.split())
        if word_count < 30:
            anomalies.append(f"  - {domain}: Very thin page content ({word_count} words) — may be a spam page.")

    return anomalies


def analyze_with_openrouter(prompt: str, model: str = None) -> tuple:
    """
    Send prompt to OpenRouter and return parsed response with a fallback mechanism.

    Args:
        prompt: The full LLM prompt string
        model: Model string, e.g. "openai/gpt-4o-mini"

    Returns:
        Tuple of (verdict_dict, raw_response_json)
    """
    model = model or DEFAULT_MODEL

    try:
        client = get_openrouter_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
            # Native JSON enforcement at the API gateway layer
            response_format={"type": "json_object"}
        )

        raw_content = response.choices[0].message.content.strip()
        
        usage = response.usage
        raw_response = {
            "model": model,
            "content": raw_content,
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else None,
                "completion_tokens": usage.completion_tokens if usage else None,
                "total_tokens": usage.total_tokens if usage else None,
            }
        }

        parsed = _parse_llm_response(raw_content)
        return parsed, raw_response

    except Exception as e:
        logger.error(f"OpenRouter call failed with {model}: {str(e)}")

        # Clean fallback escalation block
        if model != FALLBACK_MODEL:
            logger.info(f"Falling back to {FALLBACK_MODEL}...")
            try:
                return analyze_with_openrouter(prompt, model=FALLBACK_MODEL)
            except Exception as fallback_err:
                logger.error(f"Fallback also failed: {str(fallback_err)}")

        return _default_verdict(), {"error": str(e)}


def _parse_llm_response(content: str) -> dict:
    """
    Parse and clean the LLM structured JSON response.

    Args:
        content: Raw string response from LLM

    Returns:
        Dict with verdict, confidence, short_summary, explanation, key_evidence
    """
    # Clean up standard markdown wrappers if fallback providers inject them despite constraints
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
        logger.warning(f"Failed to parse LLM JSON response payload: {e}")
        return _default_verdict()

    # Normalize verdict string mapping
    verdict = data.get("verdict", "unconfirmed").lower().strip()
    if verdict not in VALID_VERDICTS:
        verdict = "unconfirmed"

    # Normalize and contain confidence ratings
    try:
        confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
    except (ValueError, TypeError):
        confidence = 0.0

    return {
        "verdict": verdict,
        "confidence": confidence,
        "short_summary": str(data.get("short_summary", "")),
        "explanation": str(data.get("explanation", "No explanation provided.")),
        "key_evidence": data.get("key_evidence") if isinstance(data.get("key_evidence"), list) else [],
    }


def _default_verdict() -> dict:
    """Return a safe default verdict when LLM processing fails entirely."""
    return {
        "verdict": "unconfirmed",
        "confidence": 0.0,
        "short_summary": "AI analysis failed — unable to determine authenticity.",
        "explanation": "Unable to generate AI analysis due to a processing or network error.",
        "key_evidence": [],
    }