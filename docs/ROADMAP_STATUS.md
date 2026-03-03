# Roadmap Status

Last updated: 2026-03-03 (Benchmark 2.0 sprint wiring + dataset expansion)

## Overall

- Product roadmap in `README.md` is feature-complete (`20/20` checked).
- Credibility-first sprint objectives are implemented and extended with closure hardening.
- Operational rollout remains completed on Spark (self-hosted path + smoke evidence).
- Evolution track active: Benchmark 2.0 profile split and 1500-sample corpus are now in repo.

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

## Evolution Track Status (Benchmark 2.0)

### 1) Dataset scale-up (1000 -> 1500)
- Completed in dataset files with balanced growth:
  - detection: 675
  - source attribution: 300
  - tamper robustness: 375
  - audio (experimental): 75
  - video (experimental): 75
- Optional metadata fields added on new rows:
  - `data_origin`
  - `generator_id`
  - `license_ref`

### 2) PR-lite + Nightly full benchmark profiles
- Added profile configs:
  - `benchmark/config/benchmark_profiles.yaml`
  - `benchmark/config/benchmark_targets.yaml`
- Benchmark runner now supports:
  - `--profile smoke|full`
  - `--profiles-config <path>`
- Dataset health now supports:
  - `--targets-config <path>`
  - `--target-profile smoke_v2|full_v2`
- Workflow routing:
  - PR/push main => smoke profile
  - nightly schedule => full profile
- Baselines split:
  - `benchmark/baselines/public_benchmark_snapshot_smoke.json`
  - `benchmark/baselines/public_benchmark_snapshot_full.json`

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

- Merge commit SHA (closure sprint): `5420984dea938b57f349fa9e8408ec581828e966`
- CI on `main` (success): [22615177023](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22615177023)
- CodeQL on `main` (success): [22615177014](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22615177014)
- Public benchmark on `main` (success): [22615176966](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22615176966)
- Publish service images on `main` (success): [22615176974](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22615176974)
- Manual Deploy Spark Runtime (success): [22615452126](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22615452126)
- Manual deploy verification: `Deploy to Spark` step executed (non-skipped) and smoke test passed in run `22615452126`.

## Remaining Blockers

- No blocker for roadmap closure scope.
- For Benchmark 2.0 acceptance closure, next required evidence:
  - successful PR smoke run with new profile config
  - successful nightly full run with 1500 target enforcement
  - baseline tuning if nightly regression thresholds are too strict
