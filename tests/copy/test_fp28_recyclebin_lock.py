"""FP28 A2 + A3 — `recycle_file` must serialise parallel-session counter walks.

``copy/recyclebin.py:51-64`` walks a `-1, -2, …` counter on the parent
directory and then calls ``target_dir.mkdir(parents=True, exist_ok=True)``;
the check + mkdir is non-atomic across sessions. Two parallel
``recycle_file`` calls with the same ``session_id`` + same basename can both
pass ``target_dir.exists()`` at the same counter value (A2). The post-move
rollback at ``L86-88`` and ``L100-105`` can then ``rmdir`` a directory the
parallel session expected to use (A3).

A2 wraps the critical section in an ``os.O_EXCL`` lockfile keyed on
``recycle_root / f"{session_id}.lock"``; A3 is solved by construction once
A2's lock serialises the section.

Pre-fix: the two-worker barrier hits the race window — exactly one source
file may end up at the expected counter-walked path; the other clobbers or
fails. The rmdir-counter assertion fires.
Post-fix: both source files land at distinct counter-walked targets; no
rollback fires; the lockfile is released cleanly.

See ``docs/specs/FP28.md`` §§ A2, A3.
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from mame_curator.copy.recyclebin import recycle_file


def test_recycle_file_serializes_parallel_sessions(tmp_path: Path) -> None:
    """Two workers, same session_id + same basename, lockstep entry."""
    recycle_root = tmp_path / "recycle"
    src_a = tmp_path / "src-a"
    src_b = tmp_path / "src-b"
    src_a.mkdir()
    src_b.mkdir()
    file_a = src_a / "rom.zip"
    file_b = src_b / "rom.zip"
    file_a.write_bytes(b"AAAA")
    file_b.write_bytes(b"BBBB")

    barrier = threading.Barrier(2)

    def _worker(path: Path) -> Path:
        barrier.wait()
        # FP31: pre-commit isolated mypy infers `Any` for `recycle_file`
        # (no source package on its path). Suppress + companion-marker per
        # the established pattern (see 1f3d9ab).
        return recycle_file(  # type: ignore[no-any-return, unused-ignore]
            path, reason="REPLACE_AND_RECYCLE", session_id="s1", recycle_root=recycle_root
        )

    with ThreadPoolExecutor(max_workers=2) as ex:
        results = list(ex.map(_worker, [file_a, file_b]))

    # Both source files moved (zero data loss); destinations must be distinct.
    assert len(results) == 2
    assert results[0] != results[1]
    assert all(p.exists() for p in results)
    # Lockfile released — must not persist post-call.
    assert not (recycle_root / "s1.lock").exists()


def test_recycle_file_rollback_does_not_rmdir_parallel_session_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A3 — manifest-write failure must not rmdir a sibling's just-made dir.

    Force the second worker's manifest write to fail. Post-fix lock holds the
    section atomically so the second worker's rollback (rmdir on a dir it
    *did* create itself) doesn't touch the first worker's directory.
    """
    import mame_curator._atomic as atomic_mod

    recycle_root = tmp_path / "recycle"
    src_a = tmp_path / "src-a"
    src_b = tmp_path / "src-b"
    src_a.mkdir()
    src_b.mkdir()
    file_a = src_a / "rom.zip"
    file_b = src_b / "rom.zip"
    file_a.write_bytes(b"AAAA")
    file_b.write_bytes(b"BBBB")

    call_count = {"n": 0}
    real_atomic_write_text = atomic_mod.atomic_write_text

    def _failing_atomic_write_text(*args: object, **kwargs: object) -> None:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise OSError("simulated manifest failure on worker 2")
        # FP31: pre-commit isolated mypy infers `Any` for atomic_write_text
        # (full mypy sees the real `-> None`). Suppress no-any-return for
        # the isolated case + arg-type for the full case (it sees
        # `*args: object` spread vs the real `(path: Path, content: str)`
        # signature) + unused-ignore companion for whichever rule didn't
        # fire in the current pass. Established pattern (see 1f3d9ab).
        return real_atomic_write_text(*args, **kwargs)  # type: ignore[no-any-return, arg-type, unused-ignore]

    monkeypatch.setattr(
        "mame_curator.copy.recyclebin.atomic_write_text", _failing_atomic_write_text
    )

    barrier = threading.Barrier(2)
    results: list[BaseException | Path] = []

    def _worker(path: Path) -> None:
        barrier.wait()
        try:
            results.append(
                recycle_file(
                    path, reason="REPLACE_AND_RECYCLE", session_id="s1", recycle_root=recycle_root
                )
            )
        except Exception as exc:
            results.append(exc)

    t1 = threading.Thread(target=_worker, args=(file_a,), daemon=True)
    t2 = threading.Thread(target=_worker, args=(file_b,), daemon=True)
    t1.start()
    t2.start()
    # FP31: bound the join so a regression that leaves the O_EXCL lockfile
    # held doesn't hang the whole test runner. Recycle of a tiny test file
    # completes in well under a second.
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert not t1.is_alive(), "t1 stuck — recycle_file lockfile not released?"
    assert not t2.is_alive(), "t2 stuck — recycle_file lockfile not released?"

    # One worker succeeded, one failed. The successful one's recycle dir must
    # still exist post-call — the failing worker's rollback must not have
    # rmdir'd it.
    successes = [r for r in results if isinstance(r, Path)]
    assert len(successes) == 1
    assert successes[0].exists()
    assert successes[0].parent.exists()
