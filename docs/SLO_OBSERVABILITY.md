# SLO Observability

This runbook defines operational SLO tracking for production smoke and deploy reliability.

## Signals

Current SLO proxy signals are derived from GitHub workflow outcomes:

1. `Production Smoke Tests` success rate
2. `Deploy Spark Runtime` success rate

These are lightweight and auditable from Actions history.

## Automation

- Workflow: `.github/workflows/slo-observability-report.yml`
- Script: `scripts/slo_observability_report.py`
- Schedule: daily

Artifacts:

- `ops/reports/slo_observability_report.json`
- `ops/reports/slo_observability_report.md`

If alerts are detected and `OPS_ALERT_WEBHOOK_URL` is configured, a webhook payload is sent.

## Local Command

```bash
make slo-report REPO=ogulcanaydogan/AI-Provenance-Tracker GH_TOKEN=$GH_TOKEN
```

## Default SLO Targets

- Smoke success rate SLO: `98%`
- Deploy success rate SLO: `95%`

## Incident Handling

1. If smoke success drops below SLO: investigate health endpoint and detector endpoint failures first.
2. If deploy success drops below SLO: inspect runner availability, SSH connectivity, and image verification stage.
3. Keep deploy and smoke run URLs in incident notes for evidence traceability.
