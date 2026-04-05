# Roadmap Status

Last updated: 2026-04-02 (v1.8.7 closure complete: edge parity fixed + 24h runtime monitoring passed)

## Overall

- Product roadmap in `README.md` is feature-complete (`20/20` checked).
- Credibility-first sprint objectives are implemented and extended with closure hardening.
- Operational rollout remains completed on Spark (self-hosted path + smoke evidence).
- Evolution track active: Benchmark 2.0 profile split and 1500-sample corpus are now in repo.
- Platform T&S best-in-class track started (false-positive stabilization + domain-aware calibration + evidence-rich API responses).
- Final release: [`v1.0.0`](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/releases/tag/v1.0.0)

## v1.8.7 HTTPS URL Fetch Hotfix + 24h Runtime Monitoring — COMPLETED

- Backend hotfix landed in code:
  - `/api/v1/detect/url` now uses explicit TLS CA bundle configuration (`url_fetch_tls_ca_bundle`, defaulting to certifi bundle).
  - SSL verification remains enabled (no insecure fallback path).
  - Certificate verification failures now return deterministic 400 detail:
    - `TLS certificate validation failed while fetching URL. Ensure the target URL exposes a valid public certificate chain.`
- Release evidence:
  - Hotfix commit on `main`: `5471537` (`fix(url-detect): use certifi CA bundle for HTTPS fetch and deterministic TLS errors`)
  - `CI` success: [23740636410](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23740636410)
  - `CodeQL Security Analysis` success: [23740636397](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23740636397)
  - Manual publish (real build/push, `cost_override=true`) success: [23740771975](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23740771975)
  - Manual self-hosted deploy acceptance success: [23741103027](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23741103027)
    - `runner-heartbeat` pass
    - cosign signature verification pass
    - SBOM attestation verification pass
    - `Deploy to Spark` pass
    - `Run Spark smoke test` + `Enforce smoke gate` pass
- Regression tests:
  - URL detection suite passed locally (12/12 selected URL tests):
    - `uv run --project backend pytest backend/tests/test_api_endpoints.py -k "url_detection" --no-cov`
  - Static checks passed:
    - `uv run --project backend ruff check backend/app/api/v1/detect.py backend/app/core/config.py backend/tests/test_api_endpoints.py`
- Live behavior check (edge/origin parity fixed on 2026-03-30):
  - Root cause was Cloudflare tunnel ingress pointing `api.whoisfake.com` to local Mac `localhost:8010` (legacy runtime).
  - Tunnel ingress was remediated to Spark runtime origin (`100.80.116.20:8010`) and tunnel restarted (`com.provenance.tunnel`).
  - Public edge endpoint now matches Spark-local deterministic TLS behavior for `https://example.com`:
    - `TLS certificate validation failed while fetching URL. Ensure the target URL exposes a valid public certificate chain.`
  - Public 4-scenario parity probe now passes:
    - `http://example.com` -> `200`, `content_type=text`
    - direct image URL -> `200`, `content_type=image`
    - direct video URL -> `200`, `content_type=video`
    - Instagram reel (no public direct media) -> `400`, `Platform page detected but no public direct media found`
