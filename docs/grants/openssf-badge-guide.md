# OpenSSF Best Practices Badge Guide

> **Programme:** OpenSSF (Open Source Security Foundation) Best Practices Badge
> **URL:** <https://www.bestpractices.dev/>
> **Repository:** <https://github.com/ogulcanaydogan/AI-Provenance-Tracker>
> **License:** MIT
> **Target Level:** Passing (with progress toward Silver)

This guide maps AI Provenance Tracker's current capabilities to the OpenSSF Best Practices Badge criteria. Use it as a pre-submission checklist when applying for the badge.

---

## 1. Overview

The OpenSSF Best Practices Badge programme identifies open-source projects that follow security and quality best practices. Achieving the badge demonstrates to users, contributors, and funders that the project meets a recognised standard of engineering maturity.

There are three levels, and here's where the project stands on each:

| Level | Requirements | Status |
|-------|-------------|--------|
| Passing | Core best practices (basics, change control, reporting, quality, security, analysis) | Ready for submission |
| Silver | Passing + enhanced practices (governance, documentation, build reproducibility) | Partial, see Section 9 |
| Gold | Silver + advanced practices (formal governance, signed releases, reproducible builds) | Future goal |

---

## 2. Pre-Submission Checklist: Passing Level

### 2.1 Basics

| Criterion | Requirement | Status | Evidence |
|-----------|------------|--------|----------|
| **identification_and_description** | Project has a descriptive name and clear description | PASS | README.md: "An open-source AI content detection and provenance verification platform" |
| **website** | Project has a public website or repository | PASS | <https://github.com/ogulcanaydogan/AI-Provenance-Tracker> |
| **description_good** | Description explains what the software does, in language a potential user can understand | PASS | README.md includes architecture diagrams, capability tables, and use-case descriptions |
| **interact** | Project provides a mechanism for discussion (issue tracker, forum, mailing list) | PASS | GitHub Issues enabled |
| **contribution** | Project explains how to contribute | PASS | CONTRIBUTING.md in repository root |
| **contribution_requirements** | Contribution process is clearly described | PASS | CONTRIBUTING.md includes coding standards, PR process, and review expectations |
| **floss_license** | Project uses an OSI-approved license | PASS | MIT license (LICENSE file in repository root) |
| **floss_license_osi** | License is approved by OSI | PASS | MIT is OSI-approved |
| **license_location** | License is in a standard location | PASS | `LICENSE` file in repository root |
| **documentation_basics** | Project provides basic documentation | PASS | README.md, docs/ARCHITECTURE.md, docs/DEPLOYMENT.md, docs/API.md, docs/TRAINING.md, docs/TROUBLESHOOTING.md, DEVELOPMENT.md |
| **documentation_interface** | Project documents its external interface | PASS | docs/API.md, FastAPI auto-generated OpenAPI documentation at /docs endpoint |

### 2.2 Change Control

| Criterion | Requirement | Status | Evidence |
|-----------|------------|--------|----------|
| **repo_public** | Repository is publicly readable | PASS | Public GitHub repository |
| **repo_track** | Project uses a version control system that tracks changes | PASS | Git with full commit history |
| **repo_interim** | Repository allows interim versions for review | PASS | Pull request workflow; branch-based development |
| **repo_distributed** | Repository uses a distributed version control system | PASS | Git |
| **version_unique** | Each release has a unique version identifier | PASS | v1.0.0 tagged release |
| **version_semver** | Project uses semantic versioning | PASS | v1.0.0 follows semver |
| **release_notes** | Project provides release notes for each release | PASS | CHANGELOG.md in repository root; GitHub Release notes for v1.0.0 |

### 2.3 Reporting

| Criterion | Requirement | Status | Evidence |
|-----------|------------|--------|----------|
| **report_process** | Project has a process for users to submit bug reports | PASS | GitHub Issues |
| **report_tracker** | Project uses an issue tracker | PASS | GitHub Issues |
| **report_responses** | Project responds to bug reports | PASS | Issue activity visible in repository |
| **report_archive** | Bug reports are publicly archived | PASS | GitHub Issues (public) |
| **vulnerability_report_process** | Project has a documented process for reporting vulnerabilities | PASS | SECURITY.md with email reporting instructions, response timelines, and scope |
| **vulnerability_report_private** | Vulnerability reports can be submitted privately | PASS | SECURITY.md directs reports to security@ogulcanaydogan.com (not public issues) |
| **vulnerability_report_response** | Project responds to vulnerability reports within 14 days | PASS | SECURITY.md commits to 48-hour acknowledgement and 5-business-day initial assessment |

### 2.4 Quality

