# Architecture Overview

## System Architecture

Bob Digital Investigator follows a microservices architecture with clear separation between frontend, backend, and supporting services.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (Next.js)                        │
│  Upload image + optional claim  ─┐                              │
│                                 │                               │
│         ┌───────────────────────┴──────────────┐              │
│         │  SSE progress stream ◄─── polling     │              │
│         └───────────────────────┬──────────────┘              │
└─────────────────────────────────┬───────────────────────────────┘
                                   │ HTTP / REST
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Django REST API (Server)                     │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐      │
│  │ Authentication│  │ Reverse Web  │  │    Discover       │      │
│  │ (Token Auth)  │  │   Search     │  │ (SearXNG Research)│      │
│  └──────────────┘  └──────┬───────┘  └────────┬─────────┘      │
│                           │                   │                 │
│                    ┌──────▼───────────────────▼──────┐          │
│                    │   Celery Task Queue (Redis)      │          │
│                    │  ┌───────────────────────────┐  │          │
│                    │  │ Pipeline: Search → Process │  │          │
│                    │  │ → Enrich → Crawl → Analyze │  │          │
│                    │  └───────────┬───────────────┘  │          │
│                    └──────────────┼──────────────────┘          │
└───────────────────────────────────┼──────────────────────────────┘
                                     │
               ┌─────────────────────┼─────────────────────┐
               ▼                     ▼                     ▼
┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   OpenWebNinja API   │  │  SearXNG (Self-  │  │   OpenRouter AI   │
│ (Reverse Image Search)│  │  hosted Metasearch)│  │ (GPT-4o / Claude) │
└─────────────────────┘  └──────────────────┘  └──────────────────┘
                                     │
               ┌─────────────────────┼─────────────────────┐
               ▼                     ▼                     ▼
