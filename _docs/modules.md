# Module Documentation

This document provides detailed information about each module in the Bob Digital Investigator project.

---

## Project Structure Overview

```
bob-digital-investigator/
├── client/                   # Next.js frontend
│   ├── src/
│   │   ├── app/             # App Router pages
│   │   ├── components/      # React components
│   │   ├── lib/             # Utility functions
│   │   └── proxy.ts         # API proxy config
│   ├── public/              # Static assets
│   ├── Dockerfile           # Multi-stage build
│   └── package.json         # Dependencies
│
└── server/                   # Django REST backend
    ├── _Project/            # Django project settings
    ├── authentication/      # User auth app
    ├── reversewebsearch/    # Core reverse search app
    ├── robot/               # AI analysis engine
    ├── discover/            # SearXNG research module
    ├── grafana/             # Monitoring dashboards
    ├── Dockerfile           # Python slim build
    └── requirements.txt     # Python dependencies
```

---

## Client Module (Next.js)

### Purpose
Frontend web application for image upload, analysis visualization, and research report display.

### Technology Stack
- **Framework**: Next.js 16 with App Router
- **UI Library**: React 19
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Runtime**: Bun 1.2+
- **HTTP Client**: Axios
- **Token Management**: js-cookie

### Directory Structure

```
client/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with metadata
│   │   ├── page.tsx            # Home page (upload + history)
│   │   ├── globals.css         # Global styles
│   │   ├── favicon.ico         # Favicon
│   │   ├── connection/
│   │   │   ├── login/          # Login page
│   │   │   │   └── page.tsx
│   │   │   └── register/       # Registration page
│   │   │       └── page.tsx
│   │   ├── reverseSearchResult/ # Results detail page
│   │   │   └── page.tsx
│   │   └── api/
│   │       └── metrics/        # Prometheus metrics endpoint
│   │           └── route.ts
│   │
│   ├── components/
│   │   ├── UploadCard.tsx           # Image upload + claim input
│   │   ├── ProcessingAnimation.tsx   # Upload progress animation
│   │   ├── HistoryBlock.tsx          # Search history sidebar
│   │   ├── AuthPage/                 # Authentication UI
│   │   │   ├── AuthLayout.tsx        # Auth page layout
│   │   │   ├── AuthInput.tsx         # Input field component
│   │   │   ├── AuthButton.tsx        # Button component
│   │   │   └── AuthDivider.tsx       # Divider component
│   │   └── resultView/               # Results display
│   │       ├── ResultsPage.tsx       # Main results container
│   │       ├── RobotResponse.tsx     # AI verdict footer
│   │       ├── ResearchView.tsx      # Research report display
│   │       ├── resultCard.tsx        # Individual result card
│   │       ├── statCards.tsx         # Statistics summary
│   │       ├── timelineSection.tsx   # Publication timeline
│   │       ├── imageGallery.tsx      # Related images grid
│   │       └── loadingScreen.tsx     # SSE progress display
│   │
│   ├── colors/
│   │   └── Colors.tsx         # Theme color constants
│   │
│   ├── lib/
│   │   └── metrics.ts         # Prometheus client metrics
│   │
│   ├── proxy.ts               # API proxy configuration
│   │
│   └── __tests__/             # Test files
│       ├── setup.ts
│       ├── api/
│       │   └── metrics.test.ts
│       ├── components/
│       │   ├── AuthButton.test.tsx
│       │   ├── AuthDivider.test.tsx
│       │   ├── AuthInput.test.tsx
│       │   ├── AuthLayout.test.tsx
│       │   ├── Colors.test.tsx
│       │   ├── HistoryBlock.test.tsx
│       │   ├── imageGallery.test.tsx
│       │   ├── loadingScreen.test.tsx
│       │   ├── ProcessingAnimation.test.tsx
│       │   ├── ResearchView.test.tsx
│       │   ├── resultCard.test.tsx
│       │   ├── RobotResponse.test.tsx
│       │   ├── statCards.test.tsx
│       │   └── timelineSection.test.tsx
│       ├── middleware/
│       │   └── proxy.test.ts
│       └── pages/
│           ├── home.test.tsx
│           ├── login.test.tsx
│           ├── register.test.tsx
│           └── reverseSearchResult.test.tsx
│
├── public/                    # Static assets
│   ├── file.svg
│   ├── globe.svg
│   ├── next.svg
│   ├── vercel.svg
│   └── window.svg
│
├── Dockerfile                 # Multi-stage Docker build
├── docker-compose.yml         # Docker Compose config
├── package.json               # Dependencies
├── tsconfig.json              # TypeScript config
├── next.config.ts             # Next.js configuration
├── eslint.config.mjs          # ESLint flat config
├── bun.lock                   # Bun lock file
├── bunfig.toml                # Bun configuration
└── README.md                  # Client-specific README
```

