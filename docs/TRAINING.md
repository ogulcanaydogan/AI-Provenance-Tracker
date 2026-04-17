# Text Training Runbook (A100 + V100)

This runbook covers targeted text detector fine-tuning for v1.1 false-positive stabilization.

## Goals

- Reduce `human -> AI` false positives without dropping F1.
- Keep calibration and detector versions reproducible.
- Produce auditable artifacts for release gating.
- Treat the public benchmark as a non-regression sanity set, not the final release gate.

## Benchmark Gate Split (v2.3.1)

- CI smoke benchmark uses `smoke_ci` targets for sanity/non-regression only.
- `smoke_ci` enforces coverage/freshness/shape checks but does not hard-fail on calibration ECE or domain FP.
- Release-grade quality hard-fail remains in:
  - scheduled/manual full benchmark (`full_v3`)
  - private benchmark gate in the assets/ops promotion flow

## Hardware Allocation

- **A100 (single run):** primary fine-tune candidate.
- **V100 pool (x5):** hyperparameter sweep and robustness sweeps.

## Runner Labels (GitHub Actions)

Configure self-hosted GPU runners with explicit labels so the workflow routes correctly:

- A100 host: `self-hosted,linux,x64,a100`
- Each V100 host: `self-hosted,linux,x64,v100`

## Data Preparation

```bash
make build-text-dataset
make build-hard-negatives INCLUDE_FALSE_NEGATIVES=1
```

Outputs:
- `backend/evidence/samples/text_labeled_expanded.jsonl`
- `backend/evidence/samples/text_hard_negatives.jsonl`

## A100 Primary Fine-Tune

```bash
make train-text-a100 FP_PENALTY=1.8 RUN_NAME=v11_text_fp_a100
```

Artifacts:
- `backend/evidence/models/text/<run_id>/model`
- `backend/evidence/models/text/<run_id>/training_manifest.json`
- `backend/evidence/models/text/latest.json`

## V100 Sweep

Dry-run command list:

```bash
make sweep-text-v100
```

Execute sweep:

```bash
make sweep-text-v100 EXECUTE=1
```

Execute one specific V100 profile:

```bash
make sweep-text-v100 EXECUTE=1 PROFILE=v11_fp_sweep_lr25e5_pen18
```

List available sweep profiles:

```bash
python3 backend/scripts/sweep_text_training.py --list-profiles
```

## Post-Training Calibration and Gate

```bash
make calibrate-text MIN_SAMPLES=120 MIN_DOMAIN_SAMPLES=40
make text-quality-gate MAX_FP_RATE=0.08 MAX_ECE=0.08
```

Gate outputs:
- `backend/evidence/calibration/text/quality_gate.json`
- `backend/evidence/calibration/text/quality_gate.md`

Runtime profile now supports:
- domain-aware thresholds
- length-band thresholds (`short-form`, `standard`, `long-form`)
- conservative uncertainty margins

The promoted runtime should pin model and calibration together:
- `TEXT_MODEL_BUNDLE_VERSION`
- `TEXT_CALIBRATION_BUNDLE_VERSION`
- `TEXT_PRIVATE_BENCHMARK_MANIFEST`

## Promote Model

1. Set env var on backend runtime:
   - `TEXT_DETECTION_MODEL_PATH=/absolute/path/to/model`
2. Redeploy backend.
3. Verify:
   - `/api/v1/detect/text` returns updated `model_version`.
   - Weekly calibration workflow remains green.

## Release Gate (v1.1)

- Long-form human FP <= 5%
- Overall FP <= 8%
- ECE < 0.08
- Golden-pair separation >= 60%

For the private moat stack, final release approval additionally requires:
- private hard-negative benchmark pass
- domain FP report
- adversarial rewrite slice report
- model/calibration bundle version pinning
