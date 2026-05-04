#!/usr/bin/env bash
#
# Starts the backend + frontend dev servers together for visual testing.
#   backend  (uvicorn)   → http://127.0.0.1:8080
#   frontend (Vite, HMR) → http://127.0.0.1:5173
# Ctrl+C stops both.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${REPO_ROOT}/config.yaml"

usage() {
  cat <<'EOF'
usage: scripts/dev.sh [--config <path>]

Visit http://127.0.0.1:5173 to see the SPA with HMR.
Ctrl+C stops both servers.
EOF
}

while (( $# )); do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done

command -v uv  >/dev/null || { echo "error: uv not on PATH (see https://docs.astral.sh/uv/)" >&2; exit 1; }
command -v npm >/dev/null || { echo "error: npm not on PATH (Node 20.x required)" >&2; exit 1; }

if [[ ! -f "${CONFIG}" ]]; then
  echo "error: config not found at ${CONFIG}" >&2
  echo "       edit ${REPO_ROOT}/config.yaml with real paths first" >&2
  exit 1
fi

cleanup() {
  trap '' EXIT INT TERM
  printf '\n→ stopping dev servers\n'
  kill 0 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "→ backend  → http://127.0.0.1:8080 (config: ${CONFIG#"${REPO_ROOT}/"})"
( cd "${REPO_ROOT}" && uv run mame-curator serve --config "${CONFIG}" --no-open-browser ) &

echo "→ frontend → http://127.0.0.1:5173 (HMR)"
echo
echo "Visit http://127.0.0.1:5173 — Ctrl+C to stop both servers."
echo

( cd "${REPO_ROOT}/frontend" && npm run dev )
