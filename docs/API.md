# API Reference

> **Base URL:** `https://<your-host>/api/v1`
>
> Interactive docs are available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Authentication

Authentication is **optional** by default. When `REQUIRE_API_KEY=true` is set,
include your key in every request:

```
X-API-Key: your-api-key-here
```

---

## Rate Limits

| Endpoint group  | Requests / minute |
| --------------- | ----------------: |
| Detection       |               100 |
| Media (img/aud) |                40 |
| Batch           |                20 |
| Intel (X/Twitter) |              20 |

Exceeding the limit returns `429 Too Many Requests`. Retry after the
`Retry-After` header value (seconds).

### Spend Control

Each client has a daily spend-point budget (default: 1 000 points).
Costs per operation:

| Operation | Points |
| --------- | -----: |
| Text      |      1 |
| Image     |      3 |
| Audio     |      4 |
| Video     |      6 |
| Batch     |      5 |
| Intel     |      8 |

When the budget is exhausted, the API returns `429` with
`"detail": "daily spend cap exceeded"`.

---

## Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "error": "Bad Request",
  "detail": "Text must be at least 50 characters",
  "status_code": 400,
  "request_id": "a1b2c3d4e5f6",
  "path": "/api/v1/detect/text"
}
```

### Validation Errors (422)

```json
{
  "error": "Validation Error",
  "detail": [
    {
      "field": "body -> text",
      "message": "String should have at least 50 characters",
      "type": "string_too_short"
    }
  ],
  "status_code": 422,
  "request_id": "f6e5d4c3b2a1",
  "path": "/api/v1/detect/text"
}
```

### Common Error Codes

| Status | Meaning                                      |
| ------ | -------------------------------------------- |
| 400    | Invalid input (too short, unsupported type)  |
| 404    | Resource not found                           |
| 413    | File exceeds size limit                      |
| 422    | Request body failed schema validation        |
| 429    | Rate limit or spend cap exceeded             |
| 500    | Internal server error — include `request_id` in bug reports |

---

## Endpoints

### Health Check

```
GET /health
```

Returns `{"status": "healthy", "version": "0.1.0"}`.

---

### Text Detection

```
POST /api/v1/detect/text
Content-Type: application/json
```

**Request body:**

```json
{
  "text": "The text to analyse (50–50 000 characters)."
}
```

**Response (200):**

```json
{
  "analysis_id": "abc123",
  "content_type": "text",
  "verdict": "ai_generated",
  "confidence_score": 0.92,
  "summary": "High confidence AI-generated text detected.",
  "signals": [...],
  "analyzed_at": "2025-06-01T12:00:00Z"
}
```

---

### URL Detection

```
POST /api/v1/detect/url
Content-Type: application/json
```

**Request body:**

```json
{
  "url": "https://example.com/article"
}
```

Fetches the page, extracts visible text, and runs text detection.
Returns the same response shape as text detection.

---

### Image Detection

```
POST /api/v1/detect/image
Content-Type: multipart/form-data
```

**Form field:** `file` — JPEG, PNG, or WebP (max 10 MB).

**Response (200):** Same shape as text detection with additional
`analysis.dimensions` field.

---

### Audio Detection

```
POST /api/v1/detect/audio
Content-Type: multipart/form-data
```

**Form field:** `file` — WAV (max 25 MB).

---

### Video Detection

```
POST /api/v1/detect/video
Content-Type: multipart/form-data
```

**Form field:** `file` — MP4, WebM, MOV, AVI, MKV (max 150 MB).

---

### Batch Text Detection

```
POST /api/v1/batch/text
Content-Type: application/json
```

**Request body:**

```json
{
  "items": [
    {"id": "1", "text": "First sample text..."},
    {"id": "2", "text": "Second sample text..."}
  ],
  "stop_on_error": false
}
```

- Maximum 50 items per batch.
- `stop_on_error`: when `true`, processing halts on the first failure.

**Response (200):**

```json
{
  "results": [...],
  "total": 2,
  "processed": 2,
  "failed": 0
}
```

**Best practices:**

1. Keep batches under 30 items for optimal latency.
2. Set `stop_on_error: false` for fault-tolerant pipelines.
3. Use unique `id` values to correlate results with inputs.

---

### Analysis History

```
GET /api/v1/analyze/history?limit=20&offset=0&content_type=text
```

| Parameter      | Type   | Default | Description              |
| -------------- | ------ | ------- | ------------------------ |
| `limit`        | int    | 10      | Items per page (1–100)   |
| `offset`       | int    | 0       | Pagination offset        |
| `content_type` | string | (all)   | Filter: text/image/audio/video |

---

### History Export

```
GET /api/v1/analyze/history/export?format=csv&content_type=text
```

Returns up to 10 000 records as a downloadable CSV or JSON file.

---

### Dashboard Analytics

```
GET /api/v1/analyze/dashboard?days=14
```

Returns windowed totals, source/type breakdown, top predicted models,
and per-day timeline metrics.

---

### Dashboard Export

```
GET /api/v1/analyze/dashboard/export?days=14&format=csv
```

---

### Aggregate Statistics

```
GET /api/v1/analyze/stats
```

---

### Audit Events

```
GET /api/v1/analyze/audit-events?limit=50&offset=0&event_type=http.request&severity=error
```

---

### Evaluation Metrics

```
GET /api/v1/analyze/evaluation?days=90
```

Returns calibration/evaluation trend data (precision, recall, F1,
recommended thresholds) aggregated across content types.

---

### X (Twitter) Intelligence

```
POST /api/v1/intel/x/collect
```

Triggers collection and analysis of recent posts from configured
X handles. Requires `X_BEARER_TOKEN` to be set.

```
GET /api/v1/intel/x/collect/estimate
```

Estimates API request cost before running a collection.

---

## Request Headers

| Header         | Purpose                              |
| -------------- | ------------------------------------ |
| `X-API-Key`    | API authentication (when enabled)    |
| `X-Request-Id` | Client-provided correlation ID       |
| `X-Actor-Id`   | Identifies the acting user for audit |

---

## SDK / Client Examples

### Python (httpx)

```python
import httpx

response = httpx.post(
    "https://your-host/api/v1/detect/text",
    json={"text": "Sample text to analyse..."},
    headers={"X-API-Key": "your-key"},
)
result = response.json()
print(result["verdict"], result["confidence_score"])
```

### JavaScript (fetch)

```javascript
const res = await fetch("https://your-host/api/v1/detect/text", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": "your-key",
  },
  body: JSON.stringify({ text: "Sample text to analyse..." }),
});
const data = await res.json();
console.log(data.verdict, data.confidence_score);
```

### cURL

```bash
curl -X POST https://your-host/api/v1/detect/text \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{"text": "Sample text to analyse..."}'
```
