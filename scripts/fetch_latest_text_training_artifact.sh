#!/usr/bin/env bash

set -euo pipefail

DEST_DIR_INPUT="${1:-benchmark/results/ci/training_bundle}"
WORKFLOW_NAME="${WORKFLOW_NAME:-Text Training Pipeline}"
ARTIFACT_NAME="${ARTIFACT_NAME:-text-training-artifacts-a100}"
ARTIFACT_BRANCH="${ARTIFACT_BRANCH:-main}"
ARTIFACT_SEARCH_LIMIT="${ARTIFACT_SEARCH_LIMIT:-20}"
REQUIRE_TRAINING_ARTIFACT="${REQUIRE_TRAINING_ARTIFACT:-false}"

abspath() {
  python3 - <<'PY' "$1"
import os
import sys

print(os.path.abspath(os.path.expanduser(sys.argv[1])))
PY
}

DEST_DIR="$(abspath "$DEST_DIR_INPUT")"

is_true() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|on) return 0 ;;
    *) return 1 ;;
  esac
}

require_fail="false"
if is_true "$REQUIRE_TRAINING_ARTIFACT"; then
  require_fail="true"
fi

if [ -z "${GH_TOKEN:-}" ] && [ -n "${GITHUB_TOKEN:-}" ]; then
  export GH_TOKEN="$GITHUB_TOKEN"
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required to fetch training artifacts."
  if [ "$require_fail" = "true" ]; then
    exit 1
  fi
  exit 0
fi

if [ -z "${GH_TOKEN:-}" ]; then
  echo "GH_TOKEN/GITHUB_TOKEN is required to fetch training artifacts."
  if [ "$require_fail" = "true" ]; then
    exit 1
  fi
  exit 0
fi

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

mapfile -t run_ids < <(
  gh run list \
    --workflow "$WORKFLOW_NAME" \
    --branch "$ARTIFACT_BRANCH" \
    --status success \
    --limit "$ARTIFACT_SEARCH_LIMIT" \
    --json databaseId \
    --jq '.[].databaseId'
)

if [ "${#run_ids[@]}" -eq 0 ]; then
  echo "No successful runs found for workflow '$WORKFLOW_NAME' on branch '$ARTIFACT_BRANCH'."
  if [ "$require_fail" = "true" ]; then
    exit 1
  fi
  exit 0
fi

selected_run_id=""
for run_id in "${run_ids[@]}"; do
  attempt_dir="$(mktemp -d)"
  if gh run download "$run_id" -n "$ARTIFACT_NAME" -D "$attempt_dir" >/dev/null 2>&1; then
    rm -rf "$DEST_DIR"
    mkdir -p "$DEST_DIR"
    cp -R "$attempt_dir"/. "$DEST_DIR"/
    selected_run_id="$run_id"
    rm -rf "$attempt_dir"
    break
  fi
  rm -rf "$attempt_dir"
done

if [ -z "$selected_run_id" ]; then
  echo "Could not download artifact '$ARTIFACT_NAME' from latest successful runs."
  if [ "$require_fail" = "true" ]; then
    exit 1
  fi
  exit 0
fi

latest_json="$(find "$DEST_DIR" -type f -path '*/backend/evidence/models/text/latest.json' -print -quit || true)"
model_dir=""
if [ -n "$latest_json" ]; then
  run_id="$(python3 - <<'PY' "$latest_json"
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload.get("run_id", ""))
PY
  )"
  if [ -n "$run_id" ]; then
    candidate="$DEST_DIR/backend/evidence/models/text/$run_id/model"
    if [ -d "$candidate" ]; then
      model_dir="$candidate"
    fi
  fi
fi

if [ -z "$model_dir" ]; then
  training_manifest="$(find "$DEST_DIR" -type f -name 'training_manifest.json' -print -quit || true)"
  if [ -n "$training_manifest" ]; then
    candidate="$(dirname "$training_manifest")/model"
    if [ -d "$candidate" ]; then
      model_dir="$candidate"
    else
      model_dir="$(dirname "$training_manifest")"
    fi
  fi
fi

calibration_profile="$(find "$DEST_DIR" -type f -path '*/backend/app/detection/text/calibration_profile.json' -print -quit || true)"

if [ -z "$model_dir" ] || [ ! -d "$model_dir" ]; then
  echo "Training artifact downloaded (run=$selected_run_id) but model directory is missing."
  if [ "$require_fail" = "true" ]; then
    exit 1
  fi
  exit 0
fi

has_model_weights="false"
if [ -f "$model_dir/model.safetensors" ] || [ -f "$model_dir/pytorch_model.bin" ]; then
  has_model_weights="true"
fi
if [ "$has_model_weights" != "true" ]; then
  echo "Training artifact downloaded (run=$selected_run_id) but no model weights found in $model_dir."
  if [ "$require_fail" = "true" ]; then
    exit 1
  fi
  exit 0
fi

if [ -z "$calibration_profile" ] || [ ! -f "$calibration_profile" ]; then
  echo "Training artifact downloaded (run=$selected_run_id) but calibration_profile.json is missing."
  if [ "$require_fail" = "true" ]; then
    exit 1
  fi
fi

model_dir="$(abspath "$model_dir")"
if [ -n "$calibration_profile" ] && [ -f "$calibration_profile" ]; then
  calibration_profile="$(abspath "$calibration_profile")"
fi

if [ -n "${GITHUB_ENV:-}" ]; then
  {
    echo "TEXT_TRAINING_ARTIFACT_RUN_ID=$selected_run_id"
    echo "TEXT_DETECTION_MODEL_PATH=$model_dir"
    if [ -n "$calibration_profile" ] && [ -f "$calibration_profile" ]; then
      echo "TEXT_CALIBRATION_PROFILE_PATH=$calibration_profile"
    fi
  } >> "$GITHUB_ENV"
fi

echo "Downloaded training artifact run: $selected_run_id"
echo "Resolved TEXT_DETECTION_MODEL_PATH=$model_dir"
if [ -n "$calibration_profile" ] && [ -f "$calibration_profile" ]; then
  echo "Resolved TEXT_CALIBRATION_PROFILE_PATH=$calibration_profile"
fi