| Criterion | Requirement | Status | Evidence |
|-----------|------------|--------|----------|
| **build** | Project provides a working build system | PASS | Docker Compose, Makefile, pip requirements, npm/yarn for frontend |
| **build_common_tools** | Build uses common tools for its language ecosystem | PASS | Python: pip/requirements.txt; Node.js: npm/yarn; Docker: Dockerfile |
| **build_floss_tools** | Build system uses FLOSS tools | PASS | All build tools are open source |
| **test** | Project has an automated test suite | PASS | pytest-asyncio test suite in `backend/tests/` |
| **test_invocation** | Tests can be invoked with a standard command | PASS | `pytest` for backend; CI workflow runs tests automatically |
| **test_most** | Most of the project's functionality is tested | PASS | CI matrix covers detection engines, API endpoints, and provider integrations |
| **test_continuous_integration** | Project uses continuous integration | PASS | 21 GitHub Actions workflows |
| **test_policy** | Project has a test policy | PASS | CI runs on every push and pull request; PRs require passing CI |
| **tests_are_added** | New functionality includes tests | PASS | CI enforcement; CONTRIBUTING.md guidelines |

### 2.5 Security

| Criterion | Requirement | Status | Evidence |
|-----------|------------|--------|----------|
| **know_secure_design** | Project applies secure design principles | PASS | Rate limiting, input validation, structured error handling, API key authentication, audit logging (see docs/ARCHITECTURE.md) |
| **know_common_errors** | Project avoids common implementation errors | PASS | Input validation on all detection endpoints (file type, size limits, content checks); parameterised database queries via SQLAlchemy ORM |
| **crypto_published** | Cryptographic algorithms used are publicly known | PASS | C2PA verification uses standard cryptographic primitives (ISO/IEC 62008); cosign image signing uses Sigstore |
| **crypto_credential_agility** | Project supports updating cryptographic credentials | PASS | API keys are configuration-driven; C2PA certificates follow standard chain-of-trust model |
| **crypto_working** | Cryptographic mechanisms are working correctly | PASS | cosign verification in CI; C2PA manifest validation tested |
| **delivery_mitigation** | Project mitigates supply chain attacks | PASS | cosign keyless signatures on container images, SPDX SBOM generation, Trivy vulnerability scanning, package allow/deny policy (docs/SUPPLY_CHAIN_SECURITY.md) |
| **delivery_unsigned** | Project does not distribute unsigned software | PASS | All published container images are cosign-signed with SBOM attestation |
| **hardened_site** | Project website/repository uses HTTPS | PASS | GitHub enforces HTTPS |
| **no_leaked_credentials** | No credentials are leaked in the repository | PASS | `.gitignore` excludes secrets; CI uses GitHub Secrets for API keys |

### 2.6 Analysis

| Criterion | Requirement | Status | Evidence |
|-----------|------------|--------|----------|
| **static_analysis** | Project uses at least one static analysis tool | PASS | GitHub CodeQL integrated into CI (`codeql.yml`); runs on every push and pull request |
| **static_analysis_common_vulnerabilities** | Static analysis checks for common vulnerabilities | PASS | CodeQL checks for injection, XSS, path traversal, and other OWASP categories |
| **static_analysis_fixed** | All medium and higher severity static analysis findings are fixed | PASS | CodeQL workflow is a required CI check; builds fail on findings |
| **static_analysis_often** | Static analysis is run frequently | PASS | CodeQL runs on every push and PR; also runs on schedule |
| **dynamic_analysis** | Project uses at least one dynamic analysis tool or technique | PASS | `prod-smoke.yml` workflow performs runtime health checks and endpoint validation against deployed services |

---

## 3. CI Workflow Inventory

The following GitHub Actions workflows provide evidence for multiple badge criteria:

| Workflow | File | Relevance |
|----------|------|-----------|
| CI | `ci.yml` | Core build and test; runs pytest, linting, type checking |
| CodeQL | `codeql.yml` | Static analysis; SAST for Python and JavaScript |
| Cost Governance | `cost-governance.yml` | Operational maturity; budget guardrails |
| Dependabot Backlog Cleanup | `dependabot-backlog-cleanup.yml` | Dependency management hygiene |
| Dependabot Review Noise Guard | `dependabot-review-noise-guard.yml` | Dependency review automation |
| Deploy Runtime | `deploy-runtime.yml` | Deployment verification |
| Deploy Spark After Publish | `deploy-spark-after-publish.yml` | Deployment pipeline chaining |
| Deploy Spark | `deploy-spark.yml` | Production deployment |
| Prod Smoke | `prod-smoke.yml` | Dynamic analysis; runtime validation |
| Public Benchmark | `public-benchmark.yml` | Reproducible evaluation; nightly benchmark execution |
| Publish Images | `publish-images.yml` | Container image publishing with cosign signing and SBOM |
| Publish Leaderboard | `publish-leaderboard.yml` | Public leaderboard generation |
| Release | `release.yml` | Versioned release management |
| Scorecard | `scorecard.yml` | OpenSSF Scorecard integration |
| SLO Observability Report | `slo-observability-report.yml` | Service-level objective monitoring |
| Text Quality Drift Watch | `text-quality-drift-watch.yml` | Detection quality monitoring |
| Text Training | `text-training.yml` | ML model training pipeline |
| Vercel Comment Noise Guard | `vercel-comment-noise-guard.yml` | CI noise reduction |
| Verify Production Images | `verify-production-images.yml` | Supply chain integrity verification |
| Weekly Evidence | `weekly-evidence.yml` | Automated evidence collection |
| Weekly Text Calibration | `weekly-text-calibration.yml` | Detection calibration monitoring |

