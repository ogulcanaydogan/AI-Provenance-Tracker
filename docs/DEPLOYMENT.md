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

Self-hosted runner runbook:

- `docs/SPARK_SELF_HOSTED_RUNNER.md`

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

Pinned image mode (recommended for reproducibility):

- `use_pinned_images=true`
- `image_tag=<commit_sha>` (or leave default to workflow SHA)

For Spark ARM64 hosts, publish multi-arch images first (`linux/amd64,linux/arm64`).

This deploys:

- `ghcr.io/<owner>/provenance-api:<image_tag>`
- `ghcr.io/<owner>/provenance-worker:<image_tag>`

with rollback-on-smoke support.

Production deploy example (self-hosted runner + pinned images):

```bash
gh workflow run deploy-spark.yml \
  -f use_pinned_images=true \
  -f image_tag=<commit_sha> \
  -f deploy_frontend=false \
  -f run_smoke=true \
  -f rollback_on_smoke_failure=true \
  -f runner_type=self-hosted
```

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
