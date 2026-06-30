# Monitoring Setup

This guide covers Prometheus metrics collection and Grafana dashboards for Bob Digital Investigator.

---

## Overview

The monitoring stack consists of:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **django-prometheus**: Django metrics integration
- **Client metrics**: Custom Prometheus metrics from Next.js

---

## Architecture

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Django     │────────▶│  Prometheus  │────────▶│   Grafana    │
│   (Port 8000)│  Scrape │  (Port 9090) │  Query │  (Port 3001) │
└──────────────┘         └──────────────┘         └──────────────┘
        ▲                                                │
        │                                                │ Display
        │                                                ▼
┌──────────────┐         ┌──────────────┐
│   Client     │────────▶│  Prometheus  │
│  (Port 3000) │  Scrape │  (Port 9090) │
└──────────────┘         └──────────────┘
```

---

## Prometheus Configuration

### Server Configuration

**File:** `server/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  # Django server metrics
  - job_name: 'django'
    static_configs:
      - targets: ['django:8000']
    metrics_path: '/'

  # Client metrics
  - job_name: 'client'
    static_configs:
      - targets: ['client:3000']
    metrics_path: '/api/metrics'
```

### Scrape Configuration

| Job | Target | Port | Path | Interval |
|-----|--------|------|------|----------|
| django | django:8000 | 8000 | / | 15s |
| client | client:3000 | 3000 | /api/metrics | 15s |

### Starting Prometheus

**With Docker Compose:**
```bash
docker compose up -d prometheus
```

**Access:** http://localhost:9090

---

## Django Metrics

### Enabled Metrics

The `django-prometheus` middleware automatically collects:

#### Request Metrics
- `django_http_requests_total` - Total HTTP requests by method, status, view
- `django_http_requests_latency_seconds` - Request latency histogram
- `django_http_responses_total` - Total HTTP responses

#### Database Metrics
- `django_db_queries_total` - Total database queries
- `django_db_query_duration_seconds` - Query execution time
- `django_db_errors_total` - Database errors

#### Cache Metrics
- `django_cache_hits_total` - Cache hits
- `django_cache_misses_total` - Cache misses
- `django_cache_operations_total` - Cache operations

#### Celery Metrics
- `celery_task_total` - Total tasks by state (pending, started, success, failure)
- `celery_task_latency_seconds` - Task execution time
- `celery_worker_total` - Active workers

### Custom Django Metrics

You can add custom metrics in your Django code:

```python
from django_prometheus.metrics import counter, histogram

# Counter
reverse_searches_total = counter(
    'bob_reverse_searches_total',
    'Total reverse image searches'
)

# Histogram
analysis_duration_seconds = histogram(
    'bob_analysis_duration_seconds',
    'Analysis pipeline duration'
)

# Usage
reverse_searches_total.inc()
with analysis_duration_seconds.time():
    # Your code here
    pass
```

---

## Client Metrics

### Metrics Endpoint

**File:** `client/src/app/api/metrics/route.ts`

**Endpoint:** `GET /api/metrics`

**Metrics Collected:**

#### Page Views
- `bob_page_views_total` - Total page views by route

#### API Calls
- `bob_api_requests_total` - Total API requests by endpoint and status
- `bob_api_request_duration_seconds` - API request duration

#### SSE Connections
- `bob_sse_connections_total` - Total SSE connections
- `bob_sse_messages_total` - Total SSE messages received

#### User Actions
- `bob_uploads_total` - Total image uploads
- `bob_searches_total` - Total reverse searches

### Client Metrics Implementation

**File:** `client/src/lib/metrics.ts`

```typescript
import { Counter, Histogram, Registry } from 'prom-client';

const registry = new Registry();

// Page views
export const pageViews = new Counter({
  name: 'bob_page_views_total',
  help: 'Total page views',
  labelNames: ['route'],
  registers: [registry]
});

// API requests
export const apiRequests = new Counter({
  name: 'bob_api_requests_total',
  help: 'Total API requests',
  labelNames: ['endpoint', 'method', 'status'],
  registers: [registry]
});

