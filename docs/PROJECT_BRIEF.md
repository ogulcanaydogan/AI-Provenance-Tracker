# AI Provenance Tracker — Project Brief

## Executive Summary

AI Provenance Tracker is an open-source platform for detecting AI-generated content across text, images, audio, and video. It provides explainable confidence scoring, multi-provider consensus analysis, and full audit trails — addressing a critical gap in digital content authenticity verification.

The platform is designed to serve journalists, academic researchers, content moderators, legal teams, and trust-and-safety professionals who need reliable, transparent tools for identifying synthetic content at scale.

---

## Problem

Generative AI has advanced to the point where AI-produced text, images, audio, and video are often indistinguishable from human-created content. This creates systemic risks:

- **Misinformation** — AI-generated articles, social media posts, and images can be produced at scale with no attribution, undermining public trust in media
- **Academic integrity** — AI-written submissions threaten the credibility of educational institutions and research output
- **Legal and forensic authenticity** — courts, regulators, and compliance teams increasingly need to establish whether digital evidence is genuine
- **Platform safety** — social media platforms and content hosts need automated detection to enforce policies against synthetic content

Existing detection tools are **fragmented and opaque**: most handle only one modality (typically text), operate as closed-source black boxes, and cannot be self-hosted, audited, or integrated into enterprise workflows.

---

## Solution

AI Provenance Tracker provides a **unified, open-source detection platform** with the following design principles:

1. **Multi-modal** — a single system handles text, image, audio, and video detection, removing the need to integrate multiple vendor tools
2. **Explainable** — every result includes a weighted signal breakdown, not just a binary verdict, so users understand the reasoning behind each score
3. **Open and auditable** — MIT-licensed, with detection methodology fully documented and a public benchmark for reproducible evaluation
4. **Production-ready** — ships with Docker Compose, Kubernetes Helm charts, and Terraform AWS infrastructure-as-code for deployment at any scale
5. **Extensible** — a provider consensus engine allows operators to combine internal detectors with external services (Copyleaks, Reality Defender, C2PA) using configurable weighting

---

## Technical Overview

### Detection Engine

The platform employs ensemble detection methods for each content type:

- **Text** — combines statistical NLP signals (perplexity, burstiness, vocabulary distribution, structural uniformity) with a fine-tuned DistilRoBERTa transformer classifier. Each signal carries a calibrated weight, and the final score represents a transparent weighted average.
- **Image** — uses Fast Fourier Transform (FFT) frequency domain analysis to identify spectral signatures of diffusion models, combined with artifact pattern recognition, EXIF metadata forensics, and a CNN binary classifier.
- **Audio** — analyses spectral flatness, dynamic range profiles, clipping patterns, and zero-crossing rates to identify synthesised audio.
- **Video** — examines container signatures, byte-level patterns, and frame-level anomalies to flag AI-generated or manipulated video.

### Multi-Provider Consensus

Rather than relying on a single detection method, the platform includes a provider adapter layer that aggregates results from multiple sources with configurable confidence weighting. This significantly reduces false positive rates and allows operators to validate internal detections against external providers.

### Social Media Intelligence

The X (Twitter) intelligence module provides automated collection, normalisation, and analysis of social media data. It generates trust-and-safety reports with explainable flags, supports drill-down analytics (cluster analysis, claims timeline, automated alerts), and includes scheduling with budget guardrails and webhook delivery.

### Public Benchmark

The project includes a reproducible benchmark framework with three evaluation tasks:
- Binary AI-vs-human detection across multiple content domains
- Source attribution (identifying which model family generated content)
- Tamper robustness (testing detection resilience against paraphrasing, translation, and human editing)

Results are published with standard trust metrics (ROC-AUC, calibration ECE, Brier score, false-positive rates) and a static leaderboard.

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend API | FastAPI (Python 3.11+), fully async |
| ML Models | PyTorch 2.1+, Hugging Face Transformers 4.37+, DistilRoBERTa |
| Database | PostgreSQL 15 (SQLAlchemy 2.0 async), Redis 7 |
| Infrastructure | Docker, Kubernetes (Helm), Terraform (AWS ECS/RDS/ALB) |
| Code Quality | Ruff, MyPy, Pytest, pre-commit hooks, structured logging (Structlog) |

---

## Deployment Options

The platform supports multiple deployment targets:

- **Docker Compose** — single-command deployment for development or small-scale production
- **Kubernetes** — Helm chart with separate API and worker deployments for horizontal scaling
- **AWS** — full Terraform stack provisioning ECS tasks, RDS databases, ALB load balancers, and ECR container registry
- **DGX Spark** — SSH-based deployment for NVIDIA GPU infrastructure

---

## Target Users

| Audience | Use Case |
|----------|----------|
| **Journalists** | Verify whether sources, quotes, or media are AI-generated before publication |
| **Academic researchers** | Check submissions and citations for AI-generated content |
| **Content moderators** | Automate detection of synthetic media on platforms |
| **Legal and compliance teams** | Establish content provenance for regulatory or forensic purposes |
| **Trust-and-safety teams** | Monitor social media accounts for coordinated AI-generated activity |
| **Developers** | Integrate detection via REST API or self-host the entire platform |

---

## Differentiation

| Aspect | AI Provenance Tracker | Typical Alternatives |
|--------|----------------------|---------------------|
| Modalities | Text, image, audio, video | Usually text-only |
| Transparency | Open source, explainable scores, public benchmark | Closed source, black-box verdicts |
| Deployment | Self-hosted, Docker, Kubernetes, AWS Terraform | SaaS-only, no self-hosting |
| Consensus | Multi-provider weighted aggregation | Single-provider results |
| Cost | Free and open source (MIT) | Paid subscriptions |

---

## Current Status

The platform is feature-complete across its core detection capabilities, with the following delivered:

- Four-modality detection engine (text, image, audio, video)
- Explainable scoring with weighted signal breakdowns
- Multi-provider consensus engine
- X intelligence module with automated collection, reporting, and alerting
- Public benchmark and leaderboard
- Batch processing and analytics dashboard
- Browser extension (Chrome)
- Enterprise deployment configurations (Docker, Helm, Terraform)
- Audit event logging and compliance tooling
- Automated scheduling with budget guardrails

---

## Repository

**GitHub:** [github.com/ogulcanaydogan/ai-provenance-tracker](https://github.com/ogulcanaydogan/ai-provenance-tracker)
**License:** MIT
