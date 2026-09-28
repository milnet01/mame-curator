"""mame-curator-1010 spec §4.3 — applying an update to a git clone.

Every test runs real `git` against a throwaway clone and a bare origin under
`tmp_path`; only `uv` is replaced, through the `run` seam, so no test touches
this checkout or the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from mame_curator.updates.app import (
    DEV_TARGET,
    UpdateError,
    apply_git_update,
    rollback_git_update,
)
from tests.updates.gitrepo import Recorder, commit, git, make_clone

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="drives git; POSIX-only")


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    return make_clone(tmp_path)


def test_update_fast_forwards_to_the_tag(clone: Path) -> None:
    result = apply_git_update(clone, target="v1.1.0", before_move=lambda: "snap1", run=Recorder())
    assert result.to_commit == git(clone, "rev-parse", "v1.1.0")
    assert result.previous_commit == git(clone, "rev-parse", "v1.0.0")
    assert not result.rolled_back


def test_dev_channel_follows_origin_main(clone: Path) -> None:
    result = apply_git_update(clone, target=DEV_TARGET, before_move=lambda: "s", run=Recorder())
    assert result.to_commit == git(clone, "rev-parse", "origin/main")


def test_dirty_tree_refuses_before_anything(clone: Path) -> None:
    """INV-5 — no snapshot, no fetch."""
    (clone / "a.txt").write_text("edited")
    snapped: list[str] = []

    def before_move() -> str:
        snapped.append("x")
        return "s"

    rec = Recorder()
    with pytest.raises(UpdateError) as err:
        apply_git_update(clone, target="v1.1.0", before_move=before_move, run=rec)
    assert err.value.code == "update_dirty_tree"
    assert snapped == []
    assert not any("fetch" in call[0] for call in rec.calls)


def test_missing_tool_refuses_before_anything(clone: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import shutil

    monkeypatch.setattr(shutil, "which", lambda t: None if t == "uv" else "/x")
    with pytest.raises(UpdateError) as err:
        apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=Recorder())
    assert err.value.code == "update_tool_missing"
    assert "uv" in err.value.detail


def test_snapshot_precedes_merge(clone: Path) -> None:
    """INV-6 — the snapshot is taken while HEAD is still the old commit."""
    old = git(clone, "rev-parse", "HEAD")
    seen: list[str] = []

    def before_move() -> str:
        seen.append(git(clone, "rev-parse", "HEAD"))
        return "snap-42"

    result = apply_git_update(clone, target="v1.1.0", before_move=before_move, run=Recorder())
    assert seen == [old]
    assert result.snapshot_id == "snap-42"


def test_diverged_clone_is_refused(clone: Path) -> None:
    """INV-7 — a local commit makes the update not a fast-forward."""
    commit(clone, "local.txt")
    head = git(clone, "rev-parse", "HEAD")
    with pytest.raises(UpdateError) as err:
        apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=Recorder())
    assert err.value.code == "update_not_fast_forward"
    assert git(clone, "rev-parse", "HEAD") == head


def test_untracked_collision_is_refused(clone: Path) -> None:
    """An untracked file the merge would overwrite: refused, HEAD unchanged."""
    (clone / "b.txt").write_text("mine")
    head = git(clone, "rev-parse", "HEAD")
    with pytest.raises(UpdateError) as err:
        apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=Recorder())
    assert err.value.code == "update_merge_refused"
    assert git(clone, "rev-parse", "HEAD") == head


def test_unreachable_origin_is_a_fetch_failure(clone: Path) -> None:
    git(clone, "remote", "set-url", "origin", str(clone.parent / "gone.git"))
    with pytest.raises(UpdateError) as err:
        apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=Recorder())
    assert err.value.code == "update_fetch_failed"
    assert err.value.status == 502


def test_failed_sync_rolls_back(clone: Path) -> None:
    """INV-8 — the tree returns to previous_commit; the re-sync succeeded."""
    old = git(clone, "rev-parse", "HEAD")
    result = apply_git_update(
        clone, target="v1.1.0", before_move=lambda: "s", run=Recorder(uv_codes=[1, 0])
    )
    assert result.rolled_back
    assert not result.sync_failed
    assert git(clone, "rev-parse", "HEAD") == old
    assert result.output == "uv: offline"


def test_failed_resync_is_reported(clone: Path) -> None:
    result = apply_git_update(
        clone, target="v1.1.0", before_move=lambda: "s", run=Recorder(uv_codes=[1, 1])
    )
    assert result.rolled_back and result.sync_failed


def test_rollback_resets_to_the_recordedcommit(clone: Path) -> None:
    result = apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=Recorder())
    sync_failed = rollback_git_update(clone, previous_commit=result.previous_commit, run=Recorder())
    assert not sync_failed
    assert git(clone, "rev-parse", "HEAD") == result.previous_commit


def test_no_shell(clone: Path) -> None:
    """INV-13 — every git and uv call is an argument list with no shell."""
    rec = Recorder(uv_codes=[1, 0])
    apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=rec)
    assert rec.calls
    for args, kwargs in rec.calls:
        assert isinstance(args, list)
        assert not kwargs.get("shell")
        assert kwargs["cwd"] == clone


def test_calls_carry_a_timeout_and_no_prompt(clone: Path) -> None:
    """review-code 2026-09-28 L1-1 — a stalled git or uv cannot hold the lock forever."""
    rec = Recorder()
    apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=rec)
    for _args, kwargs in rec.calls:
        assert kwargs.get("timeout"), kwargs
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"


def test_a_fetch_that_times_out_is_a_fetch_failure(clone: Path) -> None:
    head = git(clone, "rev-parse", "HEAD")
    with pytest.raises(UpdateError) as err:
        apply_git_update(
            clone, target="v1.1.0", before_move=lambda: "s", run=Recorder(timeout_git=("fetch",))
        )
    assert err.value.code == "update_fetch_failed"
    assert "timed out" in (err.value.output or "")
    assert git(clone, "rev-parse", "HEAD") == head


def test_a_failed_reset_is_not_reported_as_rolled_back(clone: Path) -> None:
    """L1-5 — the sync failed and the reset failed: the tree is on the new code."""
    result = apply_git_update(
        clone,
        target="v1.1.0",
        before_move=lambda: "s",
        run=Recorder(uv_codes=[1, 0], fail_git=("reset",)),
    )
    assert not result.rolled_back
    assert result.sync_failed
    assert result.to_commit == git(clone, "rev-parse", "v1.1.0")


def test_a_target_is_never_read_as_an_option(clone: Path) -> None:
    """L1-7 — a tag name reaches git after --end-of-options."""
    rec = Recorder()
    apply_git_update(clone, target="v1.1.0", before_move=lambda: "s", run=rec)
    for args, _ in rec.calls:
        if args[1] in ("merge", "merge-base"):
            assert args[-2] == "--end-of-options", args
