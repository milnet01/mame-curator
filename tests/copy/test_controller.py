"""Tests for `CopyController` pause/resume/cancel state machine."""

from __future__ import annotations

import threading

from mame_curator.copy import CopyController, CopyControlState


def test_controller_starts_running() -> None:
    c = CopyController()
    assert c.state is CopyControlState.RUNNING
    assert not c.should_cancel()
    assert not c.recycle_partial


def test_controller_pause_transitions_to_paused() -> None:
    c = CopyController()
    c.pause()
    assert c.state is CopyControlState.PAUSED


def test_controller_resume_transitions_back_to_running() -> None:
    c = CopyController()
    c.pause()
    c.resume()
    assert c.state is CopyControlState.RUNNING


def test_controller_cancel_is_sticky() -> None:
    """Once cancelled, cannot be undone."""
    c = CopyController()
    c.cancel()
    assert c.state is CopyControlState.CANCELLING
    assert c.should_cancel()
    # resume() should not undo a cancel.
    c.resume()
    assert c.state is CopyControlState.CANCELLING
    assert c.should_cancel()


def test_controller_cancel_with_recycle_partial_flag() -> None:
    c = CopyController()
    c.cancel(recycle_partial=True)
    assert c.recycle_partial is True


def test_controller_wait_if_paused_blocks_until_resume() -> None:
    """A worker calling wait_if_paused() blocks while paused; unblocks on resume."""
    c = CopyController()
    c.pause()

    unblocked = threading.Event()

    def worker() -> None:
        c.wait_if_paused()
        unblocked.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    # Worker should be blocked.
    assert not unblocked.wait(timeout=0.2)

    c.resume()
    assert unblocked.wait(timeout=2.0)
    t.join(timeout=2.0)


def test_controller_wait_if_paused_unblocks_on_cancel() -> None:
    """A paused worker unblocks when the session is cancelled (so it can exit)."""
    c = CopyController()
    c.pause()

    released = threading.Event()

    def worker() -> None:
        c.wait_if_paused()
        released.set()

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    assert not released.wait(timeout=0.1)

    c.cancel()
    assert released.wait(timeout=2.0)
    t.join(timeout=2.0)
