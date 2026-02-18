#!/usr/bin/env bash

set -euo pipefail

# Deploy this repository to DGX Spark over SSH and run docker compose remotely.
# Defaults are aligned with the user's SSH alias and requested target directory.

SPARK_HOST="${SPARK_HOST:-spark}"
SPARK_REMOTE_DIR="${SPARK_REMOTE_DIR:-/home/weezboo/ogulcan/ai-provenance-tracker}"

BACKEND_PORT="${SPARK_BACKEND_PORT:-8010}"
FRONTEND_PORT="${SPARK_FRONTEND_PORT:-3020}"
POSTGRES_PORT="${SPARK_POSTGRES_PORT:-5433}"
REDIS_PORT="${SPARK_REDIS_PORT:-6380}"

SPARK_PUBLIC_API_URL="${SPARK_PUBLIC_API_URL:-http://100.80.116.20:${BACKEND_PORT}}"
X_BEARER_TOKEN="${X_BEARER_TOKEN:-${APT_X_BEARER_TOKEN:-}}"
SPARK_DEPLOY_FRONTEND="${SPARK_DEPLOY_FRONTEND:-false}"

echo "[1/4] Verifying SSH connectivity to ${SPARK_HOST}..."
ssh -o BatchMode=yes "${SPARK_HOST}" "echo connected:\$(hostname):\$(whoami)"

echo "[2/4] Syncing repository to ${SPARK_HOST}:${SPARK_REMOTE_DIR} ..."
ssh "${SPARK_HOST}" "mkdir -p '${SPARK_REMOTE_DIR}'"
rsync -az --delete \
  --exclude ".git" \
  --exclude ".venv" \
  --exclude ".pytest_cache" \
  --exclude ".mypy_cache" \
  --exclude ".ruff_cache" \
  --exclude "backend/.venv" \
  --exclude "backend/evidence/runs" \
  --exclude "backend/evidence/smoke" \
  --exclude "frontend/node_modules" \
  --exclude "frontend/.next" \
  --exclude "frontend/out" \
  --exclude ".DS_Store" \
  ./ "${SPARK_HOST}:${SPARK_REMOTE_DIR}/"

tmp_env="$(mktemp)"
cleanup() {
  rm -f "${tmp_env}"
}
trap cleanup EXIT

cat > "${tmp_env}" <<EOF
BACKEND_PORT=${BACKEND_PORT}
FRONTEND_PORT=${FRONTEND_PORT}
POSTGRES_PORT=${POSTGRES_PORT}
REDIS_PORT=${REDIS_PORT}
DEBUG=false
NEXT_PUBLIC_API_URL=${SPARK_PUBLIC_API_URL}
X_BEARER_TOKEN=${X_BEARER_TOKEN}
EOF

echo "[3/4] Uploading remote env file (.env.spark)..."
scp -q "${tmp_env}" "${SPARK_HOST}:${SPARK_REMOTE_DIR}/.env.spark"

echo "[4/4] Building and starting services on ${SPARK_HOST}..."
ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && docker compose --env-file .env.spark up -d --build db redis"

echo "Waiting for Postgres to become ready..."
ssh "${SPARK_HOST}" "
  set -euo pipefail
  cd '${SPARK_REMOTE_DIR}'
  for i in \$(seq 1 30); do
    if docker compose --env-file .env.spark exec -T db pg_isready -U postgres >/dev/null 2>&1; then
      echo 'Postgres is ready.'
      break
    fi
    sleep 1
    if [ \"\$i\" -eq 30 ]; then
      echo 'Postgres did not become ready in time.'
      exit 1
    fi
  done
"

ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && docker compose --env-file .env.spark up -d --build backend worker"

if [ "${SPARK_DEPLOY_FRONTEND}" = "true" ]; then
  echo "Starting frontend service..."
  ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && docker compose --env-file .env.spark up -d --build frontend"
else
  echo "Skipping frontend service on Spark (set SPARK_DEPLOY_FRONTEND=true to enable)."
  ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && docker compose --env-file .env.spark stop frontend >/dev/null 2>&1 || true"
fi

echo "Deployment complete. Remote service status:"
ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && docker compose --env-file .env.spark ps"

echo "API health check (via SSH):"
ssh "${SPARK_HOST}" "
  set -euo pipefail
  cd '${SPARK_REMOTE_DIR}'
  ok=0
  for i in \$(seq 1 15); do
    if curl -fsS 'http://127.0.0.1:${BACKEND_PORT}/health' >/dev/null 2>&1; then
      ok=1
      break
    fi
    sleep 1
  done

  if [ \"\$ok\" -ne 1 ]; then
    echo 'Initial health check failed; restarting backend/worker once...'
    docker compose --env-file .env.spark restart backend worker >/dev/null
    sleep 3
    for i in \$(seq 1 15); do
      if curl -fsS 'http://127.0.0.1:${BACKEND_PORT}/health' >/dev/null 2>&1; then
        ok=1
        break
      fi
      sleep 1
    done
  fi

  if [ \"\$ok\" -ne 1 ]; then
    echo 'API health check failed after retries.'
    docker compose --env-file .env.spark logs --tail=60 backend worker
    exit 1
  fi

  curl -fsS 'http://127.0.0.1:${BACKEND_PORT}/health'
"