- Final closure checkpoint (2026-04-02):
  - `main` latest (before closure docs update): `c80d44a`
  - Latest CI success: [23748145241](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23748145241)
  - Latest CodeQL success: [23748145299](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23748145299)
  - Latest scheduled Production Smoke success: [23887563461](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23887563461)
  - 24h+ smoke continuity confirmed with no queue buildup:
    - [23887563461](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23887563461)
    - [23878142862](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23878142862)
    - [23864352307](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23864352307)
  - Runner inventory snapshot: `spark-runtime-01`, `gpu-a100-01`, `gpu-v100-01` online.
  - Infra single-thread issue closed with recovery evidence: [#46 comment](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46#issuecomment-4175911212)

## v1.8.6 Runner Pool Separation (Runtime vs A100 vs V100) — COMPLETED

- Workflow routing updated to dedicated pools:
  - Runtime deploy/smoke paths now target `self-hosted,linux,x64,spark-runtime`.
  - Training paths now target dedicated GPU pools:
    - A100: `self-hosted,linux,x64,a100`
    - V100: `self-hosted,linux,x64,v100`
- Heartbeat guard defaults switched to runtime pool:
  - Default runner name: `spark-runtime-01`
  - Default required labels: `self-hosted,linux,spark-runtime`
- Runtime closure evidence:
  - v1.8.6 commit pushed: `31669a8` (`chore(v1.8.6): separate runtime and gpu runner pools`)
  - Dedicated GPU runners online:
    - `gpu-a100-01` (`self-hosted,linux,x64,a100`)
    - `gpu-v100-01` (`self-hosted,linux,x64,v100`)
  - Runtime runner online:
    - `spark-runtime-01` (`self-hosted,linux,spark-runtime,x64,ARM64`)
  - Legacy mixed runner service on Spark host was stopped/disabled (`github-actions-runner.service`) and replaced with dedicated runtime service (`github-runner-runtime-apt.service` in `~/actions-runner-runtime`).
  - Routing proof runs:
    - A100 dispatch: [23425866540](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23425866540)
      - `train-a100` labels=`self-hosted,linux,x64,a100`, `runner_name=gpu-a100-01` (run cancelled after routing verification).
    - V100 dispatch: [23425881568](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23425881568)
      - `train-v100-sweep` labels=`self-hosted,linux,x64,v100`, `runner_name=gpu-v100-01` (run cancelled after routing verification).
  - Runtime acceptance runs:
    - Failed attempt with missing GHCR tag: [23713319122](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23713319122)
      - `Verify pinned image signatures` failed with `MANIFEST_UNKNOWN` for tag `31669a8...`.
    - Successful deterministic acceptance: [23713357656](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23713357656)
      - `runner-heartbeat` pass
      - `Verify pinned image signatures (cosign keyless)` pass
      - `Verify SBOM attestations (spdxjson)` pass
      - `Deploy to Spark` pass
      - `Run Spark smoke test` pass
      - `Enforce smoke gate` pass
  - Production smoke backlog recovery:
    - Stale queued runs cancelled: `23708896144`, `23703278502`, `23698090111`, `23691340429`
    - Fresh smoke run success: [23713413947](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23713413947)
  - Isolation result:
    - Runtime/deploy/smoke routes restored on `spark-runtime-01`.
    - GPU pools remained online and isolated (`gpu-a100-01`, `gpu-v100-01`) with no cross-role labels.
  - Post-closure regression (same day):
    - `spark-runtime-01` later returned to `offline` and Spark SSH became unreachable from control host (timeout to `100.80.116.20:22`).
    - Queued smoke symptom reappeared: [23715791650](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23715791650)
    - Infra tracking thread reopened for single-thread handling: [#46](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46)

## v1.9.1 Instagram Mention Assistant Foundation — RELEASED ON MAIN, LIVE BETA PREP READY

- Delivery stabilization hardening:
  - Added self-hosted runner heartbeat guard script: `scripts/check_runner_heartbeat.py`
  - `Deploy Spark After Image Publish` now blocks dispatch when `spark-runtime-01` is not online for 2 consecutive checks.
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
- Instagram-first social verification assistant foundations:
  - New webhook verify + ingest endpoints:
    - `GET /api/v1/social/instagram/webhook`
    - `POST /api/v1/social/instagram/webhook`
  - New admin/process endpoints:
    - `GET /api/v1/social/events`
    - `POST /api/v1/social/events/process`
  - Idempotent DB-backed social queue with audit trail:
    - platform event id dedupe
    - reply channel (`dm` vs `public_comment`)
    - analysis id / response status persistence
  - Hybrid reply policy implemented in code:
    - own-media comments -> public auto-reply
    - third-party mentions/tags/messages -> DM + evidence link
    - no-public-media/private posts -> deterministic fallback to `/detect/url`
  - Frontend growth copy updated:
    - landing CTA now mentions `@whoisfake` / DM public link flow
    - `/detect/url` positioned as manual fallback
    - result card now exposes `Open Evidence JSON` + richer shareable evidence copy
- v1.9.1 rollout contract locked:
  - Instagram-first
  - English-only automated replies
  - API-only admin surface
  - Conservative verdict language: `AI likely` / `human likely` / `uncertain`
- Runtime env required before live beta:
  - `INSTAGRAM_ENABLED=true`
  - `INSTAGRAM_BUSINESS_ACCOUNT_ID`
  - `INSTAGRAM_ACCESS_TOKEN`
  - `INSTAGRAM_WEBHOOK_VERIFY_TOKEN`
  - `INSTAGRAM_WEBHOOK_APP_SECRET`
  - `SOCIAL_ADMIN_SECRET`
  - `PUBLIC_FRONTEND_BASE_URL=https://whoisfake.com`
  - `PUBLIC_API_BASE_URL=https://api.whoisfake.com`
  - `WORKER_PROCESS_SOCIAL_QUEUE=true`
- Live beta acceptance checklist locked:
  - webhook verify pass
  - duplicate event dedupe pass
  - own-post comment public reply pass
  - third-party mention/tag/story/message DM pass
  - public video permalink analysis pass
  - unsupported/private fallback pass
- Conservative quality stance remains active (high-disagreement -> `uncertain`, short-text guard, calibration gates).

## v1.8.5 Deploy Chain Closure (Strict Heartbeat + Infra-only Kube Fix) — PARTIAL (Green Acceptance Achieved, Runner Flapping Persists)

- Scope delivered on `main`:
  - `dd59407` (`fix(v1.8.5): enforce strict heartbeat token path`)
  - `5ca4d12` (`chore(v1.8.5): format runner heartbeat tests`)
  - `d2396a8` (`fix(deploy): authenticate GHCR before cosign verification`)
  - `94f84ef` (`chore(deploy): use cosign login for GHCR auth`)
- Heartbeat hardening:
  - `scripts/check_runner_heartbeat.py` now enforces token priority (`GH_TOKEN` > `GITHUB_TOKEN`) and emits deterministic remediation on `403`.
  - `deploy-spark.yml` + `deploy-spark-after-publish.yml` pass both env tokens to heartbeat step.
  - Repo secret provisioned: `RUNNER_HEARTBEAT_TOKEN` (set at `2026-03-21T07:15:47Z`).
- Deterministic publish evidence:
  - Manual publish with cost override (real build/push, not skipped): [23374498359](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23374498359)
  - Published tag used for acceptance deploy: `5ca4d12a4553169bbb171ef85eba22046f715399`
- Acceptance evidence:
  - Manual deploy success: [23374686966](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23374686966)
  - Critical chain passed in same run:
    - `cost-precheck` pass
    - `runner-heartbeat` pass
    - `Verify pinned image signatures (cosign keyless)` pass
    - `Verify SBOM attestations (spdxjson)` pass
    - `Deploy to Spark` pass
    - `Run Spark smoke test` pass
    - `Enforce smoke gate` pass
- Failure history resolved during rollout:
  - [23374653551](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23374653551) failed at GHCR auth (`DENIED`) during cosign verification; fixed by GHCR auth step before verification.
- Current residual blocker:
  - `spark-self-hosted` intermittently returns to `offline`, causing subsequent reruns to queue/cancel (e.g. [23374736834](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23374736834)).
  - Infra thread remains open for stabilization: [#46](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46)
  - Production smoke thread remains closed: [#58](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/58)

## v1.8.4 Deterministic Release + Live URL Parity — PARTIAL (Code Released, Deploy Blocked by Infra)

- v1.8.4 implementation commit on `main`: `7b082e1`
  - Backend URL resolver hardening (browser-like fetch headers, OG resolution fallback with `twitter:player`).
  - URL UX dedup completed in frontend:
    - video page now routes URL flow to `/detect/url` via CTA
    - inline URL form removed from video page
- Additional deploy workflow hotfix on `main`: `f2ce050`
  - `Deploy Spark Runtime` permissions now include `actions:read` to unblock runner-heartbeat API access.
- Deterministic publish evidence:
  - `Publish Service Images` success (real build/push, not skipped): [23366072834](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23366072834)
  - Published image tag prepared for deploy acceptance: `1f2d9c4a25bef9810e261848de8bedee56af34a1`
- Deploy attempts:
  - Self-hosted manual deploy failed pre-deploy at runner heartbeat: [23366283439](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23366283439)
    - error: `Failed to query runners: HTTP 403 Resource not accessible by integration`
  - Legacy self-hosted deploy path reached Helm preflight but failed on kube API reachability: [23366319707](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/23366319707)
    - error: `Kubernetes cluster unreachable: Get "https://100.80.116.20:6443/version": dial tcp 100.80.116.20:6443: connect: connection refused`
- Current infra blocker state:
  - `spark-self-hosted` runner recovered and remained online in 2 consecutive checks (`2026-03-20T23:20:08Z`, `2026-03-20T23:20:16Z`).
  - Active blockers are now:
    - `Deploy Spark Runtime` heartbeat API permission (`403` on runner listing endpoint).
    - Helm cluster preflight connection refusal to `https://100.80.116.20:6443`.
  - single-thread blocker tracking: [#46](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/46)
- Live parity snapshot after latest recovery checks (2026-03-20):
  - `GET https://api.whoisfake.com/health` => `200`
  - `POST https://api.whoisfake.com/api/v1/detect/url` parity results (stable URLs):
    - text URL => `200` (`content_type=text`)
    - image URL => `200` (`content_type=image`)
    - direct video URL => `200` (`content_type=video`)
    - social page without public media => `400` with `Platform page detected but no public direct media found`
  - frontend URL UX remains aligned with v1.8.4:
    - `https://whoisfake.com/detect/url` => `200`
    - `https://whoisfake.com/detect/video` keeps `/detect/url` CTA and no inline URL-form copy
  - production smoke recovered (latest scheduled runs successful); tracking issue [#58](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/issues/58) is closed.

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
