# Supply Chain Security

This document describes image integrity controls used in the Spark production path.

## Controls Enabled

1. Multi-arch image publishing (`linux/amd64,linux/arm64`)
2. Keyless cosign signature on published GHCR images
3. SBOM generation (SPDX JSON) per image
4. Keyless cosign SBOM attestation
5. Deploy-time verification gate before Spark rollout:
   - signature verification (`cosign verify`)
   - SBOM attestation verification (`cosign verify-attestation --type spdxjson`)

## Workflows

- Publish: `.github/workflows/publish-images.yml`
- Deploy: `.github/workflows/deploy-spark.yml`
- Chain: `.github/workflows/deploy-spark-after-publish.yml`

## Runtime Policy

Production pinned deploys should run with:

- `use_pinned_images=true`
- `verify_signatures=true`

If signature or attestation verification fails, deploy must not proceed.

## Evidence Artifacts

Publish workflow uploads SBOM artifacts for each component/tag.
Deploy summaries include whether verification gates were enabled.

## Next Hardening Steps

1. Add policy checks for minimal base-image CVE severity gates.
2. Record provenance attestations in release notes automatically.
3. Add periodic verification job against latest production tags.