// API duration
export const apiDuration = new Histogram({
  name: 'bob_api_request_duration_seconds',
  help: 'API request duration',
  labelNames: ['endpoint'],
  buckets: [0.1, 0.5, 1, 2, 5],
  registers: [registry]
});

// Uploads
export const uploads = new Counter({
  name: 'bob_uploads_total',
  help: 'Total image uploads',
  registers: [registry]
});

// Usage
pageViews.inc({ route: '/reverse-search' });
apiRequests.inc({ endpoint: '/api/reverse-search/', method: 'POST', status: '202' });
apiDuration.observe({ endpoint: '/api/reverse-search/' }, 1.5);
uploads.inc();
```

---

## Grafana Setup

### Accessing Grafana

**URL:** http://localhost:3001

**Default Credentials:**
- Username: `admin`
- Password: `admin` (configured in `.env`)

### First Login

1. Navigate to http://localhost:3001
2. Login with `admin` / `admin`
3. Change password when prompted
4. Add Prometheus data source

### Adding Prometheus Data Source

1. Go to **Connections** → **Data sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Configure:
   - **Name**: Prometheus
   - **URL**: `http://prometheus:9090`
   - **Access**: Server (default)
5. Click **Save & Test**

### Importing Dashboard

**Pre-built Dashboard:** `server/grafana/dashboards/bob-metrics.json`

1. Go to **Dashboards** → **Import**
2. Upload `bob-metrics.json` or paste JSON
3. Select Prometheus data source
4. Click **Import**

---

## Grafana Dashboard

### Dashboard Panels

The pre-built dashboard includes:

#### 1. Search Pipeline Performance
- **Pipeline Duration**: Time per stage (search, process, crawl, analyze)
- **Average Pipeline Duration**: Mean total duration
- **Pipeline Duration Heatmap**: Distribution over time

#### 2. API Throughput
- **Requests per Second**: Total API requests
- **Requests by Endpoint**: Breakdown by endpoint
- **Error Rate**: 4xx and 5xx errors

#### 3. LLM Analysis
- **Verdict Distribution**: Pie chart of verdicts (real, likely, fake, etc.)
- **Average Confidence**: Mean confidence score
- **Verdicts Over Time**: Time series of verdicts

#### 4. Cache Efficiency
- **Cache Hit Rate**: Percentage of cache hits
- **Cache Hits vs Misses**: Comparison
- **Cache Operations**: Total operations by type

#### 5. Worker Status
- **Celery Queue Depth**: Pending tasks
- **Task Success Rate**: Success vs failure
- **Task Duration**: Average task execution time

### Panel Queries

#### Pipeline Duration
```promql
histogram_quantile(0.95, sum(rate(celery_task_latency_seconds_bucket[5m])) by (le, task_name))
```

#### API Throughput
```promql
sum(rate(django_http_requests_total[5m])) by (view)
```

#### Error Rate
```promql
sum(rate(django_http_requests_total{status=~"5.."}[5m])) / sum(rate(django_http_requests_total[5m]))
```

#### Cache Hit Rate
```promql
sum(rate(django_cache_hits_total[5m])) / (sum(rate(django_cache_hits_total[5m])) + sum(rate(django_cache_misses_total[5m])))
```

#### Celery Queue Depth
```promql
celery_task_total{state="pending"}
```

---

## Alerting (Optional)

### Example Alerts

#### High Error Rate
```yaml
groups:
  - name: bob_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(django_http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(django_http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }}%"
```

#### Celery Queue Backup
```yaml
      - alert: CeleryQueueBackup
        expr: celery_task_total{state="pending"} > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Celery queue backup"
          description: "{{ $value }} tasks pending"
```

#### Slow API Response
```yaml
      - alert: SlowAPIResponse
        expr: histogram_quantile(0.95, rate(django_http_requests_latency_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow API response time"
          description: "95th percentile latency is {{ $value }}s"
```

### Setting Up Alerts

1. Create `server/grafana/alerts.yml`:
```yaml
groups:
  - name: bob_alerts
    rules:
      # Add alerts here
```

2. Configure Alertmanager in `prometheus.yml`:
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

