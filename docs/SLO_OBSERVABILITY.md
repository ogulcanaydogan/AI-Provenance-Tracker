# SLO Observability

This runbook defines two complementary observability tracks:

1. Workflow reliability SLOs (deploy/smoke success rates)
2. Runtime service SLOs (latency/error rate from `/metrics`)

## Signals

### A) Workflow reliability (GitHub Actions history)

1. `Production Smoke Tests` success rate
2. `Deploy Spark Runtime` success rate

### B) Runtime service health (Prometheus metrics)

1. Request error rate (`http_requests_total`, 5xx ratio)
2. p95 latency (`http_request_duration_seconds_bucket`)
3. p99 latency (informational)
4. Top handlers by risk (error-rate/latency)

Health/docs endpoints are excluded from runtime SLO calculations.

## Automation

- Workflow: `/Users/ogulcanaydogan/Desktop/Projects/YaPAY/AI-Provenance-Tracker/.github/workflows/slo-observability-report.yml`
- Scripts:
  - `/Users/ogulcanaydogan/Desktop/Projects/YaPAY/AI-Provenance-Tracker/scripts/slo_observability_report.py`
  - `/Users/ogulcanaydogan/Desktop/Projects/YaPAY/AI-Provenance-Tracker/scripts/runtime_observability_report.py`
- Schedule: daily

Artifacts:

- `ops/reports/slo_observability_report.json`
- `ops/reports/slo_observability_report.md`
- `ops/reports/runtime_observability_report.json` (if `PRODUCTION_API_URL` configured)
- `ops/reports/runtime_observability_report.md` (if `PRODUCTION_API_URL` configured)

Alerting:

- If alerts exist and `OPS_ALERT_WEBHOOK_URL` is configured, webhook payload includes both workflow and runtime alerts.

## Dashboard and Alert Rules

- Grafana dashboard template:
  - `/Users/ogulcanaydogan/Desktop/Projects/YaPAY/AI-Provenance-Tracker/deploy/monitoring/grafana/runtime-observability-dashboard.json`
- Prometheus rules template:
  - `/Users/ogulcanaydogan/Desktop/Projects/YaPAY/AI-Provenance-Tracker/deploy/monitoring/prometheus/provenance-alert-rules.yml`

## Local Commands

Workflow SLO report:

```bash
make slo-report REPO=ogulcanaydogan/AI-Provenance-Tracker GH_TOKEN=$GH_TOKEN
```

Runtime SLO report:

```bash
make runtime-observability API_URL=https://your-api.example.com
```

## Default SLO Targets

Workflow:

- Smoke success rate SLO: `98%`
- Deploy success rate SLO: `95%`

Runtime:

- p95 latency warn threshold: `1.5s` (critical: `3.0s`)
- Error-rate warn threshold: `2%` (critical: `5%`)

## Incident Handling

1. Workflow SLO breach:
   - smoke failures: inspect `/health`, `/api/v1/detect/*`, provider adapters.
   - deploy failures: inspect runner availability, SSH path, image verification.
2. Runtime SLO breach:
   - high error-rate: inspect 5xx logs first, then dependency health (DB/Redis/provider APIs).
   - high latency: inspect p95 by handler and worker saturation (`http_requests_inprogress`).
3. Keep run URLs and generated report artifacts in incident notes for evidence traceability.
