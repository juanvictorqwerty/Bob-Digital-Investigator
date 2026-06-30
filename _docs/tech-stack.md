# Tech Stack

## Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Next.js** | 16 | React framework with App Router |
| **React** | 19 | UI library |
| **TypeScript** | Latest | Type safety |
| **Tailwind CSS** | v4 | Utility-first styling |
| **Bun** | 1.2+ | JavaScript runtime, package manager, and test runner |
| **Axios** | Latest | HTTP client |
| **js-cookie** | Latest | Token management |

### Frontend Architecture

- **App Router**: Next.js 16 App Router for routing and layouts
- **Server Components**: Leveraging React Server Components for performance
- **SSE Client**: Server-Sent Events for real-time progress updates
- **Proxy Configuration**: Custom proxy for API routing (`src/proxy.ts`)

## Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Django** | 6.0 | Python web framework |
| **Django REST Framework** | Latest | REST API with token authentication |
| **Celery** | Latest | Async task queue |
| **Redis** | 7+ | Message broker, result backend, and cache |
| **PostgreSQL** | 17 | Primary database |
| **Gunicorn** | Latest | Production WSGI server |
| **django-prometheus** | Latest | Prometheus metrics integration |
| **django-cors-headers** | Latest | CORS handling |
| **cloudinary-storage** | Latest | Cloudinary integration for Django |
| **django-redis** | Latest | Redis cache backend |

### Backend Architecture

- **REST API**: Token-based authentication (Session, Basic, Token)
- **Celery Workers**: Async task execution for long-running pipelines
- **PostgreSQL**: Relational database for structured data
- **Redis**: Multi-purpose (message broker, cache, result backend)
- **Prometheus**: Metrics collection via django-prometheus middleware

## AI / LLM

| Technology | Purpose |
|------------|---------|
| **OpenRouter** | Unified API for multiple LLM providers |
| **OpenAI GPT-4o-mini** | Primary LLM for analysis (via OpenRouter) |
| **Anthropic Claude 3 Haiku** | Fallback LLM (via OpenRouter) |
| **SearXNG** | Self-hosted privacy-respecting metasearch engine |
| **OpenWebNinja** | Reverse image search API |
| **SerpApi / SerpStack** | Additional web search APIs |
| **RapidAPI** | Supplementary data sources |

### AI Pipeline

- **Hybrid Analysis**: Rules-based heuristics + LLM reasoning
- **Model Fallback**: Automatic fallback from GPT-4o-mini to Claude 3 Haiku
- **Prompt Engineering**: Structured prompts with source hierarchy enforcement
- **Post-processing**: Overcautious verdict correction

## Infrastructure & Monitoring

| Technology | Version | Purpose |
|------------|---------|---------|
| **Docker** | Latest | Containerization |
| **Docker Compose** | Latest | Multi-container orchestration |
| **Cloudinary** | Latest | Image hosting and CDN |
| **Prometheus** | Latest | Metrics collection |
| **Grafana** | 10.4.2 | Dashboards and visualization |
| **Nginx** | Alpine | Reverse proxy and load balancer |

### Infrastructure Architecture

- **Docker Multi-stage Builds**: Optimized image sizes for both client and server
- **Docker Compose**: Single command deployment of all services
- **Nginx**: Reverse proxy for client, Django, SearXNG, Prometheus, and Grafana
- **Cloudinary**: Image storage, transformation, and CDN
- **Prometheus**: Scrapes metrics from Django and client
- **Grafana**: Pre-built dashboard for observability

## Development Tools

| Tool | Purpose |
|------|---------|
| **Bun** | JavaScript runtime, package manager, test runner |
| **ESLint** | Code linting (flat config) |
| **Prettier** | Code formatting |
| **GitHub Actions** | CI/CD (tests and deployment) |
| **draw.io** | Architecture diagrams |

## Key Dependencies

### Client (Next.js)

```json
{
  "next": "^16.0.0",
  "react": "^19.0.0",
  "typescript": "^5.0.0",
  "tailwindcss": "^4.0.0",
  "axios": "^1.6.0",
  "js-cookie": "^3.0.0"
}
```

### Server (Django)

```txt
Django==6.0.3
djangorestframework==3.15.0
celery==5.4.0
redis==5.0.0
psycopg2-binary==2.9.9
gunicorn==22.0.0
django-prometheus==2.3.1
django-cors-headers==4.4.0
cloudinary==1.41.0
django-redis==5.4.0
```

## Technology Choices Rationale

### Why Next.js 16?
- Latest React features (Server Components)
- Excellent performance with App Router
- Built-in optimizations (image, font, script)
- Strong TypeScript support

### Why Django 6.0?
- Mature, stable framework with excellent ORM
- Built-in admin interface
- Strong security features
- Excellent Python ecosystem integration

### Why Celery + Redis?
- Proven async task queue for Python
- Redis provides fast message broker and caching
- Supports complex task workflows
- Horizontal scaling capability

### Why OpenRouter?
- Unified API for multiple LLM providers
- Easy model switching
- Fallback support
- Cost-effective (pay per token)

### Why SearXNG?
- Self-hosted (no API costs)
- Privacy-respecting (no tracking)
- Multiple search engines aggregated
- Customizable and extensible

### Why Cloudinary?
- Easy image upload and transformation
- Global CDN for fast delivery
- Automatic format optimization
- Generous free tier

### Why Prometheus + Grafana?
- Industry standard for metrics
- django-prometheus provides easy integration
- Grafana dashboards for visualization
- Alerting capabilities