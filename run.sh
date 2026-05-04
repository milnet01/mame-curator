#!/usr/bin/env bash
#
# MAME Curator clone-and-run bootstrap (Linux / macOS).
#
# Provisions Python 3.12+ + uv + project deps, runs the interactive
# setup wizard if config.yaml is missing, then starts the server and
# opens a browser. Idempotent — running twice does the right thing on
# the second run.
#
# For developer dual-server (backend + Vite HMR), use scripts/dev.sh.

set -euo pipefail

cd "$(dirname "$0")"

# ---- 1. Python 3.12+ detection ---------------------------------------

if ! command -v python3 >/dev/null 2>&1; then
    cat >&2 <<'EOF'
error: python3 not found on PATH.

Install Python 3.12 or newer:
  openSUSE Tumbleweed:  sudo zypper in python313
  Ubuntu 24.04+:        sudo apt install python3.12
  Fedora:               sudo dnf install python3.12
  macOS (Homebrew):     brew install python@3.13

Then re-run ./run.sh.
EOF
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
    echo "error: Python ${PY_VERSION} is too old; need 3.12+." >&2
    exit 1
fi

# ---- 2. uv detection / install ---------------------------------------

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found — installing via the official installer (https://astral.sh/uv)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # The uv installer drops the binary in ~/.local/bin or ~/.cargo/bin.
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    if ! command -v uv >/dev/null 2>&1; then
        cat >&2 <<'EOF'
error: uv install completed but the binary isn't on PATH.

Open a new terminal (so your shell picks up the updated PATH) and
re-run ./run.sh — the second invocation will skip the install.
EOF
        exit 1
    fi
fi

# ---- 3. uv sync ------------------------------------------------------

echo "Syncing Python deps via uv..."
uv sync --quiet

# ---- 4. config.yaml — interactive setup if missing -------------------

if [ ! -f config.yaml ]; then
    echo
    echo "First run — let's get a starter config.yaml in place."
    echo "(You will be asked for paths to your MAME DAT, ROMs, etc.)"
    echo
    uv run mame-curator setup
    if [ ! -f config.yaml ]; then
        echo "error: setup did not produce config.yaml." >&2
        exit 1
    fi
fi

# ---- 5. serve --------------------------------------------------------

PORT=${PORT:-8080}
URL="http://127.0.0.1:${PORT}/"

echo
echo "Starting MAME Curator on ${URL}"
echo "(Ctrl-C to stop. Re-run ./run.sh anytime — it's idempotent.)"
echo

# Open the browser ~2s after serve starts, in the background. Best-effort:
# if no opener is available the bootstrap still succeeds; the user reads
# the URL above and opens it manually.
(
    sleep 2
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "${URL}" >/dev/null 2>&1 || true
    elif command -v open >/dev/null 2>&1; then
        open "${URL}" >/dev/null 2>&1 || true
    fi
) &

exec uv run mame-curator serve --port "${PORT}"
