"""
Hybrid fake-news analysis pipeline:
1. Apply rules-based heuristics to the processed search results
2. Pass everything to the LLM via OpenRouter for a reasoned verdict
3. Save the RobotAnalysis record to the database
"""
import logging
from datetime import datetime, timedelta
from .models import RobotAnalysis
from .llm_client import build_analysis_prompt, analyze_with_openrouter

logger = logging.getLogger(__name__)


def run_robot_analysis(websearch_result, processed_data):
    """
    Main entry point — run the full hybrid analysis pipeline.

    Args:
        websearch_result: WebsearchResults model instance (already saved to DB)
        processed_data: The full results dict from the pipeline
            (contains normalized_results, top_candidates, timeline, statistics)

    Returns:
        Dict with analysis results: {
            "verdict": str,
            "confidence": float,
            "explanation": str,
            "key_evidence": list,
            "llm_used": bool
        }
    """
    query = websearch_result.query or ""
    top_candidates = processed_data.get("top_candidates", [])
    timeline = processed_data.get("timeline", [])
    statistics = processed_data.get("statistics", {})

    # Step 1: Run rules-based heuristics
    rules_assessment = _rules_based_assessment(websearch_result, top_candidates, timeline, statistics)
    logger.info(f"Rules-based assessment: {rules_assessment}")

    # Step 2: Build LLM prompt
    prompt = build_analysis_prompt(
        query=query,
        top_candidates=top_candidates,
        timeline=timeline,
        statistics=statistics,
        rules_assessment=rules_assessment,
    )

    # Step 3: Call OpenRouter
    verdict_dict, raw_response = analyze_with_openrouter(prompt)

    # Step 4: Fallback — if LLM failed, use rules-based verdict
    llm_used = verdict_dict is not None
    if not llm_used:
        logger.warning("LLM analysis failed, falling back to rules-based verdict")
        verdict_dict = _rules_based_verdict(rules_assessment)

    # Step 5: Save to DB
    try:
        RobotAnalysis.objects.update_or_create(
            websearch_result=websearch_result,
            defaults={
                "verdict": verdict_dict["verdict"],
                "confidence_score": verdict_dict["confidence"],
                "short_summary": verdict_dict.get("short_summary", ""),
                "explanation": verdict_dict["explanation"],
                "key_evidence": verdict_dict.get("key_evidence", []),
                "llm_raw_response": raw_response,
                "llm_prompt": prompt,
            }
        )
        logger.info(f"RobotAnalysis saved: {verdict_dict['verdict']} @ {verdict_dict['confidence']:.0%}")
    except Exception as e:
        logger.error(f"Failed to save RobotAnalysis: {str(e)}")

    # Step 6: Return the verdict for inclusion in final payload
    verdict_dict["llm_used"] = llm_used
    return verdict_dict


def _rules_based_assessment(websearch_result, top_candidates, timeline, statistics):
    """
    Apply rules-based heuristics to flag potential issues.

    Returns dict of findings.
    """
    assessment = {}

    # 1. Date consistency check
    dated_candidates = [c for c in top_candidates if c.get("publish_date")]
    if len(dated_candidates) >= 3:
        dates = []
        for c in dated_candidates[:5]:
            try:
                d = datetime.fromisoformat(c["publish_date"].replace("Z", "+00:00"))
                dates.append(d)
            except (ValueError, TypeError):
                continue
        if len(dates) >= 3:
            min_date = min(dates)
            max_date = max(dates)
            span = max_date - min_date
            if span <= timedelta(hours=24):
                assessment["date_span_hours"] = span.total_seconds() / 3600
                assessment["date_anomaly"] = "All dated sources published within 24 hours — possible coordinated push"
            else:
                assessment["date_span_days"] = span.days
                assessment["date_anomaly"] = f"Sources span {span.days} days — natural spread"
        else:
            assessment["date_anomaly"] = "Too few parseable dates to analyze"
    else:
        assessment["date_anomaly"] = f"Only {len(dated_candidates)} sources have dates — limited temporal data"

    # 2. Domain trust check (top 5)
    trusted_domains_count = statistics.get("trusted_domains", 0)
    total_sources = statistics.get("total_sources", 1)
    trusted_ratio = trusted_domains_count / max(total_sources, 1)
    assessment["trusted_domain_ratio"] = f"{trusted_ratio:.0%}"

    top_5_untrusted = 0
    for c in top_candidates[:5]:
        domain = c.get("domain", "")
        if not _is_trusted(domain):
            top_5_untrusted += 1
    assessment["top_5_untrusted_count"] = top_5_untrusted
    if top_5_untrusted >= 4:
        assessment["trust_anomaly"] = "4+ of top 5 sources are from untrusted domains — credibility concern"
    elif top_5_untrusted >= 2:
        assessment["trust_anomaly"] = f"{top_5_untrusted} of top 5 sources are from untrusted domains"
    else:
        assessment["trust_anomaly"] = "Top sources are from reasonably trusted domains"

    # 3. Cross-engine corroboration
    engines_used = set()
    for c in top_candidates:
        engine = c.get("engine", "")
        if engine:
            engines_used.add(engine)
    assessment["engines_found"] = list(engines_used)
    if len(engines_used) >= 2:
        assessment["corroboration"] = "Results corroborated by multiple search engines"
    else:
        assessment["corroboration"] = "Results from only one engine — limited cross-validation"

    # 4. Source count quality
    total = statistics.get("total_sources", 0)
    if total < 5:
        assessment["source_quality"] = f"Only {total} sources found — limited evidence"
    elif total < 15:
        assessment["source_quality"] = f"{total} sources — moderate evidence"
    else:
        assessment["source_quality"] = f"{total} sources — robust evidence"

    # 5. Crawl data quality
    successful_crawls = sum(
        1 for c in top_candidates[:5]
        if c.get("crawl_data", {}).get("crawl_status") == "success"
    )
    assessment["successful_crawls"] = f"{successful_crawls}/5 top sources crawled successfully"

    # 6. Check for user query significance
    assessment["user_query_provided"] = bool(websearch_result.query) if hasattr(websearch_result, "query") else False

    return assessment


