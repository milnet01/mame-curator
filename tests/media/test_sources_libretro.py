"""Tests for ``LibretroSource`` + the MediaSource Protocol-compliance shape.

Per ``docs/specs/P10.md`` § "Public API" and § "Source contracts". The
Protocol-compliance check pins the registry-time ``isinstance`` shape every
future source must satisfy. Split from the original ``test_sources.py``
(FP31 / mame-curator-1046).
"""

from __future__ import annotations

import pytest

from tests.media.conftest import _machine


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
    """LibretroSource has no per-machine lookup — ``prepare`` is a no-op that
    attempts no HTTP. A catch-all respx route (returns 500 instead of raising)
    records any request ``prepare`` might fire; asserting it was never called
    catches a regression that issues — and silently swallows — a network call,
    which the prior unmocked-client form passed vacuously."""
    import httpx
    import respx

    from mame_curator.media import LibretroSource

    src = LibretroSource()
    with respx.mock(assert_all_called=False) as mock:
        catch_all = mock.route().mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            await src.prepare(_machine(), client=client)
    assert not catch_all.called, "prepare must not attempt any HTTP"
