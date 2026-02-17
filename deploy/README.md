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
- `.github/workflows/deploy-runtime.yml` deploys pinned SHA images to Helm and/or Railway:
  - `ghcr.io/<owner>/provenance-api:<commit-sha>`
  - `ghcr.io/<owner>/provenance-worker:<commit-sha>`

## Runtime Deploy Workflow Setup

Set repository variables to control automatic deploy target after image publish:

- `ENABLE_HELM_DEPLOY=true` to enable Helm auto-deploy
- `ENABLE_RAILWAY_DEPLOY=true` to enable Railway auto-deploy
- `DEPLOY_ENVIRONMENT=production` to use GitHub Environments (approval gates if configured)
- `ENABLE_DEPLOY_SMOKE_GATE=true` to run post-deploy production smoke tests
- `ENABLE_AUTO_ROLLBACK=true` to rollback to previous successful image SHA when smoke fails

Smoke gate secrets/variables:

- Secret: `PRODUCTION_API_URL` (required when smoke gate is enabled)
- Secret: `PRODUCTION_API_KEY` (optional)
- Variable: `PRODUCTION_API_KEY_HEADER` (default: `X-API-Key`)

Smoke + rollback behavior:

- Smoke test uses `backend/scripts/smoke_detect_prod.py`
- Rollback candidate is resolved from the previous successful `publish-images` workflow SHA
- Workflow always uploads `deploy-runtime-summary` artifact with deploy/smoke/rollback results

Helm variables/secrets:

- Variable: `HELM_RELEASE_NAME` (default: `provenance`)
- Variable: `HELM_NAMESPACE` (default: `provenance`)
- Secret: `KUBE_CONFIG_DATA` (base64 or plain kubeconfig)

Railway variables/secrets:

- Secret: `RAILWAY_TOKEN`
- Variable: `RAILWAY_PROJECT` (project ID or name)
- Variable: `RAILWAY_ENVIRONMENT` (environment ID or name)
- Variable: `RAILWAY_API_SERVICE` (service name or ID)
- Variable: `RAILWAY_WORKER_SERVICE` (optional)
- Variable: `RAILWAY_WORKSPACE` (optional)

Railway note:

- This workflow pins each service via `source.image=ghcr.io/...:<sha>`.
- If your current service is GitHub-source only, switch it once to Docker-image deployment first.

Manual deploy examples from GitHub Actions:

- `runtime_target=helm` deploys only Helm
- `runtime_target=railway` deploys only Railway
- `runtime_target=both` deploys both
- Optional `image_tag=<sha>` overrides the default triggering commit SHA
