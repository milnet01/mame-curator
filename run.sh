#!/usr/bin/env bash
#
# MAME Curator clone-and-run bootstrap (Linux / macOS).
#
# Provisions Python 3.12+ + uv + project deps, runs the interactive
# setup wizard if config.yaml is missing, then starts the server — which
# opens a browser itself, once the port is accepting. Idempotent — running
# twice does the right thing on the second run.
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
    # FP21-Q: pin curl transport security — `--proto '=https'` rejects
    # any non-HTTPS redirect target, and `--tlsv1.2` rejects pre-TLS-1.2
    # downgrades. Without these, a network attacker who can intercept
    # the user's DNS or a captive-portal layer can swap in a malicious
    # installer over plain HTTP. The official Astral installer publishes
    # over HTTPS only, so these flags are no-ops on a clean network and
    # a real defense on a hostile one. (Full integrity via a vendored
    # release tarball + sha256 is tracked as a separate ADR — see
    # docs/decisions/.)
    curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh | sh
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

# No `${PORT:-8080}` default: an unset $PORT must stay empty so that
# `mame-curator serve` can fall through to config.yaml's `server.port`.
# Forwarding an unconditional `--port 8080` would make that layer
# unreachable through the project's primary entry point.
PORT="${PORT:-}"

if [ -n "${PORT}" ]; then
    # An invalid $PORT must fail here, named, rather than three layers down:
    # a non-numeric value reaches argparse ("invalid int value: 'abc'" — no
    # range in the message), and an out-of-range one reaches the bind
    # ("permission denied" for <1024). Never silently fall back to 8080.
    # The `{1,5}` bound keeps `test -lt` inside 64-bit range: a longer digit
    # string makes `[ ... -lt ... ]` error out instead of comparing.
    # `cli/commands/serve.py:_resolve_port` re-checks the same range with the
    # same message for callers that skip this script.
    # The `-n` guard is load-bearing: without it, dropping the `:-8080`
    # default above lets an empty $PORT reach this regex and abort every
    # default bootstrap.
    if ! [[ "${PORT}" =~ ^[0-9]{1,5}$ ]] || [ "${PORT}" -lt 1024 ] || [ "${PORT}" -gt 65535 ]; then
        echo "error: PORT='${PORT}' is not a valid port — expected an integer in 1024-65535." >&2
        exit 1
    fi
fi

echo
if [ -n "${PORT}" ]; then
    # The shell knows the port only because it is the one being forwarded.
    echo "Starting MAME Curator on http://127.0.0.1:${PORT}/"
else
    # `server.port` is resolved inside `serve`, so the address is not
    # knowable here; uvicorn logs it on bind.
    echo "Starting MAME Curator — the address will be printed once the server binds"
fi
echo "(Ctrl-C to stop. Re-run ./run.sh anytime — it's idempotent.)"
echo

# No browser open here: `_cmd_serve` polls the socket and opens it once the
# port accepts (cli/spec.md § Browser). This script used to sleep 2s and
# call xdg-open, which raced the application lifespan — a ~48 MB DAT parse
# — and greeted a cold start with "Unable to connect".

if [ -n "${PORT}" ]; then
    exec uv run mame-curator serve --port "${PORT}"
fi
exec uv run mame-curator serve
