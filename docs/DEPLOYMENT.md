# Deployment Guide

This project supports multiple runtime targets. The recommended production path is:

1. Frontend on Vercel
2. Backend/worker on Spark over SSH

## Frontend (Vercel)

1. Import the repository in [Vercel](https://vercel.com).
2. Set **Root Directory** to `frontend`.
3. Set environment variable:
   - `NEXT_PUBLIC_API_URL`: public backend URL (Spark API base URL).
4. Deploy.

### Vercel Credit Guard (Enabled)

Frontend project uses `frontend/vercel.json` `ignoreCommand`:

- `frontend/scripts/vercel-ignore.sh`

Behavior:

- Skips Vercel build when commit does not affect frontend-relevant paths.
- Continues build when frontend files changed.
- Manual override supported with env var: `FORCE_VERCEL_BUILD=1`.

## Backend (Spark, Recommended)

### Option A: GitHub Actions workflow

Use workflow: `Deploy Spark Runtime` (`.github/workflows/deploy-spark.yml`).
Automatic chain is also available: `Publish Service Images` success on `main` auto-dispatches pinned Spark deploy (`.github/workflows/deploy-spark-after-publish.yml`).
Both paths now run a runner-heartbeat guard first; if `spark-self-hosted` is offline,
deploy dispatch is blocked with a deterministic error instead of staying queued.

Self-hosted runner runbook:

- `docs/SPARK_SELF_HOSTED_RUNNER.md`
- `docs/SUPPLY_CHAIN_SECURITY.md`
- `docs/COST_GOVERNANCE.md`
- `docs/SLO_OBSERVABILITY.md`
- `deploy/monitoring/grafana/runtime-observability-dashboard.json`
- `deploy/monitoring/prometheus/provenance-alert-rules.yml`

Required repository secrets:

- `SPARK_SSH_HOST`
- `SPARK_SSH_USER`
- `SPARK_SSH_KEY`
- `SPARK_SSH_PORT` (optional, default `22`)

Optional repository variables:

- `SPARK_REMOTE_DIR`
- `SPARK_PUBLIC_API_URL`
- `SPARK_DEPLOY_FRONTEND`
- `SPARK_USE_PINNED_IMAGES`
- `SPARK_RUN_SMOKE`
- `SPARK_ROLLBACK_ON_SMOKE_FAILURE`
- `SPARK_VERIFY_SIGNATURES` (default recommended: `true`)
- `PRODUCTION_API_URL` (enables runtime observability report from `/metrics`)
- `PRODUCTION_API_KEY_HEADER` (defaults to `X-API-Key` when API key auth is required)
- `CVE_FAIL_ON_CRITICAL` (default `true`)
- `CVE_FAIL_ON_HIGH` (default `false`)
- `CVE_MAX_CRITICAL` (default `0`)
- `CVE_MAX_HIGH` (default `25`)

Optional repository secrets:

- `PRODUCTION_API_KEY` (only if `/metrics` is protected)

Pinned image mode (recommended for reproducibility):

- `use_pinned_images=true`
- `image_tag=<commit_sha>` (or leave default to workflow SHA)
- `verify_signatures=true` (cosign keyless verification gate)

For Spark ARM64 hosts, publish multi-arch images first (`linux/amd64,linux/arm64`).
`Publish Service Images` now signs pushed images with keyless cosign. `Deploy Spark Runtime`
verifies signatures (certificate identity = `publish-images.yml` on `main`) before deploy when
`use_pinned_images=true` and `verify_signatures=true`.
Deploy also verifies SBOM attestations (`spdxjson`) before rollout in pinned mode.
Daily integrity checks run in `.github/workflows/verify-production-images.yml` against latest tags.

This deploys:

- `ghcr.io/<owner>/provenance-api:<image_tag>`
- `ghcr.io/<owner>/provenance-worker:<image_tag>`

with rollback-on-smoke support.

Production deploy example (self-hosted runner + pinned images):

```bash
gh workflow run deploy-spark.yml \
  -f use_pinned_images=true \
  -f image_tag=<commit_sha> \
  -f verify_signatures=true \
  -f deploy_frontend=false \
  -f run_smoke=true \
  -f rollback_on_smoke_failure=true \
  -f runner_type=self-hosted \
  -f cost_override=false
```

Latest validated production-style run:

- Commit SHA: `5420984dea938b57f349fa9e8408ec581828e966`
- Run: [Deploy Spark Runtime #22615452126](https://github.com/ogulcanaydogan/AI-Provenance-Tracker/actions/runs/22615452126)
- Result: `Deploy to Spark` executed (non-skipped) and smoke test passed.

Deploy Runtime (Pinned SHA, Legacy) smoke routing is runtime-aware:

- Helm path smoke URL priority:
  - `workflow_dispatch` input `smoke_base_url_helm`
  - `vars.SPARK_PUBLIC_API_URL`
  - hard-fail if both are empty
- Railway path smoke URL priority:
  - `workflow_dispatch` input `smoke_base_url_railway`
  - `secrets.PRODUCTION_API_URL`
  - hard-fail if both are empty
- Smoke and rollback decisions are target-specific (`smoke_gate_helm` / `smoke_gate_railway`).

Cost gate note:

- `Deploy Spark Runtime` is subject to cost-policy block mode.
- For emergency/manual override, dispatch with `cost_override=true`.

### Option B: Manual SSH deploy script

```bash
./scripts/deploy_spark.sh
```

Pinned image mode:

```bash
SPARK_USE_PINNED_IMAGES=true \
SPARK_BACKEND_IMAGE=ghcr.io/<owner>/provenance-api:<commit_sha> \
SPARK_WORKER_IMAGE=ghcr.io/<owner>/provenance-worker:<commit_sha> \
./scripts/deploy_spark.sh
```

Include frontend on Spark:

```bash
SPARK_DEPLOY_FRONTEND=true ./scripts/deploy_spark.sh
```

## Kubernetes/AWS (Alternative)

### Helm (Kubernetes)

```bash
helm upgrade --install provenance deploy/helm/provenance-stack \
  --namespace provenance --create-namespace \
  --set api.image.repository=ghcr.io/ogulcanaydogan/provenance-api \
  --set api.image.tag=<commit_sha> \
  --set worker.image.repository=ghcr.io/ogulcanaydogan/provenance-worker \
  --set worker.image.tag=<commit_sha>
```

### Terraform (AWS ECS + RDS + ALB)

```bash
cd deploy/terraform/aws
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

## Post-deploy checks

- `GET /health`
- `POST /api/v1/detect/text`
- `POST /api/v1/detect/image`
- Optional smoke: `backend/scripts/smoke_detect_prod.py`

## Notes

- Railway deployment path is maintained only for legacy compatibility.
- For visa-grade evidence, keep pinned image tags and benchmark artifacts per release.
