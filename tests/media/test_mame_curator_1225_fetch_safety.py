"""mame-curator-1225 — safety of the picture and text fetches.

Each test locks one finding from the 2026-11-11 code review (ids in the
docstrings). Contract: ``src/mame_curator/media/spec.md`` § Cache layout,
§ ``fetch_with_cache`` and § Edge cases handled.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
import pytest
import respx

from mame_curator.media import (
    ArcadeDBSource,
    MediaFetchError,
    MobyGamesSource,
    ProgettoSnapsSource,
    SourceDisabledFlag,
    WikipediaImageSource,
    cache_path_for,
    fetch_with_cache,
    refuse_private_hosts,
    resolve_wikipedia_extract,
)
from tests.media.conftest import _machine, _make_unbounded_limiter

_DEEP_JSON = "[" * 100_000 + "]" * 100_000


# ---- CR-03-2: the cache file's suffix ---------------------------------------


@pytest.mark.parametrize("suffix", [".html", ".svg", ".php", ".a:b", ".htm"])
def test_cache_path_drops_a_non_picture_suffix(tmp_path: Path, suffix: str) -> None:
    """CR-03-2: an upstream URL ending .html must not be stored as .html."""
    path = cache_path_for(f"https://example.com/x{suffix}", tmp_path)
    assert path.suffix == ""


@pytest.mark.parametrize("suffix", [".png", ".jpg", ".jpeg", ".gif", ".webp", ".PNG"])
def test_cache_path_keeps_a_picture_suffix(tmp_path: Path, suffix: str) -> None:
    path = cache_path_for(f"https://example.com/x{suffix}", tmp_path)
    assert path.suffix == suffix


# ---- CR-03-13: a 200 that is not a picture ----------------------------------


async def test_fetch_refuses_a_page_that_is_not_a_picture(tmp_path: Path) -> None:
    """CR-03-13: a soft-404 HTML page must not be cached for good."""
    url = "https://example.com/art/pacman.png"
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(url).mock(
                return_value=httpx.Response(
                    200, content=b"<html>not found</html>", headers={"content-type": "text/html"}
                )
            )
            with pytest.raises(MediaFetchError):
                await fetch_with_cache(url, tmp_path, client=client)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("content_type", ["image/png", "application/octet-stream"])
async def test_fetch_accepts_a_picture(tmp_path: Path, content_type: str) -> None:
    url = "https://example.com/art/pacman.png"
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(url).mock(
                return_value=httpx.Response(
                    200, content=b"\x89PNG", headers={"content-type": content_type}
                )
            )
            path = await fetch_with_cache(url, tmp_path, client=client)
    assert path is not None and path.read_bytes() == b"\x89PNG"


# ---- CR-03-3: where a picture may be fetched from ---------------------------


def _guarded_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(follow_redirects=True, event_hooks={"request": [refuse_private_hosts]})


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/a.png",
        "http://localhost:8080/a.png",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5/a.png",
        "http://192.168.1.2/a.png",
        "http://[::1]/a.png",
        "http://0.0.0.0/a.png",
    ],
)
async def test_fetch_refuses_a_local_or_private_address(tmp_path: Path, url: str) -> None:
    """CR-03-3: an upstream-supplied URL must not reach the user's own machine or LAN."""
    async with _guarded_client() as client:
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(url).mock(return_value=httpx.Response(200, content=b"secret"))
            with pytest.raises(MediaFetchError):
                await fetch_with_cache(url, tmp_path, client=client)
            assert not route.called


async def test_fetch_refuses_a_redirect_to_a_private_address(tmp_path: Path) -> None:
    """CR-03-3: the check runs on every hop, not only the first address."""
    start = "https://example.com/a.png"
    inner = "http://127.0.0.1:8080/api/config"
    async with _guarded_client() as client:
        with respx.mock(assert_all_called=False) as mock:
            mock.get(start).mock(return_value=httpx.Response(302, headers={"location": inner}))
            route = mock.get(inner).mock(return_value=httpx.Response(200, content=b"secret"))
            with pytest.raises(MediaFetchError):
                await fetch_with_cache(start, tmp_path, client=client)
            assert not route.called