### Key Components

#### UploadCard
**File:** `src/components/UploadCard.tsx`

**Purpose:** Handles image upload and optional claim input

**Features:**
- Drag-and-drop image upload
- File validation (type, size)
- Preview of selected image
- Optional claim text input
- Upload progress indicator
- Error handling

**State:**
- `selectedFile`: File object
- `previewUrl`: Image preview URL
- `claim`: User's claim text
- `uploading`: Upload in progress flag
- `error`: Error message

#### ProcessingAnimation
**File:** `src/components/ProcessingAnimation.tsx`

**Purpose:** Displays real-time progress during analysis

**Features:**
- SSE connection for progress updates
- Animated progress bar
- Stage indicators (search, process, crawl, analyze)
- Status messages
- Cancel/retry options

**SSE Events Handled:**
- `progress`: Update progress bar
- `complete`: Navigate to results
- `error`: Display error message

#### HistoryBlock
**File:** `src/components/HistoryBlock.tsx`

**Purpose:** Shows user's search history

**Features:**
- List of past searches
- Verdict badges (color-coded)
- Timestamp display
- Alias editing
- Click to view details
- Pagination

**Data Source:**
- `GET /api/reverse-search/history/`

#### ResultsPage
**File:** `src/components/resultView/ResultsPage.tsx`

**Purpose:** Main results display container

**Features:**
- Verdict display with confidence score
- Explanation text
- Key evidence list
- Timeline visualization
- Statistics cards
- Source list
- Research button

**Sub-components:**
- `RobotResponse.tsx`: Verdict footer
- `statCards.tsx`: Statistics summary
- `timelineSection.tsx`: Publication timeline
- `resultCard.tsx`: Individual result cards
- `imageGallery.tsx`: Related images
- `ResearchView.tsx`: Research report

#### ResearchView
**File:** `src/components/resultView/ResearchView.tsx`

**Purpose:** Displays generated research reports

**Features:**
- Summary section
- Key findings list
- Curated sources with links
- Related images grid
- Related videos list
- Loading state during generation

**SSE Events Handled:**
- `progress`: Research generation progress
- `complete`: Display research report

### State Management

**No global state management library** - Uses React hooks and context:

- `useState`: Local component state
- `useEffect`: Side effects (API calls, SSE)
- `useContext`: Auth context for token
- `useRouter`: Next.js routing
- `useCookies`: Token persistence

### API Integration

**Base URL:** Configured via `NEXT_PUBLIC_BACKEND_URL`

**Axios Instance:** Created in components for API calls

**Endpoints Used:**
- `POST /auth/login/` - Login
- `POST /auth/register/` - Register
- `POST /api/reverse-search/` - Upload image
- `GET /api/reverse-search/progress/{task_id}/` - SSE progress
- `GET /api/reverse-search/history/` - List history
- `GET /api/reverse-search/history/{id}/` - Get result
- `PATCH /api/reverse-search/history/{id}/` - Update alias
- `POST /api/discover/generate/` - Generate research
- `GET /api/discover/progress/{task_id}/` - Research progress

### Styling

**Framework:** Tailwind CSS v4