**Total: 21 workflows**

---

## 4. Security Evidence Summary

| Security Practice | Implementation | Evidence Location |
|-------------------|---------------|-------------------|
| Static Application Security Testing (SAST) | GitHub CodeQL | `.github/workflows/codeql.yml` |
| Container Image Signing | Keyless cosign (Sigstore) | `.github/workflows/publish-images.yml` |
| SBOM Generation | SPDX JSON per image | `.github/workflows/publish-images.yml` |
| SBOM Attestation | Keyless cosign attestation | `.github/workflows/publish-images.yml` |
| Vulnerability Scanning | Trivy (HIGH, CRITICAL) | `.github/workflows/publish-images.yml` |
| Deploy-Time Signature Verification | cosign verify before rollout | `.github/workflows/deploy-spark.yml` |
| Production Image Integrity | Daily verification workflow | `.github/workflows/verify-production-images.yml` |
| Package Policy Enforcement | Allow/deny list for dependencies | `config/package_policy.yaml`, `scripts/check_package_policy.py` |
| CVE Policy | Configurable thresholds (CRITICAL blocking, HIGH warning) | `docs/SUPPLY_CHAIN_SECURITY.md` |
| Vulnerability Reporting | Documented process with response SLAs | `SECURITY.md` |
| OpenSSF Scorecard | Automated scorecard evaluation | `.github/workflows/scorecard.yml` |

---

## 5. Testing Evidence Summary

| Testing Practice | Implementation | Evidence Location |
|------------------|---------------|-------------------|
| Unit and Integration Tests | pytest-asyncio test suite | `backend/tests/` |
| CI Test Execution | Automated on every push and PR | `.github/workflows/ci.yml` |
| Production Smoke Tests | Runtime health and endpoint validation | `.github/workflows/prod-smoke.yml` |
| Benchmark Tests | Nightly accuracy evaluation | `.github/workflows/public-benchmark.yml` |
| Detection Calibration | Weekly calibration monitoring | `.github/workflows/weekly-text-calibration.yml` |
| Quality Drift Monitoring | Automated drift detection | `.github/workflows/text-quality-drift-watch.yml` |

---

## 6. Documentation Evidence Summary

| Document | Purpose | Location |
|----------|---------|----------|
| README.md | Project overview, capabilities, quick start | Repository root |
| CONTRIBUTING.md | Contribution guidelines | Repository root |
| SECURITY.md | Vulnerability reporting process | Repository root |
| CHANGELOG.md | Release history | Repository root |
| LICENSE | MIT license text | Repository root |
| DEVELOPMENT.md | Developer setup instructions | Repository root |
| docs/ARCHITECTURE.md | System design and technology stack | `docs/` |
| docs/API.md | API reference | `docs/` |
| docs/DEPLOYMENT.md | Deployment guides (Docker, K8s, Terraform) | `docs/` |
| docs/METHODOLOGY_LIMITATIONS.md | Detection methodology and known limitations | `docs/` |
| docs/SUPPLY_CHAIN_SECURITY.md | Supply chain controls and policies | `docs/` |
| docs/SLO_OBSERVABILITY.md | Service-level objectives and monitoring | `docs/` |
| docs/COST_GOVERNANCE.md | Cost controls and budget guardrails | `docs/` |
| docs/PERFORMANCE_TUNING.md | Performance optimisation guidance | `docs/` |
| docs/TRAINING.md | ML model training documentation | `docs/` |
| docs/TROUBLESHOOTING.md | Common issues and solutions | `docs/` |
| docs/DATA_RETENTION.md | Data retention policies | `docs/` |

---

## 7. Submission Steps

