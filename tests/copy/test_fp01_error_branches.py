"""Error/warning-path regression tests for FP01 fixes against P03.

Split from ``test_fp01_fixes.py`` (FP31 / mame-curator-1046) when it crossed
the 300-line soft cap. Covers the Tier-3 playlist parse-error branches and
the FP08 control-byte sanitisation of recycle / BIOS-resolution warnings.
Folder name keeps the FP origin visible per ``testing.md`` § "tests anchor
to external signals".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mame_curator.copy import recycle_file, run_copy
from mame_curator.copy.errors import RecycleError
from mame_curator.copy.types import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyPlan,
)
from mame_curator.parser.listxml import BIOSChainEntry
from tests.copy._runner_helpers import _machine
from tests.copy.conftest import _seed_existing_playlist

# --- Tier 3: playlist error branches --------------------------------------


def test_read_lpl_raises_on_missing_file(tmp_path: Path) -> None:
    from mame_curator.copy.errors import PlaylistError
    from mame_curator.copy.playlist import read_lpl

    with pytest.raises(PlaylistError):
        read_lpl(tmp_path / "nope.lpl")


def test_read_lpl_raises_on_corrupt_json(tmp_path: Path) -> None:
    from mame_curator.copy.errors import PlaylistError
    from mame_curator.copy.playlist import read_lpl

    bad = tmp_path / "bad.lpl"
    bad.write_text("not json at all", encoding="utf-8")
    with pytest.raises(PlaylistError):
        read_lpl(bad)


def test_read_lpl_raises_when_items_not_list(tmp_path: Path) -> None:
    from mame_curator.copy.errors import PlaylistError
    from mame_curator.copy.playlist import read_lpl

    bad = tmp_path / "bad.lpl"
    bad.write_text(json.dumps({"items": "not-a-list"}), encoding="utf-8")
    with pytest.raises(PlaylistError):
        read_lpl(bad)


def test_recycle_raises_when_source_missing(tmp_path: Path) -> None:
    with pytest.raises(RecycleError):
        recycle_file(tmp_path / "nope.zip", reason="x", session_id="s")


# FP08 — A1 test below


def test_recycle_failure_warning_quotes_short_name_with_control_byte(
    source_dir: Path,
    dest_dir: Path,
    bios_chain: dict[str, BIOSChainEntry],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FP08 A1 — `runner.py:233`'s recycle-failure warning must quote the
    offending zip's basename via `repr()` so a control byte in a DAT machine
    short-name can't leak into the JSON copy report or the CLI status line
    as a literal LF.

    Setup: pre-create an LF-bearing zip at dest matching `replaced` short;
    monkey-patch `recycle_file` to fail; run the REPLACE_AND_RECYCLE branch
    against a winner that targets the LF-bearing existing zip.
    """
    evil_short = "evil\nname"
    evil_zip = dest_dir / f"{evil_short}.zip"
    try:
        evil_zip.write_bytes(b"old")
    except OSError:  # pragma: no cover
        pytest.skip("filesystem rejects \\n in path names")
    _seed_existing_playlist(
        dest_dir,
        [
            {
                "path": str(evil_zip.resolve()),
                "label": "Evil",
                "core_path": "DETECT",
                "core_name": "DETECT",
                "crc32": "00000000|crc",
                "db_name": "MAME.lpl",
            }
        ],
    )

    def _fail_recycle(*_a: object, **_kw: object) -> Path:
        raise RecycleError("simulated recycle failure", path=evil_zip)

    monkeypatch.setattr("mame_curator.copy.runner.recycle_file", _fail_recycle)

    plan = CopyPlan(
        winners=("kof94",),
        machines={"kof94": _machine("kof94")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={
            "kof94": AppendDecision(
                kind=AppendDecisionKind.REPLACE_AND_RECYCLE, replaces=evil_short
            )
        },
    )
    report = run_copy(plan)
    # Recycle attempt produced a warning (the simulated failure).
    assert any("recycle of" in w for w in report.warnings)
    recycle_warning = next(w for w in report.warnings if "recycle of" in w)
    # Post-fix: name is repr-escaped (Python source `\\n` = backslash + n).
    assert "evil\\nname.zip" in recycle_warning
    # Strict: literal-LF form of the zip basename must NOT appear in the
    # warning (FP07 R1 contract — directly tests "the short-name didn't
    # leak with a literal LF").
    assert "evil\nname.zip" not in recycle_warning


def test_bios_resolution_warning_quotes_short_name_with_control_byte(
    source_dir: Path,
    dest_dir: Path,
) -> None:
    """FP08 R1 (Cluster R) — `runner.py:92`'s BIOS-warning list-comprehension
    `f"{w.name}: {w.kind}"` is a sibling site to A1 with identical value
    flow (BIOS short-name from DAT data → warnings list → JSON copy report
    + CLI). FP08 A1's grep matched `warnings.append(f"...")` and missed
    this list-comp form; folded inline as Cluster R per the FP06 R2
    precedent.
    """
    evil_short = "evil\nname"
    plan = CopyPlan(
        winners=(evil_short,),
        machines={evil_short: _machine(evil_short)},
        # Empty bios_chain → resolver emits BIOSResolutionWarning(
        # name="evil\nname", kind="missing_from_listxml") which feeds
        # the line-92 list-comp.
        bios_chain={},
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    report = run_copy(plan)
    bios_warnings = [w for w in report.warnings if "missing_from_listxml" in w]
    assert len(bios_warnings) == 1
    w = bios_warnings[0]
    # Post-fix: name is repr-escaped.
    assert "evil\\nname" in w
    # Strict: literal-LF form must NOT appear.
    assert "evil\nname:" not in w