**Theme:**
- Custom color palette in `src/colors/Colors.tsx`
- Dark theme optimized
- Responsive design (mobile-first)
- CSS animations for loading states

**Key Classes:**
- `bg-primary`, `text-primary`: Primary brand color
- `bg-secondary`, `text-secondary`: Secondary color
- `bg-background`, `text-foreground`: Background/text colors
- `rounded-card`, `shadow-card`: Card styling

### Testing

**Framework:** Bun test runner

**Test Structure:**
- Unit tests for components
- Integration tests for API calls
- Mock SSE events
- Mock Axios responses

**Run Tests:**
```bash
cd client
bun test
```

---

## Server Module (Django)

### Purpose
Backend REST API for image analysis, user authentication, and research generation.

### Technology Stack
- **Framework**: Django 6.0
- **API**: Django REST Framework
- **Task Queue**: Celery 5.4
- **Message Broker**: Redis 7
- **Database**: PostgreSQL 17
- **WSGI Server**: Gunicorn
- **Metrics**: django-prometheus
- **CORS**: django-cors-headers
- **Storage**: cloudinary-storage

### Directory Structure

```
server/
├── _Project/                  # Django project settings
│   ├── __init__.py
│   ├── settings.py            # All settings (DB, cache, APIs, CORS, Celery)
│   ├── urls.py                # Root URL configuration
│   ├── celery.py              # Celery app configuration
│   ├── wsgi.py                # WSGI entry point
│   └── asgi.py                # ASGI entry point
│
├── authentication/            # User authentication app
│   ├── __init__.py
│   ├── admin.py               # Admin configuration
│   ├── apps.py                # App configuration
│   ├── models.py              # CustomUser model (email-based)
│   ├── serializers.py         # Registration + login serializers
│   ├── views.py               # Register/Login API views
│   ├── urls.py                # Auth routes
│   ├── tests.py               # Unit tests
│   └── migrations/            # Database migrations
│       └── 0001_initial.py
│
├── reversewebsearch/          # Core reverse search app
│   ├── __init__.py
│   ├── admin.py               # Admin configuration
│   ├── apps.py                # App configuration
│   ├── models.py              # WebsearchResults model
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # Upload, progress SSE, history APIs
│   ├── tasks.py               # Celery pipeline (search→process→crawl→analyze)
│   ├── data_processor.py      # 688-line normalization, deduplication, scoring, ranking
│   ├── utils.py               # Image metadata fetch, HTTP session, crawling
│   ├── trusted_domains_loader.py  # Domain trust verification
│   ├── trusted_domains.json   # Curated trusted domain lists
│   ├── urls.py                # Reverse search routes
│   ├── tests.py               # Unit tests
│   └── migrations/            # Database migrations
│       ├── 0001_initial.py
│       ├── 0002_websearchresults_image.py
│       ├── 0003_alter_websearchresults_image.py
│       ├── 0004_alter_websearchresults_image.py
│       ├── 0005_websearchresults_alias.py
│       ├── 0006_alter_websearchresults_alias.py
│       └── 0007_alter_websearchresults_alias_and_more.py
│
├── robot/                     # AI analysis engine
│   ├── __init__.py
│   ├── admin.py               # Admin configuration
│   ├── apps.py                # App configuration
│   ├── models.py              # RobotAnalysis model (verdict, evidence, report)
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # API views
│   ├── analysis_pipeline.py   # Hybrid rules + LLM analysis
│   ├── llm_client.py          # OpenRouter client (prompts, fallback, fixes)
│   ├── trusted_domains.json   # Domain trust lists
│   ├── urls.py                # Robot routes
│   ├── tests.py               # Unit tests
│   └── migrations/            # Database migrations
│       ├── 0001_initial.py
│       └── 0002_add_research_fields.py
│
├── discover/                  # SearXNG research module
│   ├── __init__.py
│   ├── admin.py               # Admin configuration
│   ├── admin_views.py         # Custom admin views
│   ├── apps.py                # App configuration
│   ├── models.py              # Extends RobotAnalysis with research fields
│   ├── serializers.py         # DRF serializers
│   ├── views.py               # Generate research + SSE progress
│   ├── tasks.py               # Celery research generation task
│   ├── research_generator.py  # Query generation, SearXNG search, LLM compilation
│   ├── llm_research_prompt.py # Research report prompt builder
│   ├── searxng_client.py      # SearXNG API client (general/images/videos)
│   ├── urls.py                # Discover routes
│   ├── tests.py               # Unit tests
│   ├── templates/
│   │   └── admin/
│   │       └── discover_admin_index.html  # Custom admin template
│   └── migrations/            # Database migrations
│
├── grafana/                   # Monitoring
│   ├── dashboards/
│   │   ├── bob-metrics.json   # Pre-built Grafana dashboard
│   │   └── default.yml        # Dashboard provisioning
│   └── datasources/
│       └── prometheus.yml     # Prometheus datasource config
│
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Python slim Docker build
├── docker-entrypoint.sh       # Docker entrypoint script
├── prometheus.yml             # Prometheus configuration
├── searxng_settings.yml       # SearXNG configuration
└── test_settings.py           # Test-specific settings
```

