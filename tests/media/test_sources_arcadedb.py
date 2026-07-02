"""Tests for ``ArcadeDBSource`` (P10 chunk 4).

Per ``docs/specs/P10.md`` § "2. ArcadeDB". Two-step lookup: ``prepare``
acquires from the per-source ``TokenBucket``, calls ``fetch_text_with_cache``
against the scraper endpoint, parses ``{"release": N, "result": [...]}``
(parse-before-trust — invalid JSON unlinks the cache slot and raises
``MediaFetchError``), and stashes the first-result URL triple in an instance
``_url_cache`` keyed by ``machine.name``. ``url_for`` reads from that cache.
Split from the original ``test_sources.py`` (FP31 / mame-curator-1046).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.media.conftest import _machine, _make_unbounded_limiter

_ARCADEDB_SCRAPER_URL = (
    "http://adb.arcadeitalia.net/service_scraper.php?ajax=query_mame&game_name=pacman"
)


def _arcadedb_fixture_text() -> str:
    """Return the captured pre-impl-prep ArcadeDB fixture as JSON text."""
    return (Path(__file__).resolve().parents[1] / "fixtures" / "arcadedb_pacman.json").read_text(
        encoding="utf-8"
    )


def test_arcadedb_source_classvars() -> None:
    """ClassVars pin identity / coverage / license."""
    from mame_curator.media import ArcadeDBSource

    assert ArcadeDBSource.name == "arcadeDB"
    assert ArcadeDBSource.license_compatible is True
    assert ArcadeDBSource.kinds == frozenset({"boxart", "title", "snap"})


def test_arcadedb_source_url_for_returns_none_before_prepare(tmp_path: Path) -> None:
    """``url_for`` returns ``None`` when ``prepare`` has never populated
    the per-machine entry — pins the empty-cache shape."""
    from mame_curator.media import ArcadeDBSource

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    assert src.url_for(_machine(), "boxart") is None
    assert src.url_for(_machine(), "title") is None
    assert src.url_for(_machine(), "snap") is None


@pytest.mark.asyncio
async def test_arcadedb_source_prepare_populates_url_cache(tmp_path: Path) -> None:
    """Happy path: scraper returns a non-empty ``result``; ``prepare``
    stashes the three URLs; ``url_for`` returns the redirector-form URL
    per ArcadeDB's documented field shape."""
    import httpx
    import respx

    from mame_curator.media import ArcadeDBSource

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    body = _arcadedb_fixture_text()
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_ARCADEDB_SCRAPER_URL).mock(return_value=httpx.Response(200, text=body))
            await src.prepare(_machine(), client=client)

    boxart = src.url_for(_machine(), "boxart")
    title = src.url_for(_machine(), "title")
    snap = src.url_for(_machine(), "snap")
    assert boxart is not None and "type=flyer" in boxart
    assert title is not None and "type=title" in title
    assert snap is not None and "type=ingame" in snap


@pytest.mark.asyncio
async def test_arcadedb_source_prepare_empty_release_caches_no_match(tmp_path: Path) -> None:
    """An empty ``result`` array → uniform negative-cache shape:
    ``_url_cache[machine.name]`` stays absent, ``url_for`` returns ``None``."""
    import httpx
    import respx

    from mame_curator.media import ArcadeDBSource

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    body = '{"release":0,"result":[]}'
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_ARCADEDB_SCRAPER_URL).mock(return_value=httpx.Response(200, text=body))
            await src.prepare(_machine(), client=client)

    assert src.url_for(_machine(), "boxart") is None
    assert src.url_for(_machine(), "title") is None
    assert src.url_for(_machine(), "snap") is None


@pytest.mark.asyncio
async def test_arcadedb_source_prepare_rate_limit_raises(tmp_path: Path) -> None:
    """Empty bucket → ``MediaRateLimited`` before any upstream I/O.
    No respx mock — any actual HTTP would 502 against the unmocked client,
    so passing the test proves we short-circuited."""
    import httpx

    from mame_curator.media import ArcadeDBSource, MediaRateLimited, TokenBucket

    # rate is required positive; drain the only token by acquire() once
    # before prepare runs.
    bucket = TokenBucket(rate=1.0, capacity=1)
    assert bucket.acquire() is True  # drain
    src = ArcadeDBSource(limiter=bucket, cache_dir=tmp_path)

    async with httpx.AsyncClient() as client:
        with pytest.raises(MediaRateLimited):
            await src.prepare(_machine(), client=client)


