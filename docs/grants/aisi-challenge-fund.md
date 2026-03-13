# AISI Challenge Fund Application

> **Programme:** AISI Challenge Fund
> **Funder:** UK AI Safety Institute (Department for Science, Innovation and Technology)
> **URL:** <https://find-government-grants.service.gov.uk/grants/aisi-challenge-fund-1>
> **Funding Range:** GBP 50,000 -- 200,000
> **Deadline:** 31 March 2026
> **Applicant:** Ogulcan Aydogan
> **Repository:** <https://github.com/ogulcanaydogan/AI-Provenance-Tracker>
> **License:** MIT

---

## 1. Project Title

**AI Provenance Tracker: Open Source Infrastructure for AI Content Authenticity**

---

## 2. Problem Statement

The rapid advancement of generative AI has created a systemic trust crisis in digital content. Large language models (GPT-4, Claude, Llama, Gemini) generate text that is statistically indistinguishable from human writing. Image diffusion models (DALL-E, Midjourney, Stable Diffusion) produce photorealistic imagery at scale. Audio synthesis and video deepfake models are maturing rapidly.

The consequences are immediate and severe:

- **Misinformation at scale.** AI-generated articles, social media posts, and images can be mass-produced with no attribution, eroding public trust in journalism, democratic institutions, and verified information.
- **Deepfake exploitation.** Synthetic audio and video enable identity fraud, non-consensual intimate imagery, and political manipulation. The UK Online Safety Act identifies deepfakes as a category of priority illegal content.
- **Academic and legal integrity.** AI-generated submissions undermine the credibility of educational institutions. Courts and regulators increasingly need to establish whether digital evidence is genuine.
- **No standardised detection infrastructure.** Existing detection tools are fragmented: most handle a single modality, operate as closed-source black boxes, and cannot be self-hosted, audited, or independently validated. There is no open, multi-modal detection platform with reproducible benchmarks.

The UK AI Safety Institute has identified frontier AI risks as a core concern. AI-generated content that is designed to deceive -- or that is indistinguishable from authentic content without detection tooling -- represents a direct safety threat. Without open, transparent, and rigorously tested detection infrastructure, neither governments nor civil society can effectively respond.

---

## 3. Proposed Solution

AI Provenance Tracker is an open-source platform that provides unified AI-generated content detection and provenance verification across four modalities: text, image, audio, and video.

### 3.1 Multi-Modal Detection Engine

| Modality | Status | Techniques | Models Detected |
|----------|--------|-----------|-----------------|
| Text | Production | Perplexity analysis, burstiness measurement, vocabulary distribution, structural analysis, fine-tuned DistilRoBERTa classifier | GPT-4, Claude, Llama, Gemini, and other LLMs |
| Image | Production | FFT frequency domain analysis, artifact pattern recognition, EXIF metadata forensics, CNN binary classifier | DALL-E, Midjourney, Stable Diffusion |
| Audio | Experimental | Spectral flatness analysis, dynamic range profiling, clipping detection, zero-crossing anomaly checks | AI-synthesised speech and audio |
| Video | Experimental | Container signature analysis, byte-pattern detection, frame-level anomaly scoring | Deepfake and AI-generated video |

Every detection returns a confidence score (0--100%) with a signal-by-signal breakdown. Results are transparent and auditable, not black-box verdicts.

### 3.2 Ensemble Scoring and Explainability

Each modality employs a weighted ensemble of detection signals. For text detection, the pipeline combines:

| Signal | Description | Weight |
|--------|-------------|--------|
| Perplexity | How predictable the text is to a language model | 30% |
| Burstiness | Variation in sentence complexity | 25% |
| Vocabulary | Word choice diversity and repetition patterns | 20% |
| Structure | Paragraph and sentence uniformity | 15% |
| ML Classifier | Fine-tuned RoBERTa model prediction | 10% |

This design ensures that every score is accompanied by a human-readable explanation of which signals contributed to the result and by how much. This is critical for trust, accountability, and downstream decision-making.

### 3.3 Multi-Provider Consensus

