# Cost Governance

This runbook defines cost controls for CI/CD spend and monthly budget protection.

## Objectives

1. Keep CI/CD spend predictable under a monthly cap.
2. Detect abnormal usage spikes early.
3. Block non-essential workflows when budget risk reaches block threshold.
4. Allow explicit override for urgent operational runs.

## Controls in Place

### Policy file (source of truth)

- `config/cost_policy.yaml`
- Required fields:
  - `monthly_cap_usd`
  - `warn_threshold_pct`
  - `block_threshold_pct`
  - `override_label`
  - `non_essential_workflows`
  - `cost_model.github_actions_usd_per_minute`
  - `cost_model.vercel_usd_per_deployment`

### Snapshot + status computation

- Workflow: `.github/workflows/cost-governance.yml`
- Script: `scripts/cost_governance_snapshot.py`
- Schedule: daily (`05:20 UTC`) + `workflow_dispatch`

Snapshot outputs now include:

- `status` (`ok|warn|block`)
- `remaining_budget`
- `policy_version`
- `budget.estimated_spend_usd`
- `budget.non_essential_allowed`

### Enforcement behavior (hybrid)

When `status=block`:

- Non-essential workflows are skipped by default.
- Override paths:
  - PR label: `cost-override-approved` (for PR workflows)
  - `workflow_dispatch` input: `cost_override=true` (for manual runs)

## Non-essential workflows

Defined in `config/cost_policy.yaml`:

- `Public Provenance Benchmark`
- `Publish Service Images`
- `Deploy Spark Runtime`

## Optional Vercel usage proxy

If configured, report also tracks Vercel deployment volume.

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

## Operational Policy

1. `warn`: reduce deploy churn, investigate retry loops and flaky workflows.
2. `block`: hold non-essential workflows unless explicit override is approved.
3. Keep `OPS_ALERT_WEBHOOK_URL` configured for alert fanout.
4. Record override reason in PR/dispatched run notes for auditability.
