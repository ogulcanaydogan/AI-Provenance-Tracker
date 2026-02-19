# Architecture

High-level design of the AI Provenance Tracker platform.

---

## System Overview

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  Next.js 16  │────▶│  FastAPI Backend  (REST API)                │
│  Frontend    │◀────│  ├─ /api/v1/detect/*   (text/image/audio/…) │
│  (React 19)  │     │  ├─ /api/v1/batch/*    (bulk text)          │
│              │     │  ├─ /api/v1/analyze/*   (history, dashboard) │
│              │     │  ├─ /api/v1/intel/*     (X/Twitter intel)    │
│              │     │  └─ /health            (liveness + deep)     │
└─────────────┘     └────────┬─────────────┬───────────────────────┘
                             │             │
                    ┌────────▼──┐   ┌──────▼──────┐
                    │ SQLite /  │   │ Redis       │
                    │ PostgreSQL│   │ (optional)  │
                    └───────────┘   └─────────────┘
                             │
                    ┌────────▼──────────┐
                    │ Background Worker │
                    │ (scheduler, hooks)│
                    └───────────────────┘
```

---

## Backend

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.115 (Python 3.12+) |
| ORM | SQLAlchemy 2 (async) with aiosqlite / asyncpg |
| Validation | Pydantic v2 + pydantic-settings |
| Logging | structlog (JSON structured logging) |
| Task scheduling | APScheduler (in-process) |
| HTTP client | httpx (async) |

### Directory Layout

```
backend/
├── app/
│   ├── api/v1/           # Route modules (detect, batch, analyze, intel)
│   ├── core/             # Settings, constants
│   ├── db/               # SQLAlchemy models, session, base
│   ├── detection/        # Detector logic per modality
│   │   ├── text.py       # Heuristic + ML text classifier
│   │   ├── image.py      # Frequency, artifact, metadata analysis
│   │   ├── audio.py      # Spectral, temporal, formant analysis
│   │   └── video.py      # Container parsing, frame sampling
│   ├── middleware/        # Rate limiter, audit logger, error handlers, cache
│   ├── providers/        # External provider adapters (Copyleaks, Reality Defender, C2PA)
│   └── services/         # Business logic (analysis store, webhooks, scheduler)
├── scripts/              # Calibration, evidence export utilities
└── tests/                # pytest-asyncio test suite
```

### Request Pipeline

1. **CORS middleware** — Allow configured origins.
2. **Audit middleware** — Log request metadata (method, path, latency, status) as audit events.
3. **Cache-Control middleware** — Attach caching headers for read-only analytics endpoints.
4. **Rate limiter** (dependency) — Per-client, per-bucket fixed-window rate limiting + daily spend cap.
5. **API key validation** (optional) — Header-based key check.
6. **Route handler** — Executes detection, queries stores, returns JSON.
7. **Global error handlers** — Structured JSON error bodies with request IDs for 4xx/5xx.

### Detection Pipeline

Each modality follows the same pattern:

1. **Input validation** — File type, size limits, content checks.
2. **Internal detector** — Heuristic + statistical analysis (no external API calls).
3. **Provider consensus** — Fan out to external providers (Copyleaks, Reality Defender, C2PA) with configurable weights, timeouts, and retries.
4. **Weighted merge** — Combine provider scores using a weighted average.
5. **Verdict mapping** — Map confidence score to verdict label (human / uncertain / likely AI / AI-generated).
6. **Persist** — Store result in DB with content hash, metadata, and full signal breakdown.
7. **Audit event** — Log `detection.completed` event.
8. **Webhook dispatch** — Optionally deliver event payload to configured webhook URLs.

### Rate Limiting & Spend Control

- **Fixed-window** rate limiting per client per endpoint bucket (text, media, batch, intel, default).
- **Daily spend cap** using a point system — each endpoint has a configurable cost.
- Clients identified by API key or X-Forwarded-For / client IP.
- 429 responses include `Retry-After` header.

### Database

- Default: SQLite with aiosqlite (zero-config for development).
- Production: PostgreSQL with asyncpg (same SQLAlchemy models).
- **Composite indexes** on `(content_type, created_at)`, `(source, created_at)`, `(event_type, created_at)`, `(actor_id, created_at)`, `(severity, created_at)` for efficient filtered queries.
- Automatic cleanup: oldest records pruned when exceeding `max_items` threshold.

---

## Frontend

### Technology Stack

| Layer | Technology |
|-------|-----------|
| Framework | Next.js 16 (App Router) |
| UI | React 19, Tailwind CSS 4 |
| Icons | lucide-react |
| File upload | react-dropzone |
| Utilities | clsx, tailwind-merge |

### Directory Layout

```
frontend/src/
├── app/
│   ├── page.tsx              # Landing page
│   ├── layout.tsx            # Root layout (Inter font, SEO metadata)
│   ├── error.tsx             # Global error boundary
│   ├── loading.tsx           # Global loading skeleton
│   ├── not-found.tsx         # 404 page
│   ├── detect/
│   │   ├── text/page.tsx     # Text detection UI
│   │   ├── image/page.tsx    # Image detection UI
│   │   ├── audio/page.tsx    # Audio detection UI (beta)
│   │   └── video/page.tsx    # Video detection UI (beta)
│   ├── history/
│   │   ├── page.tsx          # Analysis history with filtering + export
│   │   ├── loading.tsx       # History skeleton
│   │   └── error.tsx         # History error boundary
│   └── dashboard/
│       ├── page.tsx          # Analytics dashboard
│       ├── loading.tsx       # Dashboard skeleton
│       └── error.tsx         # Dashboard error boundary
├── components/
│   └── detection/            # Shared UI components (TextInput, ImageUpload, etc.)
└── lib/
    ├── api.ts                # API client (fetch wrappers)
    ├── types.ts              # TypeScript interfaces
    ├── constants.ts          # Verdict labels, colours
    └── utils.ts              # Formatting helpers
```

### Security Headers

The Next.js frontend sets the following security headers on all routes:

- **Strict-Transport-Security** — HSTS with 2-year max-age, includeSubDomains, preload.
- **Content-Security-Policy** — Restricts scripts, styles, images, fonts, and connections.
- **X-Frame-Options** — SAMEORIGIN (prevents clickjacking).
- **X-Content-Type-Options** — nosniff.
- **Referrer-Policy** — strict-origin-when-cross-origin.
- **Permissions-Policy** — Disables camera, microphone, geolocation, FLoC.

### Accessibility

- Semantic HTML (`<main>`, `<nav>`, `<section>`).
- ARIA attributes: `aria-labelledby`, `aria-label`, `aria-live="polite"`, `role="status"`, `role="alert"`.
- Decorative icons marked `aria-hidden="true"`.
- Keyboard-navigable pagination and form controls.

---

## Infrastructure

### Docker Compose

Three compose configurations:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local development (backend, frontend, worker, db, redis) |
| `docker-compose.spark.yml` | Spark cluster deployment |
| `docker-compose.ci.yml` | CI/CD pipeline |

All services include health checks and `restart: unless-stopped`.
Dependency ordering uses `condition: service_healthy`.

### CI/CD

- **GitHub Actions** — Lint (ruff), test (pytest), build (Next.js), Docker validation.
- **Dependabot** — Weekly dependency updates for pip, npm, and GitHub Actions.
- **Pre-commit** — ruff formatting/linting, detect-secrets, trailing whitespace.

---

## Observability

- **Structured logging** via structlog (JSON format, correlation IDs).
- **Audit events** persisted to DB — every API request logged with method, path, status, latency, client IP.
- **Health check** — `/health` (liveness) and `/health?deep=true` (DB + Redis connectivity).
- **Dashboard analytics** — Windowed totals, type/source breakdowns, anomaly alerts.
- **Calibration tracking** — Precision/recall/F1 metrics per content type over time.