Rather than relying on a single detection method, the platform aggregates results from multiple sources through a provider adapter layer:

- **Internal detectors** (statistical and ML-based, no external API dependency)
- **Copyleaks** (commercial AI text detection)
- **Reality Defender** (multi-modal deepfake detection)
- **Hive Moderation** (content classification)
- **C2PA cryptographic verification** (Coalition for Content Provenance and Authenticity standard)

Configurable confidence weighting allows operators to tune the consensus threshold. Multi-provider agreement significantly reduces false positive rates.

### 3.4 C2PA Provenance Verification

When a C2PA-signed manifest is present, the platform performs cryptographic provenance verification against the C2PA standard (ISO/IEC 62008). This is the emerging global standard for content authenticity, supported by Adobe, Microsoft, the BBC, and the Content Authenticity Initiative.

### 3.5 Public Benchmark and Leaderboard

The project includes a reproducible benchmark framework with three evaluation tasks:

1. **Binary detection** -- AI-vs-human classification across multiple content domains
2. **Source attribution** -- identifying which model family generated the content
3. **Tamper robustness** -- testing detection resilience against paraphrasing, translation, and human editing

Benchmark results are published via a nightly CI workflow and rendered as a public leaderboard, enabling the research community to independently validate detection accuracy.

---

## 4. Safety Impact and AISI Alignment

### 4.1 Direct Alignment with AISI Mission

The UK AI Safety Institute's mandate includes evaluating and mitigating risks from frontier AI systems. AI-generated content that is designed to deceive -- or that cannot be distinguished from authentic content -- is a first-order safety concern.

This project directly addresses the following AISI priority areas:

| AISI Concern | How This Project Addresses It |
|--------------|-------------------------------|
| Misinformation and influence operations | Multi-modal detection identifies AI-generated text, images, audio, and video used in disinformation campaigns |
| Deepfakes and synthetic media | Image and video detection pipelines flag AI-generated media; C2PA verification confirms provenance |
| Transparency and explainability | Every detection returns a weighted signal breakdown, not a black-box verdict |
| Open evaluation infrastructure | Public benchmark with nightly CI ensures reproducible, community-verifiable results |
| Frontier model risk assessment | Detection signals are calibrated against outputs from GPT-4, Claude, Llama, Gemini, DALL-E, Midjourney, and Stable Diffusion |

### 4.2 Safety Outcomes

If funded, this project will deliver:

1. **A security-audited, adversarially hardened open-source detection platform** that governments, civil society organisations, and researchers can deploy without vendor lock-in.
2. **Adversarial robustness testing** that documents how detection accuracy degrades under deliberate evasion (paraphrasing, style transfer, image post-processing) and publishes mitigations.
3. **Hardened C2PA integration** that can be used as reference infrastructure for content authenticity verification at scale.
4. **Published benchmarks and methodology documentation** that enable the research community to reproduce, critique, and improve upon detection methods.

### 4.3 Broader Ecosystem Impact

- The platform is MIT-licensed and fully open source, meaning any UK government department, regulator, or civil society organisation can deploy and audit it.
- Browser extensions (Chrome and Firefox) allow journalists, fact-checkers, and researchers to perform detection directly in their workflow.
- Docker Compose, Kubernetes Helm charts, and Terraform AWS infrastructure-as-code enable deployment at any scale, from a single laptop to enterprise infrastructure.

---

## 5. Current Project Status

AI Provenance Tracker is a mature, actively maintained project with production-grade engineering practices.

### 5.1 Engineering Maturity

| Indicator | Detail |
|-----------|--------|
| CI/CD | 20+ GitHub Actions workflows (CI, CodeQL, deploy-runtime, prod-smoke, public-benchmark, publish-images, release, scorecard, and more) |
| Security scanning | GitHub CodeQL integrated into CI; cosign image signing and SBOM attestation |
| Supply chain security | Keyless cosign signatures, SPDX SBOM generation, Trivy vulnerability scanning, package allow/deny policy enforcement |
| Deployment infrastructure | Docker Compose, Kubernetes (Helm), AWS (Terraform IaC) |
| Production monitoring | SLO/observability reporting, cost governance, text quality drift watch |
| Testing | pytest-asyncio test suite with extensive CI matrix |
| Documentation | Architecture docs, API docs, deployment guides, methodology and limitations docs, training docs, troubleshooting guides |
| Release | v1.0.0 released |
| License | MIT |

