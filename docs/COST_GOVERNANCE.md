# Cost Governance

This runbook defines cost controls for the production toolchain and explains how to avoid accidental quota burn.

## Objectives

1. Keep CI/CD spend predictable.
2. Detect abnormal usage spikes early.
3. Avoid noisy/manual checks by automating weekly snapshots.

## Controls in Place

### Vercel

- Frontend deploy guard is enabled through:
  - `frontend/vercel.json`
  - `frontend/scripts/vercel-ignore.sh`
- Non-frontend commits skip Vercel builds.
- Manual override is possible with `FORCE_VERCEL_BUILD=1`.

### GitHub Actions

- Weekly governance workflow:
  - `.github/workflows/cost-governance.yml`
- Snapshot script:
  - `scripts/cost_governance_snapshot.py`
- Captures 30-day usage proxy:
  - total run count
  - failure rate
  - runtime minutes by workflow

### Optional Vercel Usage Proxy

If configured, the same report tracks deployment volume via Vercel API.

- Secret: `VERCEL_TOKEN`
- Variable: `VERCEL_PROJECT_ID`
- Optional variable: `VERCEL_TEAM_ID`

If these are missing, report continues with GitHub-only metrics.

## Local Commands

```bash
make cost-governance REPO=ogulcanaydogan/AI-Provenance-Tracker GH_TOKEN=$GH_TOKEN
```

Outputs:

- `ops/reports/cost_governance_snapshot.json`
- `ops/reports/cost_governance_snapshot.md`

## Budget Thresholds

Default warning/critical thresholds are set in the script and can be tuned via CLI flags.

- GitHub runtime warning: `1200` minutes (30 days)
- GitHub runtime critical: `2400` minutes (30 days)
- Workflow failure-rate warning: `20%`
- Vercel deployments warning/critical: `120 / 200` (30 days)

## Operational Policy

1. If warning-level alerts appear: reduce deploy churn and retry loops.
2. If critical alerts appear: freeze non-essential deploys until root cause is addressed.
3. Keep `OPS_ALERT_WEBHOOK_URL` configured to receive automated alert payloads.
