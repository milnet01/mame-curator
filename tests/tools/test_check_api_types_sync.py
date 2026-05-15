"""Regression test for `tools/check_api_types_sync.py`.

DS05 Cluster D — the script is the project's Python ↔ TS type-drift
gate. DS02's R2 hot-fix exposed that the script's hardcoded
`PYTHON_SOURCES` tuple can silently miss new sibling modules; this
test pins both (a) the integration path (script exits 0 at HEAD)
and (b) the exact root cause (every `api/schemas*.py` sibling at
HEAD is named in the tuple, so a future split that adds another
sibling fires this test in the same commit).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "check_api_types_sync.py"


def test_script_exits_zero_at_head() -> None:
    """The real source tree must currently be in sync.

    This is the DS02 R2 outcome — the post-mortem fix-pass brought
    `PYTHON_SOURCES` up to date with the post-A5 sibling-module
    layout. If a future PR introduces drift, this assertion fires
    first locally (via the DS05 Cluster D pre-commit hook) and then
    in CI.
    """
    # S603 noqa rationale: sys.executable + a fully-qualified path to
    # the project's own script, no user input on the command line.
    # Same threat model as the script's CI invocation.
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    assert result.returncode == 0, (
        f"check_api_types_sync.py exited {result.returncode} at HEAD.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )


def test_python_sources_tuple_lists_every_schema_sibling() -> None:
    """`PYTHON_SOURCES` must cover every `api/schemas*.py` file at HEAD.

    DS02 R2 root cause: A5 added `schemas_copy.py`, `schemas_games.py`,
    and `schemas_overrides.py` as sibling modules but only the original
    `schemas.py` + FP24-EE's `schemas_setup.py` / `schemas_fs.py` were
    in the tuple. This test pins that every `api/schemas*.py` file at
    HEAD is named in `PYTHON_SOURCES`.

    If a future split adds another sibling, this test fires and the
    author must add the path to the tuple in the same commit.
    """
    spec = importlib.util.spec_from_file_location("check_sync", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    api_dir = REPO_ROOT / "src" / "mame_curator" / "api"
    sibling_schemas = {
        f"src/mame_curator/api/{p.name}"
        for p in api_dir.glob("schemas*.py")
        if not p.name.startswith("__")
    }
    listed = {p for p in mod.PYTHON_SOURCES if p.startswith("src/mame_curator/api/schemas")}
    missing = sibling_schemas - listed
    assert not missing, (
        f"PYTHON_SOURCES missing api/schemas*.py sibling(s): {sorted(missing)}. "
        "DS02 R2 root-cause: a new schema sibling was added without "
        "updating the tuple. Add it in this same commit."
    )
