"""Regression tests for FP02 round-2 fold-in fixes against P03 + FP01.

Each test pins a specific finding from the FP01 round-2 indie-review pass
on 2026-04-30. Tests anchor to the FP02 sub-bullets in `ROADMAP.md`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from mame_curator.copy import (
    copy_one,
    recycle_file,
    run_copy,
)
from mame_curator.copy.types import (
    AppendDecision,
    AppendDecisionKind,
    ConflictStrategy,
    CopyOutcomeStatus,
    CopyPlan,
    CopyReportStatus,
)
from mame_curator.parser.listxml import BIOSChainEntry
from mame_curator.parser.models import Machine


def _machine(short: str, desc: str | None = None) -> Machine:
    return Machine(name=short, description=desc or short, runnable=True)


def _seed_existing_playlist(dest_dir: Path, items: list[dict[str, str]]) -> None:
    payload = {
        "version": "1.5",
        "default_core_path": "",
        "default_core_name": "",
        "label_display_mode": 0,
        "right_thumbnail_mode": 0,
        "left_thumbnail_mode": 0,
        "sort_mode": 0,
        "items": items,
    }
    (dest_dir / "mame.lpl").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _entry(dest_dir: Path, short: str, label: str | None = None) -> dict[str, str]:
    return {
        "path": str((dest_dir / f"{short}.zip").resolve()),
        "label": label or short,
        "core_path": "DETECT",
        "core_name": "DETECT",
        "crc32": "00000000|crc",
        "db_name": "MAME.lpl",
    }


# --- Tier 2 #1: OverwriteRecord drops `parent` field ----------------------


def test_overwrite_record_has_no_parent_field() -> None:
    """OverwriteRecord exposes (old_short, new_short) only — no `parent` attr.

    Pre-FP02 the model had a `parent` field that always equalled `old_short`;
    the runner can't compute the actual parent without `cloneof_map` (FP01 #4
    design fix), so the field was misleading. Dropped per FP02 Tier 2 #1.
    """
    from mame_curator.copy.types import OverwriteRecord

    rec = OverwriteRecord(old_short="sf2", new_short="sf2ce")
    assert rec.old_short == "sf2"
    assert rec.new_short == "sf2ce"
    assert not hasattr(rec, "parent")


# --- Tier 2 #2: AppendDecision.replaces drives multi-conflict --------------


def test_append_decision_replaces_targets_correct_existing_entry(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """In a multi-conflict session, each AppendDecision.replaces must steer
    to its own target — not the first existing-but-not-winner heuristic.

    Setup: existing playlist holds `sf2` and `kof94`. New winners `sf2ce`
    and `kof94a` each REPLACE_AND_RECYCLE their respective parent. Pre-FP02
    the heuristic always returned the first non-winner entry, so kof94a
    would have recycled sf2 instead of kof94.
    """
    (dest_dir / "sf2.zip").write_bytes(b"old sf2 content")
    (dest_dir / "kof94.zip").write_bytes(b"old kof94 content")
    _seed_existing_playlist(
        dest_dir,
        [_entry(dest_dir, "sf2", "Street Fighter II"), _entry(dest_dir, "kof94", "KoF 94")],
    )

    plan = CopyPlan(
        winners=("kof94a", "sf2ce"),
        machines={
            "sf2ce": _machine("sf2ce", "SF2 CE"),
            "kof94a": _machine("kof94a", "KoF 94 (Set 2)"),
        },
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={
            "sf2ce": AppendDecision(kind=AppendDecisionKind.REPLACE_AND_RECYCLE, replaces="sf2"),
            "kof94a": AppendDecision(kind=AppendDecisionKind.REPLACE_AND_RECYCLE, replaces="kof94"),
        },
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK

    # Two distinct OverwriteRecords with the right pairing.
    pairs = {(o.old_short, o.new_short) for o in report.overwritten}
    assert ("sf2", "sf2ce") in pairs
    assert ("kof94", "kof94a") in pairs

    # The recycled files match the right OLD content (sf2 → "old sf2 content",
    # kof94 → "old kof94 content"). Pre-FP02 both would point at sf2.
    by_orig = {r.original_path.name: r.recycled_path.read_bytes() for r in report.recycled}
    assert b"old sf2 content" in by_orig.get("sf2.zip", b"")
    assert b"old kof94 content" in by_orig.get("kof94.zip", b"")


def test_append_decision_replace_requires_replaces_field(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """REPLACE without `replaces` no-ops the conflict path (no OverwriteRecord)."""
    (dest_dir / "sf2.zip").write_bytes(b"old sf2 content")
    _seed_existing_playlist(dest_dir, [_entry(dest_dir, "sf2")])

    plan = CopyPlan(
        winners=("sf2ce",),
        machines={"sf2ce": _machine("sf2ce")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        # REPLACE with no replaces field — no specific entry to replace.
        append_decisions={"sf2ce": AppendDecision(kind=AppendDecisionKind.REPLACE)},
    )
    report = run_copy(plan)
    # Winner copied successfully but no OverwriteRecord — caller-side contract:
    # without `replaces`, the runner has nothing to replace.
    assert report.status is CopyReportStatus.OK
    assert report.overwritten == ()


# --- Tier 2 #3: Recycle dirname uses session_id, not just timestamp -------


def test_recycle_dirname_uses_session_id_so_cross_session_does_not_collide(
    tmp_path: Path,
) -> None:
    """Two sessions recycling within the same second land in distinct dirs.

    Pre-FP02 the dirname was `_ts_dir_name(now)` (whole-second resolution).
    Same-second recycles from different sessions shared the dir; the
    second's `manifest.json` overwrote the first's. Session-keyed dirnames
    eliminate the collision.
    """
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    file_a = tmp_path / "a" / "sf2.zip"
    file_a.write_bytes(b"AAA")
    file_b = tmp_path / "b" / "kof94.zip"
    file_b.write_bytes(b"BBB")
    recycle_root = tmp_path / "recycle"

    # Force same-second timestamps; differ only by session_id.
    fixed_now = datetime(2026, 4, 30, 12, 0, 0, tzinfo=UTC)
    with patch("mame_curator.copy.recyclebin.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        p1 = recycle_file(file_a, reason="x", session_id="sess-A", recycle_root=recycle_root)
        p2 = recycle_file(file_b, reason="x", session_id="sess-B", recycle_root=recycle_root)

    # Different session_ids → different parent dirs.
    assert p1.parent != p2.parent
    # Each manifest references its own session.
    m1 = json.loads((p1.parent / "manifest.json").read_text(encoding="utf-8"))
    m2 = json.loads((p2.parent / "manifest.json").read_text(encoding="utf-8"))
    assert m1["session_id"] == "sess-A"
    assert m2["session_id"] == "sess-B"
    # Files preserved.
    assert p1.read_bytes() == b"AAA"
    assert p2.read_bytes() == b"BBB"


def test_recycle_same_session_shares_directory(tmp_path: Path) -> None:
    """Same session_id → recycled files land in the same directory."""
    (tmp_path / "src").mkdir()
    f1 = tmp_path / "src" / "sf2.zip"
    f1.write_bytes(b"S")
    f2 = tmp_path / "src" / "kof94.zip"
    f2.write_bytes(b"K")
    recycle_root = tmp_path / "recycle"

    p1 = recycle_file(f1, reason="x", session_id="sess-X", recycle_root=recycle_root)
    p2 = recycle_file(f2, reason="x", session_id="sess-X", recycle_root=recycle_root)
    assert p1.parent == p2.parent


# --- Tier 3 #6: Recycle 3+ same-name same-session collisions --------------


def test_recycle_three_same_name_same_session_collisions(tmp_path: Path) -> None:
    """Three same-name recycles in one session walk the counter loop past 1.

    Pre-FP02 the test only covered counter=1; this exercises counter=2 and
    counter=3 to harden the loop bound.
    """
    recycle_root = tmp_path / "recycle"
    for i, content in enumerate((b"A", b"B", b"C")):
        d = tmp_path / f"src{i}"
        d.mkdir()
        (d / "dup.zip").write_bytes(content)

    p_a = recycle_file(
        tmp_path / "src0" / "dup.zip", reason="x", session_id="s", recycle_root=recycle_root
    )
    p_b = recycle_file(
        tmp_path / "src1" / "dup.zip", reason="x", session_id="s", recycle_root=recycle_root
    )
    p_c = recycle_file(
        tmp_path / "src2" / "dup.zip", reason="x", session_id="s", recycle_root=recycle_root
    )
    assert p_a.read_bytes() == b"A"
    assert p_b.read_bytes() == b"B"
    assert p_c.read_bytes() == b"C"
    # Three distinct parent dirs (counter walked to 2).
    assert len({p_a.parent, p_b.parent, p_c.parent}) == 3


# --- Tier 3 #4: Playlist excludes SKIPPED_MISSING_SOURCE ------------------


def test_playlist_excludes_winners_with_missing_source(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """A winner whose source `.zip` is missing must NOT enter mame.lpl.

    Pre-FP02 the entry-builder iterated `(*succeeded, *skipped)`, which
    included SKIPPED_MISSING_SOURCE outcomes whose `dst` was never created.
    The resulting playlist pointed at non-existent files.
    """
    plan = CopyPlan(
        winners=("kof94", "doesnotexist"),
        machines={
            "kof94": _machine("kof94"),
            "doesnotexist": _machine("doesnotexist"),
        },
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK

    # Skipped-missing-source outcome present in the report.
    assert any(
        o.short_name == "doesnotexist" and o.status is CopyOutcomeStatus.SKIPPED_MISSING_SOURCE
        for o in report.skipped
    )

    # But mame.lpl must NOT contain doesnotexist.
    lpl = json.loads((dest_dir / "mame.lpl").read_text(encoding="utf-8"))
    paths = {Path(item["path"]).name for item in lpl["items"]}
    assert "doesnotexist.zip" not in paths
    assert "kof94.zip" in paths


def test_playlist_excludes_skipped_existing_version(
    source_dir: Path, dest_dir: Path, bios_chain: dict[str, BIOSChainEntry]
) -> None:
    """KEEP_EXISTING winner doesn't get a new entry — existing entry stays.

    Per spec, SKIPPED_EXISTING_VERSION means the existing playlist entry
    is preserved verbatim; the new winner's dst was never written so it
    must not appear in mame.lpl.
    """
    (dest_dir / "sf2.zip").write_bytes(b"old sf2 content")
    _seed_existing_playlist(dest_dir, [_entry(dest_dir, "sf2", "Street Fighter II")])

    plan = CopyPlan(
        winners=("sf2ce",),
        machines={"sf2ce": _machine("sf2ce", "Street Fighter II' - CE")},
        bios_chain=bios_chain,
        source_dir=source_dir,
        dest_dir=dest_dir,
        conflict_strategy=ConflictStrategy.APPEND,
        append_decisions={
            "sf2ce": AppendDecision(kind=AppendDecisionKind.KEEP_EXISTING),
        },
    )
    report = run_copy(plan)
    assert report.status is CopyReportStatus.OK

    lpl = json.loads((dest_dir / "mame.lpl").read_text(encoding="utf-8"))
    paths = {Path(item["path"]).name for item in lpl["items"]}
    # Existing entry preserved.
    assert "sf2.zip" in paths
    # New winner NOT added — its dst wasn't written.
    assert "sf2ce.zip" not in paths


# --- Tier 3 #5: KeyboardInterrupt cleanup with progress=cb ----------------


def test_copy_one_cleans_tmp_on_keyboard_interrupt_with_progress_callback(
    source_dir: Path, dest_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spec § Atomic copy step 6 + FP02 Tier 3 #5: chunked-progress branch
    must also clean up `.tmp` on KeyboardInterrupt.

    The pre-FP02 KI test only exercised the `progress=None` branch (which
    routes through `shutil.copy2`); the chunked path uses `_chunked_copy`
    and a different code path. Both must honour the try/finally.
    """
    src = source_dir / "kof94.zip"
    dst = dest_dir / "kof94.zip"

    def boom(_done: int, _total: int) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        copy_one(src, dst, short_name="kof94", role="winner", progress=boom)

    # Tmp removed by the try/finally even when the chunked path raised.
    assert not list(dest_dir.glob("*.tmp"))
    # Original dst (absent) still absent.
    assert not dst.exists()
