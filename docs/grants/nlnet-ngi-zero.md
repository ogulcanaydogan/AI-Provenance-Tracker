# NLnet NGI Zero Proposal

> **Programme:** NGI Zero Core / NGI Zero Commons
> **Funder:** NLnet Foundation (funded by the European Commission via Next Generation Internet)
> **URL:** <https://nlnet.nl/propose/>
> **Funding Range:** EUR 5,000 -- 50,000
> **Deadline:** 1 April 2026
> **Applicant:** Ogulcan Aydogan
> **Repository:** <https://github.com/ogulcanaydogan/AI-Provenance-Tracker>
> **License:** MIT

---

## 1. Project Name

AI Provenance Tracker

---

## 2. Abstract (200 words)

AI Provenance Tracker is an open-source platform for detecting AI-generated content and verifying digital provenance across text, images, audio, and video. As generative AI produces content indistinguishable from human-created media, the internet faces a structural trust crisis. Existing detection tools are proprietary, single-modality, and cannot be independently audited.

This project provides open infrastructure that anyone can deploy, inspect, and extend. The detection engine combines internal statistical and machine learning classifiers with a multi-provider consensus layer (Copyleaks, Reality Defender, Hive). Every result includes an explainable confidence score with a signal-by-signal breakdown, replacing opaque black-box verdicts with transparent reasoning.

A key component is the implementation of the C2PA (Coalition for Content Provenance and Authenticity) standard for cryptographic provenance verification. When signed manifests are present, the platform validates content authenticity using the same standard adopted by Adobe, Microsoft, and the BBC.

The project includes a public benchmark and leaderboard with nightly automated evaluation, enabling the research community to reproduce and validate detection accuracy. It ships with Docker, Kubernetes, and Terraform deployment configurations.

This proposal seeks funding to harden the C2PA implementation, expand multi-modal detection, publish public benchmarks, and improve documentation for community adoption.

---

## 3. Have You Been Involved with Projects or Organisations Relevant to This Proposal?

Yes. I am the creator and sole maintainer of AI Provenance Tracker. I designed and built the complete platform: the multi-modal detection engine (text, image, audio, video), the provider consensus architecture, the C2PA verification pipeline, the CI/CD infrastructure (21 GitHub Actions workflows including CodeQL security scanning), and the deployment configurations (Docker Compose, Kubernetes Helm, Terraform AWS).

The project is publicly available at <https://github.com/ogulcanaydogan/AI-Provenance-Tracker> under the MIT license, with a v1.0.0 release.

---

## 4. Requested Amount

**EUR 40,000**

---

## 5. Description of the Project

### 5.1 Problem

Generative AI has reached the point where AI-produced text, images, audio, and video are frequently indistinguishable from human-created content. This undermines trust in digital media and creates vectors for misinformation, deepfakes, academic fraud, and evidence tampering.

The detection landscape is fragmented and closed:

- Most tools detect only one modality (typically text).
- Commercial services operate as black boxes with no transparency into detection methodology.
- No open-source platform provides multi-modal detection with explainable scoring.
- C2PA, the emerging global standard for content provenance, has limited open-source implementation coverage.
- There is no public, reproducible benchmark for comparing detection methods across modalities.

### 5.2 Solution

AI Provenance Tracker addresses these gaps through five pillars:

**Multi-Modal Detection.** A single platform detects AI-generated content across text (production), image (production), audio (experimental), and video (experimental). Text detection uses statistical NLP signals (perplexity, burstiness, vocabulary distribution, structural uniformity) combined with a fine-tuned DistilRoBERTa classifier. Image detection uses FFT frequency analysis, artifact recognition, EXIF forensics, and a CNN classifier.

**Explainable Confidence Scoring.** Every detection returns a 0--100% confidence score with a weighted signal breakdown. Users see exactly which signals contributed to the result and by how much. This is essential for trust, accountability, and appropriate downstream use.

**Multi-Provider Consensus.** A provider adapter layer aggregates results from internal detectors and optional external services (Copyleaks, Reality Defender, Hive) with configurable weighting. Multi-source agreement reduces false positive rates and allows independent validation.

**C2PA Cryptographic Verification.** The platform implements the C2PA standard (ISO/IEC 62008) for content provenance. When a signed manifest is present, the system validates the cryptographic chain and reports provenance metadata. This is the standard adopted by the Content Authenticity Initiative and supported by Adobe, Microsoft, the BBC, and major camera manufacturers.