┌─────────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  SerpApi / SerpStack │  │   Cloudinary     │  │   Redis Cache     │
│   (Additional APIs)  │  │ (Image Storage)  │  │ (24h TTL results)  │
└─────────────────────┘  └──────────────────┘  └──────────────────┘
```

## Data Flow

### 1. Image Upload & Reverse Search

1. **Client** uploads an image (+ optional claim text) to `/api/reverse-search/`
2. **Django** receives the request, uploads image to Cloudinary, and enqueues a Celery task
3. **Celery Worker** executes the reverse search pipeline:
   - Calls **OpenWebNinja API** for reverse image search
   - Results are cached in **Redis** (24-hour TTL)
4. **Progress** is streamed back to client via **Server-Sent Events (SSE)**

### 2. Data Processing & Enrichment

The `data_processor.py` pipeline normalizes raw search results:

1. **Normalize** — Clean URLs, remove tracking parameters, normalize domains
2. **Deduplicate** — Remove duplicate URLs and near-duplicate domains
3. **Enrich** — Fetch image metadata (EXIF, dimensions, format, MIME type)
4. **Score** — Multi-factor relevance scoring:
   - Presence of publication date
   - Trusted domain status
   - Image metadata availability
   - Title/snippet quality
5. **Rank** — Sort by composite score, extract top 15-20 candidates
6. **Build Timeline** — Chronological spread of publication dates

### 3. Web Crawling

Top candidates are crawled **concurrently** (ThreadPoolExecutor, 10 workers):

- Extracts page title, meta description, and visible text content
- Detects paywalls (searching for paywall-related patterns in content)
- Language detection for crawled content
- AI-generation anomaly detection (checks for phrases like "as an AI language model")
- Sensational language detection
- Content quality scoring (word count, completeness)

### 4. AI Disinformation Analysis

The `analysis_pipeline.py` + `llm_client.py` run a **hybrid analysis**:

#### Rules-Based Assessment (always runs)

- **Date consistency** — Are sources clustered in a suspicious 24-hour window?
- **Domain trust** — What's the ratio of trusted vs untrusted sources?
- **Cross-engine corroboration** — Do Google and Yandex both find results?
- **Source quality** — How many total sources? Are they robust?

#### LLM Reasoning (primary — with fallback)

- **Model**: `openai/gpt-4o-mini` (primary), `anthropic/claude-3-haiku` (fallback)
- **Prompt** includes: full crawled content, timeline, statistics, crawl status, source hierarchy
- **Source hierarchy** enforced in prompt:
  1. Official government/presidential sources (strongest)
  2. Local established media (Cameroon & Africa)
  3. International news agencies with local presence
  4. Verified social media pages
  5. Other local sources
  6. Unknown / WhatsApp sources
- **Post-processing**: Catches overcautious verdicts and upgrades them
- **Fallback**: If LLM is unavailable, uses pure rules-based verdict

#### Verdict Options

| Verdict         | Meaning                                                     | Confidence Range |
| --------------- | ----------------------------------------------------------- | ---------------- |
| `real`        | Official source confirms OR multiple credible sources agree | 0.75–0.95       |
| `likely`      | Credible sources suggest truth, slight caution              | 0.60–0.80       |
| `fake`        | Strong evidence of manipulation or contradiction            | 0.70–0.95       |
| `suspicious`  | Red flags present but not conclusive                        | 0.40–0.65       |
| `unconfirmed` | Insufficient or contradictory evidence                      | 0.00–0.40       |

### 5. Deep Research (On-Demand)

After the initial analysis, the user can click "View More" to generate a **research report**:

1. **Query Generation** — 3 strategic queries based on verdict:
   - `fake/suspicious` → Search for truth, debunking, what actually happened
   - `unconfirmed` → Search for fact-checks, verification, sources
   - `real/likely` → Search for additional confirming evidence, official statements
2. **SearXNG Metasearch** — General web + images + videos across multiple queries
3. **LLM Compilation** — The LLM writes a structured report with:
   - Summary (in the claim's language)
   - Key findings
   - Curated sources (up to 5)
   - Related images (up to 5)
   - Related videos (up to 3)

## Component Interactions

### Client (Next.js)

- **UploadCard**: Handles image upload and claim input
- **ProcessingAnimation**: Displays real-time progress via SSE
- **HistoryBlock**: Shows user's search history
- **ResultsPage**: Displays analysis results with verdict
- **ResearchView**: Shows generated research reports

### Server (Django)

- **authentication**: Token-based user registration/login
- **reversewebsearch**: Core reverse image search pipeline
  - `views.py`: API endpoints (upload, progress, history)
  - `tasks.py`: Celery pipeline orchestration
  - `data_processor.py`: Result normalization and scoring
  - `utils.py`: Image metadata, HTTP sessions, crawling
- **robot**: AI analysis engine
  - `analysis_pipeline.py`: Hybrid rules + LLM analysis
  - `llm_client.py`: OpenRouter integration
- **discover**: SearXNG research generation
  - `research_generator.py`: Query generation and report compilation
  - `searxng_client.py`: SearXNG API client

### Infrastructure

- **PostgreSQL**: Primary database (user accounts, search history, analysis results)
- **Redis**: Message broker (Celery), cache (API responses), result backend
- **Celery**: Async task queue for long-running pipelines
- **Cloudinary**: Image storage and CDN
- **SearXNG**: Self-hosted metasearch engine
- **Prometheus + Grafana**: Monitoring and observability

## Communication Patterns

### Synchronous

- Client → Django: HTTP/REST (image upload, history retrieval)
- Django → Cloudinary: Image upload/download
- Django → OpenWebNinja: Reverse image search API
- Django → OpenRouter: LLM analysis API
- Django → SearXNG: Research queries

### Asynchronous

- Django → Celery → Redis: Task queuing
- Celery → External APIs: Parallel API calls
- Django → Client: Server-Sent Events (SSE) for progress updates

### Caching

- Redis caches reverse search results (24h TTL)
- Redis caches SearXNG results (24h TTL)
- Redis caches crawled page content (7d TTL)
- Redis caches image metadata (24h TTL)