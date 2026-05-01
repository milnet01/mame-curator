"""R39 shape + integration tests for the media proxy.

Per ``docs/specs/P04.md`` § Media proxy and ``docs/specs/P05.md`` § R39 wiring.
P04 ships a minimal pass-through proxy; P05 swaps in the real URL builder +
cache and short-circuits ``kind=video``.
"""

from __future__ import annotations

from typing import Any

import httpx
import respx

_BASE = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"
# Mini-DAT fixture: <machine name="pacman"><description>Pac-Man (Midway)</description>
_PACMAN_BOXART_URL = f"{_BASE}/Named_Boxarts/Pac-Man%20%28Midway%29.png"


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


def test_proxy_route_propagates_upstream_500(client: Any) -> None:
    """Upstream 500 → media_upstream_error (route catches MediaFetchError)."""
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_PACMAN_BOXART_URL).mock(return_value=httpx.Response(500))
        response = client.get("/media/pacman/boxart")

    assert response.status_code == 502
    assert response.json()["code"] == "media_upstream_error"
