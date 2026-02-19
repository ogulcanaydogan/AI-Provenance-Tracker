#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DATASETS_DIR="${DATASETS_DIR:-benchmark/datasets}"
OUTPUT_DIR="${OUTPUT_DIR:-benchmark/results/latest}"
LEADERBOARD_OUTPUT="${LEADERBOARD_OUTPUT:-benchmark/leaderboard/leaderboard.json}"
MODEL_ID="${MODEL_ID:-baseline-heuristic-v1.0-live}"
DECISION_THRESHOLD="${DECISION_THRESHOLD:-0.45}"
BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
API_KEY="${API_KEY:-}"
API_KEY_HEADER="${API_KEY_HEADER:-X-API-Key}"
LIVE_MODE="${LIVE_MODE:-true}"
AUTO_START_BACKEND="${AUTO_START_BACKEND:-true}"
AUTO_BACKEND_HOST="${AUTO_BACKEND_HOST:-127.0.0.1}"
AUTO_BACKEND_PORT="${AUTO_BACKEND_PORT:-8000}"
BASELINE_SNAPSHOT="${BASELINE_SNAPSHOT:-benchmark/baselines/public_benchmark_snapshot.json}"
SKIP_REGRESSION_CHECK="${SKIP_REGRESSION_CHECK:-false}"

is_true() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_python() {
  if [ -n "${1:-}" ]; then
    printf '%s' "$1"
    return 0
  fi
  if [ -x "${ROOT_DIR}/backend/.venv/bin/python" ]; then
    printf '%s' "${ROOT_DIR}/backend/.venv/bin/python"
    return 0
  fi
  if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
    printf '%s' "${ROOT_DIR}/.venv/bin/python"
    return 0
  fi
  printf '%s' "python3"
}

is_local_backend_url() {
  case "$1" in
    http://127.0.0.1:*|http://localhost:*|https://127.0.0.1:*|https://localhost:*) return 0 ;;
    *) return 1 ;;
  esac
}

to_abs_path() {
  case "$1" in
    /*) printf '%s' "$1" ;;
    *) printf '%s/%s' "$ROOT_DIR" "$1" ;;
  esac
}

OUTPUT_DIR_ABS="$(to_abs_path "$OUTPUT_DIR")"
BACKEND_LOG_PATH="${OUTPUT_DIR_ABS}/backend.log"
BACKEND_PID_PATH="${OUTPUT_DIR_ABS}/backend.pid"
HEALTH_URL="${BACKEND_URL%/}/health"
BENCHMARK_PYTHON="$(resolve_python "${BENCHMARK_PYTHON:-}")"
BACKEND_PYTHON="$(resolve_python "${BACKEND_PYTHON:-}")"

backend_pid=""
started_backend="false"

cleanup() {
  if [ "$started_backend" = "true" ] && [ -n "$backend_pid" ]; then
    kill "$backend_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

mkdir -p "$OUTPUT_DIR_ABS"

if is_true "$LIVE_MODE" && is_true "$AUTO_START_BACKEND"; then
  if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
    echo "Using existing backend at $BACKEND_URL"
  elif is_local_backend_url "$BACKEND_URL"; then
    echo "Starting local backend at ${AUTO_BACKEND_HOST}:${AUTO_BACKEND_PORT} for live benchmark..."
    (
      cd "$ROOT_DIR/backend"
      nohup "$BACKEND_PYTHON" -m uvicorn app.main:app \
        --host "$AUTO_BACKEND_HOST" \
        --port "$AUTO_BACKEND_PORT" \
        > "$BACKEND_LOG_PATH" 2>&1 &
      echo $! > "$BACKEND_PID_PATH"
    )

    backend_pid="$(cat "$BACKEND_PID_PATH")"
    started_backend="true"

    ready="false"
    for _ in $(seq 1 45); do
      if curl -fsS --max-time 2 "$HEALTH_URL" >/dev/null 2>&1; then
        ready="true"
        break
      fi
      sleep 1
    done

    if [ "$ready" != "true" ]; then
      echo "Backend did not become healthy at $HEALTH_URL"
      if [ -f "$BACKEND_LOG_PATH" ]; then
        tail -n 80 "$BACKEND_LOG_PATH" || true
      fi
      exit 1
    fi
  else
    echo "Skipping auto backend startup because BACKEND_URL is not local: $BACKEND_URL"
  fi
fi

cd "$ROOT_DIR"

"$BENCHMARK_PYTHON" benchmark/eval/run_public_benchmark.py \
  --datasets-dir "$DATASETS_DIR" \
  --output-dir "$OUTPUT_DIR" \
  --leaderboard-output "$LEADERBOARD_OUTPUT" \
  --model-id "$MODEL_ID" \
  --decision-threshold "$DECISION_THRESHOLD" \
  --backend-url "$BACKEND_URL" \
  --api-key "$API_KEY" \
  --api-key-header "$API_KEY_HEADER" \
  --live-mode "$LIVE_MODE"

if is_true "$SKIP_REGRESSION_CHECK"; then
  echo "Skipping regression check (SKIP_REGRESSION_CHECK=$SKIP_REGRESSION_CHECK)"
else
  "$BENCHMARK_PYTHON" benchmark/eval/check_benchmark_regression.py \
    --current "$OUTPUT_DIR/benchmark_results.json" \
    --baseline "$BASELINE_SNAPSHOT" \
    --report-json "$OUTPUT_DIR/regression_check.json" \
    --report-md "$OUTPUT_DIR/regression_check.md"
fi

echo "Benchmark pipeline completed. Artifacts: $OUTPUT_DIR"
