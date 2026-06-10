"""Tests for ``WikipediaImageSource`` (P10 chunk 5) + the shared user-agent.

Per ``docs/specs/P10.md`` § "3. Wikipedia (image)". One-step lookup against
the REST summary endpoint; ``thumbnail.source`` is the only image field.
``boxart`` kind only; ``machine.description`` passes through
``re.sub(r"\\s*\\([^)]*\\)\\s*$", "", desc).strip()`` before being URL-quoted
into the endpoint path. License is per-image (mixed) so
``license_compatible = False`` conservatively. Split from the original
``test_sources.py`` (FP31 / mame-curator-1046).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.media.conftest import _machine, _make_unbounded_limiter


def _wikipedia_url_for(title: str) -> str:
    from urllib.parse import quote

    return f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"


def _wikipedia_fixture_text() -> str:
    return (Path(__file__).resolve().parents[1] / "fixtures" / "wikipedia_pacman.json").read_text(
        encoding="utf-8"
    )


def test_wikipedia_image_source_classvars() -> None:
    """ClassVars: name=wikipediaImage, license_compatible=False, kinds={boxart}."""
    from mame_curator.media import WikipediaImageSource

    assert WikipediaImageSource.name == "wikipediaImage"
    assert WikipediaImageSource.license_compatible is False
    assert WikipediaImageSource.kinds == frozenset({"boxart"})


async def test_wikipedia_image_source_only_covers_boxart(tmp_path: Path) -> None:
    """Even after ``prepare`` populates the per-machine cache, ``url_for(m,
    "title")`` and ``..."snap"`` return ``None`` — the source vocabulary
    excludes them; only ``boxart`` reads from the cache."""
    import httpx
    import respx

    from mame_curator.media import WikipediaImageSource

    src = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    body = _wikipedia_fixture_text()
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_wikipedia_url_for("Pac-Man")).mock(
                return_value=httpx.Response(200, text=body)
            )
            await src.prepare(_machine(description="Pac-Man"), client=client)

    assert src.url_for(_machine(), "title") is None
    assert src.url_for(_machine(), "snap") is None
    boxart = src.url_for(_machine(), "boxart")
    assert boxart is not None and "Pac_flyer.png" in boxart


def test_wikipedia_image_source_url_for_returns_none_before_prepare(tmp_path: Path) -> None:
    """Empty per-machine cache → ``url_for(m, "boxart")`` returns ``None``."""
    from mame_curator.media import WikipediaImageSource

    src = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    assert src.url_for(_machine(), "boxart") is None


@pytest.mark.asyncio
async def test_wikipedia_image_source_canonicalises_parens(tmp_path: Path) -> None:
    """``description="Pac-Man (Midway)"`` hits the endpoint for ``Pac-Man``,
    not the unqualified form. Pinned against the spec's canonicalisation
    rule (``re.sub(r"\\s*\\([^)]*\\)\\s*$", "", desc).strip()``)."""
    import httpx
    import respx

    from mame_curator.media import WikipediaImageSource

    src = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    body = _wikipedia_fixture_text()
    quoted_url = _wikipedia_url_for("Pac-Man")
    parens_url = _wikipedia_url_for("Pac-Man (Midway)")

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=False) as mock:
            canonical_route = mock.get(quoted_url).mock(return_value=httpx.Response(200, text=body))
            uncanon_route = mock.get(parens_url).mock(
                return_value=httpx.Response(404, text="never hit")
            )
            await src.prepare(_machine(description="Pac-Man (Midway)"), client=client)

    assert canonical_route.called, "canonicalised title should be the requested URL"
    assert not uncanon_route.called, "raw description must not hit the REST endpoint"


@pytest.mark.asyncio
async def test_wikipedia_image_source_prepare_populates_thumbnail_url(tmp_path: Path) -> None:
    """Happy path: REST summary returns ``thumbnail.source``; ``url_for``
    returns that URL for ``boxart``."""
    import httpx
    import respx

    from mame_curator.media import WikipediaImageSource

    src = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    body = _wikipedia_fixture_text()

    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(_wikipedia_url_for("Pac-Man")).mock(
                return_value=httpx.Response(200, text=body)
            )
            await src.prepare(_machine(description="Pac-Man"), client=client)

    url = src.url_for(_machine(), "boxart")
    assert url is not None
    assert "Pac_flyer.png" in url


@pytest.mark.asyncio
async def test_wikipedia_image_source_prepare_rate_limit_raises(tmp_path: Path) -> None:
    """Empty bucket → ``MediaRateLimited`` before any upstream I/O."""
    import httpx

    from mame_curator.media import MediaRateLimited, TokenBucket, WikipediaImageSource

    bucket = TokenBucket(rate=1.0, capacity=1)
    assert bucket.acquire() is True
    src = WikipediaImageSource(limiter=bucket, cache_dir=tmp_path)

    async with httpx.AsyncClient() as client:
        with pytest.raises(MediaRateLimited):
            await src.prepare(_machine(), client=client)


def test_wikipedia_image_source_satisfies_media_source_protocol(tmp_path: Path) -> None:
    """Runtime-checkable Protocol — attribute presence."""
    from mame_curator.media import MediaSource, WikipediaImageSource

    src = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    assert isinstance(src, MediaSource)


def test_build_user_agent_contains_version_and_repo() -> None:
    """``_build_user_agent`` returns the descriptive UA Wikipedia's API
    etiquette page requests: package + version + repo link."""
    from mame_curator import __version__
    from mame_curator.media import _build_user_agent

    ua = _build_user_agent()
    assert "mame-curator" in ua
    assert __version__ in ua
    assert "github.com" in ua
