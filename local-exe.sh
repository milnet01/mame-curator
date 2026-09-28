#!/usr/bin/env bash
# local-exe.sh — build the Windows desktop bundle, the way release.yml's
# build-exe job does (mame-curator-1095 spec §4.6).
#
#   ./local-exe.sh              build dist/MAME_Curator-<version>-x86_64.exe under Wine
#   ./local-exe.sh --stage X    run one stage; the CI job on windows-latest runs
#                               the same stages with MC_PY=python
#
# PyInstaller cannot cross-compile, and its FAQ directs Windows-from-Linux
# builds at Wine: this provisions a project-local prefix at .wine-build/
# (gitignored), installs the Windows CPython below into it, and runs
# PyInstaller there against the shared spec, which picks a one-file console
# EXE on Windows. A Wine build proves the bundle is assembled correctly; CI on
# windows-latest remains the authority for real Windows behaviour.
#
# "# stage:" lines name the build stages INV-12 compares with release.yml.
# Provisioning the prefix and installing CPython are host setup, not stages.
set -euo pipefail

PY_VERSION="3.13.15"
PY_INSTALLER_URL="https://www.python.org/ftp/python/$PY_VERSION/python-$PY_VERSION-amd64.exe"
# 1.5x the first measured .exe, 22722699 bytes (2026-09-28, Wine build); spec §4.16, INV-15.
SIZE_CEILING_BYTES=34084049

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export WINEPREFIX="${WINEPREFIX:-$repo/.wine-build}"
export WINEDEBUG="${WINEDEBUG:--all}"
# No Mono / Gecko install dialogs on a fresh prefix: nothing here needs them.
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=}"
WORK="${MC_WORK:-$repo/dist/.exe-build}"

# How to run Windows Python: Wine locally, plain `python` on a Windows runner.
if [[ -n "${MC_PY:-}" ]]; then
    read -r -a PY <<<"$MC_PY"
else
    PY=(wine "$WINEPREFIX/drive_c/Python/python.exe")
fi

version() {
    sed -n 's/^version = "\(.*\)"$/\1/p' "$repo/pyproject.toml" | head -1
}

provision() {
    command -v wine >/dev/null || { echo "local-exe: wine not found" >&2; exit 1; }
    if [[ ! -x "$WINEPREFIX/drive_c/Python/python.exe" ]]; then
        mkdir -p "$WORK"
        wineboot --init >/dev/null 2>&1
        curl -fsSL -o "$WORK/python-installer.exe" "$PY_INSTALLER_URL"
        wine "$WORK/python-installer.exe" /quiet InstallAllUsers=0 PrependPath=0 \
            Include_test=0 Include_launcher=0 'TargetDir=C:\Python'
    fi
}

run_stage() {
    case "$1" in
    deps)
        # stage: deps
        mkdir -p "$WORK"
        "${PY[@]}" -m pip install --quiet --upgrade pip uv
        # The lockfile's versions, runtime plus the bundle extra, resolved for
        # Windows; not the project itself (the spec's pathex freezes src/).
        (cd "$repo" && "${PY[@]}" -m uv export --frozen --no-dev --extra bundle \
            --no-emit-project --no-hashes -o dist/.exe-build/requirements.txt --quiet)
        "${PY[@]}" -m pip install --quiet -r "$WORK/requirements.txt"
        ;;
    freeze)
        # stage: freeze
        (cd "$repo" && "${PY[@]}" -m PyInstaller --noconfirm --log-level WARN \
            --distpath dist/.exe-build/dist --workpath dist/.exe-build/build \
            packaging/mame-curator.spec)
        ;;
    pack)
        # stage: pack
        local out
        out="$repo/dist/MAME_Curator-$(version)-x86_64.exe"
        cp "$WORK/dist/MAME_Curator.exe" "$out"
        local size
        size="$(stat -c %s "$out")"
        if [ "$size" -gt "$SIZE_CEILING_BYTES" ]; then
            echo "local-exe: $out is $size bytes, over the $SIZE_CEILING_BYTES ceiling (spec §4.16)" >&2
            exit 1
        fi
        echo "local-exe: built $out ($size bytes)"
        ;;
    *)
        echo "local-exe: unknown stage '$1'" >&2
        exit 2
        ;;
    esac
}

if [[ "${1:-}" == "--stage" ]]; then
    run_stage "${2:?--stage needs a name}"
    exit 0
fi

provision
for stage in deps freeze pack; do
    run_stage "$stage"
done