---

## Server Apps

### authentication

**Purpose:** User registration and authentication

**Model:**
- `CustomUser`: Email-based user model with UUID primary key

**Features:**
- Token-based authentication
- Registration with email/password
- Login with token response
- Session authentication support

**Endpoints:**
- `POST /auth/register/` - Register new user
- `POST /auth/login/` - Login and get token

**Serializers:**
- `RegisterSerializer`: Validates and creates user
- `LoginSerializer`: Authenticates user, returns token

**Views:**
- `RegisterView`: Handle registration
- `LoginView`: Handle login

---

### reversewebsearch

**Purpose:** Core reverse image search pipeline

**Model:**
- `WebsearchResults`: Stores search results, timeline, statistics, verdict, alias

**Fields:**
- `id`: UUID primary key
- `user`: Foreign key to CustomUser
- `image_url`: Cloudinary URL
- `claim`: Optional claim text
- `raw_results`: JSON field with search results
- `processed_results`: JSON field with processed results
- `timeline`: JSON field with publication timeline
- `statistics`: JSON field with statistics
- `verdict`: String (real/likely/fake/suspicious/unconfirmed)
- `confidence`: Float (0.0-1.0)
- `explanation`: Text field
- `key_evidence`: JSON field with evidence list
- `crawled_content`: JSON field with crawled content
- `alias`: Optional user-defined label
- `created_at`: Timestamp
- `updated_at`: Timestamp

**Key Files:**

#### views.py
**Endpoints:**
- `POST /api/reverse-search/` - Upload image and start pipeline
- `GET /api/reverse-search/progress/{task_id}/` - SSE progress stream
- `GET /api/reverse-search/history/` - List user's search history
- `GET /api/reverse-search/history/{id}/` - Get specific result
- `PATCH /api/reverse-search/history/{id}/` - Update alias

**Features:**
- Image upload to Cloudinary
- Celery task queuing
- SSE progress streaming
- History retrieval with filtering

#### tasks.py
**Task:** `run_reverse_search_pipeline`

**Steps:**
1. Upload image to Cloudinary
2. Check Redis cache for existing results
3. Call OpenWebNinja API
4. Process results (data_processor.py)
5. Crawl top candidates (utils.py)
6. Run AI analysis (call robot app)
7. Save results to database
8. Send SSE completion event

**Timeout:** 5 minutes
**Retry:** 3 attempts with exponential backoff

#### data_processor.py (688 lines)
**Purpose:** Normalize, deduplicate, score, and rank search results

**Functions:**
- `normalize_url(url)`: Clean tracking parameters
- `normalize_domain(url)`: Extract and normalize domain
- `deduplicate_results(results)`: Remove duplicates
- `enrich_results(results)`: Fetch metadata
- `score_result(result)`: Calculate relevance score
- `rank_results(results)`: Sort by score
- `build_timeline(results)`: Create publication timeline

