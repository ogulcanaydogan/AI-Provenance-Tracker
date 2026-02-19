# Development Guide

Quick-start instructions for local development.

---

## Prerequisites

- Python 3.11+ (3.12 recommended)
- Node.js 20+
- Docker & Docker Compose (for Postgres/Redis)
- pre-commit (`pip install pre-commit`)

---

## Local Setup

### 1. Start infrastructure

```bash
docker compose up -d db redis
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Run the API server:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 4. Pre-commit hooks

```bash
pre-commit install
```

---

## Common Commands

### Backend (from `backend/`)

| Command | Description |
|---------|-------------|
| `ruff check .` | Lint Python code |
| `ruff format .` | Auto-format Python code |
| `pytest` | Run tests with coverage (75% threshold) |
| `pytest tests/test_api_endpoints.py -v` | Run a specific test file |
| `pytest -k "test_text"` | Run tests matching a pattern |

### Frontend (from `frontend/`)

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server |
| `npm run build` | Production build |
| `npm run lint` | ESLint check |
| `npm run typecheck` | TypeScript type check (`tsc --noEmit`) |
| `npm test` | Run Vitest unit tests |
| `npm run test:watch` | Run tests in watch mode |

### Docker

| Command | Description |
|---------|-------------|
| `docker compose up -d` | Start all services |
| `docker compose up -d db redis` | Start only infrastructure |
| `docker compose logs -f backend` | Tail backend logs |
| `docker compose down -v` | Stop and remove volumes |

---

## Environment Variables

The backend uses `pydantic-settings` and reads from the environment. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./provenance.db` | Database connection string |
| `REDIS_URL` | *(empty)* | Redis URL; omit to disable caching |
| `DEBUG` | `false` | Enable debug logging |
| `CONSENSUS_ENABLED` | `true` | Enable multi-detector consensus |
| `C2PA_ENABLED` | `true` | Enable C2PA metadata extraction |
| `RATE_LIMIT_REQUESTS` | `100` | Rate limit per minute (general) |

See `backend/app/core/config.py` for the full list.

---

## Running Tests

### Full test suite

```bash
# Backend — 143+ tests, ~78% coverage
cd backend && pytest

# Frontend — 16+ tests via Vitest
cd frontend && npm test
```

### CI-equivalent check

```bash
# Backend lint + test
cd backend && ruff check . && ruff format --check . && pytest

# Frontend lint + typecheck + test + build
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
```

---

## Troubleshooting

### `asyncpg` connection errors

If running without Docker Postgres, the backend falls back to SQLite. Set `DATABASE_URL` explicitly:

```bash
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/provenance
```

### Port conflicts

Backend defaults to `8000`, frontend to `3000`. Use env vars to override:

```bash
BACKEND_PORT=8010 docker compose up -d
```

### Pre-commit hook failures

If `detect-secrets` flags a false positive, regenerate the baseline:

```bash
detect-secrets scan --baseline .secrets.baseline
```

### Frontend type errors

Run `npm run typecheck` to see all TypeScript errors. Fix before committing — CI blocks on type failures.

---

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design, and [docs/API.md](docs/API.md) for the REST API reference.
