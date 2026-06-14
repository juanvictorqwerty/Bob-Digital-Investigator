"""
OpenRouter LLM client for the robot analysis.
Uses openai-compatible API to send prompts to OpenRouter.
"""
import json
import logging
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

# Default model — good balance of quality/price
DEFAULT_MODEL = "openai/gpt-4o-mini"

# Fallback model if the primary is unavailable
FALLBACK_MODEL = "anthropic/claude-3-haiku"


def get_openrouter_client():
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


def build_analysis_prompt(query, top_candidates, timeline, statistics, rules_assessment):
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
    # Build candidates section (top 10) — include FULL crawl snippet
    candidates_lines = []
    for i, c in enumerate(top_candidates[:10], 1):
        publish_date = c.get("publish_date", "N/A") or "N/A"
        score = c.get("score", "N/A")
        domain = c.get("domain", "unknown")
        title = c.get("title", "No title")
        engine = c.get("engine", "unknown")

        # Crawl snippet (full — up to 1000 chars)
        crawl_data = c.get("crawl_data", {}) or {}
        snippet = ""
        if crawl_data.get("crawl_status") == "success":
            raw = crawl_data.get("raw_snippet", "")
            if raw:
                snippet = raw[:1000]

        candidates_lines.append(
            f"  [{i}] Score: {score} | Domain: {domain} | Engine: {engine}\n"
            f"      Title: {title}\n"
            f"      Published: {publish_date}\n"
            f"      Crawled page content:\n{snippet}\n"
        )

    candidates_text = "\n".join(candidates_lines)

    # Build timeline section
    timeline_lines = []
    for entry in timeline:
        d = entry.get("date", "?")
        dom = entry.get("domain", "?")
        timeline_lines.append(f"  {d} — {dom}")
    timeline_text = "\n".join(timeline_lines) if timeline_lines else "  (No timeline data available)"

    # Build rules assessment
    rules_lines = []
    for key, val in rules_assessment.items():
        rules_lines.append(f"  - {key}: {val}")
    rules_text = "\n".join(rules_lines)

    # Detect and highlight crawl data anomalies
    crawl_anomalies = _detect_crawl_anomalies(top_candidates)
    crawl_text = "\n".join(crawl_anomalies) if crawl_anomalies else "  None detected."

    prompt = f"""You are a digital forensics and misinformation analysis expert. Your job is to analyze reverse image search results to verify or debunk a specific claim made by the user.

## THE USER'S CLAIM TO FACT-CHECK
{query or "(No additional claim provided by the user)"}

**Focus your analysis on this specific claim.** Determine if the search results confirm the claim, contradict it, or are inconclusive.

## Ranked Search Results (top 10 by relevance score)
Each result includes crawled page content from the source.
{candidates_text}

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
1. **Evaluate the user's claim** — Does the crawled page content support or contradict what the user suspects? Does the claim appear in multiple independent sources?
2. **Check date consistency** — Are all sources from the same narrow timeframe (suggesting a coordinated push)? Or is there a natural chronological spread?
3. **Evaluate source credibility** — Are the top sources from known reputable/trusted domains? Or from obscure/untrustworthy domains?
4. **Look for corroboration** — Do results from different sources carry consistent information?
5. **Examine crawl data** — Do the crawled snippets contain sensational language, contradictory claims, lack of factual reporting, or AI-generated text?
6. **Cross-check the image** — Does the image appear in contexts that match its original purpose, or is it being used misleadingly?

## Output Format
Respond with **valid JSON only** — no markdown fences, no extra text.

{{
  "verdict": "real|fake|suspicious|unconfirmed",
  "confidence": <0.0 to 1.0>,
  "short_summary": "<One short sentence explaining the verdict>",
  "explanation": "<Detailed 3-6 sentence explanation of your reasoning, referencing the user's claim and the crawled content>",
  "key_evidence": [
    "<Specific evidence item 1 from crawled content>",
    "<Specific evidence item 2 from crawled content>",
    "<Specific evidence item 3 from crawled content>"
  ]
}}

**Verdict meanings:**
- "real" — Strong evidence the content is authentic/genuine news; the user's claim is supported
- "fake" — Strong evidence of misinformation, manipulation, or false claims; the user's claim is contradicted
- "suspicious" — Some red flags but not conclusive
- "unconfirmed" — Insufficient data to make a determination

Now analyze the data and return your verdict.
"""
    return prompt


