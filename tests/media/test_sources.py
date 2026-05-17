"""Tests for the MediaSource Protocol + concrete source implementations.

Per ``docs/specs/P10.md`` § "Public API" and § "Source contracts".
Chunk 2 lands only ``LibretroSource``; later chunks add ProgettoSnaps,
ArcadeDB, Wikipedia, MobyGames. The Protocol-compliance check pins
the registry-time ``isinstance`` shape every future source must
satisfy.
"""

from __future__ import annotations

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
