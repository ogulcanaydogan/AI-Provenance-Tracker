# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Global error handler with structured JSON error responses and request IDs
- `docs/API.md` — comprehensive API reference with rate limits, error codes, and batch best practices; extended with previously undocumented endpoints: streaming text detection (SSE), detailed analysis, Stripe webhook, and full X-intelligence scheduler/drilldown/report; added `X-Billing-Webhook-Secret` to the request-headers table
- `SECURITY.md` — responsible disclosure policy and security contact; refreshed for v1.x support matrix, GitHub private vulnerability advisories alongside email reporting, expanded in-scope surface (webhook signatures, SSE streaming, plan-quota logic, X-intel pipeline), production security controls section, and least-privilege contributor guidance
- `CHANGELOG.md` — structured change tracking
- `.github/dependabot.yml` — automated dependency updates for pip, npm, and GitHub Actions
- `.github/CODEOWNERS` — required reviewers for critical paths
- `.pre-commit-config.yaml` — ruff, eslint, and secret scanning hooks
- Automated accessibility audit via `@axe-core/playwright` (`frontend/e2e/accessibility.spec.ts`) scanning 7 routes at WCAG 2.1 A/AA tags; current threshold rejects only `critical` severity violations, providing a regression gate without blocking on pre-existing `serious`/`moderate` findings that future remediations will address
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

- Evaluation endpoint test (`test_evaluation_endpoint_returns_registered_reports`) no longer time-bombs: seeded report now uses a relative timestamp 30 days back so it stays inside the rolling 90-day evaluation window regardless of when the test runs.
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
