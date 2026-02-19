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
SPARK_USE_PINNED_IMAGES="${SPARK_USE_PINNED_IMAGES:-auto}"
SPARK_BACKEND_IMAGE="${SPARK_BACKEND_IMAGE:-}"
SPARK_WORKER_IMAGE="${SPARK_WORKER_IMAGE:-}"

if [ "${SPARK_USE_PINNED_IMAGES}" = "auto" ]; then
  if [ -n "${SPARK_BACKEND_IMAGE}" ] || [ -n "${SPARK_WORKER_IMAGE}" ]; then
    SPARK_USE_PINNED_IMAGES="true"
  else
    SPARK_USE_PINNED_IMAGES="false"
  fi
fi

if [ "${SPARK_USE_PINNED_IMAGES}" != "true" ] && [ "${SPARK_USE_PINNED_IMAGES}" != "false" ]; then
  echo "SPARK_USE_PINNED_IMAGES must be true, false, or auto."
  exit 1
fi

if [ "${SPARK_USE_PINNED_IMAGES}" = "true" ]; then
  if [ -z "${SPARK_BACKEND_IMAGE}" ] || [ -z "${SPARK_WORKER_IMAGE}" ]; then
    echo "Pinned image mode requires both SPARK_BACKEND_IMAGE and SPARK_WORKER_IMAGE."
    exit 1
  fi
  default_compose_files="docker-compose.spark.yml docker-compose.spark.images.yml"
else
  default_compose_files="docker-compose.spark.yml"
fi

SPARK_COMPOSE_FILES="${SPARK_COMPOSE_FILES:-${default_compose_files}}"

compose_args=""
for compose_file in ${SPARK_COMPOSE_FILES}; do
  compose_args="${compose_args} -f ${compose_file}"
done
REMOTE_COMPOSE_CMD="docker compose${compose_args} --env-file .env.spark"

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
SPARK_BACKEND_IMAGE=${SPARK_BACKEND_IMAGE}
SPARK_WORKER_IMAGE=${SPARK_WORKER_IMAGE}
EOF

echo "[3/4] Uploading remote env file (.env.spark)..."
scp -q "${tmp_env}" "${SPARK_HOST}:${SPARK_REMOTE_DIR}/.env.spark"

if [ "${SPARK_USE_PINNED_IMAGES}" = "true" ]; then
  echo "[4/4] Pulling pinned backend/worker images and starting services on ${SPARK_HOST}..."
else
  echo "[4/4] Building and starting services on ${SPARK_HOST}..."
fi
ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && ${REMOTE_COMPOSE_CMD} up -d db redis"

echo "Waiting for Postgres to become ready..."
ssh "${SPARK_HOST}" "
  set -euo pipefail
  cd '${SPARK_REMOTE_DIR}'
  for i in \$(seq 1 30); do
    if ${REMOTE_COMPOSE_CMD} exec -T db pg_isready -U postgres >/dev/null 2>&1; then
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

if [ "${SPARK_USE_PINNED_IMAGES}" = "true" ]; then
  ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && ${REMOTE_COMPOSE_CMD} pull backend worker"
  ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && ${REMOTE_COMPOSE_CMD} up -d backend worker"
else
  ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && ${REMOTE_COMPOSE_CMD} up -d --build backend worker"
fi

if [ "${SPARK_DEPLOY_FRONTEND}" = "true" ]; then
  echo "Starting frontend service..."
  ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && ${REMOTE_COMPOSE_CMD} up -d --build frontend"
else
  echo "Skipping frontend service on Spark (set SPARK_DEPLOY_FRONTEND=true to enable)."
  ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && ${REMOTE_COMPOSE_CMD} stop frontend >/dev/null 2>&1 || true"
fi

echo "Deployment complete. Remote service status:"
ssh "${SPARK_HOST}" "cd '${SPARK_REMOTE_DIR}' && ${REMOTE_COMPOSE_CMD} ps"

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
    ${REMOTE_COMPOSE_CMD} restart backend worker >/dev/null
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
    ${REMOTE_COMPOSE_CMD} logs --tail=60 backend worker
    exit 1
  fi

  curl -fsS 'http://127.0.0.1:${BACKEND_PORT}/health'
"
