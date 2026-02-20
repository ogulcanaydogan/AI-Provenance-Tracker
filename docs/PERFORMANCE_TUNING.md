# Performance Tuning Guide

Guidance for optimising the AI Provenance Tracker under various workloads.

---

## Hardware Requirements

| Tier | CPU | RAM | Storage | Use Case |
|------|-----|-----|---------|----------|
| Minimum | 2 cores | 4 GB | 10 GB | Development, light API traffic |
| Recommended | 4 cores | 8 GB | 20 GB | Production, moderate traffic |
| High-throughput | 8+ cores | 16 GB | 50 GB | Batch processing, ML models loaded |

**GPU:** Optional. The `torch` and `torchvision` optional dependencies can leverage CUDA for faster ML inference. Set `APT_DEVICE=cuda` if a GPU is available. CPU inference works without GPU but is slower for ML-based detection.

---

## Latency Expectations per Endpoint

Typical response times on recommended hardware (CPU inference):

| Endpoint | p50 | p95 | Notes |
|----------|-----|-----|-------|
| `POST /detect/text` | ~200ms | ~2s | Heuristic-only is fast; ML model adds latency |
| `POST /detect/image` | ~1s | ~5s | Frequency analysis + metadata extraction |
| `POST /detect/audio` | ~3s | ~8s | WAV parsing + spectral analysis |
| `POST /detect/video` | ~5s | ~15s | Entropy + byte analysis on large files |
| `POST /batch/text` | Sum of items | — | Sequential processing within batch |
| `GET /analyze/dashboard` | ~50ms | ~200ms | Database aggregation query |
| `GET /analyze/history` | ~30ms | ~100ms | Paginated query with index |

**First-request warmup:** The first text detection request downloads and loads the ML model (~1-2 GB). Subsequent requests reuse the cached model. Pre-warm by sending a test request at startup.

---

## Database Optimization

### SQLite (Development)

- Single-writer limitation: only one concurrent write at a time.
- Suitable for development and single-instance deployments.
- Run `VACUUM` periodically to reclaim space: `sqlite3 data/provenance.db "VACUUM;"`.

### PostgreSQL (Production)

- Recommended for multi-worker and multi-replica deployments.
- Connection string: `APT_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`.
- Autovacuum is enabled by default; no manual intervention needed for routine operation.
- For high-write workloads, ensure `max_connections` is at least `pool_size * num_workers + overhead`.

### Indexes

The following indexes are created automatically by SQLAlchemy:

| Table | Indexes |
|-------|---------|
| `analysis_records` | `content_type`, `created_at`, `source`, `content_hash`, composite `(content_type, created_at)`, composite `(source, created_at)` |
| `audit_events` | `event_type`, `created_at`, `severity`, `actor_id`, `request_id`, composite `(event_type, created_at)`, composite `(actor_id, created_at)`, composite `(severity, created_at)` |

These cover all query patterns used by the dashboard, history, and audit endpoints.

---

## Redis Caching Strategy

Redis is used for rate limiter state (IP -> hit count maps with TTL expiry).

| Setting | Recommendation |
|---------|---------------|
| Memory | 50-100 MB is sufficient for rate limiting state |
| TTL | Matches `APT_RATE_LIMIT_WINDOW_SECONDS` (default 60s) |
| Eviction policy | `allkeys-lru` for automatic cleanup |

**Without Redis:** Rate limiting falls back to in-memory counters. This works for single-instance deployments but does not share state across replicas.

---

## Batch Processing Optimization

The batch endpoint (`POST /api/v1/batch/text`) processes items sequentially.

| Setting | Default | Description |
|---------|---------|-------------|
| `APT_MAX_BATCH_ITEMS` | 50 | Maximum items per request |

**Recommendations:**

- Optimal batch size: 10-25 items (balances latency vs. throughput).
- For large datasets (1000+ items), split into multiple batch requests.
- Each batch request counts as 5 spend points toward the daily cap.
- Use the streaming endpoint (`POST /detect/stream/text`) for single-item real-time feedback.

---

## Model Inference Tuning

| Setting | Description |
|---------|-------------|
| `TRANSFORMERS_CACHE` | Directory for cached Hugging Face models (default: `~/.cache/huggingface`) |
| `APT_TEXT_DETECTION_MODEL` | Model name or path (default: `roberta-base`) |
| `ML_AVAILABLE` | Set to `False` to skip ML inference entirely |

**Pre-downloading models in Docker:**

```dockerfile
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('roberta-base'); \
    AutoModelForSequenceClassification.from_pretrained('roberta-base')"
```

This eliminates first-request latency in containerised deployments.

---

## Uvicorn Worker Configuration

The backend runs on Uvicorn (ASGI server).

```bash
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --limit-concurrency 100 \
  --timeout-keep-alive 30
```

| Parameter | Recommendation |
|-----------|---------------|
| `--workers` | 2-4 per CPU core for I/O-bound workload |
| `--limit-concurrency` | 50-200 depending on available RAM |
| `--timeout-keep-alive` | 30s (matches typical load balancer timeout) |

**Note:** When using multiple workers with SQLite, only one worker can write at a time. Use PostgreSQL for multi-worker deployments.

---

## Prometheus Metrics

When `APT_ENABLE_PROMETHEUS=true` (default), the `/metrics` endpoint exposes Prometheus-compatible metrics:

- `http_request_duration_seconds` — Request latency histogram
- `http_requests_total` — Total request count by status code and handler
- `http_requests_inprogress` — Currently in-flight requests
- `http_response_size_bytes` — Response payload size

**Scrape configuration:**

```yaml
scrape_configs:
  - job_name: "provenance-tracker"
    scrape_interval: 15s
    static_configs:
      - targets: ["your-api-host:8000"]
    metrics_path: "/metrics"
```

Use these metrics to establish baseline latency SLOs and set alerting thresholds.
