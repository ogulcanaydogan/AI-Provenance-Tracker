# Troubleshooting Guide

Common issues and solutions for operating the AI Provenance Tracker.

---

## Model Download Failures

The text detection engine downloads `roberta-base` from Hugging Face on first startup.

**Symptoms:** Slow first request, timeout errors, or `OSError: Can't load tokenizer`.

**Fixes:**

- **Firewall/proxy:** Ensure outbound HTTPS to `huggingface.co` is allowed.
- **Pre-download:** Set `TRANSFORMERS_CACHE=/app/model_cache` and run `python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('roberta-base')"` during Docker build.
- **Skip ML entirely:** Set `ML_AVAILABLE=False` to rely on heuristic-only detection (lower accuracy but zero model dependencies).
- **Custom model path:** Set `APT_TEXT_DETECTION_MODEL` to a local directory containing the model files.

---

## Database Connection Issues

Default: SQLite at `./data/provenance.db`. Production: PostgreSQL via `asyncpg`.

**Symptoms:** `OperationalError: unable to open database file` or `Connection refused`.

**Fixes:**

- **SQLite permissions:** Ensure the `data/` directory exists and is writable by the app user (`appuser` in Docker).
- **PostgreSQL connection string:** Use `APT_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`.
- **Connection pool exhaustion:** SQLAlchemy async uses a default pool. For high concurrency, tune `pool_size` and `max_overflow` in the engine configuration.
- **Verify connectivity:** `curl http://localhost:8000/health?deep=true` shows database status under `checks.database`.

---

## Redis Unavailability

Redis is **optional**. The app degrades gracefully without it.

**Symptoms:** Health check shows `checks.redis: "unavailable"`. Rate limiter falls back to in-memory.

**Behaviour without Redis:**

- Rate limiting uses in-memory counters (lost on restart).
- No shared state across multiple workers/replicas.
- All detection endpoints continue to function normally.

**When to use Redis:**

- Multi-worker deployments (shared rate limit state).
- Horizontal scaling behind a load balancer.

**Configuration:** `APT_REDIS_URL=redis://host:6379/0`.

---

## Rate Limiting (429 Responses)

The API applies per-IP, per-bucket rate limits with a daily spend cap.

**Symptoms:** `429 Too Many Requests` with `Retry-After` header.

**Checking current limits:**

| Bucket | Config variable | Default |
|--------|----------------|---------|
| Text detection | `APT_RATE_LIMIT_REQUESTS` | 100/60s |
| Media (image/audio/video) | `APT_RATE_LIMIT_MEDIA_REQUESTS` | 40/60s |
| Batch processing | `APT_RATE_LIMIT_BATCH_REQUESTS` | 20/60s |
| Intel collection | `APT_RATE_LIMIT_INTEL_REQUESTS` | 20/60s |
| Daily spend cap | `APT_DAILY_SPEND_CAP_POINTS` | 1000 points |

**Spend cost per operation:** Text=1, Image=3, Audio=4, Video=6, Batch=5, Intel=8.

**Adjustments:** Increase limits via environment variables. Set `APT_DAILY_SPEND_CAP_POINTS=0` to disable the daily cap (not recommended for public-facing deployments).

---

## Browser Extension Connection Issues

The Chrome/Firefox extension connects to the backend API URL stored in local storage.

**Symptoms:** Extension shows "Connection failed" or CORS errors in browser console.

**Fixes:**

- **Verify API is reachable:** Visit `http://your-api-host:8000/` in the browser. You should see a JSON response with `name` and `version`.
- **CORS origin mismatch:** Add your frontend origin to `APT_ALLOWED_ORIGINS` (comma-separated list). The extension's popup runs from a `chrome-extension://` origin.
- **Configure API URL:** Click the gear icon in the extension popup and enter the correct backend URL.
- **Blocked pages:** The extension cannot extract text from `chrome://`, `edge://`, or `about:` pages.

---

## Provider Timeouts and Fallbacks

External consensus providers (Copyleaks, Reality Defender, Hive, C2PA) have configurable timeouts.

**Symptoms:** Slow detection responses, `consensus.providers[].status: "unavailable"`.

**Configuration:**

| Setting | Default | Description |
|---------|---------|-------------|
| `APT_PROVIDER_TIMEOUT_SECONDS` | 8.0 | Per-provider HTTP timeout |
| `APT_PROVIDER_RETRY_ATTEMPTS` | 3 | Retries before marking unavailable |

**Behaviour:** When a provider times out, it is marked `"unavailable"` in the consensus response but does not block the overall detection. The final score is computed from available providers only.

**Testing provider connectivity:** Check the `consensus.providers` array in any detection response to see per-provider status and rationale.

---

## Log Inspection

The backend uses `structlog` for JSON-formatted structured logging to stdout.

**Viewing logs:**

```bash
# Docker
docker logs ai-provenance-backend

# Filter by severity
docker logs ai-provenance-backend 2>&1 | python3 -m json.tool | grep '"level"'

# Filter by request ID
docker logs ai-provenance-backend 2>&1 | grep "req-abc123"

# Parse with jq
docker logs ai-provenance-backend 2>&1 | jq 'select(.event == "http.request")'
```

**Key log fields:** `event`, `level`, `path`, `status_code`, `duration_ms`, `client_ip`, `request_id`.

---

## Health Check Usage

**Basic check:** `GET /health` returns `{"status": "healthy", "version": "0.1.0"}`.

**Deep check:** `GET /health?deep=true` additionally verifies database and Redis connectivity.

```bash
curl -s http://localhost:8000/health?deep=true | python3 -m json.tool
```

**Status values:**

| Status | Meaning |
|--------|---------|
| `healthy` | All systems operational |
| `degraded` | Database unreachable (Redis unavailability is non-fatal) |

**Load balancer configuration:** Use `/health` (without `?deep=true`) for frequent probes. Use `?deep=true` for readiness checks during deployments.
