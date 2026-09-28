"""App self-update: install kind, the latest release, and applying it.

mame-curator-1010 spec §4.1-§4.4.

``updates/`` may import ``downloads.py`` and ``_resources.py``, never
``api/``: the snapshot step arrives as the ``before_move`` callable, and the
route writes ``data/update-state.json`` and the activity entry itself.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import platform
import re
import shutil
import subprocess  # nosec B404 — mame-curator-1010: git and uv only, as argument lists with no shell (INV-13); argv holds fixed verbs plus a tag or commit id from GitHub or git itself.
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeGuard

import httpx

from mame_curator._resources import bundle_root
from mame_curator.downloads import DownloadError, ManualFallback, download

InstallKind = Literal["git", "bundle", "package"]
Run = Callable[..., "subprocess.CompletedProcess[str]"]

LATEST_RELEASE_URL = "https://api.github.com/repos/milnet01/mame-curator/releases/latest"
DEV_TARGET = "origin/main"
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
_OUTPUT_CAP = 4000
# A stalled fetch or sync would otherwise hold the update lock until a restart.
GIT_TIMEOUT_SECONDS = 120
UV_TIMEOUT_SECONDS = 600
_HEX_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class UpdateCheckError(Exception):
    """The release check failed: network, non-200, or an unparseable body."""


class UpdateError(Exception):
    """An update refused or failed; ``code`` and ``status`` are the API's."""

    def __init__(self, code: str, status: int, detail: str, output: str | None = None) -> None:
        """Carry the wire code, HTTP status and the failing command's output."""
        super().__init__(detail)
        self.code = code
        self.status = status
        self.detail = detail
        self.output = output


def install_kind() -> InstallKind:
    """Bundle when frozen; git when bundle_root() holds a .git; else package."""
    if getattr(sys, "frozen", False):
        return "bundle"
    return "git" if (bundle_root() / ".git").exists() else "package"


# --- Checking (§4.2) -------------------------------------------------------


@dataclass(frozen=True)
class ReleaseAsset:
    """One file attached to a release."""

    name: str
    url: str
    sha256: str | None


@dataclass(frozen=True)
class ReleaseInfo:
    """The latest published release, as GitHub reports it."""

    version: str
    tag: str
    notes_markdown: str
    html_url: str
    assets: tuple[ReleaseAsset, ...]


def _asset(raw: dict[str, object]) -> ReleaseAsset:
    digest = raw.get("digest")
    ok = isinstance(digest, str) and digest.startswith("sha256:")
    sha = str(digest).removeprefix("sha256:") if ok else None
    return ReleaseAsset(name=str(raw["name"]), url=str(raw["browser_download_url"]), sha256=sha)


async def latest_release(client: httpx.AsyncClient) -> ReleaseInfo:
    """GET the latest release. Raises UpdateCheckError on any failure."""
    try:
        response = await client.get(
            LATEST_RELEASE_URL, headers={"Accept": "application/vnd.github+json"}
        )
    except httpx.HTTPError as e:
        raise UpdateCheckError(f"could not reach GitHub: {type(e).__name__}") from e
    if response.status_code != 200:
        raise UpdateCheckError(f"GitHub answered {response.status_code}")
    try:
        body = response.json()
        tag = str(body["tag_name"])
        return ReleaseInfo(
            version=tag.removeprefix("v"),
            tag=tag,
            notes_markdown=str(body.get("body") or ""),
            html_url=str(body["html_url"]),
            assets=tuple(_asset(a) for a in body.get("assets", ())),
        )
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise UpdateCheckError("GitHub's release answer did not parse") from e


def is_newer(candidate: str, current: str) -> bool:
    """Strictly greater, X.Y.Z compared numerically; a pre-release never is."""
    cand, cur = _VERSION.match(candidate), _VERSION.match(current)
    if cand is None or cur is None:
        return False
    return tuple(map(int, cand.groups())) > tuple(map(int, cur.groups()))


# --- Applying on a git clone (§4.3) ----------------------------------------


@dataclass(frozen=True)
class GitUpdateResult:
    """What apply_git_update did; the route records it."""

    previous_commit: str
    to_commit: str
    snapshot_id: str
    rolled_back: bool = False
    sync_failed: bool = False
    output: str | None = None