3. Restart Prometheus:
```bash
docker compose restart prometheus
```

---

## Logging

### Docker Compose Logs

```bash
# View all logs
docker compose logs -f

# View specific service
docker compose logs -f django
docker compose logs -f celery-worker

# View last 100 lines
docker compose logs --tail=100 django
```

### Log Levels

**Django Logging** (in `settings.py`):
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

### Structured Logging

For production, consider structured logging:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'json': {
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        }
    },
    'root': {
        'handlers': ['json'],
        'level': 'INFO',
    },
}
```

---

## Health Checks

### Django Health Endpoint

Create a health check endpoint:

**File:** `server/_Project/urls.py`
```python
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "healthy"})

urlpatterns = [
    # ... other patterns
    path('health/', health),
]
```

### Health Check Commands

```bash
# Check Django
curl -f http://localhost:8000/health/ || echo "Django unhealthy"

# Check Redis
docker compose exec redis redis-cli ping

# Check PostgreSQL
docker compose exec db pg_isready -U bob

# Check Celery
docker compose exec django python manage.py shell -c "from celery import current_app; print(current_app.control.ping())"
```

---

## Performance Monitoring

### Key Metrics to Track

1. **Pipeline Performance**
   - Average pipeline duration
   - Stage-wise duration
   - Success/failure rate

2. **API Performance**
   - Request rate
   - Response time (p50, p95, p99)
   - Error rate

3. **Database Performance**
   - Query count
   - Query duration
   - Connection pool usage

4. **Cache Performance**
   - Hit rate
   - Miss rate
   - Memory usage

5. **Celery Performance**
   - Queue depth
   - Task duration
   - Worker count
   - Success/failure rate

### Grafana Alerts

Set up alerts for:
- Error rate > 5%
- API latency p95 > 2s
- Celery queue depth > 100
- Cache hit rate < 70%
- Database connection errors

---

## Troubleshooting

### Metrics Not Appearing

```bash
# Check Prometheus targets
curl http://localhost:9090/targets

# Check Django metrics endpoint
curl http://localhost:8000/

# Check client metrics endpoint
curl http://localhost:3000/api/metrics
```

### Grafana Can't Connect to Prometheus

1. Verify Prometheus is running: `docker compose ps prometheus`
2. Check Prometheus URL in Grafana data source
3. For Docker Compose, use service name: `http://prometheus:9090`

### High Cardinality Metrics

If Prometheus is slow:
1. Reduce scrape frequency
2. Filter unnecessary metrics
3. Use metric relabeling
4. Increase retention period carefully

---

## Production Considerations

### Retention

**Prometheus:**
```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# In command line:
# --storage.tsdb.retention.time=30d
```

**Grafana:**
- Dashboard data stored in PostgreSQL or built-in
- Configure retention in Grafana settings

### Scaling

For high-traffic deployments:
- Use Prometheus federation
- Deploy multiple Prometheus instances
- Use Thanos or Cortex for long-term storage
- Scale Grafana with load balancer

### Security

- Enable authentication in Grafana
- Use HTTPS for Prometheus and Grafana
- Restrict access with firewall
- Use secrets for credentials
- Enable audit logging

---

## Useful Queries

### Prometheus Queries

```promql
# Total requests per second
sum(rate(django_http_requests_total[5m]))

# Average request duration
histogram_quantile(0.95, rate(django_http_requests_latency_seconds_bucket[5m]))

# Error rate
sum(rate(django_http_requests_total{status=~"5.."}[5m])) / sum(rate(django_http_requests_total[5m]))

# Cache hit rate
sum(rate(django_cache_hits_total[5m])) / (sum(rate(django_cache_hits_total[5m])) + sum(rate(django_cache_misses_total[5m])))

# Celery task success rate
sum(rate(celery_task_total{state="success"}[5m])) / sum(rate(celery_task_total[5m]))

# Active Celery workers
count(celery_worker_total)
```

### Grafana Variables

Use these variables in dashboard panels:

- `$job`: Job name (django, client)
- `$endpoint`: API endpoint
- `$status`: HTTP status code
- `$verdict`: Analysis verdict
- `$task_name`: Celery task name