"""mame-curator-1095 — static checks on the desktop-bundle packaging.

Reads ``packaging/mame-curator.spec`` (and, from later plan steps, the local
build scripts and ``release.yml``) without building anything. POSIX-only,
like ``test_run_sh_port.py``: the scripts these checks grow to cover are
bash. Contract: ``docs/specs/mame-curator-1095-desktop-bundles.md`` § 5.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="packaging checks are POSIX-only")

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "packaging" / "mame-curator.spec"
ALLOWED_DATA = {"frontend/dist", "docs/help", "config.example.yaml", "packaging"}


def _assigned_literal(name: str) -> object:
    tree = ast.parse(SPEC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{SPEC.name} assigns no literal {name}")


def test_spec_datas_are_allowlisted() -> None:
    """INV-14 — every bundled data source is on the allowlist, and lands at
    the same relative path (config.example.yaml at the bundle root)."""
    entries = _assigned_literal("DATAS")
    assert isinstance(entries, list) and entries
    for src, dest in entries:
        assert src in ALLOWED_DATA, f"{src!r} is not on the datas allowlist"
        assert dest == ("." if src == "config.example.yaml" else src), (src, dest)


def test_spec_builds_datas_only_from_the_allowlisted_literal() -> None:
    """A second route into ``datas`` (Tree, collect_data_files, an append)
    would bypass the allowlist the test above reads."""
    text = SPEC.read_text(encoding="utf-8")
    for bypass in ("Tree(", "collect_data_files", "datas +=", "datas.append", "datas.extend"):
        assert bypass not in text, bypass
