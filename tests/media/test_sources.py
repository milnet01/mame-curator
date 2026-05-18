"""Tests for the MediaSource Protocol + concrete source implementations.

Per ``docs/specs/P10.md`` § "Public API" and § "Source contracts".
Chunk 2 lands only ``LibretroSource``; later chunks add ProgettoSnaps,
ArcadeDB, Wikipedia, MobyGames. The Protocol-compliance check pins
the registry-time ``isinstance`` shape every future source must
satisfy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mame_curator.parser.models import Machine


def _machine(name: str = "pacman", description: str = "Pac-Man") -> Machine:
    return Machine(name=name, description=description)


def test_libretro_source_url_for_three_kinds() -> None:
    """``LibretroSource.url_for`` returns the same three URLs as P05's
    ``urls_for(machine)`` exposed via ``boxart`` / ``title`` / ``snap``
    attributes — the P05 baseline carried forward under the new
    Protocol shape."""
    from mame_curator.media import LibretroSource, urls_for

    src = LibretroSource()
    m = _machine()
    expected = urls_for(m)

    assert src.url_for(m, "boxart") == expected.boxart
    assert src.url_for(m, "title") == expected.title
    assert src.url_for(m, "snap") == expected.snap


def test_libretro_source_disabled_reason_is_none_by_default() -> None:
    """``LibretroSource`` is never disabled — it has no config to be missing.
    Pins the readiness-surface contract for sources that never gate."""
    from mame_curator.media import LibretroSource

    src = LibretroSource()
    assert src.disabled_reason is None


def test_libretro_source_satisfies_media_source_protocol() -> None:
    """``isinstance(x, MediaSource)`` succeeds — the @runtime_checkable
    attribute-presence check. Future sources must satisfy the same."""
    from mame_curator.media import LibretroSource, MediaSource

    src = LibretroSource()
    assert isinstance(src, MediaSource)


def test_libretro_source_classvars() -> None:
    """The three ClassVars pin the source's identity / coverage / license."""
    from mame_curator.media import LibretroSource

    assert LibretroSource.name == "libretro"
    assert LibretroSource.license_compatible is True
    assert LibretroSource.kinds == frozenset({"boxart", "title", "snap"})


@pytest.mark.asyncio
async def test_libretro_source_prepare_is_noop() -> None:
    """LibretroSource has no per-machine lookup — ``prepare`` is a no-op.
    Pins the single-shot-source contract carried by the Protocol."""
    import httpx

    from mame_curator.media import LibretroSource

    src = LibretroSource()
    async with httpx.AsyncClient() as client:
        # `prepare` returns None by contract; awaiting it must not raise
        # and must not hit any upstream — verified by the lack of a respx
        # mock in this test (any HTTP request would 502 against an
        # unmocked client). The implicit `result is None` is what
        # `-> None` already guarantees; we only need the await to succeed.
        await src.prepare(_machine(), client=client)


# --- ProgettoSnapsSource (P10 chunk 3b) --------------------------------------
#
# Per ``docs/specs/P10.md`` § "1. progettoSnaps — local pack model".
# The source covers `snap` kind only (upstream removed flyers/titles —
# see 2026-05-18 spec amendment). url_for returns a file:// URL when the
# corresponding ``<name>.png`` exists under ``snap_dir``; sets
# ``disabled_reason`` at construction if the directory is missing or empty.


def test_progettosnaps_source_name_is_camelcase() -> None:
    """``ProgettoSnapsSource.name == "progettoSnaps"`` (config-key casing)."""
    from mame_curator.media import ProgettoSnapsSource

    assert ProgettoSnapsSource.name == "progettoSnaps"


def test_progettosnaps_source_only_covers_snap() -> None:
    """``kinds = frozenset({"snap"})`` — boxart/title fall through to next source."""
    from mame_curator.media import ProgettoSnapsSource

    assert ProgettoSnapsSource.kinds == frozenset({"snap"})