**Scoring Factors:**
- Publication date (25%)
- Trusted domain (20%)
- Image metadata (15%)
- Title quality (15%)
- Snippet quality (15%)
- Cross-engine (10%)

#### utils.py
**Functions:**
- `fetch_image_metadata(url)`: Get EXIF, dimensions, format
- `create_http_session()`: Create aiohttp session
- `crawl_page(url)`: Extract page content
- `detect_paywall(content)`: Check for paywall
- `detect_ai_generated(content)`: Check for AI-generated text
- `detect_sensational_language(content)`: Check for clickbait
- `calculate_quality_score(content)`: Score content quality

#### trusted_domains_loader.py
**Purpose:** Load and verify trusted domains

**Functions:**
- `is_trusted_domain(domain)`: Check if domain is trusted
- `get_trusted_domains()`: Get all trusted domains
- `get_government_tlds()`: Get government TLDs
- `get_certified_facebook_pages()`: Get verified social media

**Data Source:** `trusted_domains.json`

---

### robot

**Purpose:** AI disinformation analysis engine

**Model:**
- `RobotAnalysis`: Stores verdict, confidence, explanation, evidence, LLM metadata

**Fields:**
- `id`: UUID primary key
- `websearch_result`: Foreign key to WebsearchResults
- `verdict`: String (real/likely/fake/suspicious/unconfirmed)
- `confidence`: Float (0.0-1.0)
- `explanation`: Text field
- `key_evidence`: JSON field with evidence list
- `rules_score`: Integer (rules-based score)
- `llm_model`: String (model used)
- `llm_confidence`: Float (LLM confidence)
- `created_at`: Timestamp

**Key Files:**

#### analysis_pipeline.py
**Purpose:** Hybrid rules + LLM analysis orchestration

**Functions:**
- `run_rules_based_assessment(results)`: Calculate rules-based score
- `run_llm_analysis(results, claim)`: Call OpenRouter API
- `post_process_verdict(verdict, confidence)`: Fix overcautious verdicts
- `determine_verdict(rules_score, llm_result)`: Combine scores

**Process:**
1. Run rules-based assessment
2. Call LLM with crawled content
3. Post-process verdict
4. Return final verdict and confidence

#### llm_client.py
**Purpose:** OpenRouter API integration

**Functions:**
- `call_openrouter(prompt, model)`: Call OpenRouter API
- `build_analysis_prompt(results, claim)`: Build analysis prompt
- `parse_llm_response(response)`: Extract verdict and confidence
- `handle_llm_error(error)`: Handle API errors

**Models:**
- Primary: `openai/gpt-4o-mini`
- Fallback: `anthropic/claude-3-haiku`

**Features:**
- Automatic fallback on error
- Prompt engineering with source hierarchy
- Response parsing and validation
- Error handling and retries

---

### discover

**Purpose:** On-demand SearXNG research generation

**Model:**
- Extends `RobotAnalysis` with research fields (in database via migrations)

**Fields (added to RobotAnalysis):**
- `research_report`: JSON field with research report
- `research_task_id`: Celery task ID
- `research_completed_at`: Timestamp

**Key Files:**

#### research_generator.py
**Purpose:** Research report orchestration

**Functions:**
- `generate_research(analysis_id)`: Main research generation
- `generate_queries(verdict, claim)`: Create search queries
- `execute_searches(queries)`: Run SearXNG searches
- `compile_report(results, analysis)`: LLM compilation

**Process:**
1. Load analysis result
2. Generate 3 strategic queries
3. Execute SearXNG searches (general, images, videos)
4. Compile report with LLM
5. Save to database

#### searxng_client.py
**Purpose:** SearXNG API client

**Functions:**
- `search(query, categories)`: General web search
- `search_images(query)`: Image search
- `search_videos(query)`: Video search
- `parse_results(response)`: Parse SearXNG response

**Endpoints:**
- `GET /search?q={query}&format=json`
- `GET /images?q={query}&format=json`
- `GET /videos?q={query}&format=json`

**Caching:** 24-hour TTL in Redis

