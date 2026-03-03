# Roadmap Status

Last updated: 2026-03-03 (closure sprint hardening)

## Overall

- Product roadmap in `README.md` is feature-complete (`20/20` checked).
- Credibility-first sprint objectives are implemented and extended with closure hardening.
- Operational rollout remains completed on Spark (self-hosted path + smoke evidence).

## Baseline Lock

- Baseline branch: `main`
- Baseline SHA at sprint start: `1ca7c39`
- `feature/sast-cleanup-a11y-perf` integration: **already merged into main**

## Closure Sprint Status

### 1) Dataset scale-up (500 -> 1000)
- Completed with balanced distribution:
  - detection: 450
  - source attribution: 200
  - tamper robustness: 250
  - audio (experimental): 50
  - video (experimental): 50
- Dataset health gate now enforces this target set in benchmark CI.

### 2) Hybrid cost governance
- `config/cost_policy.yaml` added as policy source of truth.
- `scripts/cost_governance_snapshot.py` now emits:
  - `status` (`ok|warn|block`)
  - `remaining_budget`
  - `policy_version`
- Non-essential workflow gating added for:
  - `Public Provenance Benchmark`
  - `Publish Service Images`
  - `Deploy Spark Runtime`
- Override mechanisms:
  - PR label: `cost-override-approved`
  - Manual dispatch input: `cost_override=true`

### 3) Moderate supply-chain enforcement
- Package policy control added:
  - `config/package_policy.yaml`
  - `scripts/check_package_policy.py`
- Publish pipeline now performs:
  - package policy check (blocking)
  - moderate CVE gate (`critical` fail, `high` warn by default)
  - release provenance note generation (`scripts/generate_release_provenance_note.py`)

### 4) Observability threshold tuning
- Runtime thresholds tuned to reduce false positives:
  - error-rate warn/critical: `3% / 6%`
  - p95 latency warn/critical: `2.0s / 3.5s`
- Updated assets:
  - `deploy/monitoring/prometheus/provenance-alert-rules.yml`
  - `deploy/monitoring/grafana/runtime-observability-dashboard.json`
  - `.github/workflows/slo-observability-report.yml`

### 5) Noise stabilization
- Dependabot changed to weekly rollup mode with lower PR concurrency.
- Vercel comment guard remains soft-fail on `403/404` (no failing noise runs).
- PR template includes explicit noise-control checklist item.

## Operational Evidence (Latest Recorded)

- Multi-arch publish + SBOM+attestation (success): [22226784059](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22226784059)
- Chained deploy dispatch (success): [22227033913](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22227033913)
- Deploy Spark Runtime (success): [22227037725](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22227037725)
- Cost governance run (success): [22226797967](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22226797967)
- SLO observability run (success): [22226797959](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22226797959)

## Remaining Blockers

- None for roadmap closure scope.
- Next stage is evolution track (larger benchmark diversity, stricter supply-chain policy, deeper runtime analytics).
