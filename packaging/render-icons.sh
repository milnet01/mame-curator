#!/usr/bin/env bash
# Render packaging/icon.svg into the three committed renditions the desktop
# bundles package (mame-curator-1095 spec §4.9): mame-curator.png (AppImage),
# mame-curator.ico (Windows) and mame-curator.icns (macOS). Run by hand after
# editing icon.svg, then commit the results; no bundle build runs this.
# Needs rsvg-convert and uv (Pillow comes from a throwaway uv environment).
set -euo pipefail
cd "$(dirname "$0")"
for tool in rsvg-convert uv; do
    command -v "$tool" >/dev/null || { echo "render-icons: $tool not found" >&2; exit 1; }
done
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
rsvg-convert -w 1024 -h 1024 icon.svg -o "$work/icon-1024.png"
rsvg-convert -w 256 -h 256 icon.svg -o mame-curator.png
uv run --no-project --quiet --with pillow python - "$work/icon-1024.png" <<'PY'
import sys
from PIL import Image

src = Image.open(sys.argv[1]).convert("RGBA")
src.save("mame-curator.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
src.save("mame-curator.icns")
PY
echo "render-icons: wrote mame-curator.png, mame-curator.ico, mame-curator.icns"
