# 🤖 Bob Digital Investigator

**Reverse Image Search · AI-Powered Disinformation Analysis · Automated Research Reports**

Bob Digital Investigator is a full-stack digital forensics platform designed to verify visual content and combat disinformation — with a particular focus on **Cameroon and African online spaces**. Upload an image, optionally add a claim you want to check, and the system will:

1. **Search the web** using reverse image search (OpenWebNinja)
2. **Analyze results** through a hybrid AI + rules-based pipeline (OpenRouter LLMs)
3. **Generate a structured research report** using a self-hosted SearXNG metasearch engine

The result is a detailed forensic dossier: source ranking, publication timelines, crawl-enriched evidence, an AI verdict (real / likely / fake / suspicious / unconfirmed), and a deep-dive research report with sources, images, and videos.

---

## ✨ Key Features

| Feature                                   | Description                                                                                                                |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **🔍 Reverse Image Search**         | Powered by OpenWebNinja — finds where and how an image appears across the web                                             |
| **🧠 AI Disinformation Analysis**   | Hybrid pipeline: rules-based heuristics + LLM reasoning via OpenRouter (GPT-4o-mini / Claude 3 Haiku)                      |
| **📊 Verdict System**               | Five-tier classification:`real`, `likely`, `fake`, `suspicious`, `unconfirmed` with calibrated confidence scores |
| **📚 Automated Research Reports**   | On-demand SearXNG metasearch + LLM compilation into structured reports with sources, images, videos, and key findings      |
| **🌐 Cameroon & Africa Focus**      | Curated trusted domain lists, government TLD detection, official presidential sources, tier-1 African news outlets         |
| **🕷️ Web Crawling**               | Concurrent source crawling with paywall detection, snippet extraction, and AI-generation anomaly detection                 |
| **📈 Real-time Progress Streaming** | Server-Sent Events (SSE) push status updates throughout the pipeline                                                       |
| **👤 User Authentication**          | Token-based registration/login with search history persistence                                                             |
| **📦 Dockerized Deployment**        | `compose.yaml` files for both client and server                                                                          |
| **📊 Monitoring**                   | Prometheus metrics + Grafana dashboard for observability                                                                   |

---

## 🏗️ Architecture

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

**Data Flow:**

1. Client uploads an image (+ optional claim text)
2. Django REST API receives the request and enqueues a Celery task
3. Celery worker runs the reverse search pipeline:
   - **Search**: OpenWebNinja reverse image search (with Redis caching)
   - **Process**: Normalize, deduplicate, score, and rank results
   - **Enrich**: Fetch image metadata (EXIF, dimensions, format)
   - **Crawl**: Concurrently crawl top 10 source pages (ThreadPoolExecutor)
   - **Analyze**: Rules-based heuristics → LLM verdict via OpenRouter
4. Progress is streamed back to the client via SSE
5. User can then trigger an on-demand **SearXNG research** for deeper investigation
6. SearXNG searches are compiled by the LLM into a structured research report

---

## 🛠️ Tech Stack

### Frontend

| Technology                | Purpose                      |
| ------------------------- | ---------------------------- |
| **Next.js 16**      | React framework (App Router) |
| **React 19**        | UI library                   |
| **TypeScript**      | Type safety                  |
| **Tailwind CSS v4** | Utility-first styling        |
| **Bun**            | JavaScript runtime, package manager, and test runner (`bun test`) |
| **Axios**           | HTTP client                  |
| **js-cookie**       | Token management             |

### Backend

| Technology                      | Purpose                                   |
| ------------------------------- | ----------------------------------------- |
| **Django 6.0**            | Python web framework                      |
| **Django REST Framework** | REST API with token authentication        |
| **Celery**                | Async task queue                          |
| **Redis**                 | Message broker, result backend, and cache |
| **PostgreSQL**            | Primary database                          |
| **Gunicorn**              | Production WSGI server                    |

### AI / LLM

| Technology                    | Purpose                                                          |
| ----------------------------- | ---------------------------------------------------------------- |
| **OpenRouter**          | Unified API for GPT-4o-mini, Claude 3 Haiku, and fallback models |
| **SearXNG**             | Self-hosted privacy-respecting metasearch engine                 |
| **OpenWebNinja**        | Reverse image search API                                         |
| **SerpApi / SerpStack** | Additional web search APIs                                       |
| **RapidAPI**            | Supplementary data sources                                       |

### Infrastructure & Monitoring

| Technology                  | Purpose                                    |
| --------------------------- | ------------------------------------------ |
| **Docker**            | Containerization (client + server)         |
| **Cloudinary**        | Image hosting and CDN                      |
| **Prometheus**        | Metrics collection (`django-prometheus`) |
| **Grafana**           | Dashboards and visualization               |
| **Sentry** (optional) | Error tracking                             |

