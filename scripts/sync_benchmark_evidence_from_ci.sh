#!/usr/bin/env bash

set -euo pipefail

DEST_DIR_INPUT="${1:-benchmark/results/latest}"
WORKFLOW_NAME="${WORKFLOW_NAME:-Publish Benchmark Leaderboard}"
ARTIFACT_NAME="${ARTIFACT_NAME:-benchmark-run-artifacts}"
ARTIFACT_BRANCH="${ARTIFACT_BRANCH:-main}"
ARTIFACT_SEARCH_LIMIT="${ARTIFACT_SEARCH_LIMIT:-25}"
TARGET_PROFILE="${TARGET_PROFILE:-full_v3}"

REQUIRED_FILES=(
  benchmark_results.json
  regression_check.json
  regression_check.md
  dataset_health.json
  dataset_health.md
  scored_samples.jsonl
  baseline_results.md
)

abspath() {
  python3 - <<'PY' "$1"
import os
import sys

print(os.path.abspath(os.path.expanduser(sys.argv[1])))
PY
}

resolve_repo() {
  if [ -n "${GITHUB_REPOSITORY:-}" ]; then
    printf "%s" "$GITHUB_REPOSITORY"
    return 0
  fi

  repo="$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null || true)"
  if [ -n "$repo" ]; then
    printf "%s" "$repo"
    return 0
  fi

  remote_url="$(git config --get remote.origin.url 2>/dev/null || true)"
  if [ -z "$remote_url" ]; then
    return 1
  fi
  remote_url="${remote_url%.git}"
  remote_url="${remote_url#git@github.com:}"
  remote_url="${remote_url#https://github.com/}"
  if [ -z "$remote_url" ]; then
    return 1
  fi
  printf "%s" "$remote_url"
}

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required."
  exit 1
fi

if ! gh api user >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated for API calls. Run: gh auth login"
  exit 1
fi

REPO_SLUG="$(resolve_repo || true)"
if [ -z "$REPO_SLUG" ]; then
  echo "Could not resolve repository slug."
  exit 1
fi

DEST_DIR="$(abspath "$DEST_DIR_INPUT")"
mkdir -p "$DEST_DIR"

mapfile -t run_rows < <(
  gh run list \
    --repo "$REPO_SLUG" \
    --workflow "$WORKFLOW_NAME" \
    --branch "$ARTIFACT_BRANCH" \
    --status success \
    --limit "$ARTIFACT_SEARCH_LIMIT" \
    --json databaseId,url \
    --jq '.[] | "\(.databaseId)\t\(.url)"'
)

if [ "${#run_rows[@]}" -eq 0 ]; then
  echo "No successful runs found for workflow '$WORKFLOW_NAME' on '$ARTIFACT_BRANCH'."
  exit 1
fi

selected_run_id=""
selected_run_url=""
tmp_dir=""

for row in "${run_rows[@]}"; do
  run_id="${row%%$'\t'*}"
  run_url="${row#*$'\t'}"
  attempt_dir="$(mktemp -d)"
  if gh run download "$run_id" --repo "$REPO_SLUG" -n "$ARTIFACT_NAME" -D "$attempt_dir" >/dev/null 2>&1; then
    selected_run_id="$run_id"
    selected_run_url="$run_url"
    tmp_dir="$attempt_dir"
    break
  fi
  rm -rf "$attempt_dir"
done

if [ -z "$selected_run_id" ] || [ -z "$tmp_dir" ]; then
  echo "Could not download artifact '$ARTIFACT_NAME' from recent successful runs."
  exit 1
fi

for filename in "${REQUIRED_FILES[@]}"; do
  source_file="$(find "$tmp_dir" -type f -name "$filename" -print -quit || true)"
  if [ -z "$source_file" ]; then
    echo "Missing required file in artifact: $filename"
    rm -rf "$tmp_dir"
    exit 1
  fi
  cp "$source_file" "$DEST_DIR/$filename"
done

python3 - <<'PY' "$DEST_DIR/evidence_lock.json" "$selected_run_id" "$selected_run_url" "$WORKFLOW_NAME" "$ARTIFACT_NAME" "$TARGET_PROFILE"
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

output = Path(sys.argv[1])
payload = {
    "run_id": sys.argv[2],
    "run_url": sys.argv[3],
    "source_workflow": sys.argv[4],
    "artifact_name": sys.argv[5],
    "profile": sys.argv[6],
    "synced_at": datetime.now(UTC).isoformat(),
}
output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote evidence lock: {output}")
PY

rm -rf "$tmp_dir"

echo "Synced benchmark evidence from run: $selected_run_id"
echo "Run URL: $selected_run_url"
echo "Destination: $DEST_DIR"