**Public Benchmark and Leaderboard.** A reproducible benchmark framework evaluates binary detection accuracy, source attribution, and tamper robustness. Nightly CI workflows publish results to a public leaderboard.

### 5.3 Current Status

The platform is functional with a v1.0.0 release. Key indicators of engineering maturity:

- 21 GitHub Actions CI/CD workflows (CI, CodeQL, deploy-runtime, prod-smoke, public-benchmark, publish-images, release, scorecard, SLO observability, cost governance, text quality drift watch, and more)
- Supply chain security: cosign image signatures, SPDX SBOM generation, Trivy vulnerability scanning
- Deployment: Docker Compose, Kubernetes Helm charts, Terraform AWS IaC
- Browser extensions for Chrome and Firefox
- MIT license

---

## 6. Relevance to NGI Zero

This project aligns with the Next Generation Internet initiative in the following ways:

### 6.1 Open Internet Infrastructure

AI-generated content threatens the trustworthiness of information on the open internet. Without accessible detection infrastructure, only large platforms and well-resourced organisations can identify synthetic content. This project democratises detection by providing MIT-licensed, self-hostable infrastructure that any organisation, researcher, or individual can deploy.

### 6.2 Open Standards: C2PA

The C2PA standard is the most promising approach to content provenance at internet scale. This project provides one of the few open-source implementations of C2PA verification, enabling interoperability with the broader Content Authenticity Initiative ecosystem. Hardening this implementation directly supports the adoption of open standards for content authenticity.

### 6.3 Privacy and Sovereignty

The platform can be fully self-hosted with no external API dependencies. Internal detectors operate without sending content to third parties. This is essential for organisations handling sensitive content (journalism, legal, government) that cannot use cloud-based detection services.

### 6.4 Transparency and Accountability

The explainable scoring system and public benchmark directly support transparency. Detection methodology is documented, results are reproducible, and limitations are openly acknowledged (see docs/METHODOLOGY_LIMITATIONS.md in the repository).

### 6.5 Search and Discovery

Content authenticity verification improves the quality of information discovery on the internet. By enabling reliable identification of AI-generated content, the project supports users and platforms in distinguishing authentic from synthetic content.

---

## 7. Comparison with Existing Solutions

| Solution | Modalities | Open Source | Explainable | C2PA | Public Benchmark |
|----------|-----------|-------------|-------------|------|-----------------|
| **AI Provenance Tracker** | Text, Image, Audio, Video | Yes (MIT) | Yes (weighted signal breakdown) | Yes | Yes (nightly CI) |
| GPTZero | Text | No | Partial | No | No |
| Copyleaks | Text | No | No | No | No |
| Reality Defender | Image, Audio, Video | No | Partial | No | No |
| Hive Moderation | Text, Image | No | No | No | No |
| Content Credentials (Adobe) | Image | Partial | No | Yes | No |

AI Provenance Tracker is unique in combining multi-modal detection, explainable scoring, C2PA verification, and a public benchmark in a single open-source platform.

---

## 8. Budget

**Total: EUR 40,000**

| Milestone | Amount (EUR) | Description |
|-----------|-------------|-------------|
| M1: C2PA hardening | 12,000 | Harden cryptographic verification against manifest tampering, certificate chain edge cases, and partial-signature scenarios. Produce comprehensive test suite and compliance documentation. |
| M2: Multi-modal detection improvements | 10,000 | Improve audio and video detection pipelines from experimental to beta quality. Add new detection signals based on current research. Expand model family coverage for text and image. |
| M3: Public benchmark expansion | 8,000 | Add benchmark datasets for additional languages, content domains, and model families. Implement cross-lingual detection evaluation. Publish methodology documentation. |
| M4: Documentation and community adoption | 5,000 | Create integration tutorials, contributor onboarding guides, and API documentation. Prepare materials for community workshops and conference presentations. |
| M5: Security hardening | 5,000 | Dependency auditing, API surface hardening, rate limiting improvements, and input validation hardening across all modalities. Address findings from automated security scanning (CodeQL, Trivy). |
| **Total** | **40,000** | |

---

## 9. Milestones and Timeline

