# Supply Chain Security

This document describes image integrity controls used in the Spark production path.

## Controls Enabled

1. Multi-arch image publishing (`linux/amd64,linux/arm64`)
2. Keyless cosign signature on published GHCR images
3. SBOM generation (SPDX JSON) per image
4. Keyless cosign SBOM attestation
5. Vulnerability scanning (Trivy) on published images with optional policy gate
6. Deploy-time verification gate before Spark rollout:
   - signature verification (`cosign verify`)
   - SBOM attestation verification (`cosign verify-attestation --type spdxjson`)
7. Daily production-tag integrity verification workflow (`verify-production-images.yml`)

## Workflows

- Publish: `.github/workflows/publish-images.yml`
- Deploy: `.github/workflows/deploy-spark.yml`
- Chain: `.github/workflows/deploy-spark-after-publish.yml`
- Periodic verify: `.github/workflows/verify-production-images.yml`

## Runtime Policy

Production pinned deploys should run with:

- `use_pinned_images=true`
- `verify_signatures=true`

If signature or attestation verification fails, deploy must not proceed.
If `ENABLE_CVE_POLICY_GATE=true`, publish/verification workflows fail when vulnerability
counts exceed configured thresholds.

## Evidence Artifacts

Publish workflow uploads SBOM artifacts for each component/tag.
Deploy summaries include whether verification gates were enabled.
Verification workflow uploads latest-tag attestations and vulnerability reports.

## CVE Policy Variables

- `ENABLE_CVE_POLICY_GATE` (default `false`)
- `CVE_MAX_CRITICAL` (default `0`)
- `CVE_MAX_HIGH` (default `0`)

## Next Hardening Steps

1. Record provenance attestations in release notes automatically.
2. Add package allowlist/denylist policy checks.
3. Add periodic verification against release tags in addition to `latest`.
