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
