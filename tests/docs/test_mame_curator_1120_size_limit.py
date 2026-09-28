"""mame-curator-1120 — the P06 bundle budget is a gate, not a sentence.

docs/specs/P06-frontend-mvp.md § Architecture notes: initial JS ≤ 350 kB
gzipped, "enforced by a CI gate using size-limit" read from package.json's
"size-limit" array. The gate measures every emitted JS chunk, which bounds
the first load from above however Vite splits the chunks.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_package_json_declares_the_350_kb_gzipped_budget() -> None:
    package = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    entries = package.get("size-limit", [])
    assert entries, 'frontend/package.json has no "size-limit" array'
    assert all(entry.get("gzip", True) for entry in entries)
    assert any(entry.get("limit") == "350 kB" for entry in entries), entries
    assert package["scripts"].get("size") == "size-limit"


def test_every_gate_runs_the_size_check_after_the_build() -> None:
    # local-CI is globbed, not named: this only reads it, and naming the
    # shell script would trip the win32-skip guard in tests/docs.
    local_ci = sorted(REPO_ROOT.glob("local-CI.*"))
    assert len(local_ci) == 1, local_ci
    workflows = REPO_ROOT / ".github" / "workflows"
    for path in (workflows / "ci.yml", workflows / "release.yml", local_ci[0]):
        name = path.relative_to(REPO_ROOT)
        text = path.read_text(encoding="utf-8")
        assert "npm run size" in text, f"{name} does not run the size-limit gate"
        assert text.index("npm run build") < text.index("npm run size"), (
            f"{name} checks the size before building"
        )
