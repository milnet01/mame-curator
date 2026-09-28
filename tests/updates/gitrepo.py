"""A throwaway git clone and origin for the mame-curator-1010 update tests.

Shared by ``tests/updates/test_git_update.py`` and
``tests/api/test_routes_updates.py``. Callers are POSIX-only: they drive git.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(  # noqa: S603 — fixed argv, test-owned repo
        ["git", *args],  # noqa: S607 — git from PATH, as the code under test runs it
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name)
    git(repo, "add", name)
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", name)


def make_clone(tmp_path: Path) -> Path:
    """A clone on tag v1.0.0 whose origin carries v1.1.0 one commit ahead."""
    work = tmp_path / "work"
    work.mkdir(parents=True)
    git(work, "init", "-q", "-b", "main")
    commit(work, "a.txt")
    git(work, "tag", "v1.0.0")
    commit(work, "b.txt")
    git(work, "tag", "v1.1.0")
    git(tmp_path, "clone", "-q", "--bare", str(work), "origin.git")
    repo = tmp_path / "clone"
    git(tmp_path, "clone", "-q", str(tmp_path / "origin.git"), "clone")
    git(repo, "reset", "-q", "--hard", "v1.0.0")
    return repo


class Recorder:
    """The `run` seam: real git, a faked `uv` whose exit codes are scripted.

    ``fail_git`` names git subcommands to answer with exit 1 instead of
    running; ``timeout_git`` names ones to raise ``TimeoutExpired`` on.
    """

    def __init__(
        self,
        uv_codes: list[int] | None = None,
        *,
        fail_git: tuple[str, ...] = (),
        timeout_git: tuple[str, ...] = (),
    ) -> None:
        self.calls: list[tuple[Any, dict[str, Any]]] = []
        self.uv_codes = list(uv_codes or [])
        self.fail_git = fail_git
        self.timeout_git = timeout_git

    def __call__(self, args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append((args, kwargs))
        if args[0] == "uv":
            code = self.uv_codes.pop(0) if self.uv_codes else 0
            return subprocess.CompletedProcess(args, code, "", "uv: offline" if code else "")
        if args[1] in self.timeout_git:
            raise subprocess.TimeoutExpired(args, kwargs.get("timeout") or 0)
        if args[1] in self.fail_git:
            return subprocess.CompletedProcess(args, 1, "", f"git {args[1]}: failed")
        return subprocess.run(args, **kwargs)  # noqa: S603 — argv from the code under test
