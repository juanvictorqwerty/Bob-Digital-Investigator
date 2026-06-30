# 🤖 Bob Digital Investigator

**Reverse Image Search · AI-Powered Disinformation Analysis · Automated Research Reports**

Bob Digital Investigator is a full-stack digital forensics platform designed to verify visual content and combat disinformation — with a particular focus on **Cameroon and African online spaces**. Upload an image, optionally add a claim you want to check, and the system will:

1. **Search the web** using reverse image search (OpenWebNinja)
2. **Analyze results** through a hybrid AI + rules-based pipeline (OpenRouter LLMs)
3. **Generate a structured research report** using a self-hosted SearXNG metasearch engine

The result is a detailed forensic dossier: source ranking, publication timelines, crawl-enriched evidence, an AI verdict (real / likely / fake / suspicious / unconfirmed), and a deep-dive research report with sources, images, and videos.

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.12+ (for manual development)
- Bun 1.2+ or Node.js 20+ (for frontend)
- Redis 7+ (message broker + cache)

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/juanvictorqwerty/Bob-Digital-Investigator.git
cd Bob-Digital-Investigator

# Copy environment template
cp server/.env.example server/.env

# Edit server/.env with your API keys and configuration
# Then start all services
docker compose up --build
```

Access the application:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Grafana Dashboard**: http://localhost:3001

### Manual Development

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

---

## 📚 Documentation

For detailed documentation, see the [`_docs/`](_docs/) directory:

- **[Architecture Overview](_docs/architecture.md)** — System design, data flow, and component interactions
- **[Tech Stack](_docs/tech-stack.md)** — Detailed technology breakdown
- **[API Reference](_docs/api-reference.md)** — All API endpoints with examples
- **[Pipeline Documentation](_docs/pipeline.md)** — Full 5-stage analysis pipeline
- **[Configuration Guide](_docs/configuration.md)** — Environment variables and API keys setup
- **[Deployment Guide](_docs/deployment.md)** — Docker deployment and production setup
- **[Module Documentation](_docs/modules.md)** — Detailed module and code structure
- **[Monitoring Setup](_docs/monitoring.md)** — Prometheus and Grafana configuration
- **[Contributing Guide](_docs/contributing.md)** — Development guidelines and workflow

---

## 🔑 Required API Keys

| Service | Required | Purpose |
|---------|----------|---------|
| **OpenWebNinja** | ✅ | Reverse image search |
| **OpenRouter** | ✅ | LLM analysis (GPT-4o, Claude) |
| **Cloudinary** | ✅ | Image hosting and CDN |

See [Configuration Guide](_docs/configuration.md) for setup instructions.

---

## 🧪 Testing

```bash
# Run all tests
docker compose exec django python manage.py test

# Run client tests
cd client && bun test
```

---

## 📄 License

This project is open source. See the [LICENSE](LICENSE) file for details.

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