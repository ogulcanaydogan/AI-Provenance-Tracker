# OTF Internet Freedom Fund, Concept Note

> **Program:** Open Technology Fund, Internet Freedom Fund
> **URL:** https://apply.opentech.fund/internet-freedom-fund-concept-note/
> **Type:** Concept Note (Stage 1 of 2)
> **Amount requested:** $120,000 USD
> **Duration:** 12 months
> **Category:** Technical Development
> **Status:** Ready to submit
> **Deadline:** Rolling (expect 6-8 weeks for response)

---

## Concept Note Answers

### Project Title

AI Provenance Tracker: Open Detection Infrastructure for AI-Generated Disinformation

### Project Description (1-3 sentences)

Journalists, election monitors, and civil society groups in repressive environments face a growing wave of AI-generated disinformation, but the tools to detect it are proprietary, cloud-only, and impossible to audit. AI Provenance Tracker is an open source, self-hostable platform that detects AI-generated content across text, images, audio, and video with explainable scoring. We're building the detection infrastructure that newsrooms and human rights organisations can run on their own servers, without sending sensitive content to third-party APIs.

### Problem Statement

Authoritarian governments and state-affiliated actors increasingly use generative AI to fabricate evidence against dissidents, produce deepfake videos to discredit journalists, and flood social media with synthetic propaganda during elections. In 2024-2025, AI-generated disinformation campaigns were documented in at least 16 countries with restricted press freedom.

The people who need detection tools most can't use them safely. Current AI detection services (GPTZero, Originality.ai, Hive Moderation) are commercial SaaS products that require uploading content to US or EU servers. For a journalist in a surveilled country, sending a suspected deepfake to a foreign API creates a metadata trail. For an election monitor working offline in a rural area, cloud-only tools simply don't work.

There's also a trust problem. When a detection tool says "87% likely AI-generated," users have no way to understand why. Proprietary detectors are black boxes. If a government claims a leaked document is "AI-generated" to discredit it, there's no independent way to verify that claim. Detection needs to be transparent and reproducible, not just accurate.

Without open, self-hostable detection infrastructure, the asymmetry gets worse: well-funded actors can generate synthetic content at scale, while the people trying to verify information have no independent tools.

### Project Form Type

**Technical Development**

This is a production-ready open source platform (v1.0.0 released March 2026) that needs targeted development to serve internet freedom communities specifically. The core detection engine works; we need to adapt deployment, UX, and model coverage for the environments where it's most needed.

### Project Activities & Milestones

**Months 1-3: Offline-first deployment and low-resource adaptation**
- Package the detection engine as a standalone binary and Docker image that runs fully offline (no API keys, no internet required after initial setup)
- Test and optimise for low-spec hardware (4GB RAM, ARM processors like Raspberry Pi 4) so field offices and newsrooms in bandwidth-constrained areas can run it
- Build a simple web UI that non-technical users can operate without terminal access
- Deliverable: Offline installer tested on 3 hardware configurations

**Months 4-7: Detection model expansion for underserved languages**
- Current text detection works best on English content. We'll extend coverage to Arabic, Farsi, Russian, Mandarin, and Spanish, the languages where AI disinformation campaigns are most active
- Train detection classifiers on AI-generated text from regional model families (Jais for Arabic, Yi for Chinese, GigaChat for Russian) that aren't covered by Western-centric detectors
- Add support for detecting AI-generated voice cloning in non-English speech patterns
- Deliverable: Multi-language detection benchmark with published accuracy numbers per language

**Months 8-10: Newsroom integration and field testing**
- Partner with 2-3 newsrooms or fact-checking organisations for real-world deployment
- Build integrations for common newsroom workflows: browser extension for quick checks, API endpoint for CMS integration, batch processing for archive analysis
- Create documentation and training materials in the 5 target languages
- Deliverable: Deployed instances at partner organisations with usage data

**Months 11-12: Public benchmark and sustainability**
- Publish a public, reproducible benchmark for AI content detection accuracy across all supported modalities and languages
- Nightly CI already runs benchmarks; we'll expand the test corpus with region-specific samples
- Document the full methodology so anyone can reproduce our results and challenge our scores
- Write a sustainability plan: the core platform is MIT-licensed and runs on commodity hardware, so ongoing costs are primarily model retraining ($2K-5K/quarter on donated compute)
- Deliverable: Published benchmark, sustainability report, all code tagged and released

### Similar Projects & Differentiation

**Existing tools and their limitations:**
- **GPTZero, Originality.ai**: Commercial SaaS, English-focused, proprietary algorithms, require internet. No self-hosting option.
- **Copyleaks**: Enterprise pricing, cloud-only, no transparency on methodology.
- **Content Credentials (C2PA)**: Excellent standard for provenance, but only works when content has been signed at creation. Doesn't help with unsigned content, which is most of what surfaces in disinformation campaigns.
- **Deepware, FakeCatcher**: Focused on video deepfakes only. No text or audio detection.

