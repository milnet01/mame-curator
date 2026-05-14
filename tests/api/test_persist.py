"""FP27 B2 — `restore_snapshot` stage-then-promote transaction atomicity.

At HEAD, `api/persist.py:94-111` loops over `targets.items()` and either
`atomic_write_bytes(dst, src.read_bytes())` (when the snapshot has the
file) or `dst.unlink()` (when it doesn't). The atomic-write writes
DIRECTLY to the live target, not via a staging area, so a crash
mid-loop leaves a mixed pre-restore / post-restore state.

Fix (option 1, chosen): stage-then-promote. Copy every snapshot file
into `snap_dir / "_restore_staging" / <name>` first, then `os.replace`
each staged file into its live target, then unlink absentees. The
staging step doubles disk I/O during the operation; in exchange every
`atomic_write_bytes` lands in staging (not live), which means any
mid-stage failure leaves the live targets untouched. Promote failures
mid-loop still produce half-restored end states (per-file `os.replace`
is the POSIX atomic unit), but the read-from-snapshot step is
front-loaded — once staging completes, the snapshot dir can vanish
without losing data.

The contract this test pins: **every `atomic_write_bytes` call inside
`restore_snapshot` writes to a path under `_restore_staging`** — never
directly to a live target. That structural invariant alone is enough
to distinguish pre-fix from post-fix.

Pre-fix: calls land at `targets[name]` (live paths) → fails.
Post-fix: calls land at `snap_dir / "_restore_staging" / name`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.api.persist import restore_snapshot


def _stage_snapshot(snapshots_dir: Path, snap_id: str, files: dict[str, bytes]) -> Path:
    """Write a synthetic snapshot dir under snapshots_dir/<snap_id>/."""
    snap_dir = snapshots_dir / snap_id
    snap_dir.mkdir(parents=True)
    for name, payload in files.items():
        (snap_dir / name).write_bytes(payload)
    return snap_dir


@pytest.mark.xfail(
    reason="FP27 T2 — B2 implementation not yet landed; this test stays "
    "RED until restore_snapshot adds the _restore_staging stage-then-promote step.",
    strict=True,
)
def test_restore_snapshot_atomic_writes_land_in_staging_area(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every `atomic_write_bytes` invocation made by `restore_snapshot`
    must write to a path under `_restore_staging/`, not directly to a
    live target.

    Pre-fix: `restore_snapshot` calls `atomic_write_bytes(dst, ...)`
    where `dst` is the live target — no staging dir involved → fails.
    Post-fix: `atomic_write_bytes` writes into `snap_dir/_restore_staging/`,
    then a promote step replaces live targets → passes.
    """
    snapshots_dir = tmp_path / "snapshots"
    _stage_snapshot(
        snapshots_dir,
        "snap1",
        {"a.yaml": b"NEW A", "b.yaml": b"NEW B"},
    )

    live = tmp_path / "live"
    live.mkdir()
    (live / "a.yaml").write_bytes(b"OLD A")
    (live / "b.yaml").write_bytes(b"OLD B")
    (live / "x.yaml").write_bytes(b"EXTRA X")  # to be unlinked

    targets = {
        "a.yaml": live / "a.yaml",
        "b.yaml": live / "b.yaml",
        "x.yaml": live / "x.yaml",
    }

    write_destinations: list[Path] = []
    # Capture the module's own reference (the implementation imports
    # `atomic_write_bytes` from `mame_curator._atomic` at module load,
    # so monkeypatching there is what counts).
    from mame_curator.api import persist as persist_mod

    real_atomic_write_bytes = persist_mod.atomic_write_bytes  # type: ignore[attr-defined]  # FP27 T2 B2: persist_mod's bound import; not in __all__.

    def _spy_atomic_write_bytes(path: Path, data: bytes) -> None:
        write_destinations.append(Path(path))
        real_atomic_write_bytes(path, data)

    monkeypatch.setattr(persist_mod, "atomic_write_bytes", _spy_atomic_write_bytes)

    restore_snapshot(snapshots_dir, "snap1", targets)

    # Sanity: at least one write happened (a.yaml + b.yaml are in the
    # snapshot, so two atomic_write_bytes calls are expected).
    assert len(write_destinations) >= 2, (
        f"expected ≥2 atomic_write_bytes calls (one per snapshot file), "
        f"got {len(write_destinations)}: {write_destinations!r}"
    )

    # Post-fix invariant: every destination path is under
    # `_restore_staging/`. Pre-fix every destination is a live path.
    live_writes = [d for d in write_destinations if "_restore_staging" not in str(d)]
    assert not live_writes, (
        "FP27 B2 — `restore_snapshot` must write all atomic_write_bytes "
        "destinations under `_restore_staging/`, never directly to live "
        "targets. Saw direct-live writes: "
        f"{live_writes!r}. See `docs/specs/FP27.md` § B2."
    )

    # End state: live targets correctly restored (sanity check on the
    # promote step).
    assert (live / "a.yaml").read_bytes() == b"NEW A"
    assert (live / "b.yaml").read_bytes() == b"NEW B"
    assert not (live / "x.yaml").exists(), "x.yaml absent from snapshot must be unlinked"