def test_progettosnaps_source_returns_file_url_when_pack_present(
    tmp_path: Path,
) -> None:
    """Pack present + machine PNG on disk → ``file://`` URL pointing at it."""
    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    (snap_dir / "pacman.png").write_bytes(b"\x89PNG\r\n\x1a\nfake")

    src = ProgettoSnapsSource(snap_dir=snap_dir)
    url = src.url_for(_machine(), "snap")

    assert url is not None
    assert url.startswith("file://")
    assert url.endswith("/pacman.png")
    # The path inside the file:// URL must be the resolved absolute
    # path (not relative) so the orchestrator's `Path(urlparse(url).path)`
    # works regardless of CWD.
    assert snap_dir.resolve().as_posix() in url


def test_progettosnaps_source_returns_none_when_file_missing(
    tmp_path: Path,
) -> None:
    """Pack present (dir non-empty) but ``<name>.png`` not in it → ``None``."""
    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    # One unrelated file so the directory is non-empty (disabled_reason
    # stays None); pacman.png is deliberately absent.
    (snap_dir / "galaga.png").write_bytes(b"gal")

    src = ProgettoSnapsSource(snap_dir=snap_dir)
    assert src.url_for(_machine(name="pacman"), "snap") is None
    assert src.disabled_reason is None


def test_progettosnaps_source_returns_none_for_non_snap_kinds(
    tmp_path: Path,
) -> None:
    """``url_for(m, "boxart")`` and ``url_for(m, "title")`` return ``None``."""
    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    (snap_dir / "pacman.png").write_bytes(b"pac")

    src = ProgettoSnapsSource(snap_dir=snap_dir)
    assert src.url_for(_machine(), "boxart") is None
    assert src.url_for(_machine(), "title") is None


def test_progettosnaps_source_sets_disabled_reason_when_dir_empty(
    tmp_path: Path,
) -> None:
    """Pack dir exists but contains no files → ``disabled_reason`` populated."""
    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()  # empty

    src = ProgettoSnapsSource(snap_dir=snap_dir)
    assert src.disabled_reason is not None
    assert "refresh-snaps" in src.disabled_reason


def test_progettosnaps_source_sets_disabled_reason_when_dir_absent(
    tmp_path: Path,
) -> None:
    """Pack dir doesn't exist at all → ``disabled_reason`` populated."""
    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    # snap_dir intentionally not created.

    src = ProgettoSnapsSource(snap_dir=snap_dir)
    assert src.disabled_reason is not None
    assert "refresh-snaps" in src.disabled_reason


def test_progettosnaps_source_caches_existence_per_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two ``url_for(m, "snap")`` calls → at most one ``Path.is_file`` against
    the per-machine file. The existence cache lives on the instance so a
    fresh per-request source starts cold but never re-stats within its
    lifetime."""
    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    pacman = snap_dir / "pacman.png"
    pacman.write_bytes(b"pac")

    real_is_file = Path.is_file
    seen: list[str] = []

    def counting_is_file(self: Path) -> bool:
        if self == pacman:
            seen.append(str(self))
        return real_is_file(self)

    monkeypatch.setattr(Path, "is_file", counting_is_file)

    src = ProgettoSnapsSource(snap_dir=snap_dir)
    # Discard the construction-time directory scan baseline (it walks the
    # directory, not the per-machine file, so it doesn't push into `seen`).
    seen.clear()

    m = _machine(name="pacman")
    src.url_for(m, "snap")
    src.url_for(m, "snap")

    assert len(seen) == 1, f"per-machine existence check should be cached; got {seen}"


def test_progettosnaps_source_satisfies_media_source_protocol(
    tmp_path: Path,
) -> None:
    """Runtime-checkable Protocol — attribute presence verified."""
    from mame_curator.media import MediaSource, ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    (snap_dir / "pacman.png").write_bytes(b"pac")
    src = ProgettoSnapsSource(snap_dir=snap_dir)

    assert isinstance(src, MediaSource)


@pytest.mark.asyncio
async def test_progettosnaps_source_prepare_is_noop(
    tmp_path: Path,
) -> None:
    """ProgettoSnapsSource never hits the network — ``prepare`` returns None."""
    import httpx

    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    src = ProgettoSnapsSource(snap_dir=snap_dir)

    async with httpx.AsyncClient() as client:
        await src.prepare(_machine(), client=client)
