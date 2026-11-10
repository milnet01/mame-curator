"""mame-curator-1201 — the recycle lock admits one holder and never spins.

A cold read found five ways the lock broke its spec. Each test drives the
lock with a fake clock: a second holder, "B", is a script run from the
waiter's own sleeps, so every interleaving is fixed and nothing waits in
real time.
"""

from __future__ import annotations

import errno
import os
import sys
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from mame_curator.copy import recyclebin
from mame_curator.copy.errors import RecycleError

B = b"B-holder"
REFRESH = 10.0
POSIX_ONLY = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows will not delete or rename a lock its holder has open, so no swap",
)


class _World:
    """A fake clock, and B: a live holder that refreshes its lock as time passes."""

    def __init__(self, lock: Path) -> None:
        self.now = 1000.0
        self.lock = lock
        self.sleeps = 0
        self.b_alive = False
        self.b_release_at: float | None = None
        self.b_next_refresh = 0.0
        self.b_mtime_offset = 0.0
        self.b_robbed_at: float | None = None

    def monotonic(self) -> float:
        return self.now

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps += 1
        assert self.sleeps < 100_000, "still waiting long past any deadline"
        self.now += seconds
        self._run_b()

    def start_b(self, *, release_after: float | None, mtime_offset: float = 0.0) -> None:
        """B takes the lock now: whatever was at the path is gone."""
        self.lock.unlink(missing_ok=True)
        self.lock.write_bytes(B)
        self.b_alive, self.b_mtime_offset = True, mtime_offset
        self.b_release_at = None if release_after is None else self.now + release_after
        self.b_next_refresh = self.now + REFRESH
        self._touch_b()

    def _touch_b(self) -> None:
        stamp = self.now + self.b_mtime_offset
        os.utime(self.lock, (stamp, stamp))

    def _run_b(self) -> None:
        if not self.b_alive:
            return
        if not (self.lock.exists() and self.lock.read_bytes().startswith(B)):
            self.b_robbed_at, self.b_alive = self.now, False
            return
        if self.b_release_at is not None and self.now >= self.b_release_at:
            self.lock.unlink()
            self.b_alive = False
        elif self.now >= self.b_next_refresh:
            with self.lock.open("ab") as f:
                f.write(b".")
            self._touch_b()
            self.b_next_refresh += REFRESH


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _World:
    fake = _World(tmp_path / "s1.lock")
    monkeypatch.setattr(recyclebin, "time", fake)
    monkeypatch.setattr(recyclebin, "_LOCK_RETRY_SLEEP", 0.5)
    return fake


def _after_each_look(monkeypatch: pytest.MonkeyPatch, lock: Path, hook: Callable[[], None]) -> None:
    """Run `hook` after every stat of the lock, by whichever call the lock uses.

    Also after a stat that raised, so a hook can count looks that fail.
    """
    for name in ("stat", "lstat"):
        real = getattr(os, name)

        def _look(
            path: object, *a: object, _real: Callable[..., object] = real, **k: object
        ) -> object:
            try:
                return _real(path, *a, **k)
            finally:
                if Path(str(path)) == lock:
                    hook()

        monkeypatch.setattr(os, name, _look)


def _stale_lock(world: _World) -> os.stat_result:
    world.lock.write_bytes(b"crashed")
    os.utime(world.lock, (0, 0))
    return os.lstat(world.lock)


def _acquire_and_check_owner(tmp_path: Path, world: _World) -> float:
    with recyclebin._session_lock(tmp_path, "s1"):
        assert not world.lock.read_bytes().startswith(B), "the waiter is inside B's lock"
        return world.now


# ---- F1: a waiter removes only a lock it has itself watched go stale ---------


