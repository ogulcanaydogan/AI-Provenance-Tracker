# Helm Deployment (Provenance-as-a-Service)

Chart path: `deploy/helm/provenance-stack`

## Components
- `api` deployment (`uvicorn app.main:app`)
- `worker` deployment (`python -m app.worker.main`)
- optional in-cluster `postgres` StatefulSet

## Install
```bash
helm upgrade --install provenance deploy/helm/provenance-stack \
  --namespace provenance --create-namespace \
  --set api.image.repository=ghcr.io/ogulcanaydogan/provenance-api \
  --set api.image.tag=latest \
  --set worker.image.repository=ghcr.io/ogulcanaydogan/provenance-worker \
  --set worker.image.tag=latest \
  --set secrets.xBearerToken="$X_BEARER_TOKEN"
```

## External Postgres
Use managed Postgres by disabling bundled DB and setting URL:
```bash
helm upgrade --install provenance deploy/helm/provenance-stack \
  --set postgres.enabled=false \
  --set externalDatabase.enabled=true \
  --set externalDatabase.url='postgresql+asyncpg://user:pass@host:5432/provenance'
```
