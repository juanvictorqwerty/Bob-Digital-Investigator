# Configuration Guide

This guide covers all environment variables, API keys, and configuration options for Bob Digital Investigator.

---

## Environment Variables

All environment variables are defined in `server/.env` (not committed to git).

### Required Variables

#### Database

```env
DB_NAME=bob
DB_USER=bob
DB_PASSWORD=your_secure_password
DB_HOST=db
DB_PORT=5432
```

**Description:**
- `DB_NAME`: PostgreSQL database name
- `DB_USER`: PostgreSQL username
- `DB_PASSWORD`: PostgreSQL password (use strong password in production)
- `DB_HOST`: Database host (use `db` for Docker, `localhost` for manual)
- `DB_PORT`: PostgreSQL port (default: 5432)

#### Django

```env
DJANGO_SECRET_KEY=your_django_secret_key_here
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=your_admin_password
BACKEND_URL=http://localhost:8000
```

**Description:**
- `DJANGO_SECRET_KEY`: Django secret key (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `DJANGO_SUPERUSER_EMAIL`: Admin user email (created on first run)
- `DJANGO_SUPERUSER_PASSWORD`: Admin user password
- `BACKEND_URL`: Backend URL for CSRF trusted origins (e.g., `http://95.111.225.85`)

#### Frontend URLs

```env
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
BACKEND_INTERNAL_URL=http://django:8000
```

**Description:**
- `FRONTEND_URL`: Frontend URL for CORS (e.g., `http://95.111.225.85`)
- `NEXT_PUBLIC_BACKEND_URL`: Backend URL exposed to Next.js (must be public URL)
- `BACKEND_INTERNAL_URL`: Internal Django URL for Docker networking

#### Redis

```env
REDIS_HOST=redis
REDIS_PORT=6379
```

**Description:**
- `REDIS_HOST`: Redis host (use `redis` for Docker, `localhost` for manual)
- `REDIS_PORT`: Redis port (default: 6379)

#### SearXNG

```env
SEARXNG_BASE_URL=http://searxng:8080
```

**Description:**
- `SEARXNG_BASE_URL`: SearXNG instance URL (use `http://searxng:8080` for Docker, `http://localhost:8888` for manual)

#### Nginx

```env
NGINX_PORT=80
```

**Description:**
- `NGINX_PORT`: Nginx port (default: 80, use 8080 for non-root)

---

### Optional Variables

#### Cloudinary (Image Hosting)

```env
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

**Description:**
- `CLOUDINARY_CLOUD_NAME`: Your Cloudinary cloud name
- `CLOUDINARY_API_KEY`: Cloudinary API key
- `CLOUDINARY_API_SECRET`: Cloudinary API secret

**How to get:**
1. Sign up at [cloudinary.com](https://cloudinary.com)
2. Go to Dashboard
3. Copy cloud name, API key, and API secret

**Note:** If not set, images will be stored locally (temporary, not recommended for production)

#### API Keys

```env
OPENROUTER_API_KEY=sk-or-v1-...
REVERSE_IMAGE=ak_...
```

**Description:**
- `OPENROUTER_API_KEY`: OpenRouter API key for LLM analysis
- `REVERSE_IMAGE`: OpenWebNinja API key for reverse image search

**How to get OpenRouter key:**
1. Sign up at [openrouter.ai](https://openrouter.ai)
2. Go to Keys section
3. Create new API key
4. Add credits to your account

**How to get OpenWebNinja key:**
1. Sign up at [openwebninja.com](https://openwebninja.com)
2. Subscribe to reverse image search API
3. Copy API key

#### Monitoring (Grafana)

```env
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
GRAFANA_ROOT_URL=http://localhost/grafana/
```

**Description:**
- `GF_SECURITY_ADMIN_USER`: Grafana admin username
- `GF_SECURITY_ADMIN_PASSWORD`: Grafana admin password (change in production!)
- `GRAFANA_ROOT_URL`: Grafana root URL (e.g., `http://95.111.225.85/grafana/`)

---

## Configuration Files

### Django Settings

**File:** `server/_Project/settings.py`

Key settings:
- `DEBUG`: Enable/disable debug mode (set to `False` in production)
- `ALLOWED_HOSTS`: Allowed hostnames (set to your domain in production)
- `DATABASES`: Database configuration
- `CORS_ALLOWED_ORIGINS`: CORS settings
- `CSRF_TRUSTED_ORIGINS`: CSRF trusted origins
- `CELERY_BROKER_URL`: Redis URL for Celery
- `CACHES`: Redis cache configuration

### Celery Configuration

**File:** `server/_Project/celery.py`

```python
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_TASK_TRACK_STARTED = True
```

### SearXNG Configuration

**File:** `server/searxng_settings.yml`

Custom SearXNG settings for the research feature. This file is mounted into the SearXNG container.

Key settings:
- Search engines enabled
- Rate limiting
- User agent
- Safe search settings

### Trusted Domains

**File:** `server/reversewebsearch/trusted_domains.json`

Curated list of trusted domains for Cameroonian and African sources:

**Categories:**
- **Trusted Domains**: Government domains, international news agencies
- **Certified Facebook Pages**: Official social media pages
- **Government TLDs**: `.gov`, `.gov.cm`, `.gov.ru`, `.gouv.cm`, `.gov.af`
- **Tier-1 News Agencies**: Reuters, AP, AFP, BBC, France24, RFI
- **Tier-1 African News**: Jeune Afrique, Africanews, Cameroon Tribune, CRTV

**To update:**
1. Edit `server/reversewebsearch/trusted_domains.json`
2. Add new domains to appropriate category
3. Commit changes

---

## Docker Compose Configuration

**File:** `docker-compose.yml`

### Services

- **db**: PostgreSQL 17 database
- **redis**: Redis 7 for caching and message broker
- **searxng**: SearXNG metasearch engine
- **django**: Django REST API server
- **celery-worker**: Celery async task worker
- **client**: Next.js frontend
- **prometheus**: Prometheus metrics collector
- **grafana**: Grafana dashboard
- **nginx**: Nginx reverse proxy

### Volumes

- `postgresql_data`: PostgreSQL data persistence
- `redis_data`: Redis data persistence
- `staticfiles`: Django static files
- `prometheus_data`: Prometheus metrics storage
- `grafana_data`: Grafana dashboard storage

### Networks

- `bob-network`: Bridge network for all services

---

## Environment Variable Precedence

Docker Compose uses the following precedence (highest to lowest):

1. **Environment variables** set in shell
2. **`.env` file** in project root
3. **`env_file` directive** in docker-compose.yml
4. **Default values** in docker-compose.yml (`${VAR:-default}`)

**Example:**
```yaml
environment:
  DB_HOST: db  # Overrides .env if set
  DB_PORT: "5432"
```

---

## Production Configuration Checklist

### Security

- [ ] Set `DEBUG=False` in Django settings
- [ ] Use strong `DJANGO_SECRET_KEY` (generate new one)
- [ ] Use strong database password
- [ ] Change `GF_SECURITY_ADMIN_PASSWORD` from default
- [ ] Set `ALLOWED_HOSTS` to your domain only
- [ ] Enable HTTPS (configure in Nginx)
- [ ] Use environment variables for all secrets (never commit .env)

### Performance

- [ ] Set `NGINX_PORT=80` (or 443 for HTTPS)
- [ ] Configure Redis persistence (RDB/AOF)
- [ ] Set up PostgreSQL backups
- [ ] Configure Celery worker concurrency (default: 4)
- [ ] Enable Cloudinary for image storage (CDN)

### Monitoring

- [ ] Set up Grafana admin credentials
- [ ] Configure Prometheus retention period
- [ ] Set up Grafana alerts (optional)
- [ ] Enable Sentry for error tracking (optional)

### API Keys

- [ ] OpenRouter API key with credits
- [ ] OpenWebNinja API key
- [ ] Cloudinary account configured
- [ ] All API keys stored in GitHub Secrets (for deployment)

---

## Common Configuration Issues

### Issue: `BACKEND_URL` not set

**Error:** `django.core.exceptions.ImproperlyConfigured: Set the BACKEND_URL environment variable`

**Solution:** Add `BACKEND_URL=http://localhost:8000` (or your production URL) to `.env`

### Issue: CORS errors

**Error:** `Access-Control-Allow-Origin` mismatch

**Solution:** Ensure `FRONTEND_URL` in `.env` matches your frontend URL exactly (including protocol and port)

### Issue: CSRF verification failed

**Error:** `CSRF verification failed`

**Solution:** Add your backend URL to `CSRF_TRUSTED_ORIGINS` in Django settings or set `BACKEND_URL` in `.env`

### Issue: Celery tasks not running

**Error:** Tasks stuck in `PENDING` state

**Solution:**
1. Check Redis is running: `docker compose logs redis`
2. Check Celery worker is running: `docker compose logs celery-worker`
3. Verify `CELERY_BROKER_URL` is correct

### Issue: Database connection error

**Error:** `could not connect to server`

**Solution:**
1. Check PostgreSQL is running: `docker compose logs db`
2. Verify `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` are correct
3. For Docker: use `DB_HOST=db`
4. For manual: use `DB_HOST=localhost`

---

## Environment Variable Templates

### Development (.env)

```env
# Database
DB_NAME=bob
DB_USER=bob
DB_PASSWORD=changeme
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# SearXNG
SEARXNG_BASE_URL=http://localhost:8888

# Django
DJANGO_SECRET_KEY=dev-secret-key-change-in-production
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=changeme
BACKEND_URL=http://localhost:8000

# Frontend
FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
BACKEND_INTERNAL_URL=http://django:8000

# Nginx
NGINX_PORT=80

# Cloudinary (optional for dev)
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# API Keys
OPENROUTER_API_KEY=
REVERSE_IMAGE=

# Monitoring
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=admin
GRAFANA_ROOT_URL=http://localhost/grafana/
```

### Production (.env)

```env
# Database (use strong passwords!)
DB_NAME=bob_prod
DB_USER=bob_prod
DB_PASSWORD=your_secure_production_password
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# SearXNG
SEARXNG_BASE_URL=http://searxng:8080

# Django (generate new secret key!)
DJANGO_SECRET_KEY=your-generated-secret-key-here
DJANGO_SUPERUSER_EMAIL=admin@yourdomain.com
DJANGO_SUPERUSER_PASSWORD=your_secure_admin_password
BACKEND_URL=http://95.111.225.85

# Frontend
FRONTEND_URL=http://95.111.225.85
NEXT_PUBLIC_BACKEND_URL=http://95.111.225.85
BACKEND_INTERNAL_URL=http://django:8000

# Nginx
NGINX_PORT=80

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# API Keys
OPENROUTER_API_KEY=sk-or-v1-...
REVERSE_IMAGE=ak_...

# Monitoring
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=your_secure_grafana_password
GRAFANA_ROOT_URL=http://95.111.225.85/grafana/
```

---

## Generating Django Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Or using Django shell:
```bash
cd server
python manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"