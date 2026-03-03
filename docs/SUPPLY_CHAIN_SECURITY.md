# Supply Chain Security

This document defines image integrity and dependency-source controls for Spark production deploys.

## Controls Enabled

1. Multi-arch image publishing (`linux/amd64,linux/arm64`)
2. Keyless cosign signature on GHCR images
3. SBOM generation (SPDX JSON) per image
4. Keyless SBOM attestation (`spdxjson`)
5. Trivy vulnerability scan per image (`HIGH,CRITICAL`)
6. Moderate CVE gate:
   - `CRITICAL` threshold is blocking
   - `HIGH` threshold is warning by default (optional hard-fail)
7. Package allow/deny policy check on lockfiles/requirements before image publish
8. Deploy-time verification gate before Spark rollout:
   - signature verification (`cosign verify`)
   - SBOM attestation verification (`cosign verify-attestation --type spdxjson`)
9. Daily production-tag integrity verification workflow (`verify-production-images.yml`)
10. Release provenance note artifact for each published component/tag

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

## CVE Policy Variables

- `CVE_FAIL_ON_CRITICAL` (default `true`)
- `CVE_FAIL_ON_HIGH` (default `false`)
- `CVE_MAX_CRITICAL` (default `0`)
- `CVE_MAX_HIGH` (default `25`)

## Package Policy

- Config: `config/package_policy.yaml`
- Script: `scripts/check_package_policy.py`
- Artifact: `ops/reports/package_policy_report.{json,md}`

The publish workflow fails when policy violations are detected.

## Release Provenance Note

- Script: `scripts/generate_release_provenance_note.py`
- Artifact: `release-provenance-<component>-<sha>.{json,md}`

Each note records:

- image ref + digest
- keyless signing status
- SBOM/attestation metadata
- vulnerability summary

## Evidence Artifacts

Publish workflow uploads:

- SBOM artifacts
- Trivy reports
- package policy report
- release provenance notes

Deploy summaries include whether verification gates were enabled and passed.
