#!/usr/bin/env bash
#
# local-CI.sh — run the exact same checks as .github/workflows/ci.yml locally.
#
# This is a faithful local mirror of the GitHub CI workflow. Every command
# below is byte-for-byte the command CI runs, in the same order, grouped by
# the same three jobs (lint-types-test / frontend-lint-types-test / gitleaks).
# A clean run here means CI will pass — with two inherent caveats that a single
# local machine cannot reproduce:
#
#   1. OS matrix. CI runs the backend job on ubuntu-latest, macos-latest, AND
#      windows-latest. This script runs on the local OS only. Cross-platform
#      code paths (Windows path semantics, macOS fsync) are only exercised on
#      CI's other runners.
#      This caveat has bitten once for real (mame-curator-1088): a test that
#      shells out to `bash` passed every local gate and reddened both Windows
#      legs. The class is now caught locally by
#      tests/docs/test_posix_only_tests_skip_on_win32.py, which runs inside
#      the `pytest` step below. When you add a check that can only fail on a
#      runner this script cannot be, add the local stand-in there rather than
#      widening this caveat.
#   2. Python matrix. CI runs the backend job on Python 3.12 AND 3.13. This
#      script runs on whatever interpreter `uv` resolves for the project.
#
# Everything else — the tool versions (uv-managed deps, gitleaks 8.30.1, the
# Node version from frontend/package.json engines.node), the command flags, the
# step order — matches CI exactly. Keep this file and ci.yml in lockstep: when
# one changes, change the other.
#
# This script runs BEFORE EVERY PUSH — that is the standing rule, and it is
# wired as a pre-commit `pre-push` hook (`local-ci` in .pre-commit-config.yaml).
# Enable it once per clone with:
#     uv run pre-commit install --hook-type pre-push
# Running it by hand first is still the faster loop; the hook is the backstop.
#
# Exemption (user rule, 2026-08-03): a DOC-ONLY push may skip this run —
# `git push --no-verify` — when the diff touches no executable surface
# (*.md, docs/, ROADMAP, CHANGELOG). Anything that can change behaviour,
# including this script, the workflows, and the shell bootstraps, runs it.
#
# Usage:
#   ./local-CI.sh            # run all checks against the already-installed env
#   ./local-CI.sh --fresh    # provision first (uv sync --extra dev + npm ci),
#                            # exactly as CI's cold-start "Install dependencies"
#                            # steps do, then run the checks
#
# Note: a bare `uv run <project-command>` (e.g. `uv run mame-curator serve`)
# re-syncs WITHOUT `--extra dev` and silently removes pytest-cov et al, after
# which the `pytest` step below fails on unrecognised --cov arguments. Recover
# with `uv sync --extra dev`, or just use `--fresh`.
#
# Exit code: 0 iff every check passed; 1 otherwise. Unlike CI (which fail-fasts
# each job on the first failing step), this script runs ALL checks and prints a
# summary at the end, so one pass surfaces every failure. The pinned tool
# versions and commands are identical either way.

set -uo pipefail

# Always operate from the repo root (the directory this script lives in).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

FRESH=0
for arg in "$@"; do
    case "$arg" in
        --fresh) FRESH=1 ;;
        -h|--help) sed -n '2,40p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "unknown argument: $arg (see --help)" >&2; exit 2 ;;
    esac
done

# ANSI helpers (fall back to plain text when stdout is not a TTY).
if [[ -t 1 ]]; then
    BOLD=$'\033[1m'; RED=$'\033[31m'; GREEN=$'\033[32m'; DIM=$'\033[2m'; RESET=$'\033[0m'
else
    BOLD=""; RED=""; GREEN=""; DIM=""; RESET=""
fi

FAILURES=()

# run <label> <command...> — echo the exact command, run it, record pass/fail.
run() {
    local label="$1"; shift
    echo
    echo "${BOLD}▶ ${label}${RESET}"
    echo "${DIM}\$ $*${RESET}"
    if "$@"; then
        echo "${GREEN}✓ ${label}${RESET}"
    else
        echo "${RED}✗ ${label} (exit $?)${RESET}"
        FAILURES+=("$label")
    fi
}

# run_in <dir> <label> <command...> — same, but from a subdirectory (frontend).
run_in() {
    local dir="$1"; shift
    local label="$1"; shift
    echo
    echo "${BOLD}▶ ${label}${RESET}"
    echo "${DIM}\$ (cd $dir && $*)${RESET}"
    if ( cd "$dir" && "$@" ); then
        echo "${GREEN}✓ ${label}${RESET}"
    else
        echo "${RED}✗ ${label} (exit $?)${RESET}"
        FAILURES+=("$label")
    fi
}

echo "${BOLD}=== local-CI.sh — mirror of .github/workflows/ci.yml ===${RESET}"
echo "Repo:    $REPO_ROOT"
echo "OS:      $(uname -srm)"
echo "Python:  $(uv run python --version 2>/dev/null || echo '(uv not resolved yet)')"
echo "Node:    $(node --version 2>/dev/null || echo '(node not found)')"

# --- Optional provisioning (CI's "Install dependencies" steps) ---------------
if [[ "$FRESH" -eq 1 ]]; then
    run "Provision backend (uv sync --extra dev)" uv sync --extra dev
    run_in frontend "Provision frontend (npm ci)" npm ci
fi

# --- Job 1: lint-types-test (backend) ----------------------------------------
# Order matches ci.yml exactly: ruff check → ruff format --check → mypy →
# bandit → pytest → api-type-sync.
run "Ruff check"                uv run ruff check
run "Ruff format check"         uv run ruff format --check
run "mypy"                      uv run mypy
run "Bandit"                    uv run bandit -c pyproject.toml -r src
run "pytest"                    uv run pytest
run "API type sync (Python ↔ TS)" python3 tools/check_api_types_sync.py

# --- Job 2: frontend-lint-types-test -----------------------------------------
# ci.yml sets `working-directory: frontend`; we mirror via run_in. Order:
# ESLint → build (tsc -b && vite build) → Vitest.
if [[ ! -d frontend/node_modules ]]; then
    echo
    echo "${RED}✗ frontend/node_modules is missing — run './local-CI.sh --fresh' (or 'cd frontend && npm ci') first${RESET}"
    FAILURES+=("frontend deps missing")
else
    run_in frontend "ESLint"                   npm run lint
    run_in frontend "Build (type-check + bundle)" npm run build
    run_in frontend "Vitest"                   npm test
fi

# --- Job 3: gitleaks (secret scan) -------------------------------------------
# ci.yml pins GITLEAKS_VERSION 8.30.1 and runs a full-repo scan.
if command -v gitleaks >/dev/null 2>&1; then
    run "gitleaks (secret scan)" gitleaks detect --verbose --redact --no-banner --exit-code 1
else
    echo
    echo "${RED}✗ gitleaks not installed (CI pins 8.30.1) — install it to match CI${RESET}"
    FAILURES+=("gitleaks not installed")
fi

# --- Summary -----------------------------------------------------------------
echo
echo "${BOLD}=== Summary ===${RESET}"
if [[ ${#FAILURES[@]} -eq 0 ]]; then
    echo "${GREEN}${BOLD}All checks passed.${RESET} CI should be green (modulo the OS/Python matrix — see header)."
    exit 0
else
    echo "${RED}${BOLD}${#FAILURES[@]} check(s) failed:${RESET}"
    for f in "${FAILURES[@]}"; do echo "  ${RED}✗ $f${RESET}"; done
    exit 1
fi
