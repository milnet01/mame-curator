"""Tests for ``resolve_wikipedia_extract`` + ``WikipediaExtract`` (P10 chunk 8).

Per ``docs/specs/P10.md`` § "async resolve_wikipedia_extract" +
§ "WikipediaExtract". The extract hits the same REST summary endpoint (and
therefore the same ``fetch_text_with_cache`` slot + rate-limit bucket) as the
chunk-5 ``WikipediaImageSource``; it parses ``extract`` / ``title`` /
``content_urls.desktop.page`` and sets ``license`` as a client-side constant.
A genuine upstream 404 → ``None``. Field mapping is verified against
``tests/fixtures/wikipedia_pacman.json``.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
import respx
from pydantic import ValidationError

from mame_curator.media import (
    MediaRateLimited,
    TokenBucket,
    WikipediaExtract,
    resolve_wikipedia_extract,
)
from mame_curator.media.cache import cache_path_for
from tests.media.conftest import _machine, _make_unbounded_limiter

_SUMMARY_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"


def _summary_url(title: str) -> str:
    return f"{_SUMMARY_BASE}/{quote(title)}"


def _fixture_text() -> str:
    return (Path(__file__).resolve().parents[1] / "fixtures" / "wikipedia_pacman.json").read_text(
        encoding="utf-8"
    )


async def test_wikipedia_extract_returns_frozen_model(tmp_path: Path) -> None:
    """Mocked 200 → a frozen ``WikipediaExtract``; extract non-empty, license
    is the client-side ``CC-BY-SA-4.0`` constant (absent from the response)."""
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_summary_url("Pac-Man")).mock(
                return_value=httpx.Response(200, text=_fixture_text())
            )
            result = await resolve_wikipedia_extract(
                _machine(description="Pac-Man"),
                cache_dir=tmp_path,
                client=client,
                limiter=_make_unbounded_limiter(),
            )
    assert isinstance(result, WikipediaExtract)
    assert result.title == "Pac-Man"
    assert result.extract  # non-empty
    assert result.url == "https://en.wikipedia.org/wiki/Pac-Man"
    assert result.license == "CC-BY-SA-4.0"
    with pytest.raises(ValidationError):  # frozen model rejects mutation
        result.title = "mutated"


async def test_wikipedia_extract_returns_none_on_404(tmp_path: Path) -> None:
    """Upstream 404 → ``None``; no JSON cache file left behind."""
    url = _summary_url("Pac-Man")
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(url).mock(return_value=httpx.Response(404))
            result = await resolve_wikipedia_extract(
                _machine(description="Pac-Man"),
                cache_dir=tmp_path,
                client=client,
                limiter=_make_unbounded_limiter(),
            )
    assert result is None
    assert not cache_path_for(url, tmp_path).exists()


async def test_wikipedia_extract_caches_text_response_and_reparses(tmp_path: Path) -> None:
    """First call writes the raw JSON body under ``cache_dir``; the second
    call short-circuits at the cache layer (no upstream hit) and re-parses the
    cached text into a fresh, equal ``WikipediaExtract``."""
    url = _summary_url("Pac-Man")
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            route = mock.get(url).mock(return_value=httpx.Response(200, text=_fixture_text()))
            first = await resolve_wikipedia_extract(
                _machine(description="Pac-Man"),
                cache_dir=tmp_path,
                client=client,
                limiter=_make_unbounded_limiter(),
            )
            assert cache_path_for(url, tmp_path).exists()
            second = await resolve_wikipedia_extract(
                _machine(description="Pac-Man"),
                cache_dir=tmp_path,
                client=client,
                limiter=_make_unbounded_limiter(),
            )
    assert route.call_count == 1, "second call must hit the disk cache, not upstream"
    assert first == second
    assert isinstance(second, WikipediaExtract)


async def test_wikipedia_extract_uses_description_as_title(tmp_path: Path) -> None:
    """``Machine(description="Pac-Man")`` → the summary URL uses that title."""
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            route = mock.get(_summary_url("Pac-Man")).mock(
                return_value=httpx.Response(200, text=_fixture_text())
            )
            await resolve_wikipedia_extract(
                _machine(description="Pac-Man"),
                cache_dir=tmp_path,
                client=client,
                limiter=_make_unbounded_limiter(),
            )
    assert route.called


async def test_wikipedia_extract_canonicalises_parenthesised_qualifier(tmp_path: Path) -> None:
    """``"Pac-Man (Midway)"`` → the trailing parenthesised qualifier is stripped
    before the title is quoted into the summary URL."""
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            route = mock.get(_summary_url("Pac-Man")).mock(
                return_value=httpx.Response(200, text=_fixture_text())
            )
            await resolve_wikipedia_extract(
                _machine(description="Pac-Man (Midway)"),
                cache_dir=tmp_path,
                client=client,
                limiter=_make_unbounded_limiter(),
            )
    assert route.called, "canonicalised title must drop the '(Midway)' qualifier"


async def test_wikipedia_extract_unparseable_json_unlinks_cache_and_raises(tmp_path: Path) -> None:
    """A 200 with a non-JSON body → ``MediaFetchError`` after the poisoned
    cache slot is unlinked (parse-before-trust, matching the sibling sources)."""
    from mame_curator.media import MediaFetchError

    url = _summary_url("Pac-Man")
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(url).mock(return_value=httpx.Response(200, text="<html>not json"))
            with pytest.raises(MediaFetchError):
                await resolve_wikipedia_extract(
                    _machine(description="Pac-Man"),
                    cache_dir=tmp_path,
                    client=client,
                    limiter=_make_unbounded_limiter(),
                )
    assert not cache_path_for(url, tmp_path).exists(), "poisoned slot must be unlinked"


async def test_wikipedia_extract_returns_none_when_summary_missing_fields(tmp_path: Path) -> None:
    """A valid-JSON summary lacking the fields we surface (no ``extract``) →
    ``None`` (defensive — don't build a half-empty model)."""
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_summary_url("Pac-Man")).mock(
                return_value=httpx.Response(200, text='{"title": "Pac-Man"}')
            )
            result = await resolve_wikipedia_extract(
                _machine(description="Pac-Man"),
                cache_dir=tmp_path,
                client=client,
                limiter=_make_unbounded_limiter(),
            )
    assert result is None


async def test_wikipedia_extract_respects_rate_limit(tmp_path: Path) -> None:
    """An exhausted bucket → ``MediaRateLimited`` before any upstream hit."""
    bucket = TokenBucket(rate=1.0, capacity=1)
    assert bucket.acquire() is True  # drain the only token
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(host="en.wikipedia.org")
            with pytest.raises(MediaRateLimited):
                await resolve_wikipedia_extract(
                    _machine(description="Pac-Man"),
                    cache_dir=tmp_path,
                    client=client,
                    limiter=bucket,
                )
    assert not route.called, "rate-limit must short-circuit before any upstream call"
