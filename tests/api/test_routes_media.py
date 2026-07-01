"""R39 shape + integration tests for the media proxy.

Per ``docs/specs/P04.md`` § Media proxy and ``docs/specs/P05.md`` § R39 wiring.
P04 ships a minimal pass-through proxy; P05 swaps in the real URL builder +
cache and short-circuits ``kind=video``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import respx

from mame_curator.media import TokenBucket

_BASE = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"
# Mini-DAT fixture: <machine name="pacman"><description>Pac-Man (Midway)</description>
_PACMAN_BOXART_URL = f"{_BASE}/Named_Boxarts/Pac-Man%20%28Midway%29.png"
_REDIRECT_TARGET = f"{_BASE}/Named_Boxarts/Pac-Man-relocated.png"
# P10 chunk 8 — Wikipedia extract endpoint. Description "Pac-Man (Midway)"
# canonicalises to "Pac-Man" before the REST summary lookup.
_WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/Pac-Man"


def _wiki_fixture_text() -> str:
    return (Path(__file__).resolve().parents[1] / "fixtures" / "wikipedia_pacman.json").read_text(
        encoding="utf-8"
    )


def test_route_r39_shape_media_unknown_kind(client: Any) -> None:
    """R39 — unknown {kind} returns 400 with code media_kind_invalid."""
    response = client.get("/media/pacman/unknown_kind")
    assert response.status_code == 400
    assert response.json()["code"] == "media_kind_invalid"


def test_route_r39_shape_media_unknown_game(client: Any) -> None:
    """R39 — unknown {name} returns 404 with code game_not_found
    (distinct from upstream 404)."""
    response = client.get("/media/no_such_machine/boxart")
    assert response.status_code == 404
    assert response.json()["code"] == "game_not_found"


def test_proxy_route_uses_cache(client: Any) -> None:
    """First request hits upstream; second request hits disk (no upstream call).
    Both return identical bytes.
    """
    body = b"\x89PNG\r\n\x1a\n" + b"cached-image-bytes"
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(_PACMAN_BOXART_URL).mock(return_value=httpx.Response(200, content=body))
        first = client.get("/media/pacman/boxart")
        second = client.get("/media/pacman/boxart")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.content == body
    assert second.content == body
    assert route.call_count == 1, "second request should not hit upstream"


def test_proxy_route_video_returns_404_without_upstream_call(client: Any) -> None:
    """``kind=video`` short-circuits with media_upstream_not_found before any
    upstream call (MediaUrls has no ``video`` field; design §6.3 defers video
    to progettoSnaps via P06+).
    """
    with respx.mock(assert_all_called=False) as mock:
        # No specific URL — any GitHub call would be picked up by this route.
        route = mock.get(host="raw.githubusercontent.com")
        response = client.get("/media/pacman/video")

    assert response.status_code == 404
    assert response.json()["code"] == "media_upstream_not_found"
    assert not route.called, "video must short-circuit before any upstream call"


def test_proxy_route_propagates_upstream_404(client: Any) -> None:
    """Upstream 404 → media_upstream_not_found (route catches None from fetch_with_cache)."""
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_PACMAN_BOXART_URL).mock(return_value=httpx.Response(404))
        response = client.get("/media/pacman/boxart")

    assert response.status_code == 404
    assert response.json()["code"] == "media_upstream_not_found"


def test_proxy_route_500_falls_through_to_404(client: Any) -> None:
    """P10 chunk 7: an upstream 500 no longer surfaces as 502.

    ``resolve_image`` swallows the source's ``MediaFetchError`` and advances
    the chain; with the (libretro-only, per conftest) chain exhausted it
    returns ``None`` → the route raises 404 ``media_upstream_not_found``. The
    502 ``media_upstream_error`` surface is retired for media (spec §
    "Route contract — chunk 7 retires the 502 error surface").
    """
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_PACMAN_BOXART_URL).mock(return_value=httpx.Response(500))
        response = client.get("/media/pacman/boxart")

    assert response.status_code == 404
    assert response.json()["code"] == "media_upstream_not_found"


def test_proxy_route_follows_redirect(client: Any) -> None:
    """FP10 A1: 301 from upstream must transit (httpx ``follow_redirects=True``).

    Without that flag, httpx returns the 301 to the route, which surfaces as
    ``MediaFetchError("upstream 301 ...")`` → 502 to the client. After the
    fix, httpx follows the redirect transparently and the proxied 200 lands.
    """
    body = b"\x89PNG\r\n\x1a\n" + b"after-redirect"
    with respx.mock() as mock:
        route1 = mock.get(_PACMAN_BOXART_URL).mock(
            return_value=httpx.Response(301, headers={"Location": _REDIRECT_TARGET})
        )
        route2 = mock.get(_REDIRECT_TARGET).mock(return_value=httpx.Response(200, content=body))
        response = client.get("/media/pacman/boxart")

    assert response.status_code == 200
    assert response.content == body
    assert route1.called
    assert route2.called, "redirect target must be fetched (follow_redirects=True)"


def test_proxy_route_404_detail_leaks_no_internal_class(client: Any) -> None:
    """The fall-through 404 detail stays user-facing — no typed-exception class
    name and no keyed/internal URL leaks into the wire body.

    (P10 chunk 7 replaces the FP10-A3 502 detail contract: a source's
    ``MediaFetchError`` is swallowed by ``resolve_image``, so the only
    media error surface is the 404 the route synthesises.)
    """
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_PACMAN_BOXART_URL).mock(return_value=httpx.Response(500))
        response = client.get("/media/pacman/boxart")

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert "MediaFetchError" not in detail, "class name should not leak to user"
    assert "boxart" in detail, "detail should name the requested kind"


def test_proxy_route_transport_error_falls_through_to_404(client: Any) -> None:
    """mame-curator-1053 — a transport-level failure (connection refused, DNS
    failure, timeout) raises ``httpx.TransportError`` *before any response
    arrives*. ``cache.py`` catches it via ``except httpx.HTTPError``
    (``TransportError`` is an ``HTTPError`` subclass) and wraps it as
    ``MediaFetchError``. P10 chunk 7: ``resolve_image`` swallows that and
    advances the chain, so a transport failure on the last source yields
    ``None`` → 404 (no longer 502). This is the only test that drives the
    transport-error branch through the orchestrator.
    """
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_PACMAN_BOXART_URL).mock(side_effect=httpx.ConnectError("connection refused"))
        response = client.get("/media/pacman/boxart")

    assert response.status_code == 404
    assert response.json()["code"] == "media_upstream_not_found"


# --- P10 chunk 8: GET /media/{name}/wiki (Wikipedia extract) -----------------


def test_media_wiki_returns_extract_json(client: Any) -> None:
    """Wikipedia 200 → the route returns the parsed extract JSON.

    ``/media/pacman/wiki`` must match the literal wiki route, NOT bind
    ``kind="wiki"`` on the image proxy (which would 400).
    """
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_WIKI_SUMMARY_URL).mock(
            return_value=httpx.Response(200, text=_wiki_fixture_text())
        )
        response = client.get("/media/pacman/wiki")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Pac-Man"
    assert body["extract"]
    assert body["url"] == "https://en.wikipedia.org/wiki/Pac-Man"
    assert body["license"] == "CC-BY-SA-4.0"


def test_media_wiki_returns_null_on_404(client: Any) -> None:
    """Wikipedia 404 (no page) → route returns JSON ``null`` with HTTP 200."""
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_WIKI_SUMMARY_URL).mock(return_value=httpx.Response(404))
        response = client.get("/media/pacman/wiki")

    assert response.status_code == 200
    assert response.json() is None


def test_media_wiki_returns_null_when_rate_limited(client: Any) -> None:
    """An exhausted ``wikipedia_limiter`` → route catches ``MediaRateLimited``
    (a ``MediaError``) and returns JSON ``null``, HTTP 200 — a non-essential
    About paragraph never 500s. No upstream call is attempted."""
    drained = TokenBucket(rate=1.0, capacity=1)
    assert drained.acquire() is True  # empty the bucket
    client.app.state.wikipedia_limiter = drained
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(host="en.wikipedia.org")
        response = client.get("/media/pacman/wiki")

    assert response.status_code == 200
    assert response.json() is None
    assert not route.called, "rate-limit must short-circuit before any upstream call"


def test_media_wiki_video_kind_remains_unsupported(client: Any) -> None:
    """Adding the wiki route must not break the P05 video short-circuit:
    ``GET /media/{name}/video`` still returns ``media_upstream_not_found``."""
    with respx.mock(assert_all_called=False) as mock:
        route = mock.get(host="raw.githubusercontent.com")
        response = client.get("/media/pacman/video")

    assert response.status_code == 404
    assert response.json()["code"] == "media_upstream_not_found"
    assert not route.called
