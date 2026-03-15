# CAIS Compute Cluster Application

> **Program:** Center for AI Safety (CAIS) Compute Cluster
> **URL:** https://safe.ai/compute-cluster
> **Apply:** https://airtable.com/appeMGyDPWhtwa3Dw/shrN5XbLE9oBIWVP8
> **Type:** Free compute access (256x A100 80GB GPUs)
> **Cost:** Free
> **Status:** Ready to apply
> **Deadline:** Rolling

---

## Application Details

### Project Name

AI-Provenance-Tracker: Multi-Language AI Content Detection for Press-Restricted Environments

### Research Description

We're training detection classifiers for AI-generated content across five underserved languages: Arabic, Farsi, Russian, Mandarin, and Spanish. Current AI content detectors are almost exclusively English-focused, which means disinformation campaigns targeting non-English populations go largely undetected.

The detection engine covers four modalities (text, image, audio, video) and uses a multi-model consensus approach with explainable scoring. Each detection returns a signal-by-signal breakdown, not just a confidence number.

The specific ML safety connection: detecting AI-generated content is a prerequisite for studying how AI systems are misused. If you can't reliably identify synthetic content in Arabic or Farsi, you can't study the disinformation campaigns that use it. Our models provide the detection ground truth that safety researchers need.

### Compute Requirements

**Training runs (primary need):**
- Fine-tuning RoBERTa-large and XLM-R on language-specific AI-generated text corpora
- Training language-specific detection heads for Jais (Arabic), Yi (Chinese), GigaChat (Russian)
- Estimated: 8x A100 for 48 hours per language, 5 languages = 1,200 GPU-hours
- Batch size: 32, mixed precision (bf16), gradient accumulation 4 steps

**Benchmark runs (secondary):**
- Nightly detection accuracy benchmarks across all supported modalities and languages
- Estimated: 4x A100 for 6 hours per run
- We'd run benchmarks weekly on the cluster, nightly on smaller local hardware

**Voice cloning detection (tertiary):**
- Training audio detection models for non-English speech patterns
- Estimated: 4x A100 for 24 hours per language model
- This is the most compute-intensive component due to spectrogram processing

**Total estimated usage:** ~3,000 GPU-hours over 6 months

### ML Safety Connection

AI-generated disinformation is a direct misuse of frontier models. Our project addresses this by:
1. Building detection infrastructure that works in non-English contexts (where most disinformation goes undetected)
2. Publishing reproducible benchmarks that the safety community can use to evaluate detection progress
3. Releasing all models and training code under MIT license, so other researchers can extend the work

We're not competing with commercial detectors. We're building the open infrastructure layer for AI content detection in languages and environments that commercial tools don't serve.

### Current Status

- v1.0.0 released (March 2026)
- 21 CI/CD workflows, OpenSSF Best Practices PASSING
- English text detection operational with multi-provider consensus
- C2PA verification built in for signed content
- Applied to NLnet NGI Zero, Mozilla Democracy x AI, OTF Internet Freedom Fund
- MIT license, all code public at github.com/ogulcanaydogan/AI-Provenance-Tracker

### Team

Ogulcan Aydogan, software engineer, United Kingdom. Solo maintainer of 10 open source AI security projects. Experience with PyTorch, Transformers, production ML pipelines. The compute cluster would replace our current reliance on donated GPU time, which is unreliable and limits training schedule.

---

## Submission Steps

1. Visit https://airtable.com/appeMGyDPWhtwa3Dw/shrN5XbLE9oBIWVP8
2. Fill application form using content above
3. Specify GPU requirements: 8x A100 for training, 4x A100 for benchmarks
4. Wait for response (no specified timeline)
5. Update TRACKING.md and master tracker

---

## Notes

- Cluster: 256x A100 GPUs, 80GB memory, 1,600 Gbit/s inter-node
- "Primarily aimed at professors and their research teams, though others are also welcome to apply"
- No cost, no overhead to manage
- If accepted, we'd have reliable compute for the multi-language expansion that OTF and Mozilla are funding
- This is complementary to our AWS credits application (AWS for CI/CD + storage, CAIS for GPU training)