def _detect_crawl_anomalies(top_candidates):
    """
    Detect suspicious patterns in crawled page content.

    Args:
        top_candidates: List of result dicts with crawl_data

    Returns:
        List of anomaly description strings
    """
    anomalies = []

    for c in top_candidates[:5]:
        crawl_data = c.get("crawl_data", {}) or {}
        if crawl_data.get("crawl_status") != "success":
            continue

        snippet = crawl_data.get("raw_snippet", "") or ""

        if not snippet or len(snippet.strip()) < 50:
            anomalies.append(
                f"  - {c.get('domain', '?')}: Crawled page has very little content "
                f"({len(snippet.strip())} chars) — may be a low-quality or auto-generated page."
            )
            continue

        # Check for AI-generated text markers
        ai_markers = ["as an ai", "as a language model", "i cannot", "i don't have"]
        snippet_lower = snippet.lower()
        for marker in ai_markers:
            if marker in snippet_lower:
                anomalies.append(
                    f"  - {c.get('domain', '?')}: Page content contains AI disclaimer ('{marker}') "
                    f"— possible AI-generated or placeholder content."
                )
                break

        # Check for sensational language
        sensational = ["breaking!", "shocking!", "you won't believe", "viral", "must see", "urgent"]
        sensational_found = [w for w in sensational if w in snippet_lower]
        if sensational_found:
            anomalies.append(
                f"  - {c.get('domain', '?')}: Sensational language detected: {sensational_found}"
            )

        # Check for extremely short pages (thin content)
        word_count = len(snippet.split())
        if word_count < 30:
            anomalies.append(
                f"  - {c.get('domain', '?')}: Very thin page content ({word_count} words) "
                f"— may be a spam or placeholder page."
            )

    return anomalies


def analyze_with_openrouter(prompt, model=None):
    """
    Send prompt to OpenRouter and return parsed response.

    Args:
        prompt: The full LLM prompt string
        model: Model string, e.g. "openai/gpt-4o-mini"

    Returns:
        Tuple of (verdict_dict, raw_response_json)
        verdict_dict = { "verdict": str, "confidence": float, "explanation": str, "key_evidence": list }
    """
    model = model or DEFAULT_MODEL

    try:
        client = get_openrouter_client()

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
        )

        raw_content = response.choices[0].message.content.strip()
        raw_response = {
            "model": model,
            "content": raw_content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
                "total_tokens": response.usage.total_tokens if response.usage else None,
            }
        }

        # Parse JSON from response
        parsed = _parse_llm_response(raw_content)

        return parsed, raw_response

    except Exception as e:
        logger.error(f"OpenRouter call failed with {model}: {str(e)}")

        # Try fallback model
        if model != FALLBACK_MODEL:
            logger.info(f"Falling back to {FALLBACK_MODEL}...")
            try:
                return analyze_with_openrouter(prompt, model=FALLBACK_MODEL)
            except Exception as fallback_err:
                logger.error(f"Fallback also failed: {str(fallback_err)}")

        # Return None so caller can use rules-based fallback
        return None, {"error": str(e)}


def _parse_llm_response(content):
    """
    Parse the LLM JSON response, handling markdown fences and stray text.

    Args:
        content: Raw string response from LLM

    Returns:
        Dict with verdict, confidence, explanation, key_evidence
    """
    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        # Remove opening fence (possibly with json keyword)
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        # Remove closing fence if present
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

    # Try to find JSON object
    try:
        # Find first { and last }
        start = content.index("{")
        end = content.rindex("}") + 1
        json_str = content[start:end]
        data = json.loads(json_str)
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to parse LLM JSON response: {e}")
        logger.debug(f"Raw content: {content[:500]}")
        return _default_verdict()

    # Validate fields
    verdict = data.get("verdict", "unconfirmed")
    if verdict not in ("real", "fake", "suspicious", "unconfirmed"):
        verdict = "unconfirmed"

    confidence = data.get("confidence", 0.0)
    try:
        confidence = float(confidence)
        confidence = max(0.0, min(1.0, confidence))
    except (ValueError, TypeError):
        confidence = 0.0

    short_summary = data.get("short_summary", "")
    explanation = data.get("explanation", "No explanation provided.")
    key_evidence = data.get("key_evidence", [])
    if not isinstance(key_evidence, list):
        key_evidence = []

    return {
        "verdict": verdict,
        "confidence": confidence,
        "short_summary": short_summary,
        "explanation": explanation,
        "key_evidence": key_evidence,
    }


def _default_verdict():
    """Return a safe default verdict when LLM parsing fails."""
    return {
        "verdict": "unconfirmed",
        "confidence": 0.0,
        "short_summary": "AI analysis failed — unable to determine authenticity.",
        "explanation": "Unable to generate AI analysis due to a processing error.",
        "key_evidence": [],
    }