def _rules_based_verdict(rules_assessment):
    """
    Fallback verdict when LLM is unavailable.
    Uses rules-based assessment to produce a reasonable verdict.
    """
    confidence = 0.5
    evidence = []
    verdict = "unconfirmed"

    # Negative signals
    neg_signals = 0
    pos_signals = 0

    date_anomaly = rules_assessment.get("date_anomaly", "")
    if "coordinated push" in date_anomaly or "24 hours" in date_anomaly:
        neg_signals += 2
        evidence.append("All sources published within a narrow 24-hour window")

    trust_anomaly = rules_assessment.get("trust_anomaly", "")
    if "credibility concern" in trust_anomaly:
        neg_signals += 2
        evidence.append("Most top sources are from untrusted/unreliable domains")
    elif "untrusted" in trust_anomaly:
        neg_signals += 1
        evidence.append("Some top sources are from untrusted domains")

    if rules_assessment.get("top_5_untrusted_count", 0) >= 3:
        neg_signals += 1

    corroboration = rules_assessment.get("corroboration", "")
    if "multiple" in corroboration:
        pos_signals += 1
        evidence.append("Results corroborated by both Google and Yandex")

    source_quality = rules_assessment.get("source_quality", "")
    if "robust" in source_quality:
        pos_signals += 2
        evidence.append("Large number of sources found across multiple domains")
    elif "moderate" in source_quality:
        pos_signals += 1
        evidence.append("Moderate number of sources found")

    trusted_ratio_str = rules_assessment.get("trusted_domain_ratio", "0%")
    try:
        trusted_ratio = float(trusted_ratio_str.strip("%")) / 100
    except (ValueError, AttributeError):
        trusted_ratio = 0.0

    if trusted_ratio >= 0.5:
        pos_signals += 2
        evidence.append("High proportion of sources from trusted/established domains")
    elif trusted_ratio >= 0.2:
        pos_signals += 1

    # Determine verdict
    if neg_signals >= 3 and pos_signals <= 1:
        verdict = "fake"
        confidence = 0.55 + min(0.35, neg_signals * 0.1)
    elif neg_signals >= 2:
        verdict = "suspicious"
        confidence = 0.5 + min(0.3, neg_signals * 0.1)
    elif pos_signals >= 3:
        verdict = "real"
        confidence = 0.6 + min(0.3, pos_signals * 0.1)
    elif pos_signals >= 1:
        verdict = "real"
        confidence = 0.5
    else:
        verdict = "unconfirmed"
        confidence = 0.3

    confidence = max(0.0, min(1.0, confidence))

    explanation = (
        f"Rules-based assessment: {len(evidence)} evidence points considered. "
        f"Positive signals: {pos_signals}, Negative signals: {neg_signals}. "
        f"Verdict: {verdict} (confidence: {confidence:.0%}). "
        f"Note: LLM AI analysis was unavailable, this is a heuristic-only judgment."
    )

    return {
        "verdict": verdict,
        "confidence": confidence,
        "short_summary": f"Rules-based analysis: {verdict} with {confidence:.0%} confidence.",
        "explanation": explanation,
        "key_evidence": evidence,
    }


def _is_trusted(domain):
    """Check if domain is in the trusted list (duplicated from data_processor for isolation)."""
    from reversewebsearch.data_processor import is_trusted_domain
    return is_trusted_domain(domain)