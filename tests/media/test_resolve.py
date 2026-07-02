"""P10 chunk 7 — ``resolve_image`` orchestrator + ``build_registry`` factory.

Per ``docs/specs/P10.md`` § "async resolve_image" + § chunk-7 notes. The
orchestrator walks the registry chain, awaiting each source's ``prepare`` then
reading ``url_for``, and returns the first cached image ``Path``. A per-source
``MediaRateLimited`` / ``MediaFetchError`` is swallowed and the chain advances;
a ``file://`` candidate (local snap pack) is served directly without touching
``fetch_with_cache``. All sources missing → ``None`` (route → 404).

``fetch_with_cache`` is monkeypatched (per-URL result) so the tests drive the
fall-through logic without real HTTP.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import httpx
import pytest

from mame_curator.media import (
    Kind,
    MediaSource,
    MediaSourceRegistry,
    SourceDisabledFlag,
    TokenBucket,
    build_registry,
    resolve_image,
)
from mame_curator.media import resolve as resolve_mod
from mame_curator.media.cache import MediaFetchError
from mame_curator.media.rate_limit import MediaRateLimited
from mame_curator.parser.models import Machine
from tests.media.conftest import _machine


class _StubSource:
    """A ``MediaSource`` whose ``url_for`` + ``prepare`` behaviour is scripted."""

    def __init__(
        self,
        name: str,
        *,
        url: str | None = "http://example.test/img.png",
        kinds: frozenset[Kind] = frozenset({"boxart"}),
        prepare_exc: Exception | None = None,
    ) -> None:
        self.name = name
        self.license_compatible = True
        self.kinds = kinds
        self.disabled_reason: str | None = None
        self._url = url
        self._prepare_exc = prepare_exc
        self.prepared = False

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        self.prepared = True
        if self._prepare_exc is not None:
            raise self._prepare_exc

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        return self._url


def _registry(*sources: _StubSource) -> MediaSourceRegistry:
    """Build a registry over the given stubs, preserving order (no baseline).

    The stubs are structural ``MediaSource`` s at runtime; the ``cast`` bridges
    the instance-var-vs-ClassVar gap mypy flags (isinstance accepts them).
    """
    names = tuple(s.name for s in sources)
    available = cast("dict[str, MediaSource]", {s.name: s for s in sources})
    return MediaSourceRegistry(names, available)


def _patch_fetch(monkeypatch: pytest.MonkeyPatch, results: dict[str, object]) -> None:
    """Monkeypatch ``resolve.fetch_with_cache`` to map url → Path / None / raise.

    A value that is an ``Exception`` instance is raised; otherwise it's returned
    (``Path`` on hit, ``None`` on upstream 404).
    """

    async def _fake(url: str, cache_dir: Path, *, client: httpx.AsyncClient) -> Path | None:
        outcome = results[url]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome  # type: ignore[return-value]

    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _fake)


@pytest.mark.asyncio
async def test_resolve_first_source_wins(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """First source with a hit returns immediately; later sources untouched."""
    hit = tmp_path / "a.png"
    hit.write_bytes(b"x")
    first = _StubSource("first", url="http://one.test/a.png")
    second = _StubSource("second", url="http://two.test/b.png")
    _patch_fetch(monkeypatch, {"http://one.test/a.png": hit})
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "boxart",
            registry=_registry(first, second),
            cache_dir=tmp_path,
            client=client,
        )
    assert result == hit
    assert first.prepared and not second.prepared


@pytest.mark.asyncio
async def test_resolve_404_fallthrough(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """First source's upstream 404 (fetch → None) advances to the next source."""
    hit = tmp_path / "b.png"
    hit.write_bytes(b"x")
    first = _StubSource("first", url="http://one.test/a.png")
    second = _StubSource("second", url="http://two.test/b.png")
    _patch_fetch(monkeypatch, {"http://one.test/a.png": None, "http://two.test/b.png": hit})
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "boxart",
            registry=_registry(first, second),
            cache_dir=tmp_path,
            client=client,
        )
    assert result == hit
    assert first.prepared and second.prepared


@pytest.mark.asyncio
async def test_resolve_500_fallthrough(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A source's fetch-time ``MediaFetchError`` is swallowed; chain advances."""
    hit = tmp_path / "b.png"
    hit.write_bytes(b"x")
    first = _StubSource("first", url="http://one.test/a.png")
    second = _StubSource("second", url="http://two.test/b.png")
    _patch_fetch(
        monkeypatch,
        {"http://one.test/a.png": MediaFetchError("upstream 500"), "http://two.test/b.png": hit},
    )
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "boxart",
            registry=_registry(first, second),
            cache_dir=tmp_path,
            client=client,
        )
    assert result == hit


@pytest.mark.asyncio
async def test_resolve_rate_limit_fallthrough(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A source's ``prepare`` ``MediaRateLimited`` is swallowed; chain advances."""
    hit = tmp_path / "b.png"
    hit.write_bytes(b"x")
    first = _StubSource("first", url="http://one.test/a.png", prepare_exc=MediaRateLimited("busy"))
    second = _StubSource("second", url="http://two.test/b.png")
    _patch_fetch(monkeypatch, {"http://two.test/b.png": hit})
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "boxart",
            registry=_registry(first, second),
            cache_dir=tmp_path,
            client=client,
        )
    assert result == hit
    assert first.prepared and second.prepared


