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

        # Identify authoritative source type for the prompt
        source_tier = "standard"
        if domain in {'prc.cm', 'presidence.cm', 'kremlin.ru', 'elysee.fr', 'whitehouse.gov', 'state.gov'}:
            source_tier = "OFFICIAL_GOVERNMENT"
        elif domain in {'reuters.com', 'apnews.com', 'afp.com', 'afp.fr', 'bbc.com', 'bbc.co.uk', 'france24.com', 'rfi.fr'}:
            source_tier = "TIER1_NEWS_AGENCY"
        elif domain in {'jeuneafrique.com', 'africanews.com', 'cameroon-tribune.cm', 'crtv.cm', 'journalducameroun.com'}:
            source_tier = "TIER1_AFRICAN_NEWS"

        crawl_data = c.get("crawl_data") or {}
        snippet = ""
        if crawl_data.get("crawl_status") == "success":
            raw = crawl_data.get("raw_snippet", "")
            if raw:
                snippet = raw[:1000]

        candidates_buffer.write(
            f"  [{i}] Score: {score} | Domain: {domain} | Tier: {source_tier} | Engine: {engine}\n"
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

    # NEW: Check for strong primary source evidence
    has_govt_source = statistics.get('government_sources', 0) > 0
    has_tier1_news = statistics.get('tier1_news_sources', 0) > 0
    has_specific_date = any(e.get('date') for e in timeline)

    # NEW: Build source quality summary for the LLM
    source_quality_summary = []
    if has_govt_source:
        source_quality_summary.append("✓ Official government/presidential source present")
    if has_tier1_news:
        source_quality_summary.append("✓ Tier-1 international news agency present")
    if has_specific_date:
        source_quality_summary.append("✓ Specific publication date(s) available")
    if not source_quality_summary:
        source_quality_summary.append("⚠ No high-authority primary sources detected")

    source_quality_text = "\n".join(source_quality_summary)

    # NEW: Build crawl status section
    crawl_status_data = statistics.get('crawl_status', {})
    results_crawled = crawl_status_data.get('results_crawled', 10)
    successful_crawls = crawl_status_data.get('successful_crawls', 0)
    failed_crawls = crawl_status_data.get('failed_crawls', 0)
    failed_domains = crawl_status_data.get('failed_domains', [])

    if failed_domains:
        crawl_status_text = (
            f"Crawl attempt: {successful_crawls}/{results_crawled} successful.\n"
            f"  Failed: {failed_crawls} ({', '.join(failed_domains)})."
        )
        crawl_failure_note = (
            f"[NOTE: {failed_crawls} source(s) blocked crawling. "
            f"Do NOT downgrade the verdict solely because these specific domains "
            f"could not be crawled. Use available metadata from the search results instead.]"
        )
    else:
        crawl_status_text = f"Crawl attempt: {successful_crawls}/{results_crawled} successful (no failures)."
        crawl_failure_note = ""

    # NEW: Detect if any crawled sources had paywalls
    paywall_domains = []
    for c in top_candidates[:10]:
        crawl_data = c.get("crawl_data") or {}
        if crawl_data.get("paywall_detected"):
            domain = c.get('domain', '?')
            paywall_domains.append(domain)

    paywall_text = ""
    if paywall_domains:
        paywall_text = f"⚠ Paywall detected on: {', '.join(paywall_domains)} — content may be truncated."

    return f"""You are a digital forensics and misinformation analysis expert specialized in Cameroon and African fact-checking. Your job is to analyze reverse image search results to verify or debunk a specific claim made by the user.

## THE USER'S CLAIM TO FACT-CHECK
{query or "(No additional claim provided by the user)"}

**Focus your analysis on this specific claim.** Determine if the search results confirm the claim, contradict it, or are inconclusive.

## SOURCE HIERARCHY — WEIGHT THESE HEAVILY

You must evaluate claims based on the QUALITY of sources, not just QUANTITY. Follow this hierarchy strictly:

**TIER 1 — OFFICIAL GOVERNMENT / PRESIDENTIAL SOURCES (STRONGEST)**
- Domains like: prc.cm, presidence.cm, whitehouse.gov, elysee.fr, state.gov
- Cameroonian government sites: any .gov.cm, ministerial sites
- These are PRIMARY sources. A specific, dated press release from an official presidential website is STRONG evidence on its own.
- If an official government source confirms the claim with a specific date, the verdict should be "real" or "likely" (NOT "unconfirmed").
- A SINGLE official source with specifics beats ten blog posts.
- DO NOT demand "extensive corroboration from other highly reputable outlets" when you already have an official source.

**TIER 2 — LOCAL ESTABLISHED MEDIA (Cameroon & Africa)**
- Domains like: crtv.cm, cameroon-tribune.cm, journalducameroun.com, actucameroun.com
- Weight them like international agencies for local claims.
- Sources in French are the default for official Cameroonian content. Do NOT penalize French-language sources.

**TIER 3 — INTERNATIONAL NEWS AGENCIES WITH LOCAL PRESENCE**
- Reuters, AFP, AP, BBC, France24, RFI
- One tier-1 agency + one official source = "real".
- One tier-1 agency alone with specifics = "likely" or "real".

**TIER 4 — VERIFIED SOCIAL PAGES**
- Official Facebook pages: PRC TV Cameroun, ministries, CRTV
- Timestamped posts are valid. Not as strong as .gov.cm, but real evidence.

**TIER 5 — OTHER .cm / LOCAL SOURCES**
- Diaspora blogs, local forums. Weak alone, OK as supporting context.

**TIER 6 — WHATSAPP / UNKNOWN**
- No domain, no date, no text. Note the origin. Do not auto-downgrade, but do not rely on it alone.

## KEY RULES (DO NOT IGNORE)

1. **DATE SPECIFICITY MATTERS**: Exact date (e.g. "15 mars 2024") > vague timing ("recently"). Multiple sources with the SAME specific date = corroboration, NOT "coordinated push."

2. **DO NOT OVER-DEMAND CORROBORATION**: A single official presidential press release is better evidence than 10 blog posts. "Lack of extensive corroboration" is NOT a valid reason for "unconfirmed" when primary sources exist.

3. **CONFIDENCE CALIBRATION**:
   - If an official source confirms with date: confidence ≥ 0.75
   - If tier-1 news + official source agree: confidence ≥ 0.85
   - Only use "unconfirmed" when sources are genuinely absent, contradictory, or too vague.
   - "Unconfirmed" at 80% confidence is a LOGICAL ERROR — fix the verdict instead.

4. **CRAWL FAILURES ARE NOT PENALTIES**: If a high-quality source (e.g. prc.cm) blocked crawling, flag it but do NOT downgrade the verdict. Use available metadata (title, URL, date) from the search result itself.

5. **WHATSAPP IS CONTEXT, NOT A VERDICT**: If an image has WhatsApp compression artifacts but also appears on prc.cm or CRTV, the official source validates it. The WhatsApp origin is irrelevant in that case.

## Source Quality Summary
{source_quality_text}

## Crawl Status
{crawl_status_text}

{crawl_failure_note}

{paywall_text}

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
- Official government sources: {statistics.get('government_sources', 'N/A')}
- Tier-1 news agencies: {statistics.get('tier1_news_sources', 'N/A')}
- Unique domains: {statistics.get('unique_domains', 'N/A')}

## Crawl Data Anomalies
{crawl_text}

## Rules-based Preliminary Assessment
{rules_text}

## Analysis Instructions
1. **Evaluate the user's claim** — Does the crawled page content support or contradict what the user suspects?
2. **Check source authority** — Is there an official government or tier-1 news source? If yes, weight it heavily. One is enough.
3. **Check date consistency** — Are sources from the same specific date (corroboration) or scattered vaguely?
4. **Evaluate source credibility** — Are top sources from known reputable/trusted domains? Or from obscure/untrustworthy domains?
5. **Examine crawl data** — Do the crawled snippets contain sensational language, contradictory claims, lack of factual reporting, or AI-generated text?
6. **Check for crawl failures** — If a credible source couldn't be crawled, note it but don't penalize the verdict.
7. **DO NOT be overcautious** — If an official source with a specific date confirms the claim, return "real" or "likely", not "unconfirmed". If confidence > 0.60 and you're about to write "unconfirmed", STOP and upgrade to "likely" or "suspicious".

## Output Format
Respond with a strict JSON object that matches this exact schema:
{{
  "verdict": "real|likely|fake|suspicious|unconfirmed",
  "confidence": 0.0 to 1.0,
  "short_summary": "One sentence in French or English — match the user's query language",
  "explanation": "Detailed 3-6 sentence explanation of your reasoning. Reference the user's claim and the best crawled source(s). Be specific: name the domain, date, and what the crawled content actually says.",
  "key_evidence": [
    "Specific item from crawled content: domain, date, and what it says",
    "Another item if available"
  ],
  "crawl_status": {{
    "results_crawled": 10,
    "successful_crawls": {successful_crawls},
    "failed_crawls": {failed_crawls},
    "failed_domains": {json.dumps(failed_domains)}
  }},
  "notes": "Optional: WhatsApp origin detected, language of sources, crawl failures, any caveats"
}}

**Verdict meanings:**
- "real" — Official source confirms + specifics, OR multiple independent credible sources agree. Confidence: 0.75–0.95.
- "likely" — Credible source(s) confirm with specifics, slightly more caution than "real." Confidence: 0.60–0.80.
- "fake" — Strong evidence of manipulation, contradiction by credible sources, or known false claim. Confidence: 0.70–0.95.
- "suspicious" — Red flags but not conclusive. Confidence: 0.40–0.65.
- "unconfirmed" — ONLY when: no credible sources, no specifics, genuinely contradictory/vague, or total absence of data. Confidence: 0.00–0.40.

**CRITICAL GOLDEN RULE**: If you find yourself writing "unconfirmed" with confidence > 0.6, STOP. You have enough evidence. Pick "likely" or "suspicious" instead.

**EXAMPLES OF CORRECT vs. INCORRECT REASONING:**

✅ CORRECT: Official government source (prc.cm) confirms with specific date → verdict "real" at 0.85 confidence.
❌ WRONG: Same scenario → verdict "unconfirmed" at 0.75. This is a logic error. Primary sources are enough.

✅ CORRECT: No official sources, only a local blog without date → verdict "unconfirmed" at 0.35.
❌ WRONG: Same scenario → verdict "likely" at 0.70. Weak evidence doesn't support this.
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

        # NEW: Post-process to catch overcautious verdicts
        parsed = _fix_overcautious_verdict(parsed, prompt)

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


def _fix_overcautious_verdict(parsed: dict, prompt: str) -> dict:
    """
    Post-process LLM verdicts to fix logical inconsistencies.

    If the LLM returns 'unconfirmed' with high confidence, or if the prompt
    clearly contains strong official sources, override to 'likely' or 'real'.
    """
    verdict = parsed.get("verdict", "unconfirmed")
    confidence = parsed.get("confidence", 0.0)
    explanation = parsed.get("explanation", "")

    # Fix 1: Unconfirmed with high confidence is a logical error
    if verdict == "unconfirmed" and confidence >= 0.65:
        logger.warning(f"Overcautious verdict detected: unconfirmed at {confidence} confidence. Upgrading to 'likely'.")
        parsed["verdict"] = "likely"
        parsed["explanation"] = explanation + " [SYSTEM NOTE: Verdict upgraded from 'unconfirmed' because confidence was high but verdict was too cautious.]"

    # Fix 2: If prompt mentions official government sources and confidence is high
    if "✓ Official government/presidential source present" in prompt and confidence >= 0.70:
        if verdict in ("unconfirmed", "suspicious"):
            logger.warning(f"Overcautious verdict detected: {verdict} despite official govt source. Upgrading to 'likely'.")
            parsed["verdict"] = "likely"
            parsed["explanation"] = explanation + " [SYSTEM NOTE: Verdict upgraded because an official government source with specific details was present.]"

    # Fix 3: If both govt + tier1 news present, should be at least "likely"
    if ("✓ Official government/presidential source present" in prompt and 
        "✓ Tier-1 international news agency present" in prompt and
        confidence >= 0.75):
        if verdict in ("unconfirmed", "suspicious", "likely"):
            logger.info(f"Strong corroboration detected (govt + tier1). Upgrading verdict to 'real'.")
            parsed["verdict"] = "real"
            parsed["explanation"] = explanation + " [SYSTEM NOTE: Verdict upgraded to 'real' due to corroboration between official government source and tier-1 news agency.]"

    return parsed


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