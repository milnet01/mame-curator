"""Pause / resume / cancel controller for in-flight copy sessions."""

from __future__ import annotations

import threading
from enum import StrEnum


class CopyControlState(StrEnum):
    """Lifecycle state of a copy session driven by `CopyController`."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    DONE = "DONE"


class CopyController:
    """Thread-safe pause/resume/cancel state for a copy session.

    Pause holds at file boundary (never mid-file). Cancel is sticky —
    once set, cannot be undone. `wait_if_paused()` and `should_cancel()`
    are checked between files by `run_copy`.
    """

    def __init__(self) -> None:
        """Initialise in RUNNING state; not paused, not cancelled."""
        self._lock = threading.Lock()
        self._state = CopyControlState.RUNNING
        self._resume_event = threading.Event()
        self._resume_event.set()  # not paused
        self._cancel_flag = False
        self._recycle_partial = False

    @property
    def state(self) -> CopyControlState:
        """Current control state."""
        with self._lock:
            return self._state

    @property
    def recycle_partial(self) -> bool:
        """Whether a cancel requested partial-copy recycling."""
        with self._lock:
            return self._recycle_partial

    def pause(self) -> None:
        """Transition to PAUSED unless already cancelled."""
        with self._lock:
            if self._cancel_flag:
                return
            self._state = CopyControlState.PAUSED
            self._resume_event.clear()

    def resume(self) -> None:
        """Transition back to RUNNING; sticky-cancel still wakes waiters."""
        with self._lock:
            if self._cancel_flag:
                self._resume_event.set()
                return
            self._state = CopyControlState.RUNNING
            self._resume_event.set()

    def cancel(self, *, recycle_partial: bool = False) -> None:
        """Sticky cancel; wakes any paused waiter so it can exit."""
        with self._lock:
            self._cancel_flag = True
            self._recycle_partial = recycle_partial
            self._state = CopyControlState.CANCELLING
            self._resume_event.set()

    def wait_if_paused(self) -> None:
        """Block until resume or cancel; called between files by `run_copy`."""
        # Safe-without-lock: Event.set() is atomic; we only need the wakeup edge.
        self._resume_event.wait()

    def should_cancel(self) -> bool:
        """Return True once `cancel()` has been called."""
        with self._lock:
            return self._cancel_flag
