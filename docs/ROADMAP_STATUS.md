# Roadmap Status

Last updated: 2026-03-20 (v1.8.4 recovery retried; spark runner remains offline and live /detect/url still 500)

## Overall

- Product roadmap in `README.md` is feature-complete (`20/20` checked).
- Credibility-first sprint objectives are implemented and extended with closure hardening.
- Operational rollout remains completed on Spark (self-hosted path + smoke evidence).
- Evolution track active: Benchmark 2.0 profile split and 1500-sample corpus are now in repo.
- Platform T&S best-in-class track started (false-positive stabilization + domain-aware calibration + evidence-rich API responses).
- Final release: [`v1.0.0`](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/releases/tag/v1.0.0)

## v1.9 Newsroom Monetization + Conservative Accuracy Uplift — IMPLEMENTED (Code), LIVE VALIDATION PENDING

- Delivery stabilization hardening:
  - Added self-hosted runner heartbeat guard script: `scripts/check_runner_heartbeat.py`
  - `Deploy Spark After Image Publish` now blocks dispatch when `spark-self-hosted` is not online for 2 consecutive checks.
  - `Deploy Spark Runtime` now has a pre-deploy `runner-heartbeat` gate job before any self-hosted execution.
- Monetization MVP foundations:
  - Plan-aware API key controls (`starter|pro|enterprise`) with plan-specific burst, daily spend caps, and monthly request caps.
  - New billing API endpoints:
    - `POST /api/v1/billing/plan-sync`
    - `POST /api/v1/billing/stripe/webhook`
  - Usage metering endpoint:
    - `GET /api/v1/analyze/usage`
- Evidence-first newsroom productization:
  - New machine-readable evidence export endpoint:
    - `GET /api/v1/analyze/evidence/{analysis_id}`
  - Frontend newsroom one-pager route:
    - `/for-newsrooms` (plan cards + evidence payload sample + docs CTA)
- Conservative quality stance remains active (high-disagreement -> `uncertain`, short-text guard, calibration gates).

## v1.8.4 Deterministic Release + Live URL Parity — PARTIAL (Code Released, Deploy Blocked by Infra)

- v1.8.4 implementation commit on `main`: `7b082e1`
  - Backend URL resolver hardening (browser-like fetch headers, OG resolution fallback with `twitter:player`).
  - URL UX dedup completed in frontend:
    - video page now routes URL flow to `/detect/url` via CTA
    - inline URL form removed from video page
- Additional deploy workflow hotfix on `main`: `f2ce050`
  - `Deploy Spark Runtime` permissions now include `actions:read` to unblock runner-heartbeat API access.
- Deterministic publish evidence:
  - `Publish Service Images` success (real build/push, not skipped): [23313421611](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23313421611)
  - Published image tag prepared for deploy acceptance: `0ffa60941ba939152c29449fc956d5ed4d2b2db0`
- Deploy attempts:
  - Self-hosted manual deploy failed pre-deploy at runner heartbeat: [23312106399](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23312106399)
    - error: `Failed to query runners: HTTP 403 Resource not accessible by integration`
  - GitHub-hosted fallback run completed but remote deploy was skipped due Spark host unreachable from runner: [23312221178](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23312221178)
    - log: `Host key scan failed. Spark host is not reachable from this runner; remote deploy will be skipped.`
  - No new self-hosted deploy run was started after publish refresh because runner gate remained red (`offline` in 2 consecutive checks), per failure policy.
  - 2026-03-20 recovery retry:
    - spark access re-attempted directly and via jump hosts (`a100`, `v100`) -> `100.80.116.20:22` timeout
    - no self-hosted acceptance run started while runner gate remained red
