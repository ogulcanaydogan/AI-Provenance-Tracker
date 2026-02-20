# Roadmap Status

Last updated: 2026-02-20

## Overall

- Product roadmap in `README.md` is feature-complete (`20/20` checked).
- Credibility-first sprint objectives are implemented in code and CI.
- Operational rollout is completed (self-hosted Spark deploy + smoke pass).

## Completed Workstreams

### Workstream 1: Public claim reframe
- `README.md` explicitly marks audio/video as experimental.
- Limitation language is prominent and aligned with probabilistic output.

### Workstream 2: Benchmark v1.0 live mode
- Live scoring benchmark runner is active (`benchmark/eval/run_public_benchmark.py`).
- Dataset contract no longer depends on fixture `baseline_score`.
- Artifacts include:
  - `benchmark_results.json`
  - `scored_samples.jsonl`
  - regression reports
- One-command local benchmark pipeline:
  - `make benchmark-public` (auto-starts local backend when needed).

### Workstream 3: C2PA real verification
- `backend/app/services/c2pa_verifier.py` uses real `c2patool` verification flow.
- Consensus uses manifest/signature state rather than marker heuristics.

### Workstream 4: Reality Defender integration hardening
- Provider mapping and error handling is implemented in consensus engine.
- Contract tests cover success/timeout/error/malformed payload paths.

### Workstream 5: Scientific humility pack
- `docs/METHODOLOGY_LIMITATIONS.md` and benchmark data statement are present.
- README includes explicit do/don't usage guidance for high-stakes contexts.

### Workstream 6: CI/release/evidence
- CI runs live benchmark + regression checks.
- Leaderboard publishing includes `scored_samples.jsonl` artifacts.
- Benchmark outputs include version, dataset hashes, run command, commit SHA, provider matrix.

## Operational Status

### Done
- Spark deploy workflow is implemented with smoke + rollback flow.
- Pinned GHCR image mode is implemented for Spark deploy.
- Self-hosted Spark runner is online with labels: `self-hosted`, `Linux`, `ARM64`, `spark`.
- Runner persistence is configured via `systemd` user service (`github-actions-runner.service`).
- GHCR publish pipeline now builds multi-arch images (`linux/amd64,linux/arm64`).
- GHCR publish pipeline signs backend/worker images with keyless cosign.
- Real production deploy executed on self-hosted runner with pinned images and smoke test success.
- Publish -> deploy chaining is enabled (`.github/workflows/deploy-spark-after-publish.yml`) to auto-dispatch pinned Spark deploy for the same SHA.
- Spark deploy verifies cosign signatures for pinned images before deploy (`verify_signatures=true`).

### Remaining blockers
- None for roadmap completion.
- GitHub-hosted runners still cannot reach private Spark network directly (expected), but this is mitigated by the self-hosted runner path.

## Operational Evidence (Latest)

- Multi-arch publish run (success): [22216976601](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22216976601)
- Deploy Spark Runtime run (success): [22217190173](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22217190173)
- Last successful production deploy commit SHA: `8ced8a9bb491a624018e052bf3229b6a4bb4b2b4`
- Deploy step status: `Deploy to Spark` executed (non-skipped) and passed.
- Smoke status: `Run Spark smoke test` passed (`checks_passed=4/4`).

## Steady-State Next Actions

1. Keep weekly benchmark publish + evidence pack cadence.
2. Keep pinned deploys tied to commit SHA tags and recorded in release notes.
3. Keep runner and token hygiene (periodic rotation, service health checks).

## Evolution Backlog (Priority Order)

1. Cost governance: add Vercel usage budget/alert SOP and monthly spend threshold review.
2. Observability depth: add uptime/error SLO dashboard and alert routing for backend + smoke regressions.
3. Evaluation growth: expand public benchmark dataset toward 1k+ samples with per-domain breakdown and calibration tracking.
4. Supply-chain depth: add SBOM + signed provenance attestation and deploy-time policy checks.