@pytest.mark.asyncio
async def test_arcadedb_source_prepare_unparseable_body_unlinks_cache(tmp_path: Path) -> None:
    """Parse-before-trust: invalid JSON → cache slot unlinked + ``MediaFetchError``
    chained from ``JSONDecodeError``. Next call re-fetches; transient bad
    upstream doesn't permanently disable the source for this machine."""
    import httpx
    import respx

    from mame_curator.media import (
        ArcadeDBSource,
        MediaFetchError,
        cache_path_for,
    )

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    cache_file = cache_path_for(_ARCADEDB_SCRAPER_URL, tmp_path)

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_ARCADEDB_SCRAPER_URL).mock(
                return_value=httpx.Response(200, text="<html>oops, html not json</html>")
            )
            with pytest.raises(MediaFetchError) as exc_info:
                await src.prepare(_machine(), client=client)

    import json

    assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)
    assert not cache_file.exists(), "bad cache slot should be unlinked"


@pytest.mark.asyncio
async def test_arcadedb_source_prepare_non_object_json_unlinks_cache(tmp_path: Path) -> None:
    """FP32 H1: a valid-but-non-object JSON body (``[]`` / ``null`` / a bare
    string) must not let ``data.get("result")`` raise an uncaught
    ``AttributeError`` past the fallback chain. Parse-before-trust treats it
    like unparseable: unlink the poisoned slot + raise ``MediaFetchError``
    (which ``resolve_image`` swallows → falls through to the next source)."""
    import httpx
    import respx

    from mame_curator.media import ArcadeDBSource, MediaFetchError, cache_path_for

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    cache_file = cache_path_for(_ARCADEDB_SCRAPER_URL, tmp_path)

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_ARCADEDB_SCRAPER_URL).mock(return_value=httpx.Response(200, text="[]"))
            with pytest.raises(MediaFetchError):
                await src.prepare(_machine(), client=client)

    assert not cache_file.exists(), "non-object JSON slot should be unlinked"


@pytest.mark.asyncio
async def test_arcadedb_source_prepare_survives_nested_shape_drift(tmp_path: Path) -> None:
    """FP33 H2: nested upstream shape drift must not crash ``prepare`` (which
    would escape to the route as a 500). A ``result`` list whose first element
    is not an object, and non-string URL fields, are treated as no-match —
    ``url_for`` returns ``None`` and the chain advances."""
    import httpx
    import respx

    from mame_curator.media import ArcadeDBSource

    # result[0] is an int, not an object → pre-fix `first.get(...)` AttributeError.
    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_ARCADEDB_SCRAPER_URL).mock(
                return_value=httpx.Response(200, text='{"release":1,"result":[1]}')
            )
            await src.prepare(_machine(), client=client)  # must not raise
    assert src.url_for(_machine(), "boxart") is None


@pytest.mark.asyncio
async def test_arcadedb_source_prepare_ignores_non_string_url_fields(tmp_path: Path) -> None:
    """FP33 H2: a non-string ``url_image_flyer`` (upstream drift / injection)
    must NOT be cached — otherwise ``url_for`` returns a non-str and
    ``resolve_image``'s ``url.startswith('file://')`` crashes (and a str-shaped
    ``file://`` value would feed the H1 LFI)."""
    import httpx
    import respx

    from mame_curator.media import ArcadeDBSource

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    body = '{"release":1,"result":[{"url_image_flyer":123,"url_image_title":null}]}'
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_ARCADEDB_SCRAPER_URL).mock(return_value=httpx.Response(200, text=body))
            await src.prepare(_machine(), client=client)  # must not raise
    assert src.url_for(_machine(), "boxart") is None
    assert src.url_for(_machine(), "title") is None


def test_arcadedb_source_satisfies_media_source_protocol(tmp_path: Path) -> None:
    """Runtime-checkable Protocol — attribute presence."""
    from mame_curator.media import ArcadeDBSource, MediaSource

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    assert isinstance(src, MediaSource)
