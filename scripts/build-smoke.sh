#!/usr/bin/env bash
# scripts/build-smoke.sh — the clean-room proof for the Linux bundle
# (mame-curator-1095 spec §4.15).
#
# Runs every dist/MAME_Curator-*-x86_64.AppImage inside debian:13-slim — no
# Python, a scrubbed environment, no network — and requires the self-test
# sentinel (§4.13). Exits 0 only if every artefact passes.
#
# Opt-in: it needs MAME_CURATOR_BUILD_SMOKE=1 and podman or docker, so the
# everyday pre-push gate never pays for it. INV-13's recipe runs it.
# Precedent: finbreak's scripts/build-smoke.sh.
set -euo pipefail

if [[ "${MAME_CURATOR_BUILD_SMOKE:-}" != "1" ]]; then
    echo "build-smoke: skipped (set MAME_CURATOR_BUILD_SMOKE=1 to run)" >&2
    exit 0
fi

TEST_IMAGE="docker.io/library/debian:13-slim"
SENTINEL="MAME_CURATOR_SELFTEST_OK"
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v podman >/dev/null 2>&1; then
    runner=podman
elif command -v docker >/dev/null 2>&1; then
    runner=docker
else
    echo "build-smoke: needs podman or docker" >&2
    exit 1
fi

shopt -s nullglob
artefacts=("$repo"/dist/MAME_Curator-*-x86_64.AppImage)
if (( ${#artefacts[@]} == 0 )); then
    echo "build-smoke: no dist/MAME_Curator-*-x86_64.AppImage; run ./local-appimage.sh first" >&2
    exit 1
fi

failed=0
for app in "${artefacts[@]}"; do
    name="$(basename "$app")"
    # --appimage-extract-and-run: no FUSE in the container. env -i plus a
    # fresh HOME: nothing from this machine's environment reaches the run.
    out="$("$runner" run --rm --network none --security-opt label=disable \
        -v "$app:/app/$name:ro" "$TEST_IMAGE" \
        env -i HOME=/tmp/home PATH=/usr/bin:/bin \
        "/app/$name" --appimage-extract-and-run self-test 2>&1 || true)"
    if [[ "$(printf '%s\n' "$out" | tail -1)" == "$SENTINEL" ]]; then
        echo "build-smoke: PASS $name"
    else
        echo "build-smoke: FAIL $name" >&2
        printf '%s\n' "$out" | tail -5 >&2
        failed=1
    fi
done
exit "$failed"