**What we do differently:**
- Fully self-hostable and offline-capable: no content leaves the user's machine
- Multi-modal: text, image, audio, and video in one platform
- Explainable scoring: each detection returns a signal-by-signal breakdown, not just a number
- Multi-provider consensus: aggregates internal detectors with optional external APIs (Copyleaks, Hive, Reality Defender) when connectivity is available
- C2PA verification built in: checks cryptographic provenance when signed manifests exist
- MIT-licensed, no usage restrictions or API keys required for core features

We're not competing with commercial detectors. We're building the infrastructure layer that doesn't exist: open, auditable, self-hostable detection that works in environments where commercial tools can't reach.

### Project Duration

12 months

### Funding Amount (USD)

$120,000

**Rough budget breakdown:**
- $45,000: Senior developer (0.5 FTE, 12 months) for offline packaging, low-resource optimisation, and newsroom integrations
- $30,000: ML engineer (0.4 FTE, 6 months) for multi-language model training and benchmark development
- $20,000: Compute costs for model training and benchmark infrastructure (GPU time for 5 language models)
- $10,000: Field testing and partner coordination (travel, equipment for partner newsrooms)
- $8,000: Translation and localisation of docs and UI into Arabic, Farsi, Russian, Mandarin, Spanish
- $7,000: Security audit of offline deployment mode and API endpoints

### Beneficiaries

Our primary users are **journalists and fact-checkers in countries with restricted press freedom** who encounter suspected AI-generated content in their daily work. They need to verify whether a video, audio clip, or document is synthetic before publishing stories or reporting it. Today they rely on gut instinct or send content to commercial services that create metadata trails.

Secondary users include **election monitoring organisations** operating in countries where AI-generated propaganda is deployed during campaign periods. These groups often work in areas with limited connectivity and can't depend on cloud APIs.

We've designed the tool's UX for non-technical users from the start: the web interface shows confidence scores with plain-language explanations ("This text has unusually uniform sentence structure and low vocabulary variation, consistent with AI generation from a GPT-family model"). No terminal access or technical knowledge required.

The self-hosting requirement is critical for these users. A journalist investigating government corruption can't upload evidence to a third-party server. An election monitor working offline in a rural polling station needs detection that runs locally. These constraints shaped every architectural decision in the project.

### Geographic Focus

- Eastern Africa, Western Africa, Northern Africa (press freedom restrictions, AI disinformation documented)
- Western Asia, Southern Asia (surveillance environments, growing AI-generated propaganda)
- Eastern Europe (state-affiliated disinformation campaigns)
- Central America, South America (election integrity concerns)

The offline-first approach means geographic constraints around connectivity don't limit deployment.

### Applicant

Ogulcan Aydogan

### Contact Email

security@ogulcanaydogan.com

### Team Expertise & Background

I'm a software engineer based in the United Kingdom building open source AI security and governance infrastructure. My portfolio includes 10 open source projects covering AI supply chain security (Sigstore/SLSA attestation for ML models), prompt injection detection (OWASP LLM Top 10), regulatory compliance scanning (EU AI Act, NIST AI RMF), and AI content provenance.

AI Provenance Tracker specifically: I built and maintain the entire platform, which is now at v1.0.0 with 21 CI/CD workflows, production deployment on NVIDIA DGX infrastructure, and a public benchmark running nightly. The detection engine covers four content modalities with explainable scoring.

Relevant technical experience:
- Cryptographic signing and verification (DSSE, Sigstore, C2PA)
- ML model training and evaluation (PyTorch, Transformers, custom classifiers)
- Production infrastructure (Kubernetes, Terraform, Docker)
- Supply chain security (SBOM generation, container image signing, vulnerability scanning)

The project has received interest from NLnet (NGI Zero), Mozilla (Democracy x AI), and the UK AISI Challenge Fund. It's registered on the FLOSS/fund directory and indexed by the OpenSSF Scorecard.

Repository: https://github.com/ogulcanaydogan/AI-Provenance-Tracker

---

## Submission Steps

1. Create account at https://apply.opentech.fund/ (or log in)
2. Navigate to Internet Freedom Fund concept note form
3. Fill in fields using the answers above
4. For "Project Form Type" select "Technical Development"
5. For "Geographic Location" select relevant regions (Eastern Africa, Western Asia, Eastern Europe, etc.)
6. Submit concept note
7. Expect response in 6-8 weeks
8. If invited to Stage 2, prepare full proposal with detailed budget and timeline
9. Update `TRACKING.md` and master tracker with submission date

---

## Notes

- OTF is funded by USAGM (US Agency for Global Media). Funding status has been politically uncertain; check current status before submitting.
- UK-based individuals/organisations are eligible (not OFAC-restricted).
- OTF prioritises first-time applicants and underrepresented groups.
- Ideal budget range is $50K-$200K for 6-12 months; our $120K/12mo request fits squarely in the sweet spot.
- The concept note is brief; if selected for Stage 2, a full proposal will be required.
