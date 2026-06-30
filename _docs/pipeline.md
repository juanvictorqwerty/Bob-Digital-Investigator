# Pipeline Documentation

The Bob Digital Investigator pipeline is a sophisticated 5-stage process that transforms an uploaded image into a comprehensive forensic analysis with AI-powered verdicts and optional deep research reports.

## Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    REVERSE SEARCH PIPELINE                   │
└─────────────────────────────────────────────────────────────┘

Stage 1: Reverse Image Search (OpenWebNinja)
    ↓
Stage 2: Data Processing & Enrichment
    ↓
Stage 3: Web Crawling (Concurrent)
    ↓
Stage 4: AI Disinformation Analysis (Hybrid Rules + LLM)
    ↓
Stage 5: [Optional] Deep Research (SearXNG + LLM)
```

---

## Stage 1: Reverse Image Search

**Purpose:** Find where and how an image appears across the web

**Technology:** OpenWebNinja API

**Process:**
1. User uploads image to Cloudinary
2. Image URL is sent to OpenWebNinja reverse image search API
3. API returns matching pages across Google, Yandex, and other search engines
4. Results are cached in Redis (24-hour TTL)

**Output:** Raw search results with URLs, titles, snippets, and image matches

**Caching:**
- Key: Hash of image URL
- TTL: 24 hours
- Benefit: Avoid redundant API calls for repeated searches

**Error Handling:**
- API timeout: 30 seconds
- Retry: 3 attempts with exponential backoff
- Fallback: Return empty results with error status

---

## Stage 2: Data Processing & Enrichment

**Purpose:** Normalize, deduplicate, score, and rank raw search results

**File:** `server/reversewebsearch/data_processor.py` (688 lines)

### 2.1 Normalization

**Process:**
- Clean URLs (remove tracking parameters, UTM parameters)
- Normalize domains (lowercase, remove www.)
- Standardize date formats
- Remove duplicate URLs
- Extract domain from URL

**Example:**
```
Input:  https://www.example.com/page?utm_source=twitter&fbclid=abc123
Output: https://example.com/page
```

### 2.2 Deduplication

**Process:**
- Remove exact URL duplicates
- Detect near-duplicate domains (e.g., example.com and www.example.com)
- Keep highest-scoring result per domain

**Algorithm:**
- Domain normalization
- Levenshtein distance for similar domains
- Priority: Trusted domains > higher score > earlier date

### 2.3 Enrichment

**Process:**
- Fetch image metadata (EXIF, dimensions, format, MIME type)
- Extract publication date from URL or content
- Detect language of snippet
- Check for paywall indicators

**Metadata Extracted:**
- Image dimensions (width, height)
- File format (JPEG, PNG, WebP)
- MIME type
- EXIF data (camera, date, GPS if available)

### 2.4 Scoring

**Multi-factor relevance scoring (0-100):**

| Factor | Weight | Description |
|--------|--------|-------------|
| Publication Date | 25% | Recent dates score higher (exponential decay) |
| Trusted Domain | 20% | Trusted domains get bonus points |
| Image Metadata | 15% | Results with image metadata score higher |
| Title Quality | 15% | Non-empty, descriptive titles |
| Snippet Quality | 15% | Non-empty, relevant snippets |
| Cross-Engine | 10% | Found by multiple search engines |

**Trusted Domain Bonus:**
- Government domains (.gov, .gov.cm): +30 points
- International news agencies (Reuters, AP, BBC): +25 points
- African news outlets (Cameroon Tribune, Jeune Afrique): +20 points
- Verified social media: +15 points

### 2.5 Ranking

**Process:**
1. Calculate composite score for each result
2. Sort by score (descending)
3. Extract top 15-20 candidates for crawling
4. Build timeline from publication dates

**Timeline:**
- Chronological spread of publication dates
- Identifies suspicious clustering (e.g., all sources published within 24 hours)
- Used in AI analysis for date consistency check

**Output:**
- Ranked list of 15-20 candidates
- Timeline of publication dates
- Statistics (total sources, trusted ratio, date spread)

---

## Stage 3: Web Crawling

**Purpose:** Extract full content from top-ranked sources for deeper analysis

**Technology:** ThreadPoolExecutor (10 concurrent workers)

**Process:**
1. Take top 10-15 candidates from Stage 2
2. Crawl each page concurrently
3. Extract: title, meta description, visible text content
4. Perform quality and anomaly detection

### 3.1 Content Extraction

**Extracted Data:**
- Page title
- Meta description
- Visible text content (first 5000 characters)
- Page language
- Word count

### 3.2 Paywall Detection

**Method:** Pattern matching in content

**Indicators:**
- "subscribe to continue"
- "premium content"
- "sign up to read more"
- "paywall" patterns

**Action:** Mark as paywalled, reduce content quality score

### 3.3 Anomaly Detection

**AI-Generated Content Detection:**
- Check for phrases: "as an AI language model", "I don't have personal opinions"
- Detect repetitive patterns
- Identify generic, non-specific language

**Sensational Language Detection:**
- Excessive exclamation marks
- Clickbait phrases: "You won't believe", "Shocking truth"
- ALL CAPS words
- Emoji overuse

**Content Quality Scoring:**
- Word count (higher = better)
- Completeness (not truncated)
- Specificity (names, dates, locations)
- Source attribution

**Output:**
- Crawled content per source
- Paywall status
- Anomaly flags
- Quality score

---

## Stage 4: AI Disinformation Analysis

**Purpose:** Generate verdict and explanation using hybrid rules + LLM

**Files:**
- `server/robot/analysis_pipeline.py` — Hybrid analysis orchestration
- `server/robot/llm_client.py` — OpenRouter integration

### 4.1 Rules-Based Assessment (Always Runs)

**Independent of LLM, provides baseline assessment:**

#### Date Consistency Check

**Logic:**
- Calculate time spread between earliest and latest publication
- Flag if all sources published within 24 hours (suspicious)
- Flag if sources span multiple years (good)

**Scoring:**
- Spread > 30 days: +20 points (credible)
- Spread 7-30 days: +10 points
- Spread 1-7 days: 0 points
- Spread < 24 hours: -15 points (suspicious)

#### Domain Trust Check

**Logic:**
- Count trusted vs untrusted sources
- Calculate trust ratio

**Scoring:**
- > 70% trusted: +25 points
- 40-70% trusted: +10 points
- 20-40% trusted: 0 points
- < 20% trusted: -20 points

#### Cross-Engine Corroboration

**Logic:**
- Check if results found by multiple search engines (Google, Yandex, Bing)

**Scoring:**
- Found by 3+ engines: +15 points
- Found by 2 engines: +10 points
- Found by 1 engine: 0 points

#### Source Quality Check

**Logic:**
- Total number of sources
- Diversity of domains

**Scoring:**
- > 20 sources: +20 points
- 10-20 sources: +10 points
- 5-10 sources: 0 points
- < 5 sources: -10 points

**Rules-Based Verdict:**
- Score > 60: `likely` or `real`
- Score 40-60: `unconfirmed`
- Score < 40: `suspicious` or `fake`

### 4.2 LLM Reasoning (Primary — With Fallback)

**Model:** `openai/gpt-4o-mini` (primary), `anthropic/claude-3-haiku` (fallback)

**Prompt Structure:**
```
You are a digital forensics expert analyzing image authenticity.

