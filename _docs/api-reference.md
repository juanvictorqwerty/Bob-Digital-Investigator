# API Reference

Base URL: `http://localhost:8000` (development) or your production domain

All authenticated endpoints require an `Authorization: Token <token>` header.

---

## Authentication

### Register a new user

```http
POST /auth/register/
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "token": "abc123..."
}
```

### Login

```http
POST /auth/login/
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure_password_123"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "token": "abc123..."
}
```

---

## Reverse Image Search

### Upload image and start analysis

```http
POST /api/reverse-search/
```

**Headers:**
```
Authorization: Token <your_token>
Content-Type: multipart/form-data
```

**Request Body (form-data):**
```
image: <file>
claim: "Optional claim text to verify" (optional)
```

**Response (202 Accepted):**
```json
{
  "task_id": "celery-task-uuid",
  "status": "processing",
  "message": "Reverse search pipeline started"
}
```

### Get real-time progress (SSE)

```http
GET /api/reverse-search/progress/<task_id>/
```

**Headers:**
```
Authorization: Token <your_token>
Accept: text/event-stream
```

**Response (Server-Sent Events):**
```
event: progress
data: {"status": "processing", "stage": "search", "progress": 25, "message": "Searching for image..."}

event: progress
data: {"status": "processing", "stage": "process", "progress": 50, "message": "Processing results..."}

event: progress
data: {"status": "processing", "stage": "analyze", "progress": 75, "message": "Running AI analysis..."}

event: complete
data: {"status": "completed", "result_id": 123}
```

### List search history

```http
GET /api/reverse-search/history/
```

**Headers:**
```
Authorization: Token <your_token>
```

**Response (200 OK):**
```json
[
  {
    "id": 123,
    "created_at": "2025-01-15T10:30:00Z",
    "image_url": "https://res.cloudinary.com/...",
    "claim": "Optional claim text",
    "verdict": "likely",
    "confidence": 0.75,
    "source_count": 15,
    "has_research": false
  }
]
```

### Get specific search result

```http
GET /api/reverse-search/history/<id>/
```

**Headers:**
```
Authorization: Token <your_token>
```

**Response (200 OK):**
```json
{
  "id": 123,
  "created_at": "2025-01-15T10:30:00Z",
  "image_url": "https://res.cloudinary.com/...",
  "claim": "Optional claim text",
  "verdict": "likely",
  "confidence": 0.75,
  "explanation": "Multiple credible sources suggest...",
  "key_evidence": ["Evidence 1", "Evidence 2"],
  "timeline": [...],
  "statistics": {...},
  "sources": [...],
  "has_research": false
}
```

### Update result alias

```http
PATCH /api/reverse-search/history/<id>/
```

**Headers:**
```
Authorization: Token <your_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "alias": "My custom label for this search"
}
```

**Response (200 OK):**
```json
{
  "id": 123,
  "alias": "My custom label for this search",
  ...
}
```

---

## Research (Discover)

### Generate research report

```http
POST /api/discover/generate/
```

**Headers:**
```
Authorization: Token <your_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "analysis_id": 123
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "celery-task-uuid",
  "status": "processing",
  "message": "Research generation started"
}
```

### Get research progress (SSE)

```http
GET /api/discover/progress/<task_id>/
```

**Headers:**
```
Authorization: Token <your_token>
Accept: text/event-stream
```

**Response (Server-Sent Events):**
```
event: progress
data: {"status": "processing", "stage": "query_generation", "progress": 20, "message": "Generating search queries..."}

event: progress
data: {"status": "processing", "stage": "searching", "progress": 50, "message": "Searching SearXNG..."}

event: progress
data: {"status": "processing", "stage": "compiling", "progress": 80, "message": "Compiling research report..."}

event: complete
data: {"status": "completed", "research_id": 456}
```

---

## Admin

### Django Admin Interface

```http
GET /admin/
```

Access the Django admin interface for managing users, search results, and analysis data.

---

## Metrics

### Prometheus Metrics (Server)

```http
GET /
```

Returns Prometheus metrics in text format.

**Metrics include:**
- `django_http_requests_total` — Total HTTP requests
- `django_http_requests_latency_seconds` — Request latency
- `django_db_queries_total` — Database queries
- `celery_task_total` — Celery task counts
- `celery_task_latency_seconds` — Task execution time

### Prometheus Metrics (Client)

```http
GET /api/metrics
```

Client-side Prometheus metrics.

---

## Error Responses

All endpoints return standard HTTP status codes:

| Status | Meaning |
|--------|---------|
| `200 OK` | Request successful |
| `201 Created` | Resource created |
| `202 Accepted` | Async task started |
| `400 Bad Request` | Invalid request data |
| `401 Unauthorized` | Missing or invalid token |
| `403 Forbidden` | Insufficient permissions |
| `404 Not Found` | Resource not found |
| `500 Internal Server Error` | Server error |

**Error Response Format:**
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

---

## Rate Limiting

Currently no rate limiting is implemented, but it's recommended to:
- Cache responses where possible
- Implement client-side debouncing for uploads
- Use exponential backoff for retries

---

## CORS

Allowed origins (configured in Django settings):
- `http://localhost:3000` (development)
- `http://localhost` (development)
- `http://95.111.225.85` (production)
- Your production domain

---

## Authentication Flow

1. **Register** at `/auth/register/` to create an account
2. **Login** at `/auth/login/` to get a token
3. **Include token** in all subsequent requests:
   ```
   Authorization: Token <your_token>
   ```
4. **Token persists** until user logs out or admin revokes it

---

## SSE (Server-Sent Events) Usage

### JavaScript Example

```javascript
const eventSource = new EventSource(
  'http://localhost:8000/api/reverse-search/progress/task_id/',
  {
    headers: {
      'Authorization': `Token ${token}`
    }
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.progress, data.message);
};

eventSource.addEventListener('complete', (event) => {
  const data = JSON.parse(event.data);
  console.log('Completed!', data.result_id);
  eventSource.close();
});
```

### Axios Example

```javascript
import axios from 'axios';

const response = await axios.get(
  'http://localhost:8000/api/reverse-search/progress/task_id/',
  {
    headers: { 'Authorization': `Token ${token}` },
    responseType: 'stream'
  }
);

response.data.on('data', (chunk) => {
  const lines = chunk.toString().split('\n');
  lines.forEach(line => {
    if (line.startsWith('data:')) {
      const data = JSON.parse(line.slice(5));
      console.log(data);
    }
  });
});