# Roadmap Status

Last updated: 2026-02-19

## Overall

- Product roadmap in `README.md` is feature-complete (`20/20` checked).
- Credibility-first sprint objectives are implemented in code and CI.
- Remaining items are operational rollout tasks, not missing core features.

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

### Remaining blockers
1. Spark host is not reachable from GitHub-hosted runners in current network layout.
2. Real remote deploy requires either:
   - self-hosted GitHub runner on reachable network, or
   - direct SSH/manual deploy from reachable machine.

## Completion Path (End State)

1. Bring one self-hosted runner online in Spark-reachable network.
2. Run `Deploy Spark Runtime` with:
   - `runner_type=self-hosted`
   - `use_pinned_images=true`
3. Confirm smoke success on public API URL.
4. Keep weekly benchmark publish + evidence pack cadence.