CONTEXT:
- Claim: [user's claim text, if provided]
- Image: [image URL]
- Timeline: [publication dates spread]
- Statistics: [source count, trusted ratio, etc.]
- Crawl Status: [how many sources crawled, paywall count]

SOURCE HIERARCHY (weight by credibility):
1. Official government/presidential sources (strongest)
2. Local established media (Cameroon & Africa)
3. International news agencies with local presence
4. Verified social media pages
5. Other local sources
6. Unknown / WhatsApp sources

CRAWLED CONTENT:
[Full text from top 10 sources]

TASK:
Analyze the evidence and provide:
1. Verdict: real / likely / fake / suspicious / unconfirmed
2. Confidence: 0.00-1.00
3. Explanation: 2-3 sentences explaining your reasoning
4. Key Evidence: 3-5 bullet points supporting your verdict
```

**Source Hierarchy Enforcement:**
- Prompt explicitly weights sources by credibility tier
- LLM instructed to prioritize official sources
- Local media > international > social > unknown

**Post-Processing:**
- Detect overcautious verdicts (e.g., `unconfirmed` when evidence clearly points to `fake`)
- Upgrade verdict if confidence is high but verdict is conservative
- Example: `unconfirmed` with 0.85 confidence → upgrade to `likely`

**Fallback Logic:**
1. Try GPT-4o-mini
2. If timeout/error → Try Claude 3 Haiku
3. If both fail → Use rules-based verdict

**Output:**
```json
{
  "verdict": "likely",
  "confidence": 0.75,
  "explanation": "Multiple credible sources including Cameroon Tribune and official government sources confirm...",
  "key_evidence": [
    "Published by Cameroon Tribune on 2025-01-15",
    "Confirmed by presidential social media accounts",
    "No contradictory sources found"
  ],
  "llm_model": "openai/gpt-4o-mini",
  "llm_confidence": 0.82
}
```

---

## Stage 5: Deep Research (On-Demand)

**Purpose:** Generate comprehensive research report for deeper investigation

**Trigger:** User clicks "View More" on analysis result

**Files:**
- `server/discover/research_generator.py` — Research orchestration
- `server/discover/searxng_client.py` — SearXNG API client
- `server/discover/llm_research_prompt.py` — Prompt builder

### 5.1 Query Generation

**Strategy:** Generate 3 strategic queries based on verdict

**Query Templates:**

| Verdict | Query Strategy | Example |
|---------|----------------|---------|
| `fake` / `suspicious` | Search for truth, debunking, what actually happened | "Cameroon earthquake January 2025 debunked" |
| `unconfirmed` | Search for fact-checks, verification, sources | "Cameroon earthquake January 2025 fact check" |
| `real` / `likely` | Search for additional confirming evidence, official statements | "Cameroon earthquake January 2025 official statement" |

**Query Generation Process:**
1. Extract key entities from claim (locations, dates, people)
2. Add verdict-specific modifiers
3. Generate 3 variations for comprehensive coverage

### 5.2 SearXNG Metasearch

**Technology:** Self-hosted SearXNG instance

**Search Types:**
- **General web:** Main search across multiple engines
- **Images:** Related images
- **Videos:** Related videos

**Process:**
1. Execute 3 general web searches (one per query)
2. Execute 1 image search
3. Execute 1 video search
4. Deduplicate results
5. Rank by relevance

**Caching:**
- Key: Hash of search query
- TTL: 24 hours
- Benefit: Avoid redundant SearXNG calls

**Output:**
- Top 10 web results
- Top 5 images
- Top 3 videos

### 5.3 LLM Compilation

**Model:** `openai/gpt-4o-mini` (primary), `anthropic/claude-3-haiku` (fallback)

**Prompt Structure:**
```
You are a research assistant compiling a forensic report.

ORIGINAL ANALYSIS:
- Verdict: [verdict]
- Claim: [claim text]
- Confidence: [confidence]

RESEARCH FINDINGS:
[Top 10 web results with titles, URLs, snippets]

IMAGES:
[Top 5 images with URLs]

VIDEOS:
[Top 3 videos with URLs]

TASK:
Write a structured research report in [language] with:
1. Summary (2-3 sentences)
2. Key Findings (3-5 bullet points)
3. Curated Sources (up to 5, with URLs)
4. Related Images (up to 5, with URLs)
5. Related Videos (up to 3, with URLs)
```

**Output:**
```json
{
  "summary": "Research confirms...",
  "key_findings": [
    "Finding 1",
    "Finding 2",
    "Finding 3"
  ],
  "sources": [
    {
      "title": "Source title",
      "url": "https://...",
      "snippet": "Brief description"
    }
  ],
  "images": [
    {
      "url": "https://...",
      "thumbnail": "https://..."
    }
  ],
  "videos": [
    {
      "title": "Video title",
      "url": "https://...",
      "thumbnail": "https://..."
    }
  ]
}
```

---

## Pipeline Orchestration

### Celery Task Structure

**Task:** `run_reverse_search_pipeline`

**Steps:**
1. Upload image to Cloudinary
2. Call OpenWebNinja API (with Redis cache check)
3. Process results (normalize, deduplicate, score, rank)
4. Crawl top candidates (concurrent)
5. Run AI analysis (rules + LLM)
6. Save results to database
7. Send completion event via SSE

**Task Timeout:** 5 minutes

**Retry Policy:**
- Max retries: 3
- Retry delay: 60 seconds (exponential backoff)
- Retryable errors: API timeouts, network errors
- Non-retryable errors: Invalid image, authentication failures

### Progress Tracking

**SSE Events:**
```javascript
{
  "status": "processing",
  "stage": "search|process|crawl|analyze",
  "progress": 0-100,
  "message": "Human-readable status",
  "timestamp": "2025-01-15T10:30:00Z"
}
```

**Stage Progress:**
- Search: 0-25%
- Process: 25-50%
- Crawl: 50-75%
- Analyze: 75-100%

---

## Performance Metrics

### Typical Execution Times

| Stage | Duration | Notes |
|-------|----------|-------|
| Image Upload | 1-2s | Cloudinary upload |
| Reverse Search | 5-15s | OpenWebNinja API call |
| Data Processing | 1-2s | Normalization, scoring |
| Web Crawling | 10-30s | 10 concurrent workers |
| AI Analysis | 10-20s | LLM API call |
| **Total** | **30-70s** | Varies by source count and LLM response time |

### Optimization Strategies

1. **Caching:** Redis caches API responses (24h TTL)
2. **Concurrency:** ThreadPoolExecutor for parallel crawling
3. **Early Termination:** Stop crawling if paywall detected
4. **Lazy Loading:** Research report generated on-demand only
5. **Connection Pooling:** Reuse HTTP connections to external APIs

---

## Error Handling

### Retryable Errors

- OpenWebNinja API timeout
- OpenRouter API timeout
- SearXNG API timeout
- Network errors (connection reset, DNS failure)
- Redis connection errors

**Action:** Retry with exponential backoff (3 attempts)

### Non-Retryable Errors

- Invalid image format
- Authentication failures (invalid API keys)
- Database errors (unique constraint violations)
- Celery queue full

**Action:** Fail task, return error to user

### Graceful Degradation

- **LLM unavailable:** Use rules-based verdict
- **SearXNG unavailable:** Skip research report
- **Cloudinary unavailable:** Store image locally (temporary)
- **OpenWebNinja unavailable:** Return error with message

---

## Monitoring Points

**Key Metrics to Track:**
- Pipeline execution time per stage
- API call success/failure rates
- Cache hit/miss ratios
- LLM response times
- Celery queue depth
- Error rates by stage

**See:** [Monitoring Setup](monitoring.md) for detailed metrics configuration