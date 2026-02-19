# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Global error handler with structured JSON error responses and request IDs
- `docs/API.md` — comprehensive API reference with rate limits, error codes, and batch best practices
- `SECURITY.md` — responsible disclosure policy and security contact
- `CHANGELOG.md` — structured change tracking
- `.github/dependabot.yml` — automated dependency updates for pip, npm, and GitHub Actions
- `.github/CODEOWNERS` — required reviewers for critical paths
- `.pre-commit-config.yaml` — ruff, eslint, and secret scanning hooks
- Frontend accessibility improvements: ARIA labels, roles, live regions on all detect and history pages
- Detect page UX: file size limit hints, beta badges on audio/video detection
- Next.js bundle analyzer integration via `ANALYZE=true` environment variable

### Changed

- Dashboard and history pages now include CSV/JSON export buttons
- History endpoint accepts optional `content_type` filter parameter
- OpenAPI docs enriched with tag descriptions and request examples
- Docker services use health checks and `restart: unless-stopped` policies
- `depends_on` conditions upgraded to `service_healthy` in all compose files

### Fixed

- Removed obsolete `version` key from `docker-compose.yml`

## [0.1.0] — 2025-06-01

### Added

- Multi-modal AI content detection: text, image, audio, video
- Batch text analysis endpoint with `stop_on_error` control
- URL-based text detection with HTML extraction
- Provider consensus layer (internal model, Copyleaks, Reality Defender, C2PA)
- Analysis history with pagination
- Dashboard analytics with windowed statistics and timeline
- Audit event logging and HTTP request tracking
- Evaluation/calibration trend metrics
- X (Twitter) intelligence pipeline with cost estimation
- Scheduled collection with spend guards and webhook delivery
- React/Next.js frontend with landing page, detection UI, history, and dashboard
- Docker Compose configurations for development and Spark deployment
- CI/CD pipelines: lint, test, deploy (Railway/Spark SSH)
- Terraform IaC for Railway infrastructure
- Public benchmark suite with leaderboard
- `CONTRIBUTING.md` contributor guide with DCO sign-off
- SEO metadata, Open Graph tags, custom 404 page