---

## 📁 Project Structure

```
bob-digital-investigator/
├── _docs/
│   ├── commands.txt          # Local dev command reference
│   └── diagrams.drawio       # Architecture diagrams
│
├── client/                   # Next.js frontend
│   ├── Dockerfile            # Multi-stage Bun Docker build
│   ├── compose.yaml          # Docker Compose for client
│   ├── package.json          # Dependencies
│   ├── tsconfig.json         # TypeScript config
│   ├── next.config.ts        # Next.js config
│   ├── eslint.config.mjs     # ESLint flat config
│   └── src/
│       ├── proxy.ts          # API proxy configuration
│       ├── colors/           # Theme constants
│       ├── app/
│       │   ├── layout.tsx    # Root layout
│       │   ├── page.tsx      # Home page (upload + history)
│       │   ├── globals.css   # Global styles
│       │   ├── connection/
│       │   │   ├── login/    # Login page
│       │   │   └── register/ # Registration page
│       │   ├── reverseSearchResult/  # Results detail page
│       │   └── api/metrics/  # Prometheus client metrics endpoint
│       └── components/
│           ├── UploadCard.tsx            # Image upload + claim input
│           ├── ProcessingAnimation.tsx    # Upload progress animation
│           ├── HistoryBlock.tsx           # Search history sidebar
│           ├── AuthPage/                 # Auth UI components
│           └── resultView/
│               ├── ResultsPage.tsx        # Main results container
│               ├── RobotResponse.tsx      # AI verdict footer
│               ├── ResearchView.tsx       # Research report display
│               ├── resultCard.tsx         # Individual result card
│               ├── statCards.tsx          # Statistics summary
│               ├── timelineSection.tsx    # Publication timeline
│               ├── imageGallery.tsx       # Related images grid
│               └── loadingScreen.tsx      # SSE progress display
│
└── server/                   # Django REST backend
    ├── Dockerfile            # Python slim Docker build
    ├── compose.yaml          # Docker Compose for server
    ├── manage.py             # Django management script
    ├── requirements.txt      # Python dependencies
    ├── prometheus.yml        # Prometheus config
    ├── searxng_settings.yml  # SearXNG configuration
    ├── _Project/             # Django project settings
    │   ├── settings.py       # All settings (DB, cache, APIs, CORS, Celery)
    │   ├── urls.py           # Root URL configuration
    │   ├── celery.py         # Celery app configuration
    │   ├── wsgi.py           # WSGI entry point
    │   └── asgi.py           # ASGI entry point
    ├── authentication/       # User auth app
    │   ├── models.py         # CustomUser model (email-based)
    │   ├── serializers.py    # Registration + login serializers
    │   ├── views.py          # Register/Login API views
    │   └── urls.py           # Auth routes
    ├── reversewebsearch/     # Core reverse search app
    │   ├── models.py         # WebsearchResults model
    │   ├── views.py          # Upload, progress SSE, history APIs
    │   ├── serializers.py    # DRF serializers
    │   ├── tasks.py          # Celery pipeline (search→process→crawl→analyze)
    │   ├── data_processor.py # 688-line data normalization pipeline
    │   ├── utils.py          # Image metadata fetch, HTTP session, crawling
    │   ├── trusted_domains.py        # Domain trust helpers
    │   ├── trusted_domains.json      # Curated trusted domain lists
    │   └── urls.py           # Reverse search routes
    ├── robot/                # AI analysis engine
    │   ├── models.py         # RobotAnalysis model (verdict, evidence, report)
    │   ├── analysis_pipeline.py      # Hybrid rules + LLM analysis
    │   ├── llm_client.py             # OpenRouter client (prompts, fallback, fixes)
    │   ├── serializers.py    # DRF serializers
    │   └── views.py          # API views
    ├── discover/             # SearXNG research module
    │   ├── models.py         # (extends RobotAnalysis with research fields)
    │   ├── views.py          # Generate research + SSE progress
    │   ├── tasks.py          # Celery research generation task
    │   ├── research_generator.py     # Query generation, SearXNG search, LLM compilation
    │   ├── llm_research_prompt.py    # Research report prompt builder
    │   ├── searxng_client.py         # SearXNG API client (general/images/videos)
    │   ├── urls.py           # Discover routes
    │   └── templates/admin/  # Custom admin index template
    ├── grafana/              # Monitoring
    │   ├── dashboards/       # Pre-built Grafana dashboard (JSON)
    │   └── datasources/      # Prometheus datasource config
    └── migrations/           # Database migrations
```

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose (recommended for production)
- Python 3.12+ (for manual development)
- Bun 1.2+ or Node.js 20+ (for manual frontend development)
- Redis 7+ (message broker + cache)

### Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/juanvictorqwerty/Bob-Digital-Investigator.git
cd Bob-Digital-Investigator

# Create environment file (see Configuration section)
cp server/.env.example server/.env

# Start everything with Docker Compose
docker compose up --build
```

The client will be available at `http://localhost:3000` and the API at `http://localhost:8000`.

### Manual Development Setup

You'll need **4 terminal sessions**:

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
cd server
celery -A _Project worker -l info

# Terminal 3: Start Django
cd server
python manage.py migrate
python manage.py runserver

# Terminal 4: Start Next.js
cd client
bun install
bun run dev
```

### Environment Variables

Create `server/.env`:

```env
# Database
DB_NAME=bob_investigator
DB_USER=bob_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Django
DJANGO_SECRET_KEY=your_django_secret_key
DEBUG=True
FRONTEND_URL=http://localhost:3000

# External APIs
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
SERPAPI_KEY=your_serpapi_key
RAPIDAPI_KEY=your_rapidapi_key
OPENROUTER_API_KEY=your_openrouter_key
REVERSE_IMAGE=your_openwebninja_key

# SearXNG (optional — defaults to http://localhost:8888)
SEARXNG_BASE_URL=http://localhost:8888
```

---

## ⚙️ Configuration

### External API Keys

| Service                | Required | Used For                      | How to Get                                |
| ---------------------- | -------- | ----------------------------- | ----------------------------------------- |
| **OpenWebNinja** | ✅       | Reverse image search          | [openwebninja.com](https://openwebninja.com) |
| **OpenRouter**   | ✅       | LLM analysis (GPT-4o, Claude) | [openrouter.ai](https://openrouter.ai)       |
| **Cloudinary**   | ✅       | Image hosting & CDN           | [cloudinary.com](https://cloudinary.com)     |
|                        |          |                               |                                           |

### SearXNG (Self-hosted Metasearch)

For the research feature, you need a running SearXNG instance:

```yaml
# Example docker-compose searxng service
services:
  searxng:
    image: searxng/searxng:latest
    ports:
      - "8888:8080"
    volumes:
      - ./searxng_settings.yml:/etc/searxng/settings.yml:ro
    environment:
      - SEARXNG_BASE_URL=http://localhost:8888
