# Public Benchmark Data Statement (v2.0)

## Purpose
This benchmark provides a reproducible, detector-backed baseline for:
1. AI-generated vs human detection (multi-domain)
2. Source attribution (heuristic model-family baseline)
3. Tamper robustness under paraphrase/translation/human edit
4. Audio AI-vs-human detection (**experimental**)
5. Video AI-vs-human detection (**experimental**)

## Included files
- `detection_multidomain.jsonl` (675)
- `source_attribution.jsonl` (300)
- `tamper_robustness.jsonl` (375)
- `audio_detection.jsonl` (75, experimental)
- `video_detection.jsonl` (75, experimental)

Total rows: **1500**

## Schema
### Shared fields (live benchmark input)
- `sample_id` (string)
- `task` (string)
- `domain` (string)
- `label_is_ai` (0 or 1)
- `modality` (`text|image|audio|video`)
- `input_ref` (repo-relative sample path or URL)

### Optional fields
- `transform` (`clean|paraphrase|translate|human_edit`) for tamper robustness
- `source_model_family` for source attribution ground truth
- `predicted_model_family_baseline` for heuristic attribution baseline output
- `data_origin` (`synthetic|public_human|transformed`)
- `generator_id` (synthetic lineage hint)
- `license_ref` (public content license reference)

## Sampling notes
- This is a public seed corpus for transparent CI/evaluation plumbing, not a population-representative internet sample.
- Dataset growth from 500 -> 1000 -> 1500 uses controlled augmentation metadata (`transform`) plus provenance metadata (`data_origin`, `generator_id`, `license_ref`) to increase coverage while preserving reproducible references.
- Audio/video coverage remains intentionally small and marked experimental.
- Attribution is currently heuristic and should be interpreted as a baseline, not forensic proof.

## Known limitations
- **Sampling bias**: domains and writing/media styles are not fully representative.
- **Domain skew**: some domains/modalities are overrepresented.
- **Label noise risk**: weak labels and synthetic generation assumptions can introduce error.
- **External validity limits**: real-world adversarial content may differ significantly from benchmark samples.
- **Provider availability**: external provider outages and missing C2PA manifests affect comparability.

## Safety and intended use
- Use results for trend tracking, regression detection, and engineering validation.
- Do not use benchmark scores as legal evidence or as a sole basis for high-stakes decisions.