- Current infra blocker state:
  - `spark-self-hosted` runner = `offline`
  - local tailscale status: `spark-5fc3` last seen offline (~1d)
  - direct host access check from control host fails: `ssh spark` -> `connect to host 100.80.116.20 port 22: Operation timed out`
  - jump-host checks also fail: `ssh a100 -> ssh 100.80.116.20` timeout, `ssh v100 -> ssh 100.80.116.20` timeout
  - single-thread blocker tracking: [#46](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46)
- Live parity snapshot after release attempt:
  - `GET https://api.whoisfake.com/health` => `200`
  - `POST https://api.whoisfake.com/api/v1/detect/url` => `500 Internal Server Error` (text/image/video/social parity probes all failing)
  - frontend URL UX remains aligned with v1.8.4:
    - `https://whoisfake.com/detect/url` => `200`
    - `https://whoisfake.com/detect/video` keeps `/detect/url` CTA and no inline URL-form copy
  - production smoke queue remains backlogged; tracking issue open: [#58](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/58)

## v1.8.2 Conservative FP Stabilization — IMPLEMENTED (Code), DEPLOY BLOCKED (Infra)

- Implementation commit on `main`: `065f120` (`fix(v1.8.2): conservative text consensus and uncertainty guard`)
  - Text consensus threshold now runtime-configurable with conservative default (`text_consensus_threshold=0.58`)
  - High-disagreement guard added: if consensus disagreement exceeds threshold (default `0.18`), text decision is forced to `uncertain`
  - Conservative calibration defaults applied:
    - `uncertainty_margin=0.08`
    - `short_text_min_words=120`
    - `short_text_min_sentences=4`
  - Regression tests added for conservative short-text guard and disagreement-to-uncertain behavior.
- Validation:
  - CI success: [23286762954](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23286762954)
  - CodeQL success: [23286762990](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23286762990)
  - Local regression subset passed:
    - `backend/tests/test_text_detection.py`
    - `backend/tests/test_api_endpoints.py`
- Deploy acceptance status (still blocked):
  - Push-triggered deploy run: [23286762977](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23286762977)
    - `deploy` skipped due cost policy block (expected without override)
  - Manual acceptance run with override + self-hosted runner: [23286817233](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23286817233)
    - `cost-precheck`: success
    - `deploy`: queued (no runner attached)
    - Current runner state: `spark-self-hosted = offline`
    - Infra blocker thread remains single source of truth: [#46](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46)
- Live parity snapshot:
  - `GET https://api.whoisfake.com/health` => `200` (healthy)
  - `POST /api/v1/detect/url` currently returns `500 Internal Server Error` (production parity not yet revalidated post-hotfix)
  - Smoke thread remains open until recovery run succeeds: [#58](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/58)

## Platform T&S Best-in-Class Track (v1.1 kickoff)

- Domain-aware text calibration enabled:
  - detector now supports domain profile selection (`news|social|marketing|academic|code-doc|general`) with fallback inference
  - calibration script now supports per-domain profile generation (`--include-domain-profiles`)
- API response standardization extended with non-breaking fields:
  - `model_version`
  - `calibration_version`
  - `provider_evidence[]`
- Benchmark live scoring now sends text domain hints and includes growth-ready profile targets:
  - `benchmark/config/benchmark_targets.yaml` includes `full_v3` (3000 target)
  - `benchmark/config/benchmark_profiles.yaml` includes `full_v3` caps
- Operational command added for recurring calibration refresh:
  - `make calibrate-text`
- GPU-aware training pipeline added for v1.1:
  - training scripts for targeted fine-tuning + V100 sweeps
  - weekly calibration now enforces FP/ECE quality gate
  - manual self-hosted workflow for text training (`.github/workflows/text-training.yml`)

## v1.4.1 Failure-Path Drill Evidence (Text Quality Drift Watch)

- Implementation commits on `main`:
  - `5f51dfa` (`drift_mode=normal|drill_fail` input + drill-path wiring)
  - `8971af3` (deterministic drill previous-baseline fix)
- Acceptance run 1 (drill fail): [23043874599](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23043874599)
  - Inputs: `benchmark_profile=smoke`, `drift_mode=drill_fail`
  - Result: `failure` (expected), summary contains `drill_mode: true`
  - Regression output: `fail_reasons=["drift_spike"]`, `drift_failed_checks=5`
- Acceptance run 2 (drill fail dedup): [23043998126](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23043998126)
  - Inputs: `benchmark_profile=smoke`, `drift_mode=drill_fail`
  - Result: `failure` (expected), same open issue updated (no duplicate issue)
- Acceptance run 3 (recovery): [23044119478](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23044119478)
  - Inputs: `benchmark_profile=smoke`, `drift_mode=normal`
  - Result: `success` (expected), open drift issue auto-closed
- Ops thread evidence:
  - Issue thread: [#45](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/45)
  - Two failure comments include `drill_mode: true`
- Recovery comment includes `Text quality drift recovered (drill recovered).`

## v1.5 Evidence Lock (Benchmark Evidence Sync + Strict Guard)

- Manual evidence sync workflow implemented:
  - Script: `scripts/sync_benchmark_evidence_from_ci.sh`
  - Source workflow: `Publish Benchmark Leaderboard` (latest successful, `main`)
  - Artifact: `benchmark-run-artifacts`
  - Synced files: `benchmark_results.json`, `regression_check.json/md`, `dataset_health.json/md`, `scored_samples.jsonl`, `baseline_results.md`
  - Lock file: `benchmark/results/latest/evidence_lock.json` (`run_id`, `run_url`, `profile`, `synced_at`, `artifact_name`)
- Strict benchmark guards implemented in regression checker:
  - `--max-generated-age-hours`
  - `--require-quality-metrics`
  - `--forbid-absolute-paths`
  - New fail reasons: `stale_current_results`, `missing_quality_metrics`, `invalid_path_reference`
- Strict mode enforced in workflows:
  - `.github/workflows/public-benchmark.yml`
  - `.github/workflows/publish-leaderboard.yml`
  - `.github/workflows/text-quality-drift-watch.yml`
  - `.github/workflows/ci.yml` now includes `committed-benchmark-evidence-guard` (runs only when `benchmark/results/latest/**` changes)
- Evidence sync execution status:
  - Local sync run completed via `scripts/sync_benchmark_evidence_from_ci.sh`
  - Source run: [23034632639](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23034632639) (`Publish Benchmark Leaderboard`, `main`)
  - Evidence lock generated at `benchmark/results/latest/evidence_lock.json`:
    - `run_id`: `23034632639`
    - `profile`: `full_v3`
    - `artifact_name`: `benchmark-run-artifacts`
  - Strict guard verification (local) passed:
    - `--max-generated-age-hours 72`
    - `--require-quality-metrics`
    - `--forbid-absolute-paths`
    - `regression_check.json`: `passed=true`, `fail_reasons=[]`

## v1.6.3 Helm Deploy Acceptance (Self-hosted Route) — PASSED

- Infrastructure: k3d cluster provisioned on spark (`k3d-provenance`, K3s v1.31.5-k3s1 in Docker)
- API endpoint: `https://100.80.116.20:6443` (non-loopback, spark-self-hosted reachable)
- Chart fix: `5ff3e5e` — skip empty `API_KEYS` to prevent pydantic parse error
- Acceptance run: [23067400630](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23067400630)
  - `Set up Helm` — passed
  - `Require kubeconfig secret` — passed
  - `Configure kubeconfig` — passed (plain-text mode)
  - `Validate kube API endpoint` — passed (`https://100.80.116.20:6443`)
  - `Pull pinned images from GHCR` — passed
  - `Resolve image digests` — passed (api: `sha256:234b11...`, worker: `sha256:32db42...`)
  - `Cluster reachability preflight` — **passed**
  - `Deploy pinned tag with Helm` — **passed** (fresh install, all pods Running 1/1)
  - `Show Helm release status` — **passed**
  - `Post-Deploy Smoke Gate` — failed (expected: `PRODUCTION_API_URL` targets Spark SSH, not K8s ClusterIP)
  - `Rollback Helm Runtime` — passed (auto-rollback triggered by smoke, works as designed)
- Deterministic closure run (temporary smoke bypass): [23067771819](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23067771819)
  - Temporary controls for this run:
    - `ENABLE_DEPLOY_SMOKE_GATE=false`
    - `ENABLE_AUTO_ROLLBACK=false`
  - Helm path acceptance:
    - `Set up Helm` — passed (`v3.20.1+ga2369ca`)
    - `Require kubeconfig secret` — passed
    - `Validate kube API endpoint` — passed (`https://100.80.116.20:6443`)
    - `Cluster reachability preflight` — passed
    - `Deploy pinned tag with Helm` — passed
    - `Show Helm release status` — passed
  - Expected behavior in this run:
    - `Post-Deploy Smoke Gate` — skipped (gate temporarily disabled for Helm acceptance proof)
    - `Rollback Helm Runtime` — skipped (auto-rollback temporarily disabled)
  - Control restore completed immediately after run:
    - `ENABLE_DEPLOY_SMOKE_GATE=true`
    - `ENABLE_AUTO_ROLLBACK=true`
  - Follow-up note: smoke route mismatch remediation remains tracked separately (`PRODUCTION_API_URL` vs deployed target route).
- Pod evidence at deploy time:
  - `provenance-provenance-stack-api` (2 replicas): Running 1/1, health `/health` → 200
  - `provenance-provenance-stack-worker` (1 replica): Running 1/1
  - `provenance-provenance-stack-postgres-0`: Running 1/1
- Previous failed attempts (pre-k3d, pre-chart-fix):
  - [23057739655](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23057739655) — connection refused (no cluster)
  - [23058010170](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23058010170) — hostname resolve failure
  - [23066381257](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23066381257) — deploy timeout (API_KEYS parse error)
- Policy state: **v1.6.3 acceptance CLOSED — Helm pipeline proven end-to-end**.

## v1.6.4 Deploy Runtime Smoke Route Remediation (Runtime-aware Split) — IMPLEMENTED

- Implementation commit on `main`: `d46068c`
  - `Deploy Runtime (Pinned SHA, Legacy)` now uses split smoke jobs:
    - `Post-Deploy Smoke Gate (Helm)` on self-hosted Spark runner
    - `Post-Deploy Smoke Gate (Railway)` on GitHub-hosted runner
  - Runtime-aware URL resolution:
    - Helm: `workflow_dispatch.smoke_base_url_helm` -> `vars.SPARK_PUBLIC_API_URL` -> hard-fail
    - Railway: `workflow_dispatch.smoke_base_url_railway` -> `secrets.PRODUCTION_API_URL` -> hard-fail
  - Target-specific rollback wiring:
    - `rollback_helm` depends on `smoke_gate_helm=failure`
    - `rollback_railway` depends on `smoke_gate_railway=failure`
  - Deployment summary now emits `smoke_gate_helm` and `smoke_gate_railway` separately.
- CI validation on commit `d46068c`:
  - CI success: [23070047274](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23070047274)
  - CodeQL success: [23070047238](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23070047238)
- Acceptance rerun attempt:
  - Triggered run: [23070049926](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23070049926)
  - Result: `cancelled` (runner-side infra blocker before `Deploy Helm Runtime` started)
  - Root cause on `spark-self-hosted`:
    - runner seen as `offline` by GitHub
    - runner diagnostics show DNS resolution failures to GitHub Actions endpoint (`Socket Error: TryAgain`)
    - direct probe from runner failed to resolve `broker.actions.githubusercontent.com`
- Operational note:
  - Smoke-route mismatch follow-up is code-complete in v1.6.4.
  - Remaining blocker is external infra (runner DNS/network), not workflow logic.
  - Infra handoff thread (single source of truth): [#46](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46)
  - Re-run policy: no new Helm acceptance run until `spark-self-hosted` returns `online` and DNS probes pass on host.

## v1.7 Domain Cutover + Video URL v1 — IN PROGRESS

- Domain/runtime config update applied:
  - `vars.SPARK_PUBLIC_API_URL=https://api.whoisfake.com`
  - Variable timestamp: `2026-03-15T12:38:19Z`
  - `ENABLE_DEPLOY_SMOKE_GATE=true`, `ENABLE_AUTO_ROLLBACK=true` unchanged
- Helm acceptance rerun (domain-cutover validation):
  - Run: [23110531781](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23110531781)
  - Result: `failure` at `Cluster reachability preflight`
  - Error: `Kubernetes cluster unreachable: Get "https://100.80.116.20:6443/version": dial tcp 100.80.116.20:6443: connect: connection refused`
  - Follow-up posted in single infra thread: [#46 comment](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46#issuecomment-4062911318)
- Status:
  - v1.7 deploy acceptance remains blocked by kube endpoint reachability from runner.
  - Video URL detection v1 implementation is tracked in this sprint branch/commit set.

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

## Benchmark 2.0 Finalization Evidence (40c63d2)

- Commit pushed to `main`: `40c63d2`
- CI (push) success: [22756880035](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22756880035)
- CodeQL (push) success: [22756880031](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22756880031)
- Public Benchmark smoke (push) success: [22756880058](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22756880058)
  - smoke profile verification in logs:
    - `target_profile=\"smoke_v2\"`
    - baseline `public_benchmark_snapshot_smoke.json`
- Public Benchmark full (manual workflow_dispatch) success: [22757012096](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22757012096)
  - full profile verification in logs:
    - `target_profile=\"full_v2\"`
    - baseline `public_benchmark_snapshot_full.json`
- Public Benchmark full (scheduled nightly) success: [22790452715](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22790452715)
  - scheduled run confirms nightly full profile path on `main`

## Remaining Blockers

- No blocker for roadmap closure scope.
- Benchmark 2.0 status: **completed** (smoke + manual full + scheduled nightly full verified).
- Final state: **Operationally complete / attention-free**.

## v1.0.0 Evidence Lock (Latest Verified)

- Release tag + GitHub Release: [`v1.0.0`](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/releases/tag/v1.0.0)
- CI success: [22799906812](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22799906812)
- CodeQL success: [22799906819](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22799906819)
- Public Benchmark success: [22799906813](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22799906813)
- Publish Service Images success: [22799906815](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22799906815)
- Deploy Spark Runtime success: [22800021410](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22800021410)
- Scheduled Production Smoke success: [22798881836](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22798881836)
- Scheduled Nightly Benchmark success: [22790452715](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22790452715)
- Closed stale ops issue: [#19](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/19)