### 5.2 Repository Metrics

| Metric | Value |
|--------|-------|
| GitHub Stars | 2 |
| CI Workflows | 21 |
| Release | v1.0.0 |
| License | MIT |
| Languages | Python (FastAPI), TypeScript (Next.js 16, React 19) |

---

## 6. Budget

**Total request: GBP 75,000**

| Line Item | Amount (GBP) | Description |
|-----------|-------------|-------------|
| Independent security audit | 35,000 | Third-party penetration test and code audit of the detection backend, API surface, provider integrations, and deployment infrastructure. Deliverable: formal audit report with findings classified by severity. |
| Adversarial robustness testing | 18,000 | Systematic testing of detection accuracy under adversarial evasion techniques (paraphrasing, style transfer, image post-processing, audio re-encoding, video re-compression). Deliverable: published robustness report with accuracy degradation curves and recommended mitigations. |
| C2PA integration hardening | 12,000 | Harden the C2PA cryptographic verification pipeline against manifest tampering, certificate chain attacks, and partial-signature scenarios. Deliverable: hardened C2PA module with test suite and compliance documentation. |
| Documentation, benchmarks, and community | 10,000 | Expand public benchmark coverage (additional model families, languages, and content domains). Publish methodology papers. Create contributor onboarding guides and detection integration tutorials. |
| **Total** | **75,000** | |

### 6.1 Budget Justification

- **Security audit (GBP 35,000):** Open-source detection infrastructure that governments and civil society rely on must be independently audited. This is the single largest line item because a compromised detection platform could produce false assurances, which is worse than no detection at all. The budget covers a reputable UK-based security consultancy (e.g., NCC Group, Pentest Partners, or equivalent) for a scoped engagement.
- **Adversarial robustness (GBP 18,000):** Detection systems are only as useful as their resilience to evasion. This budget covers researcher time to design and execute adversarial test suites, computational resources for large-scale evaluation, and publication of results.
- **C2PA hardening (GBP 12,000):** C2PA is the emerging global standard for content provenance. Hardening the integration to production-grade reliability requires cryptographic expertise and thorough test coverage against edge cases.
- **Documentation and benchmarks (GBP 10,000):** Open infrastructure requires clear documentation and reproducible evaluation. This covers technical writing, benchmark dataset curation, and community engagement.

---

## 7. Timeline

**Total duration: 16 weeks**

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1--2 | Kick-off and scoping | Finalise audit scope with security consultancy. Define adversarial test plan. Establish milestone tracking. |
| 3--6 | Security audit | External penetration test and code audit. Receive preliminary findings. Begin remediation of critical and high-severity issues. |
| 5--10 | Adversarial robustness testing | Design and execute adversarial test suites for all four modalities. Document accuracy degradation under evasion. Implement mitigations for identified weaknesses. |
| 7--12 | C2PA integration hardening | Harden manifest verification against tampering and edge cases. Expand test coverage. Produce compliance documentation. |
| 8--14 | Documentation and benchmarks | Expand benchmark coverage. Publish methodology papers. Write contributor and integration guides. |
| 13--16 | Remediation, final audit, and publication | Complete remediation of all audit findings. Final verification pass. Publish security audit report (redacting sensitive details per responsible disclosure). Publish adversarial robustness report. Tag release. |

Note: Phases overlap intentionally to maintain momentum. Weeks 5--6 and 7--8 involve parallel workstreams.

---

## 8. Team

| Name | Role | Relevant Experience |
|------|------|-------------------|
| Ogulcan Aydogan | Project Lead, Principal Engineer | Full-stack ML engineer. Designed and built the AI Provenance Tracker platform end-to-end: multi-modal detection engine, provider consensus architecture, CI/CD infrastructure (20+ workflows), Docker/Kubernetes/Terraform deployment, and public benchmark system. Background in NLP, computer vision, and production ML systems. |