```

The SearXNG settings file is included at `server/searxng_settings.yml`.

### Trusted Domains

The system maintains a curated list of trusted domains for Cameroonian and African sources in `server/reversewebsearch/trusted_domains.json`:

- **Trusted Domains**: `/\.gov\.cm$/`, `/\.gov\.ru$/`, `reuters.com`, `apnews.com`, `bbc.com`, etc.
- **Certified Facebook Pages**: Official pages for `prctv.cm`, `crtv`, `cameroon_tribune`, etc.
- **Government TLDs**: `.gov`, `.gov.cm`, `.gov.ru`, `.gouv.cm`, `.gov.af` etc.
- **Tier-1 News Agencies**: Reuters, AP, AFP, BBC, France24, RFI
- **Tier-1 African News**: Jeune Afrique, Africanews, Cameroon Tribune, CRTV, Actu Cameroun

---

## 📡 API Endpoints

### Authentication

| Method   | Endpoint            | Description                            |
| -------- | ------------------- | -------------------------------------- |
| `POST` | `/auth/register/` | Register a new user (email + password) |
| `POST` | `/auth/login/`    | Login, returns auth token              |

### Reverse Image Search

| Method    | Endpoint                                    | Description                                    |
| --------- | ------------------------------------------- | ---------------------------------------------- |
| `POST`  | `/api/reverse-search/`                    | Upload image + optional claim, starts pipeline |
| `GET`   | `/api/reverse-search/progress/<task_id>/` | SSE stream for pipeline progress               |
| `GET`   | `/api/reverse-search/history/`            | List authenticated user's search history       |
| `GET`   | `/api/reverse-search/history/<id>/`       | Get specific search result with alias          |
| `PATCH` | `/api/reverse-search/history/<id>/`       | Update result alias                            |

### Research (Discover)

| Method   | Endpoint                              | Description                                               |
| -------- | ------------------------------------- | --------------------------------------------------------- |
| `POST` | `/api/discover/generate/`           | Start SearXNG research generation (takes `analysis_id`) |
| `GET`  | `/api/discover/progress/<task_id>/` | SSE stream for research progress                          |

### Admin

| Method  | Endpoint    | Description            |
| ------- | ----------- | ---------------------- |
| `GET` | `/admin/` | Django admin interface |

### Metrics

| Method  | Endpoint     | Description                      |
| ------- | ------------ | -------------------------------- |
| `GET` | `/metrics` | Prometheus metrics (client-side) |
| `GET` | `/`        | Prometheus metrics (server-side) |

All authenticated endpoints require an `Authorization: Token <token>` header.

---

## 🔬 How It Works: The Full Pipeline

### Stage 1: Reverse Image Search

1. User uploads an image (+ optional text claim)
2. Image is uploaded to **Cloudinary** for permanent storage
3. The reverse search uses **OpenWebNinja API** to find matching pages across the web
4. Results are cached in Redis (24-hour TTL) to avoid redundant API calls

### Stage 2: Data Processing & Enrichment

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

### Stage 3: Web Crawling

Top candidates are crawled **concurrently** (ThreadPoolExecutor, 10 workers):

- Extracts page title, meta description, and visible text content
- Detects paywalls (searching for paywall-related patterns in content)
- Language detection for crawled content
- AI-generation anomaly detection (checks for phrases like "as an AI language model")
- Sensational language detection
- Content quality scoring (word count, completeness)

### Stage 4: AI Disinformation Analysis

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

### Stage 5: Deep Research (On-Demand)

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

---

## 📊 Monitoring

### Prometheus Metrics

The server exposes metrics via `django-prometheus` at the root endpoint. The client also exposes a `/api/metrics` endpoint. Key metrics include:

- Request counts, latencies, and error rates
- Celery task execution times
- Cache hit/miss ratios
- Database query performance

### Grafana Dashboard

A pre-built Grafana dashboard is included at `server/grafana/dashboards/bob-metrics.json`. It provides:

- **Search Pipeline Performance** — Duration of each pipeline stage
- **API Throughput** — Requests per endpoint
- **LLM Analysis** — Verdict distribution, confidence trends
- **Cache Efficiency** — Hit rates for SearXNG and API responses
- **Worker Status** — Celery queue depth, task success/failure rates

Start the monitoring stack:

```bash
docker run -d -p 9090:9090 -v server/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
docker run -d -p 3000:3000 -v server/grafana:/etc/grafana grafana/grafana
```

---

## 🧪 Project Modules Summary

### `authentication`

- `CustomUser` model (email-based, UUID primary key)
- Token-based registration and login
- Session, basic, and token authentication support

### `reversewebsearch`

- Core reverse image search pipeline
- `WebsearchResults` model stores raw results, timeline, statistics, optional alias
- `data_processor.py` — 688-line normalization, deduplication, scoring, ranking engine
- `trusted_domains_loader.py` — Domain trust verification with Cameroon/Africa focus
- Celery task `run_reverse_search_pipeline` orchestrates the full pipeline

### `robot`

- AI analysis engine
- `RobotAnalysis` model: verdict, confidence, explanation, key evidence, LLM metadata
- `analysis_pipeline.py` — Hybrid rules + LLM pipeline
- `llm_client.py` — OpenRouter integration with prompt construction, response parsing, overcautious-verdict correction, and model fallback

### `discover`

- On-demand SearXNG research generation
- `searxng_client.py` — Full SearXNG API client (general, images, videos)
- `research_generator.py` — Query generation, SearXNG search execution, LLM compilation
- `llm_research_prompt.py` — Structured prompt building for research reports

---

## 🐳 Docker Deployment

### Server (Django + Celery)

The server `Dockerfile` uses `python:3.12-slim` with multi-stage caching. The `compose.yaml` includes the Django app, Celery worker, PostgreSQL, and Redis.

### Client (Next.js)

The client `Dockerfile` uses `oven/bun:1.2.6` with multi-stage builds:

1. **`deps`** — Install production dependencies
2. **`build`** — Install dev dependencies and build Next.js
3. **`final`** — Minimal runtime image with only production artifacts

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow existing code style (ESLint + Prettier for frontend, PEP 8 for backend)
- Add type hints for Python and TypeScript
- Write tests for new features
- Update migrations when changing models
- Keep the trust domains list updated when adding new sources

---

## 📄 License

This project is open source. See the LICENSE file for details.

---

## 🙏 Acknowledgements

- **[OpenWebNinja](https://openwebninja.com)** — Reverse image search API
- **[OpenRouter](https://openrouter.ai)** — Unified LLM API
- **[SearXNG](https://docs.searxng.org)** — Privacy-respecting metasearch engine
- **[Cloudinary](https://cloudinary.com)** — Image hosting and transformation
- **[Django REST Framework](https://www.django-rest-framework.org)** — API toolkit
- **[Celery](https://docs.celeryq.dev)** — Distributed task queue
- **[Next.js](https://nextjs.org)** — React framework
- **[Tailwind CSS](https://tailwindcss.com)** — Utility CSS framework
- **[Prometheus](https://prometheus.io)** & **[Grafana](https://grafana.com)** — Monitoring stack
