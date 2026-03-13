# Benchmark Regression Check

- Generated: `2026-03-13T09:59:59.384496+00:00`
- Baseline snapshot: `/Users/ogulcanaydogan/Desktop/Projects/AI-Portfolio/first_badge/AI-Provenance-Tracker/benchmark/baselines/public_benchmark_snapshot_full.json`
- Current benchmark: `/Users/ogulcanaydogan/Desktop/Projects/AI-Portfolio/first_badge/AI-Provenance-Tracker/benchmark/results/latest/benchmark_results.json`
- Previous benchmark: `n/a`
- Targets config: `/Users/ogulcanaydogan/Desktop/Projects/AI-Portfolio/first_badge/AI-Provenance-Tracker/benchmark/config/benchmark_targets.yaml`
- Target profile: `full_v3`
- Fail reasons: `none`
- Status: `pass`

| Metric | Constraint | Current | Limit | Delta | Source | Result |
| --- | --- | ---: | ---: | ---: | --- | --- |
| tasks.ai_vs_human_detection.f1 | >= | 1.0000 | 0.5400 | +0.4600 | baseline_snapshot | PASS |
| tasks.ai_vs_human_detection.roc_auc | >= | 1.0000 | 0.8200 | +0.1800 | baseline_snapshot | PASS |
| tasks.source_attribution.accuracy | >= | 0.8000 | 0.5200 | +0.2800 | baseline_snapshot | PASS |
| tasks.tamper_detection.robustness_score | >= | 0.9257 | 0.7700 | +0.1557 | baseline_snapshot | PASS |
| tasks.audio_ai_vs_human_detection.f1 | >= | 1.0000 | 0.6200 | +0.3800 | baseline_snapshot | PASS |
| tasks.video_ai_vs_human_detection.f1 | >= | 1.0000 | 0.6200 | +0.3800 | baseline_snapshot | PASS |
| tasks.ai_vs_human_detection.calibration_ece | <= | 0.0007 | 0.0800 | -0.0793 | targets:full_v3 | PASS |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.code | <= | 0.0000 | 0.3000 | -0.3000 | targets:full_v3 | PASS |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.finance | <= | 0.0000 | 0.3000 | -0.3000 | targets:full_v3 | PASS |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.legal | <= | 0.0000 | 0.3000 | -0.3000 | targets:full_v3 | PASS |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.science | <= | 0.0000 | 0.3000 | -0.3000 | targets:full_v3 | PASS |
| generated_at | <= age(h) | 6.64 | 72.00 | -65.36 | freshness_guard | PASS |

## Drift Summary

| Metric | Current | Previous | Delta | Limit | Status |
| --- | ---: | ---: | ---: | ---: | --- |
| tasks.ai_vs_human_detection.calibration_ece | 0.0007 | n/a | n/a | 0.0200 | NO_BASELINE |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.code | 0.0000 | n/a | n/a | 0.0500 | NO_BASELINE |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.finance | 0.0000 | n/a | n/a | 0.0500 | NO_BASELINE |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.legal | 0.0000 | n/a | n/a | 0.0500 | NO_BASELINE |
| tasks.ai_vs_human_detection.false_positive_rate_by_domain.science | 0.0000 | n/a | n/a | 0.0500 | NO_BASELINE |
