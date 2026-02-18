# Frontend (Next.js)

This app is the UI for the AI Provenance Tracker backend.

## Local Development

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open `http://localhost:3000`.

## Required Environment Variable

- `NEXT_PUBLIC_API_URL`: backend base URL used by the browser (for example `http://localhost:8000` or `http://100.80.116.20:8010`).

`NEXT_PUBLIC_*` values are embedded at build time by Next.js, so set this before `npm run build` or Docker image builds.

## Docker

The frontend Dockerfile accepts build-time `NEXT_PUBLIC_API_URL`:

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_URL=http://100.80.116.20:8010 \
  -t ai-provenance-frontend:local \
  ./frontend
```
