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

from mame_curator.media import TokenBucket
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
    """ProgettoSnapsSource never hits the network — ``prepare`` returns None and
    attempts no HTTP. The catch-all respx route proves the latter: a swallowed
    network call would still flip ``catch_all.called``."""
    import httpx
    import respx

    from mame_curator.media import ProgettoSnapsSource

    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    src = ProgettoSnapsSource(snap_dir=snap_dir)

    with respx.mock(assert_all_called=False) as mock:
        catch_all = mock.route().mock(return_value=httpx.Response(500))
        async with httpx.AsyncClient() as client:
            await src.prepare(_machine(), client=client)
    assert not catch_all.called, "prepare must not attempt any HTTP"


# --- ArcadeDBSource (P10 chunk 4) -----------------------------------------
#
# Per ``docs/specs/P10.md`` § "2. ArcadeDB". Two-step lookup: ``prepare``
# acquires from the per-source ``TokenBucket``, calls
# ``fetch_text_with_cache`` against the scraper endpoint, parses
# ``{"release": N, "result": [...]}`` (parse-before-trust — invalid JSON
# unlinks the cache slot and raises ``MediaFetchError``), and stashes
# the first-result URL triple in an instance ``_url_cache`` keyed by
# ``machine.name``. ``url_for`` reads from that cache.

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


def _make_unbounded_limiter() -> TokenBucket:
    """Return a TokenBucket with capacity high enough for one prepare call."""
    return TokenBucket(rate=10.0, capacity=10)


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


def test_arcadedb_source_satisfies_media_source_protocol(tmp_path: Path) -> None:
    """Runtime-checkable Protocol — attribute presence."""
    from mame_curator.media import ArcadeDBSource, MediaSource

    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    assert isinstance(src, MediaSource)


# --- WikipediaImageSource (P10 chunk 5) -----------------------------------
#
# Per ``docs/specs/P10.md`` § "3. Wikipedia (image)". One-step lookup
# against the REST summary endpoint; ``thumbnail.source`` is the only
# image field. ``boxart`` kind only; ``machine.description`` passes
# through ``re.sub(r"\s*\([^)]*\)\s*$", "", desc).strip()`` before being
# URL-quoted into the endpoint path. License is per-image (mixed) so
# ``license_compatible = False`` conservatively.


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


def test_wikipedia_image_source_only_covers_boxart(tmp_path: Path) -> None:
    """``url_for(m, "title")`` and ``..."snap"`` always return ``None``."""
    from mame_curator.media import WikipediaImageSource

    src = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    # Even after a populated cache (sidestep prepare by writing directly),
    # title/snap return None — the source vocabulary excludes them.
    src._url_cache["pacman"] = "https://example.com/x.png"
    assert src.url_for(_machine(), "title") is None
    assert src.url_for(_machine(), "snap") is None
    assert src.url_for(_machine(), "boxart") == "https://example.com/x.png"


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
    assert url.endswith("Pac_flyer.png") or "Pac_flyer.png" in url


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