| Milestone | Duration | Start | End | Deliverables |
|-----------|----------|-------|-----|-------------|
| M1: C2PA hardening | 6 weeks | Week 1 | Week 6 | Hardened C2PA verification module. Comprehensive test suite covering manifest tampering, certificate chain validation, partial signatures, and expired certificates. Compliance documentation mapping implementation to ISO/IEC 62008 requirements. |
| M2: Detection improvements | 8 weeks | Week 3 | Week 10 | Improved audio and video detection pipelines with documented accuracy metrics. At least two new detection signals per modality. Updated benchmark results showing accuracy improvements. |
| M3: Benchmark expansion | 6 weeks | Week 7 | Week 12 | Benchmark datasets for at least three additional languages. Cross-lingual evaluation results. Updated public leaderboard. Methodology documentation published. |
| M4: Documentation and community | 4 weeks | Week 11 | Week 14 | Integration tutorial (API usage). Contributor guide with architecture walkthrough. Updated API documentation. At least one conference submission or community workshop. |
| M5: Security hardening | 4 weeks | Week 13 | Week 16 | Dependency audit report. Hardened API surface. Updated rate limiting and input validation. All CodeQL and Trivy findings addressed. |

Total project duration: **16 weeks** (4 months). Milestones overlap where work can proceed in parallel.

---

## 10. Technical Architecture

```
Frontend (Next.js 16 / React 19)
        |
        v
FastAPI Backend (Python 3.12+)
  |-- /api/v1/detect/*   (text, image, audio, video)
  |-- /api/v1/batch/*    (bulk text detection)
  |-- /api/v1/analyze/*  (history, dashboard)
  |-- /health            (liveness + deep health check)
  |
  |-- Detection Engine
  |     |-- Text:  perplexity, burstiness, vocabulary, structure, DistilRoBERTa
  |     |-- Image: FFT frequency, artifacts, EXIF metadata, CNN classifier
  |     |-- Audio: spectral flatness, dynamic range, clipping, zero-crossing
  |     |-- Video: container signatures, byte patterns, frame anomalies
  |
  |-- Provider Consensus Layer
  |     |-- Copyleaks adapter
  |     |-- Reality Defender adapter
  |     |-- Hive adapter
  |     |-- C2PA verification
  |
  |-- Storage: SQLite / PostgreSQL (SQLAlchemy 2 async)
  |-- Cache: Redis (optional)
  |-- Scheduler: APScheduler (background tasks)
```

Deployment options:
- Docker Compose (single-machine)
- Kubernetes with Helm charts (cluster)
- AWS with Terraform IaC (cloud)

---

## 11. Licensing and Intellectual Property

- The project is MIT-licensed.
- All code, documentation, benchmark datasets, and evaluation results produced under this grant will be published under the MIT license on GitHub.
- There are no proprietary dependencies required for core functionality. External provider integrations (Copyleaks, Reality Defender, Hive) are optional adapters; the platform operates fully with internal detectors alone.

---

## 12. Sustainability

After grant completion:

- The project will continue as an actively maintained open-source project.
- The public benchmark and leaderboard will continue to run via automated CI workflows (no ongoing cost beyond GitHub Actions minutes).
- Community contributions will be encouraged through improved documentation and contributor onboarding materials (Milestone M4).
- Additional funding will be sought for ongoing development through complementary grant programmes (AISI Challenge Fund, Mozilla Technology Fund, Open Technology Fund).

---

## 13. Contact

| Field | Value |
|-------|-------|
| Applicant | Ogulcan Aydogan |
| GitHub | <https://github.com/ogulcanaydogan> |
| Repository | <https://github.com/ogulcanaydogan/AI-Provenance-Tracker> |
| Email | security@ogulcanaydogan.com |
| Country | United Kingdom |

---

## 14. Submission Checklist

Before submitting at <https://nlnet.nl/propose/>:

- [ ] Abstract (200 words maximum) -- Section 2 of this document
- [ ] Project description -- Section 5
- [ ] Relevance to NGI -- Section 6
- [ ] Budget and milestones -- Sections 8 and 9
- [ ] Comparison with existing solutions -- Section 7
- [ ] License confirmation (MIT) -- Section 11
- [ ] Repository link: <https://github.com/ogulcanaydogan/AI-Provenance-Tracker>
- [ ] Review NLnet submission guidelines at <https://nlnet.nl/propose/>
- [ ] Submit before **1 April 2026**

---

*Document prepared for the NLnet NGI Zero funding proposal. All technical claims are verifiable against the public GitHub repository.*