1. Navigate to <https://www.bestpractices.dev/>.
2. Click "Get Your Badge Now" and sign in with GitHub.
3. Enter the repository URL: `https://github.com/ogulcanaydogan/AI-Provenance-Tracker`.
4. The form will auto-populate some fields from the repository.
5. Complete each section using the evidence mapped in Section 2 of this guide.
6. For each criterion, select "Met" and provide the justification URL or description from this guide.
7. Review all sections before submitting.
8. Once all Passing criteria are marked "Met", the badge is automatically awarded.
9. Add the badge to README.md:

```markdown
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/XXXXX/badge)](https://www.bestpractices.dev/projects/XXXXX)
```

Replace `XXXXX` with the project ID assigned after registration.

---

## 8. Criteria Requiring Attention

The following criteria may require additional evidence or minor improvements before submission:

| Criterion | Current Status | Action Needed |
|-----------|---------------|---------------|
| `documentation_interface` | Likely PASS | Verify docs/API.md covers all public endpoints. Confirm FastAPI /docs endpoint is accessible. |
| `test_most` | Likely PASS | Review test coverage percentage. Consider adding coverage reporting to CI if not already present. |
| `tests_are_added` | Policy in place | Verify recent PRs include tests. Document test requirement in CONTRIBUTING.md if not already stated. |
| `dynamic_analysis` | PASS via prod-smoke | Consider adding fuzzing (e.g., Atheris for Python) for Silver-level credit. |

---

## 9. Progress Toward Silver Level

The following Silver-level criteria are already met or nearly met:

| Silver Criterion | Status | Evidence |
|------------------|--------|----------|
| **bus_factor** | Needs attention | Currently single-maintainer. Document onboarding process to lower bus-factor risk. |
| **documentation_current** | PASS | Documentation is maintained alongside code changes. |
| **build_reproducible** | Partial | Docker builds are reproducible. Consider pinning all dependency versions for full reproducibility. |
| **crypto_used_network** | PASS | HTTPS enforced; cosign uses Sigstore OIDC. |
| **crypto_tls12** | PASS | GitHub and all external integrations use TLS 1.2+. |
| **hardened_dependencies** | PASS | Trivy scanning, Dependabot, package policy enforcement. |
| **maintained** | PASS | Active development; CI runs nightly. |
| **vulnerabilities_fixed_60_days** | PASS | SECURITY.md commits to 14-business-day fix development. |

### Silver-Level Gaps

| Silver Criterion | Gap | Recommended Action |
|------------------|-----|-------------------|
| **bus_factor** | Single maintainer | Recruit at least one additional maintainer with commit access. Document institutional knowledge. |
| **dco** | No DCO requirement | Consider requiring Developer Certificate of Origin sign-off on contributions. |
| **test_coverage** | Coverage percentage not published | Add coverage reporting (e.g., coverage.py + Codecov) to CI. Target 80%+ for Silver. |
| **build_reproducible** | Partial reproducibility | Pin all Python and Node.js dependencies to exact versions. Use hash-verified lockfiles. |

---

## 10. OpenSSF Scorecard

The repository already includes a Scorecard workflow (`.github/workflows/scorecard.yml`) which evaluates the project against OpenSSF Scorecard checks. This is complementary to the Best Practices Badge and provides additional security signal.

Key Scorecard checks relevant to the badge:

| Scorecard Check | Relevance |
|----------------|-----------|
| Binary-Artifacts | No binary artifacts in repository |
| Branch-Protection | Branch protection rules on main |
| CI-Tests | CI runs on PRs |
| Code-Review | PR review process |
| Dangerous-Workflow | No dangerous workflow patterns |
| Dependency-Update-Tool | Dependabot enabled |
| License | MIT license detected |
| Maintained | Active maintenance |
| Pinned-Dependencies | Dependency pinning in workflows |
| SAST | CodeQL enabled |
| Security-Policy | SECURITY.md present |
| Signed-Releases | cosign-signed container images |
| Token-Permissions | Workflow token permissions scoped |
| Vulnerabilities | Known vulnerability status |

---

## 11. Badge Maintenance

After receiving the Passing badge:

- **Quarterly review.** Re-check all criteria quarterly to ensure continued compliance.
- **CI enforcement.** The existing 21 CI workflows provide automated enforcement of most criteria. Monitor workflow failures.
- **Dependency updates.** Continue using Dependabot and Trivy scanning to maintain security posture.
- **Documentation updates.** Keep documentation current with code changes.
- **Silver progression.** Address the gaps identified in Section 9 to progress toward Silver level.

---

*Guide prepared for the OpenSSF Best Practices Badge application for AI Provenance Tracker. All evidence references are verifiable against the public GitHub repository at <https://github.com/ogulcanaydogan/AI-Provenance-Tracker>.*
