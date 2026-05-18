# Roadmap

## Current: v1.0.0

Multimodal AI provenance detection platform (text, image, audio, video). Produces explainable evidence cards with provider consensus and benchmark-driven quality gates. Live at whoisfake.com.

---

## v1.1.0 — Audio/Video GA + Accessibility (Q2 2026)

- [ ] Promote audio detector from experimental to stable (confidence calibration complete)
- [ ] Promote video detector from experimental to stable (frame-sampling pipeline hardened)
- [ ] Accessibility audit and remediation for the Next.js frontend (WCAG 2.1 AA)
- [x] Ship deferred docs: `API.md` extended with previously undocumented endpoints (streaming text detection, detailed analysis, Stripe webhook, X scheduler/drilldown/report) and `X-Billing-Webhook-Secret` header. `SECURITY.md` refresh still pending.
- [ ] Dependabot config for automated dependency PRs

**Target branch**: `feature/v1.1.0`

---

## v1.2.0 — Browser Extension GA + Leaderboard (Q3 2026)

- [ ] Firefox extension promoted to stable (currently flagged experimental in manifest)
- [ ] Public benchmark leaderboard auto-refresh (weekly cron already wired, needs leaderboard page)
- [ ] Provider SDK: typed Python client for the detection API
- [ ] Rate-limiting + quotas on the public API

---

## v2.0.0 — Real-Time Streaming Analysis (Q4 2026)

- [ ] WebSocket endpoint for real-time per-chunk provenance analysis in streaming LLM responses
- [ ] REST API v2 with pagination, filtering, and bulk endpoints
- [ ] Evidence card diff: compare two analyses of the same content over time
- [ ] Multi-tenant enterprise mode with isolated evidence chains

---

## Known issues / backlog

See [open issues](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues).