async def test_fetch_allows_a_public_address(tmp_path: Path) -> None:
    url = "https://upload.wikimedia.org/a.png"
    async with _guarded_client() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(url).mock(return_value=httpx.Response(200, content=b"\x89PNG"))
            assert await fetch_with_cache(url, tmp_path, client=client) is not None


def test_arcadedb_lookup_uses_https(tmp_path: Path) -> None:
    """CR-03-3: the first ArcadeDB request must not go out over plain http."""
    url = ArcadeDBSource._scraper_url(_machine())
    assert url.startswith("https://adb.arcadeitalia.net/")


# ---- CR-03-8: deeply nested JSON --------------------------------------------


async def test_arcadedb_deeply_nested_reply_is_a_bad_reply(tmp_path: Path) -> None:
    """CR-03-8: RecursionError must not escape the source chain as a 500."""
    src = ArcadeDBSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host="adb.arcadeitalia.net").mock(
                return_value=httpx.Response(200, text=_DEEP_JSON)
            )
            with pytest.raises(MediaFetchError):
                await src.prepare(_machine(), client=client)


async def test_wikipedia_image_deeply_nested_reply_is_a_bad_reply(tmp_path: Path) -> None:
    src = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host="en.wikipedia.org").mock(
                return_value=httpx.Response(200, text=_DEEP_JSON)
            )
            with pytest.raises(MediaFetchError):
                await src.prepare(_machine(), client=client)


async def test_wikipedia_extract_deeply_nested_reply_is_a_bad_reply(tmp_path: Path) -> None:
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host="en.wikipedia.org").mock(
                return_value=httpx.Response(200, text=_DEEP_JSON)
            )
            with pytest.raises(MediaFetchError):
                await resolve_wikipedia_extract(
                    _machine(), cache_dir=tmp_path, client=client, limiter=_make_unbounded_limiter()
                )


def _mobygames(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> MobyGamesSource:
    monkeypatch.setenv("MOBYGAMES_API_KEY", "secret-key-123")
    return MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "none",
    )


async def test_mobygames_deeply_nested_reply_is_a_bad_reply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = _mobygames(tmp_path, monkeypatch)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host="api.mobygames.com").mock(
                return_value=httpx.Response(200, text=_DEEP_JSON)
            )
            with pytest.raises(MediaFetchError):
                await src.prepare(_machine(), client=client)


# ---- CR-03-7: MobyGames replies are size-capped ------------------------------


async def test_mobygames_reply_over_the_text_cap_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CR-03-7: a valid but oversized reply must not be read whole."""
    src = _mobygames(tmp_path, monkeypatch)
    big = {"games": [], "pad": "x" * (300 * 1024)}
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host="api.mobygames.com").mock(return_value=httpx.Response(200, json=big))
            with pytest.raises(MediaFetchError, match="BodyTooLarge"):
                await src.prepare(_machine(), client=client)


# ---- CR-03-9: the snap pack path --------------------------------------------


def test_snap_source_refuses_a_name_that_leaves_the_pack(tmp_path: Path) -> None:
    """CR-03-9: a DAT short name with ``..`` must not read a .png outside the pack."""
    snap_dir = tmp_path / "snap"
    snap_dir.mkdir()
    (snap_dir / "pacman.png").write_bytes(b"\x89PNG")
    (tmp_path / "outside.png").write_bytes(b"\x89PNG")
    src = ProgettoSnapsSource(snap_dir=snap_dir)
    assert src.url_for(_machine(name="../outside"), "snap") is None
    assert src.url_for(_machine(name="pacman"), "snap") is not None


# ---- CR-03-1: the MobyGames key never reaches the log ------------------------


def test_main_keeps_request_urls_out_of_the_log(monkeypatch: pytest.MonkeyPatch) -> None:
    """CR-03-1: httpx logs each full URL at INFO, and the MobyGames key rides in it."""
    import mame_curator.main as main_mod

    httpx_logger = logging.getLogger("httpx")
    saved = httpx_logger.level
    monkeypatch.setattr(main_mod, "run", lambda args: 0)
    monkeypatch.setattr("sys.argv", ["mame-curator", "--verbose", "parse", "x.xml"])
    try:
        main_mod.main()
        # The logger's own level, not its effective one: under pytest the
        # root logger's level is pytest's, so isEnabledFor() proves nothing.
        assert httpx_logger.level >= logging.WARNING
    finally:
        httpx_logger.setLevel(saved)