Additional specialist contractors will be engaged for the security audit (external consultancy) and adversarial robustness testing (ML security researcher), funded from the budget above.

---

## 9. Intellectual Property and Open Source Commitment

- The project is and will remain **MIT-licensed**.
- All code, documentation, benchmark datasets, audit reports (with responsible redactions), and robustness testing results funded by this grant will be published openly on GitHub.
- There are no proprietary dependencies. External provider integrations (Copyleaks, Reality Defender, Hive) are optional adapters; the platform functions fully with internal detectors alone.

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Security audit reveals critical vulnerability in detection pipeline | Medium | High | Budget includes remediation time. Responsible disclosure process is already documented in SECURITY.md. |
| Adversarial attacks reduce detection accuracy below useful threshold for specific modalities | Medium | Medium | Results will be published transparently. Mitigations will be implemented where feasible. Limitations will be clearly documented per existing project practice (see docs/METHODOLOGY_LIMITATIONS.md). |
| C2PA standard evolves during project timeline | Low | Low | Implementation tracks the current ISO/IEC 62008 specification. Modular architecture allows updates without full rewrite. |
| Contractor availability delays | Low | Medium | Engagement with security consultancy will begin immediately upon funding confirmation. Parallel workstreams reduce critical-path dependencies. |

---

## 11. Supporting Materials Checklist

Before submission, confirm the following materials are prepared:

- [ ] **GitHub repository** -- public, MIT-licensed, with full commit history: <https://github.com/ogulcanaydogan/AI-Provenance-Tracker>
- [ ] **README** -- project overview, capabilities, architecture diagrams, deployment instructions
- [ ] **SECURITY.md** -- vulnerability reporting process, response timelines, scope
- [ ] **CONTRIBUTING.md** -- contributor guidelines
- [ ] **docs/ARCHITECTURE.md** -- system design, technology stack, request pipeline, detection pipeline
- [ ] **docs/METHODOLOGY_LIMITATIONS.md** -- detection methodology, known limitations, safe-use guidance
- [ ] **docs/SUPPLY_CHAIN_SECURITY.md** -- cosign signatures, SBOM attestation, Trivy scanning, CVE policy
- [ ] **docs/SLO_OBSERVABILITY.md** -- service-level objectives, monitoring, alerting
- [ ] **docs/COST_GOVERNANCE.md** -- cost controls and budget guardrails
- [ ] **CI evidence** -- 21 GitHub Actions workflows visible in repository Actions tab
- [ ] **Release** -- v1.0.0 tagged release with changelog
- [ ] **CodeQL** -- security analysis integrated into CI (visible in repository Security tab)
- [ ] **Benchmark** -- public benchmark and leaderboard (nightly CI-driven)
- [ ] **Browser extensions** -- Chrome and Firefox extensions in repository
- [ ] **Deployment configs** -- Docker Compose, Kubernetes Helm charts, Terraform AWS IaC in `deploy/` directory
- [ ] **Budget breakdown** -- this document, Section 6
- [ ] **Timeline** -- this document, Section 7

---

## 12. Submission Steps

1. Navigate to <https://find-government-grants.service.gov.uk/grants/aisi-challenge-fund-1>.
2. Create an account or sign in to the Government Grants portal.
3. Complete the application form, using the content from this document for each section.
4. Upload supporting materials (or provide GitHub links where upload is not required).
5. Review all sections for accuracy and completeness.
6. Submit before **31 March 2026**.
7. Retain the confirmation email and application reference number.

---

## 13. Contact

| Field | Value |
|-------|-------|
| Applicant | Ogulcan Aydogan |
| GitHub | <https://github.com/ogulcanaydogan> |
| Repository | <https://github.com/ogulcanaydogan/AI-Provenance-Tracker> |
| Email | security@ogulcanaydogan.com |

---

*Document prepared for the AISI Challenge Fund (UK) application. All technical claims are verifiable against the public GitHub repository.*