#### llm_research_prompt.py
**Purpose:** Research report prompt builder

**Functions:**
- `build_research_prompt(analysis, search_results)`: Build compilation prompt
- `format_sources(sources)`: Format sources for prompt
- `format_images(images)`: Format images for prompt
- `format_videos(videos)`: Format videos for prompt

**Prompt Structure:**
- Original analysis context
- Research findings
- Images and videos
- Task instructions
- Output format specification

---

## Shared Components

### Database Models

**User Model (authentication):**
- `CustomUser`: Email-based authentication

**Search Model (reversewebsearch):**
- `WebsearchResults`: Search results and analysis

**Analysis Model (robot):**
- `RobotAnalysis`: AI verdict and evidence

### Celery Tasks

**Task 1:** `run_reverse_search_pipeline`
- **App:** reversewebsearch
- **Duration:** 30-70 seconds
- **Retry:** 3 attempts

**Task 2:** `generate_research_report`
- **App:** discover
- **Duration:** 20-40 seconds
- **Retry:** 3 attempts

### Caching Strategy

**Redis Keys:**
- `reverse_search:{image_hash}` - Reverse search results (24h)
- `searxng:{query_hash}` - SearXNG results (24h)
- `crawl:{url_hash}` - Crawled content (7d)
- `image_meta:{url}` - Image metadata (24h)

**TTL Values:**
- Reverse search: 86400 seconds (24h)
- SearXNG: 86400 seconds (24h)
- Crawled content: 604800 seconds (7d)
- Image metadata: 86400 seconds (24h)

---

## Configuration Files

### Django Settings

**File:** `server/_Project/settings.py`

**Key Sections:**
- Database configuration
- Redis cache configuration
- Celery configuration
- CORS settings
- CSRF trusted origins
- Cloudinary storage
- Prometheus metrics
- Installed apps
- Middleware

### Celery Configuration

**File:** `server/_Project/celery.py`

**Configuration:**
- Broker URL: Redis
- Result backend: Redis
- Task serialization: JSON
- Result serialization: JSON
- Task tracking: Enabled

### Prometheus Configuration

**File:** `server/prometheus.yml`

**Scrape Configs:**
- Django server: `http://django:8000/`
- Client: `http://client:3000/api/metrics`
- Interval: 15 seconds

---

## Testing

### Server Tests

**Framework:** Django test runner

**Test Files:**
- `authentication/tests.py`
- `reversewebsearch/tests.py`
- `robot/tests.py`
- `discover/tests.py`

**Run Tests:**
```bash
cd server
python manage.py test
```

**Test Database:** Separate test database (`bob_test`)

**Fixtures:** Test data in JSON format

### Client Tests

**Framework:** Bun test runner

**Test Files:** `src/__tests__/`

**Run Tests:**
```bash
cd client
bun test
```

---

## Dependencies

### Python Dependencies

**File:** `server/requirements.txt`

**Key Dependencies:**
- Django 6.0.3
- djangorestframework 3.15.0
- celery 5.4.0
- redis 5.0.0
- psycopg2-binary 2.9.9
- gunicorn 22.0.0
- django-prometheus 2.3.1
- django-cors-headers 4.4.0
- cloudinary 1.41.0
- django-redis 5.4.0
- requests 2.31.0
- aiohttp 3.9.0

### Node Dependencies

**File:** `client/package.json`

**Key Dependencies:**
- next 16.0.0
- react 19.0.0
- typescript 5.0.0
- tailwindcss 4.0.0
- axios 1.6.0
- js-cookie 3.0.0

---

## Deployment

### Docker Build

**Client:**
```bash
docker compose build client
```

**Server:**
```bash
docker compose build django
docker compose build celery-worker
```

### Environment Variables

See [Configuration Guide](configuration.md) for complete list.

### Volumes

- `postgresql_data`: Database persistence
- `redis_data`: Redis persistence
- `staticfiles`: Static files
- `prometheus_data`: Metrics storage
- `grafana_data`: Dashboard storage