@pytest.mark.asyncio
async def test_resolve_all_404_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Every source 404s → ``resolve_image`` returns ``None`` (route → 404)."""
    first = _StubSource("first", url="http://one.test/a.png")
    second = _StubSource("second", url="http://two.test/b.png")
    _patch_fetch(monkeypatch, {"http://one.test/a.png": None, "http://two.test/b.png": None})
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "boxart",
            registry=_registry(first, second),
            cache_dir=tmp_path,
            client=client,
        )
    assert result is None


@pytest.mark.asyncio
async def test_resolve_returns_first_hit_without_consulting_rest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """After the first hit the orchestrator returns early — a later source with
    no candidate (``url_for`` → None) is never reached, proving short-circuit."""
    hit = tmp_path / "b.png"
    hit.write_bytes(b"x")
    miss = _StubSource("miss", url="http://one.test/a.png")
    win = _StubSource("win", url="http://two.test/b.png")
    never = _StubSource("never", url=None)
    _patch_fetch(monkeypatch, {"http://one.test/a.png": None, "http://two.test/b.png": hit})
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "boxart",
            registry=_registry(miss, win, never),
            cache_dir=tmp_path,
            client=client,
        )
    assert result == hit
    assert not never.prepared


@pytest.mark.asyncio
async def test_resolve_file_scheme_short_circuits_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A ``file://`` candidate is served directly, never touching fetch_with_cache."""
    snap = tmp_path / "pacman.png"
    snap.write_bytes(b"\x89PNG")
    local = _StubSource("progettoSnaps", url=snap.as_uri(), kinds=frozenset({"snap"}))

    async def _boom(*a: object, **k: object) -> Path | None:
        raise AssertionError("fetch_with_cache must not be called for file:// URLs")

    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _boom)
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "snap",
            registry=_registry(local),
            cache_dir=tmp_path,
            client=client,
        )
    assert result == snap


@pytest.mark.asyncio
async def test_resolve_file_scheme_ignores_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """FP32 LOW: the ``file://`` short-circuit must gate on ``.is_file()``, not
    ``.exists()`` — a candidate path that is a *directory* (named ``x.png``)
    must fall through, never be returned as an image path."""
    snap_dir = tmp_path / "pacman.png"
    snap_dir.mkdir()  # a directory, not a file
    local = _StubSource("progettoSnaps", url=snap_dir.as_uri(), kinds=frozenset({"snap"}))

    async def _boom(*a: object, **k: object) -> Path | None:
        raise AssertionError("fetch_with_cache must not be called for file:// URLs")

    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _boom)
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "snap",
            registry=_registry(local),
            cache_dir=tmp_path,
            client=client,
        )
    assert result is None, "a directory candidate must not be served as an image"


@pytest.mark.asyncio
async def test_resolve_file_scheme_rejected_from_non_local_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """FP33 H1 (LFI): the file:// short-circuit must fire ONLY for the local
    snap-pack source (name 'progettoSnaps'). A NETWORK source returning a
    file:// URL — e.g. a MITM on ArcadeDB's plaintext hop injecting
    file:///etc/passwd — must be dropped, never served; otherwise it's an
    arbitrary local-file read that bypasses fetch_with_cache's scheme guard."""
    secret = tmp_path / "secret.png"
    secret.write_bytes(b"\x89PNG-sensitive-bytes")
    hostile = _StubSource("arcadeDB", url=secret.as_uri(), kinds=frozenset({"boxart"}))

    async def _boom(*a: object, **k: object) -> Path | None:
        raise AssertionError("fetch_with_cache must not be called for file:// URLs")

    monkeypatch.setattr(resolve_mod, "fetch_with_cache", _boom)
    async with httpx.AsyncClient() as client:
        result = await resolve_image(
            _machine(),
            "boxart",
            registry=_registry(hostile),
            cache_dir=tmp_path,
            client=client,
        )
    assert result is None, "a non-local source's file:// URL must not be served"


def _limiter() -> TokenBucket:
    return TokenBucket(rate=10.0, capacity=10)


def test_build_registry_constructs_configured_plus_baseline(tmp_path: Path) -> None:
    """``build_registry`` builds the named sources + the libretro baseline."""
    reg = build_registry(
        configured=("arcadeDB",),
        cache_dir=tmp_path,
        arcadedb_limiter=_limiter(),
        wikipedia_limiter=_limiter(),
        mobygames_limiter=_limiter(),
        mobygames_disabled=SourceDisabledFlag(),
        snap_dir=tmp_path / "snaps",
    )
    # arcadeDB covers boxart; libretro auto-appended.
    assert [s.name for s in reg.chain_for("boxart")] == ["arcadeDB", "libretro"]


def test_build_registry_omits_unconfigured_mobygames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Dropping mobyGames from the config skips its construction (no keyless
    WARNING) and keeps it out of the chain."""
    monkeypatch.delenv("MOBYGAMES_API_KEY", raising=False)
    import logging

    with caplog.at_level(logging.WARNING):
        reg = build_registry(
            configured=("libretro",),
            cache_dir=tmp_path,
            arcadedb_limiter=_limiter(),
            wikipedia_limiter=_limiter(),
            mobygames_limiter=_limiter(),
            mobygames_disabled=SourceDisabledFlag(),
            snap_dir=tmp_path / "snaps",
        )
    assert [s.name for s in reg.chain_for("boxart")] == ["libretro"]
    assert not any("MobyGames" in r.message for r in caplog.records)
