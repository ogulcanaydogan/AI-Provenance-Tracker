# Public Benchmark Data Statement (v0.1)

## Purpose
This benchmark provides a reproducible baseline for AI provenance evaluation across three tasks:
1. AI-generated vs human detection (multi-domain)
2. Source attribution (model family classification)
3. Tamper robustness (paraphrase, translation, human edits)

## Included files
- `detection_multidomain.jsonl`
- `source_attribution.jsonl`
- `tamper_robustness.jsonl`

## Schema
### `detection_multidomain.jsonl`
- `sample_id` (string)
- `domain` (string)
- `label_is_ai` (0 or 1)
- `baseline_score` (float, 0..1)
- `source` (string)

### `source_attribution.jsonl`
- `sample_id` (string)
- `true_model_family` (string)
- `predicted_model_family_baseline` (string)

### `tamper_robustness.jsonl`
- `sample_id` (string)
- `base_id` (string)
- `transform` (`clean|paraphrase|translate|human_edit`)
- `label_is_ai` (0 or 1)
- `baseline_score` (float, 0..1)

## Collection and limitations
- This v0.1 dataset is a transparent baseline seed designed for reproducibility and CI.
- It is not a final production corpus and should not be used for legal or high-stakes decisions.
- Scores are baseline outputs for evaluation plumbing and metric tracking.

## Licensing and privacy
- No personal data is included.
- Use only compliant, non-sensitive content when extending these datasets.
