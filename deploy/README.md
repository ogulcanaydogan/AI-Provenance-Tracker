# Deployment Artifacts

- Helm chart: `deploy/helm/provenance-stack`
- AWS Terraform stack: `deploy/terraform/aws`

This is the deployable Provenance-as-a-Service baseline:
- `provenance-api` (FastAPI)
- `provenance-worker` (scheduler + webhook retries)
- Postgres backing store

CI/CD workflows:
- `.github/workflows/publish-images.yml` publishes service images to GHCR:
  - `ghcr.io/<owner>/provenance-api:latest`
  - `ghcr.io/<owner>/provenance-worker:latest`
- `.github/workflows/deploy-spark.yml` is the primary production deploy path (SSH to Spark + docker compose).
- `.github/workflows/deploy-runtime.yml` is legacy/manual deploy for pinned SHA images to Helm and/or Railway:
  - `ghcr.io/<owner>/provenance-api:<commit-sha>`
  - `ghcr.io/<owner>/provenance-worker:<commit-sha>`
  - deploy phase resolves immutable refs: `ghcr.io/<owner>/provenance-api@sha256:...`
  - deploy phase resolves immutable refs: `ghcr.io/<owner>/provenance-worker@sha256:...`

## Runtime Deploy Workflow Setup

Legacy runtime workflow is manual-only (`workflow_dispatch`) and no longer auto-triggers from image publish.
Set repository variables only if you want to use Helm/Railway via manual runtime deploy:

- `DEPLOY_ENVIRONMENT=production` to use GitHub Environments (approval gates if configured)
- `ENABLE_DEPLOY_SMOKE_GATE=true` to run post-deploy production smoke tests
- `ENABLE_AUTO_ROLLBACK=true` to rollback to previous successful image SHA when smoke fails
- `ENABLE_COSIGN_VERIFY=true` to verify image signatures before deploy/rollback

Smoke gate secrets/variables:

- Secret: `PRODUCTION_API_URL` (required when smoke gate is enabled)
- Secret: `PRODUCTION_API_KEY` (optional)
- Variable: `PRODUCTION_API_KEY_HEADER` (default: `X-API-Key`)

Smoke + rollback behavior:

- Smoke test uses `backend/scripts/smoke_detect_prod.py`
- Rollback candidate is resolved from the previous successful `publish-images` workflow SHA
- Workflow always uploads `deploy-runtime-summary` artifact with deploy/smoke/rollback results
- Runtime deploy uses digest-pinned image refs (`@sha256`) for Helm and Railway
- When cosign verification is enabled, unsigned/invalid images are blocked

Cosign verification setup (optional):

- Secret: `COSIGN_PUBLIC_KEY` (required when `ENABLE_COSIGN_VERIFY=true`)

Helm variables/secrets:

- Variable: `HELM_RELEASE_NAME` (default: `provenance`)
- Variable: `HELM_NAMESPACE` (default: `provenance`)
- Secret: `KUBE_CONFIG_DATA` (base64 or plain kubeconfig)

Railway variables/secrets:

- Secret: `RAILWAY_API_TOKEN` (preferred)
- Secret: `RAILWAY_TOKEN` (fallback for compatibility)
- Variable: `RAILWAY_PROJECT` (project ID or name)
- Variable: `RAILWAY_ENVIRONMENT` (environment ID or name)
- Variable: `RAILWAY_API_SERVICE` (service name or ID)
- Variable: `RAILWAY_WORKER_SERVICE` (optional)
- Variable: `RAILWAY_WORKSPACE` (optional)

Railway note:

- This workflow pins each service via `source.image=ghcr.io/...@sha256:...`.
- If your current service is GitHub-source only, switch it once to Docker-image deployment first.
- Workflow runs a non-blocking `railway whoami` probe before deploy for diagnostics.

Spark workflow secrets/variables:

- Secret: `SPARK_SSH_HOST` (hostname or IP)
- Secret: `SPARK_SSH_USER`
- Secret: `SPARK_SSH_KEY` (private key content for deploy user)
- Secret: `SPARK_SSH_PORT` (optional, default `22`)
- Secret: `SPARK_SMOKE_API_KEY` (optional API key used by smoke checks)
- Secret: `OPS_ALERT_WEBHOOK_URL` (optional failure alert webhook for smoke/deploy failures)
- Variable: `SPARK_REMOTE_DIR` (optional, default `/home/weezboo/ogulcan/ai-provenance-tracker`)
- Variable: `SPARK_PUBLIC_API_URL` (optional, used for frontend build-time API URL)
- Variable: `SPARK_DEPLOY_FRONTEND` (optional `true|false`, default `false`)
- Variable: `SPARK_RUN_SMOKE` (optional `true|false`, default `true`)
- Variable: `SPARK_ROLLBACK_ON_SMOKE_FAILURE` (optional `true|false`, default `true`)
- Variable: `SPARK_SMOKE_API_KEY_HEADER` (optional, default `X-API-Key`)

Spark deploy script defaults to `docker-compose.spark.yml` (production-safe service commands and no dev bind mounts).
Spark workflow runs smoke checks after deploy and can automatically redeploy the previous commit on smoke failure.
Spark workflow auto-runs on `main` push when backend/deploy files change.
If Spark is on a private network (`100.80.x.x`, Tailscale), trigger `workflow_dispatch` with `runner_type=self-hosted`.

Manual deploy examples from GitHub Actions:

- `runtime_target=helm` deploys only Helm
- `runtime_target=railway` deploys only Railway
- `runtime_target=both` deploys both
- Optional `image_tag=<sha>` overrides the default triggering commit SHA