def test_a_lock_that_appears_after_the_first_look_is_not_removed(
    tmp_path: Path, world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another waiter reclaimed the crashed lock and B took it; this waiter must wait."""
    _stale_lock(world)
    looks: list[float] = []

    def _b_takes_over() -> None:
        looks.append(world.now)
        if len(looks) == 1:
            world.start_b(release_after=120)

    _after_each_look(monkeypatch, world.lock, _b_takes_over)

    acquired_at = _acquire_and_check_owner(tmp_path, world)

    assert world.b_robbed_at is None, "the waiter removed B's live lock"
    assert acquired_at >= looks[0] + 120


def test_a_lock_that_changes_after_the_stale_decision_is_not_removed(
    tmp_path: Path, world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lock is swapped between the look that judged it stale and the removal."""
    _stale_lock(world)
    looks: list[float] = []

    def _b_takes_over_once_stale() -> None:
        looks.append(world.now)
        stale = world.now - looks[0] > recyclebin._LOCK_STALE_SECONDS
        if stale and not world.b_alive and world.b_release_at is None:
            world.start_b(release_after=120)

    _after_each_look(monkeypatch, world.lock, _b_takes_over_once_stale)

    _acquire_and_check_owner(tmp_path, world)

    assert world.b_release_at is not None, "the waiter never watched the lock go stale"
    assert world.b_robbed_at is None, "the waiter removed B's live lock"


def test_a_second_reclaimer_leaves_the_lock_to_the_first(tmp_path: Path, world: _World) -> None:
    """While one waiter holds the reclaim guard, another removes nothing."""
    stale = _stale_lock(world)
    guard = world.lock.with_name("s1.lock.reclaim")
    guard.write_bytes(b"")

    blocked_by = recyclebin._reclaim_lock(world.lock, recyclebin._lock_signature(world.lock))

    assert blocked_by == guard
    assert os.lstat(world.lock).st_ino == stale.st_ino
    assert guard.exists(), "the guard belongs to the other reclaimer"


# ---- F2: release and refresh touch only the holder's own lock ----------------


@POSIX_ONLY
def test_release_leaves_a_lock_it_does_not_own(tmp_path: Path) -> None:
    lock = tmp_path / "s1.lock"
    with recyclebin._session_lock(tmp_path, "s1"):
        lock.unlink()
        lock.write_bytes(B)
    assert lock.read_bytes() == B


@POSIX_ONLY
def test_the_refresher_touches_only_the_lock_it_holds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(recyclebin, "_LOCK_REFRESH_SECONDS", 0.001)
    lock = tmp_path / "s1.lock"
    mine = tmp_path / "mine.lock"
    with recyclebin._session_lock(tmp_path, "s1"):
        os.replace(lock, mine)
        lock.write_bytes(B)
        os.utime(lock, (0, 0))
        start = mine.stat().st_size
        refreshed = threading.Event()
        for _ in range(2000):
            if mine.stat().st_size >= start + 2:
                refreshed.set()
                break
            refreshed.wait(0.005)
        assert refreshed.is_set(), "the holder's own lock was never refreshed"
        assert lock.read_bytes() == B
        assert lock.stat().st_mtime == 0


# ---- F3: staleness does not compare two clocks -------------------------------


def test_a_live_lock_written_by_a_clock_far_behind_is_not_stale(
    tmp_path: Path, world: _World
) -> None:
    """recycle_root on a share whose clock is an hour behind this one's."""
    world.start_b(release_after=120, mtime_offset=-3600)
    start = world.now

    acquired_at = _acquire_and_check_owner(tmp_path, world)

    assert world.b_robbed_at is None, "the waiter took a live lock"
    assert acquired_at >= start + 120


def test_a_suspend_does_not_age_a_live_lock(
    tmp_path: Path, world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The machine sleeps for an hour while B holds the lock; B refreshes on waking."""
    world.start_b(release_after=None)
    real_sleep = world.sleep
    suspended = [False]

    def _sleep(seconds: float) -> None:
        if not suspended[0]:
            suspended[0] = True
            world.now += 3600
            world.b_next_refresh = world.now + 5
            world.b_release_at = world.now + 120
        real_sleep(seconds)

    monkeypatch.setattr(world, "sleep", _sleep)
    start = world.now

    acquired_at = _acquire_and_check_owner(tmp_path, world)

    assert world.b_robbed_at is None, "the waiter took a live lock after the suspend"
    assert acquired_at >= start + 3600 + 120


# ---- F4: a lock that cannot be looked at does not spin -----------------------


@pytest.mark.skipif(sys.platform == "win32", reason="making a symlink needs a privilege on Windows")
def test_a_dangling_symlink_lock_is_reclaimed_without_spinning(
    tmp_path: Path, world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.lock.symlink_to(tmp_path / "nowhere")
    looks: list[float] = []

    def _count() -> None:
        looks.append(world.now)
        assert len(looks) < 100_000, "spinning on a lock it cannot look at"

    _after_each_look(monkeypatch, world.lock, _count)
    start = world.now

    acquired_at = _acquire_and_check_owner(tmp_path, world)

    assert acquired_at >= start + recyclebin._LOCK_STALE_SECONDS


def test_a_lock_that_cannot_be_looked_at_fails_in_bounded_time(
    tmp_path: Path, world: _World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A persistent ESTALE on a network share: sleep between tries, then give up."""
    world.lock.write_bytes(b"")
    looks: list[float] = []

    def _estale() -> None:
        looks.append(world.now)
        assert len(looks) < 100_000, "spinning on a lock it cannot look at"
        raise OSError(errno.ESTALE, "Stale file handle")

    _after_each_look(monkeypatch, world.lock, _estale)
    start = world.now

    with pytest.raises(RecycleError) as stuck, recyclebin._session_lock(tmp_path, "s1"):
        pass

    assert stuck.value.path == world.lock
    assert world.now - start >= recyclebin._LOCK_WAIT_SECONDS


# ---- F5: a lock kept in use for ever ends the wait ---------------------------


def test_a_lock_held_for_ever_ends_the_wait_with_an_error(tmp_path: Path, world: _World) -> None:
    """A holder stuck on a dead share keeps refreshing; the waiter gives up."""
    world.start_b(release_after=None)
    start = world.now

    with pytest.raises(RecycleError) as stuck, recyclebin._session_lock(tmp_path, "s1"):
        pass

    assert stuck.value.path == world.lock
    waited = world.now - start
    assert recyclebin._LOCK_WAIT_SECONDS <= waited < recyclebin._LOCK_WAIT_SECONDS + 5
    assert world.b_robbed_at is None
