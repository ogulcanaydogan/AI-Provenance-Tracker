#!/usr/bin/env bash

set -euo pipefail

# Vercel "ignoreCommand" semantics:
# - exit 0 => skip build/deploy
# - exit 1 => continue build/deploy
#
# This script keeps Vercel credits focused on frontend-impacting changes.

if [ "${FORCE_VERCEL_BUILD:-0}" = "1" ]; then
  echo "FORCE_VERCEL_BUILD=1 -> continue build."
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git checkout -> continue build."
  exit 1
fi

head_ref="${VERCEL_GIT_COMMIT_SHA:-HEAD}"
base_ref="${VERCEL_GIT_PREVIOUS_SHA:-}"

if [ -z "${base_ref}" ] || ! git cat-file -e "${base_ref}^{commit}" >/dev/null 2>&1; then
  if git rev-parse "${head_ref}^" >/dev/null 2>&1; then
    base_ref="$(git rev-parse "${head_ref}^")"
  else
    echo "No valid base commit -> continue build."
    exit 1
  fi
fi

changed_files="$(git diff --name-only "${base_ref}" "${head_ref}" || true)"

if [ -z "${changed_files}" ]; then
  echo "No changed files -> skip build."
  exit 0
fi

frontend_change_regex='^(frontend/|src/|public/|app/|components/|hooks/|lib/|e2e/|next\.config\.(ts|js|mjs|cjs)$|package(-lock)?\.json$|tsconfig\.json$|tailwind\.config\.(ts|js|cjs|mjs)$|postcss\.config\.(ts|js|cjs|mjs)$|eslint\.config\.(ts|js|cjs|mjs)$|vitest\.config\.(ts|js|cjs|mjs)$|playwright\.config\.(ts|js|cjs|mjs)$|vercel\.json$|Dockerfile$)'

if printf '%s\n' "${changed_files}" | grep -E -q "${frontend_change_regex}"; then
  echo "Frontend-impacting changes detected -> continue build."
  exit 1
fi

echo "No frontend-impacting changes detected -> skip build."
exit 0