def _call(run: Run, argv: list[str], repo: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    """Run ``argv`` in ``repo``; a timeout comes back as a failed process."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        return run(
            argv,
            cwd=repo,
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(argv, 124, "", f"{argv[0]} timed out after {timeout}s")


def _git(run: Run, repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _call(run, ["git", *args], repo, GIT_TIMEOUT_SECONDS)


def _sync(run: Run, repo: Path) -> subprocess.CompletedProcess[str]:
    return _call(run, ["uv", "sync", "--no-dev", "--inexact"], repo, UV_TIMEOUT_SECONDS)


def is_commit_id(value: object) -> TypeGuard[str]:
    """A full 40-character hex commit id, as ``git rev-parse HEAD`` prints."""
    return isinstance(value, str) and _HEX_COMMIT.match(value) is not None


def _out(proc: subprocess.CompletedProcess[str]) -> str:
    # stderr first: it carries the reason, and the API shows the first line.
    return ((proc.stderr or "") + (proc.stdout or "")).strip()[:_OUTPUT_CAP]


def head_commit(repo: Path, run: Run = subprocess.run) -> str | None:
    """``git rev-parse HEAD``, or None where git cannot answer."""
    try:
        proc = _git(run, repo, "rev-parse", "HEAD")
    except OSError:
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def dev_status(repo: Path, run: Run = subprocess.run) -> tuple[str, int]:
    """Fetch ``main`` and return (origin/main's short id, commits HEAD lacks)."""
    try:
        fetch = _git(run, repo, "fetch", "origin", "main")
        if fetch.returncode != 0:
            raise UpdateCheckError("git fetch failed: " + _out(fetch)[-200:])
        behind = _git(run, repo, "rev-list", "--count", f"HEAD..{DEV_TARGET}")
        short = _git(run, repo, "rev-parse", "--short", DEV_TARGET)
    except OSError as e:
        raise UpdateCheckError(f"git could not run: {e}") from e
    if behind.returncode != 0 or short.returncode != 0:
        raise UpdateCheckError("git could not compare HEAD with origin/main")
    try:
        count = int(behind.stdout.strip() or 0)
    except ValueError as e:
        raise UpdateCheckError("git gave an unreadable commit count") from e
    return short.stdout.strip(), count


def _preflight(run: Run, repo: Path) -> None:
    for tool in ("git", "uv"):
        if shutil.which(tool) is None:
            raise UpdateError("update_tool_missing", 409, f"{tool} is not on PATH")
    status = _git(run, repo, "status", "--porcelain", "--untracked-files=no")
    if status.returncode != 0 or status.stdout.strip():
        raise UpdateError(
            "update_dirty_tree", 409, "the clone has uncommitted changes", _out(status) or None
        )


def apply_git_update(
    repo: Path,
    *,
    target: str,
    before_move: Callable[[], str],
    run: Run = subprocess.run,
) -> GitUpdateResult:
    """Fast-forward ``repo`` to ``target`` (a tag, or ``origin/main``)."""
    _preflight(run, repo)
    snapshot_id = before_move()
    head = _git(run, repo, "rev-parse", "HEAD")
    previous = head.stdout.strip()
    if head.returncode != 0 or not is_commit_id(previous):
        raise UpdateError("update_merge_refused", 409, "git could not read HEAD", _out(head))

    fetch = (
        _git(run, repo, "fetch", "origin", "main")
        if target == DEV_TARGET
        else _git(run, repo, "fetch", "--tags", "origin")
    )
    if fetch.returncode != 0:
        raise UpdateError("update_fetch_failed", 502, "git fetch failed", _out(fetch))
    ancestry = _git(run, repo, "merge-base", "--is-ancestor", "HEAD", "--end-of-options", target)
    if ancestry.returncode != 0:
        raise UpdateError(
            "update_not_fast_forward", 409, f"{target} is not ahead of this clone's HEAD"
        )
    merge = _git(run, repo, "merge", "--ff-only", "--end-of-options", target)
    if merge.returncode != 0:
        if _git(run, repo, "rev-parse", "HEAD").stdout.strip() == previous:
            raise UpdateError("update_merge_refused", 409, "git refused the merge", _out(merge))
        # The tree moved before the merge failed: §4.3 step 6's rollback.
        return _roll_back(run, repo, previous, snapshot_id, _out(merge))

    sync = _sync(run, repo)
    if sync.returncode != 0:
        return _roll_back(run, repo, previous, snapshot_id, _out(sync))
    to_commit = _git(run, repo, "rev-parse", "HEAD").stdout.strip()
    return GitUpdateResult(previous_commit=previous, to_commit=to_commit, snapshot_id=snapshot_id)


def _roll_back(
    run: Run, repo: Path, previous: str, snapshot_id: str, output: str
) -> GitUpdateResult:
    """§4.3 step 6: reset to ``previous`` and sync again, reporting what held."""
    if _git(run, repo, "reset", "--hard", previous).returncode != 0:
        # The code did not go back: report the tree as it is, dependencies unsynced.
        to_commit = _git(run, repo, "rev-parse", "HEAD").stdout.strip()
        return GitUpdateResult(
            previous_commit=previous,
            to_commit=to_commit,
            snapshot_id=snapshot_id,
            sync_failed=True,
            output=output,
        )
    again = _sync(run, repo)
    return GitUpdateResult(
        previous_commit=previous,
        to_commit=previous,
        snapshot_id=snapshot_id,
        rolled_back=True,
        sync_failed=again.returncode != 0,
        output=output,
    )


def rollback_git_update(repo: Path, *, previous_commit: str, run: Run = subprocess.run) -> bool:
    """Reset to ``previous_commit`` and re-sync. Returns True if the sync failed."""
    _preflight(run, repo)
    reset = _git(run, repo, "reset", "--hard", previous_commit)
    if reset.returncode != 0:
        raise UpdateError("update_merge_refused", 409, "git reset failed", _out(reset))
    return _sync(run, repo).returncode != 0


# --- Applying on a bundle (§4.4) -------------------------------------------


def bundle_target(
    version: str, *, system: str | None = None, machine: str | None = None
) -> tuple[str, Path]:
    """This platform's asset name and the folder it is written to."""
    system = system or platform.system()
    if system == "Linux":
        appimage = os.environ.get("APPIMAGE")
        folder = Path(appimage).parent if appimage else Path(sys.executable).parent
        return f"MAME_Curator-{version}-x86_64.AppImage", folder
    if system == "Windows":
        return f"MAME_Curator-{version}-x86_64.exe", Path(sys.executable).parent
    if system == "Darwin":
        return (
            f"MAME_Curator-{version}-{machine or platform.machine()}.dmg",
            Path.home() / "Downloads",
        )
    raise UpdateError("update_no_asset", 409, f"no release asset for {system}")


def _sha256_of(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


async def download_bundle(
    release: ReleaseInfo, *, name: str, folder: Path, client: httpx.AsyncClient
) -> Path:
    """Download ``name`` beside a ``.partial`` and rename it only once verified."""
    asset = next((a for a in release.assets if a.name == name), None)
    if asset is None:
        raise UpdateError("update_no_asset", 409, f"release {release.tag} has no {name}")
    if asset.sha256 is None:
        raise UpdateError("update_unverifiable", 409, f"release {release.tag} gives no digest")
    dest = folder / name
    partial = folder / f"{name}.partial"
    try:
        got = await download(url=asset.url, dest=partial, client=client)
    except DownloadError as e:
        got = ManualFallback(url=asset.url, reason=str(e))
    if isinstance(got, ManualFallback):
        with contextlib.suppress(OSError):
            partial.unlink(missing_ok=True)
        raise UpdateError("update_download_failed", 502, "the download failed", got.reason)
    if await asyncio.to_thread(_sha256_of, partial) != asset.sha256:
        partial.unlink(missing_ok=True)
        raise UpdateError("update_digest_mismatch", 502, "the download's hash did not match")
    os.replace(partial, dest)
    if name.endswith(".AppImage"):
        dest.chmod(0o755)
    return dest
