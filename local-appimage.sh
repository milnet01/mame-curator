#!/usr/bin/env bash
# local-appimage.sh — build the Linux desktop bundle, the way release.yml's
# build-appimage job does (mame-curator-1095 spec §4.5).
#
#   ./local-appimage.sh              build dist/MAME_Curator-<version>-x86_64.AppImage
#   ./local-appimage.sh --stage X    run one stage; used inside the build
#                                    container, locally and by the CI job
#
# The build runs inside python:3.13-slim-bookworm: it ships a shared libpython
# (PyInstaller needs one) and a glibc older than any build host here, so the
# AppImage starts on older desktops too (INV-20). Without --stage, this script
# starts that container with podman (docker as a fallback), mounting the repo
# read-only at /src and dist/ writable at /out.
#
# Each "# stage:" line below names a build stage; release.yml's job carries a
# step named "stage: <name>" for each, and tests/tools/test_release_scripts.py
# checks the two lists agree (INV-12). The container launch is host setup and
# is not a stage.
set -euo pipefail

BUILD_IMAGE="docker.io/library/python:3.13-slim-bookworm"
# appimagetool publishes only a rolling "continuous" tag, so the binary is
# pinned by sha256 and a changed upstream build stops the build (spec §4.5).
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
APPIMAGETOOL_SHA256="a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0"
# 1.5x the first measured AppImage, 28797432 bytes (2026-09-28); spec §4.16, INV-15.
SIZE_CEILING_BYTES=43196148

SRC="${MC_SRC:-/src}"      # repository root inside the container
OUT="${MC_OUT:-/out}"      # writable output directory (the host's dist/)
WORK="${MC_WORK:-/tmp/mc-build}"
VENV="$WORK/venv"

version() {
    sed -n 's/^version = "\(.*\)"$/\1/p' "$SRC/pyproject.toml" | head -1
}

run_stage() {
    case "$1" in
    deps)
        # stage: deps
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        # binutils for PyInstaller's binary analysis; file for appimagetool.
        apt-get install -y -qq --no-install-recommends binutils file ca-certificates curl >/dev/null
        python3 -m venv "$VENV"
        "$VENV/bin/pip" install --quiet --upgrade pip uv
        # The lockfile's versions, runtime plus the bundle extra, not the project itself:
        # PyInstaller freezes src/ directly (the spec's pathex).
        (cd "$SRC" && "$VENV/bin/uv" export --frozen --no-dev --extra bundle \
            --no-emit-project --no-hashes -o "$WORK/requirements.txt" --quiet)
        "$VENV/bin/pip" install --quiet -r "$WORK/requirements.txt"
        ;;
    freeze)
        # stage: freeze
        "$VENV/bin/pyinstaller" --noconfirm --log-level WARN \
            --distpath "$WORK/dist" --workpath "$WORK/build" \
            "$SRC/packaging/mame-curator.spec"
        ;;
    appdir)
        # stage: appdir
        local appdir="$WORK/MAME_Curator.AppDir"
        rm -rf "$appdir"
        mkdir -p "$appdir/usr/lib"
        cp -a "$WORK/dist/mame-curator" "$appdir/usr/lib/mame-curator"
        install -Dm0644 "$SRC/packaging/mame-curator.png" "$appdir/mame-curator.png"
        ln -sf mame-curator.png "$appdir/.DirIcon"
        cat > "$appdir/mame-curator.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=MAME Curator
Comment=Curate a MAME arcade library in your browser
Exec=mame-curator
Icon=mame-curator
Terminal=false
Categories=Game;Utility;
DESKTOP
        cat > "$appdir/AppRun" <<'APPRUN'
#!/bin/sh
HERE=$(dirname "$(readlink -f "$0")")
exec "$HERE/usr/lib/mame-curator/mame-curator" "$@"
APPRUN
        chmod 0755 "$appdir/AppRun"
        ;;
    tool)
        # stage: tool
        mkdir -p "$OUT/.cache"
        local tool="$OUT/.cache/appimagetool-x86_64.AppImage"
        if ! echo "$APPIMAGETOOL_SHA256  $tool" | sha256sum --check --status 2>/dev/null; then
            curl -fsSL -o "$tool" "$APPIMAGETOOL_URL"
            echo "$APPIMAGETOOL_SHA256  $tool" | sha256sum --check --status || {
                echo "local-appimage: appimagetool sha256 changed upstream; review it and update APPIMAGETOOL_SHA256" >&2
                exit 1
            }
        fi
        chmod 0755 "$tool"
        ;;
    pack)
        # stage: pack
        local out
        out="$OUT/MAME_Curator-$(version)-x86_64.AppImage"
        # --appimage-extract-and-run: no FUSE inside the container.
        ARCH=x86_64 "$OUT/.cache/appimagetool-x86_64.AppImage" --appimage-extract-and-run \
            "$WORK/MAME_Curator.AppDir" "$out"
        local size
        size="$(stat -c %s "$out")"
        if [ "$size" -gt "$SIZE_CEILING_BYTES" ]; then
            echo "local-appimage: $out is $size bytes, over the $SIZE_CEILING_BYTES ceiling (spec §4.16)" >&2
            exit 1
        fi
        echo "local-appimage: built $out ($size bytes)"
        ;;
    *)
        echo "local-appimage: unknown stage '$1'" >&2
        exit 2
        ;;
    esac
}

if [[ "${1:-}" == "--stage" ]]; then
    run_stage "${2:?--stage needs a name}"
    exit 0
fi

# --- Host: run every stage inside the build container ------------------------
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v podman >/dev/null 2>&1; then
    runner=podman
elif command -v docker >/dev/null 2>&1; then
    runner=docker
else
    echo "local-appimage: needs podman or docker" >&2
    exit 1
fi
mkdir -p "$repo/dist"
# Rootless podman maps the container's root to this user, so its output is
# already ours; rootful docker writes as root, so hand the files back.
owner=""
[[ "$runner" == docker ]] && owner="$(id -u):$(id -g)"
# label=disable: SELinux hosts label bind mounts, which makes /src unreadable.
# shellcheck disable=SC2016  # $stage and $owner are expanded by the container's bash
"$runner" run --rm --security-opt label=disable \
    -v "$repo:/src:ro" -v "$repo/dist:/out" -e "owner=$owner" \
    "$BUILD_IMAGE" bash -c '
        set -euo pipefail
        for stage in deps freeze appdir tool pack; do
            bash /src/local-appimage.sh --stage "$stage"
        done
        if [[ -n "$owner" ]]; then chown -R "$owner" /out; fi'
