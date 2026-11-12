#!/usr/bin/env bash
#
# MAME Curator clone-and-run bootstrap (Linux / macOS).
#
# Provisions Python 3.12+ + uv + project deps, then starts the server — which
# opens a browser itself, once the port is accepting, where a first run is set
# up. Idempotent — running twice does the right thing on the second run.
#
# For developer dual-server (backend + Vite HMR), use scripts/dev.sh.

set -euo pipefail

cd "$(dirname "$0")"

# ---- 1. Python 3.12+ detection ---------------------------------------

# Installing python3.12 beside an older system Python leaves `python3` old, so
# the versioned names count too. `uv` looks for those names itself.
PY_OK=""
PY_VERSION=""
for candidate in python3 python3.14 python3.13 python3.12; do
    command -v "${candidate}" >/dev/null 2>&1 || continue
    if "${candidate}" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
        PY_OK=1
        break
    fi
    [ -n "${PY_VERSION}" ] || PY_VERSION=$("${candidate}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
done

if [ -z "${PY_OK}" ]; then
    if [ -n "${PY_VERSION}" ]; then
        echo "error: Python ${PY_VERSION} is too old; need 3.12+." >&2
    else
        echo "error: python3 not found on PATH." >&2
    fi
    cat >&2 <<'EOF'

Install Python 3.12 or newer:
  openSUSE Tumbleweed:  sudo zypper in python313
  Ubuntu 24.04+:        sudo apt install python3.12
  Fedora:               sudo dnf install python3.12
  macOS (Homebrew):     brew install python@3.13

Then re-run ./run.sh.
EOF
    exit 1
fi

# ---- 2. uv detection / install ---------------------------------------

# mame-curator-1179: one uv release, and its installer's SHA-256 from that
# release. The installer holds the SHA-256 of each uv download and checks it,
# so checking the installer checks uv too. run.bat pins the same version;
# tests/tools/test_launcher_text.py keeps the two in step. To move to a new
# uv: take uv-installer.sh from its GitHub release and hash it.
UV_VERSION="0.13.7"
UV_INSTALLER_SHA256="d263ee68314cf5bea36b08e6bd9e2c4563240d7adb73756cf33af5c199b92db4"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv not found — installing uv ${UV_VERSION} from its GitHub release..."
    installer="$(mktemp)"
    # FP21-Q: `--proto '=https'` refuses a redirect to plain HTTP and
    # `--tlsv1.2` an older TLS, so the download cannot be swapped in transit.
    curl --proto '=https' --tlsv1.2 -LsSf -o "${installer}" \
        "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-installer.sh"
    # sha256sum on Linux, shasum on macOS.
    got="$(sha256sum "${installer}" 2>/dev/null || shasum -a 256 "${installer}")"
    if [ "${got%% *}" != "${UV_INSTALLER_SHA256}" ]; then
        rm -f "${installer}"
        echo "error: the uv installer download does not match its pinned SHA-256; not running it." >&2
        echo "Try again later. If it keeps happening, install uv yourself: https://docs.astral.sh/uv/" >&2
        exit 1
    fi
    sh "${installer}"
    rm -f "${installer}"
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
# --inexact: install what the app needs, but never uninstall anything
# else, so a developer's own tools survive a launch.
# --no-dev: end users do not need the test and lint tools.
uv sync --inexact --no-dev --quiet

# ---- 4. serve --------------------------------------------------------

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
    exec uv run --no-dev mame-curator serve --port "${PORT}"
fi
exec uv run --no-dev mame-curator serve
