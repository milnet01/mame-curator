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

See ``docs/specs/FP28-hardening-correctness.md`` §§ A2, A3.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from mame_curator.copy import recyclebin
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


# ---- Windows refusing the lock file ------------------------------------------
#
# These stub os.open, so they prove what the lock does WITH a PermissionError.
# They do not prove Windows raises one for a lock being deleted.

DENIED = PermissionError(13, "Permission denied")


class _Clock:
    """Stands in for `time` in the module: a sleep moves it on and waits for nothing."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds

    def time(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> _Clock:
    fake = _Clock()
    monkeypatch.setattr(recyclebin, "time", fake)
    return fake


def _stub_lock_open(monkeypatch: pytest.MonkeyPatch, step: Callable[[int], None]) -> list[int]:
    """Call `step(attempt)` before each open of the lock; if it returns, really open it."""
    real_open = os.open
    attempts: list[int] = []

    def _open(path: Any, flags: int, mode: int = 0o777) -> int:
        if Path(path).name == "s1.lock":
            attempts.append(len(attempts) + 1)
            step(attempts[-1])
        return real_open(path, flags, mode)

    monkeypatch.setattr(os, "open", _open)
    return attempts


def test_windows_retries_a_lock_it_is_refused_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _Clock
) -> None:
    monkeypatch.setattr(recyclebin, "_WINDOWS", True)

    def _refuse_first(attempt: int) -> None:
        if attempt == 1:
            raise DENIED

    attempts = _stub_lock_open(monkeypatch, _refuse_first)

    with recyclebin._session_lock(tmp_path, "s1"):
        assert (tmp_path / "s1.lock").exists()

    assert len(attempts) == 2
    assert not (tmp_path / "s1.lock").exists()


def test_windows_gives_the_real_error_when_refused_until_the_deadline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _Clock
) -> None:
    monkeypatch.setattr(recyclebin, "_WINDOWS", True)
    deadline = recyclebin._LOCK_DENIED_RETRY_SECONDS

    def _always_refuse(attempt: int) -> None:
        # Ends the test if the deadline or the sleep is gone; it would loop for ever.
        assert clock.now < deadline * 2 and attempt < 10_000, "still retrying past the deadline"
        raise DENIED

    attempts = _stub_lock_open(monkeypatch, _always_refuse)

    with (
        pytest.raises(PermissionError) as refused,
        recyclebin._session_lock(tmp_path, "s1"),
    ):
        pass

    assert refused.value is DENIED
    assert len(attempts) > 1
    assert clock.now >= deadline


def test_windows_deadline_counts_only_an_unbroken_run_of_refusals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _Clock
) -> None:
    """A long wait behind a working holder must not use up the time for a refusal."""
    monkeypatch.setattr(recyclebin, "_WINDOWS", True)

    def _refuse_wait_refuse(attempt: int) -> None:
        if attempt == 1:
            raise DENIED
        if attempt == 2:
            clock.now += recyclebin._LOCK_DENIED_RETRY_SECONDS * 2
            raise FileExistsError
        if attempt == 3:
            raise DENIED

    attempts = _stub_lock_open(monkeypatch, _refuse_wait_refuse)

    with recyclebin._session_lock(tmp_path, "s1"):
        pass

    assert len(attempts) == 4


def test_posix_gives_the_real_error_at_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _Clock
) -> None:
    """POSIX has no delete-pending state: a refusal is a folder that stays refused."""
    monkeypatch.setattr(recyclebin, "_WINDOWS", False)

    def _always_refuse(_attempt: int) -> None:
        raise DENIED

    attempts = _stub_lock_open(monkeypatch, _always_refuse)

    with (
        pytest.raises(PermissionError) as refused,
        recyclebin._session_lock(tmp_path, "s1"),
    ):
        pass

    assert refused.value is DENIED
    assert len(attempts) == 1
    assert clock.now == 0.0


# ---- a stale lock, and a lock still in use (mame-curator-1193) ---------------


def test_a_stale_lock_that_cannot_be_removed_gives_a_clear_error_in_bounded_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, clock: _Clock
) -> None:
    """Before the fix the unlink error was suppressed and the loop retried at
    once, with no sleep and no end."""
    from mame_curator.copy.errors import RecycleError

    lock = tmp_path / "s1.lock"
    lock.write_bytes(b"")
    os.utime(lock, (0, 0))
    clock.now = recyclebin._LOCK_STALE_SECONDS * 10
    started = clock.now
    real_unlink = Path.unlink
    unlinks: list[int] = []

    def _refuse_unlink(self: Path, missing_ok: bool = False) -> None:
        if self.name == "s1.lock":
            unlinks.append(1)
            # Ends the test if the sleep or the deadline is gone.
            assert len(unlinks) < 10_000, "still retrying a lock it cannot remove"
            raise DENIED
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", _refuse_unlink)

    with pytest.raises(RecycleError) as stuck, recyclebin._session_lock(tmp_path, "s1"):
        pass

    assert stuck.value.path == lock
    assert "stale" in str(stuck.value)
    # mame-curator-1201: watched stale first, then refused for the 5 seconds.
    waited = clock.now - started
    floor = recyclebin._LOCK_STALE_SECONDS + recyclebin._LOCK_UNREMOVABLE_SECONDS
    assert floor <= waited < floor + recyclebin._LOCK_UNREMOVABLE_SECONDS
    assert lock.exists()


def test_a_lock_held_longer_than_the_stale_age_is_not_reclaimed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A move holding the lock past the stale age (a large cross-drive file)
    must keep it: the second caller waits for the release.

    Real time, scaled down: stale after 0.5 s, the holder holds for 1.5 s.
    """
    monkeypatch.setattr(recyclebin, "_LOCK_STALE_SECONDS", 0.5)
    monkeypatch.setattr(recyclebin, "_LOCK_REFRESH_SECONDS", 0.05)
    held = threading.Event()
    order: list[str] = []

    def _holder() -> None:
        with recyclebin._session_lock(tmp_path, "s1"):
            held.set()
            time.sleep(1.5)
            order.append("holder released")

    def _waiter() -> None:
        held.wait(timeout=5)
        with recyclebin._session_lock(tmp_path, "s1"):
            order.append("waiter acquired")

    threads = [threading.Thread(target=f, daemon=True) for f in (_holder, _waiter)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)
    assert not any(t.is_alive() for t in threads), "a lock user is stuck"

    assert order == ["holder released", "waiter acquired"]
    assert not (tmp_path / "s1.lock").exists()
