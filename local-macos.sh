#!/usr/bin/env bash
# local-macos.sh — build the macOS desktop bundle, the way release.yml's
# build-macos job does (mame-curator-1095 spec §4.7).
#
#   ./local-macos.sh              build dist/MAME_Curator-<version>-<arch>.dmg on a Mac
#   ./local-macos.sh --stage X    run one stage; the CI job on macos-latest runs these
#
# Only a Mac can run this: PyInstaller must execute a macOS CPython, which
# nothing on Linux hosts ("Packaging macOS binaries while running under Linux
# is currently not possible at all" — PyInstaller FAQ). On this project's
# Linux machine it is shellcheck-only, and its first real run is CI's.
# The .app is unsigned (spec §3 decision 2).
#
# "# stage:" lines name the build stages INV-12 compares with release.yml.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="${MC_WORK:-$repo/dist/.mac-build}"
read -r -a PY <<<"${MC_PY:-python3}"
# 1.5x the first measured .dmg, 26961058 bytes (2026-09-28, CI's macos-latest
# rehearsal run); spec §4.16, INV-15.
SIZE_CEILING_BYTES=40441587

version() {
    sed -n 's/^version = "\(.*\)"$/\1/p' "$repo/pyproject.toml" | head -1
}

run_stage() {
    case "$1" in
    deps)
        # stage: deps
        mkdir -p "$WORK"
        "${PY[@]}" -m pip install --quiet --upgrade pip uv
        (cd "$repo" && "${PY[@]}" -m uv export --frozen --no-dev --extra bundle \
            --no-emit-project --no-hashes -o "$WORK/requirements.txt" --quiet)
        "${PY[@]}" -m pip install --quiet -r "$WORK/requirements.txt"
        ;;
    freeze)
        # stage: freeze
        (cd "$repo" && "${PY[@]}" -m PyInstaller --noconfirm --log-level WARN \
            --distpath "$WORK/dist" --workpath "$WORK/build" \
            packaging/mame-curator.spec)
        ;;
    pack)
        # stage: pack
        local out
        out="$repo/dist/MAME_Curator-$(version)-$(uname -m).dmg"
        hdiutil create -volname "MAME Curator" -srcfolder "$WORK/dist/MAME Curator.app" \
            -ov -format UDZO "$out"
        local size
        size="$(wc -c <"$out" | tr -d ' ')"
        if [ "$size" -gt "$SIZE_CEILING_BYTES" ]; then
            echo "local-macos: $out is $size bytes, over the $SIZE_CEILING_BYTES ceiling (spec §4.16)" >&2
            exit 1
        fi
        echo "local-macos: built $out ($size bytes)"
        ;;
    *)
        echo "local-macos: unknown stage '$1'" >&2
        exit 2
        ;;
    esac
}

if [[ "${1:-}" == "--stage" ]]; then
    run_stage "${2:?--stage needs a name}"
    exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "local-macos: macOS only — a macOS bundle cannot be built on $(uname -s)" >&2
    exit 1
fi
for stage in deps freeze pack; do
    run_stage "$stage"
done
