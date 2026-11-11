"""mame-curator-1225 — the picture route's cross-site and content-type guards.

CR-07-7: a GET of ``/media/*`` makes the app fetch from third parties, so a
hostile page must not trigger it. CR-03-2: a served picture carries
``X-Content-Type-Options: nosniff``. CR-03-3: the app's media client refuses
local and private addresses. Contract: ``api/spec.md`` § Cross-site guard and
§ Media proxy; ``media/spec.md`` § Cache layout.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mame_curator.api.origin_guard import OriginGuard
from mame_curator.media import refuse_private_hosts

LOCAL = {"host": "127.0.0.1:8080"}


async def _ok(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _guarded() -> TestClient:
    inner = Starlette(routes=[Route("/media/pacman/boxart", _ok), Route("/api/games", _ok)])
    return TestClient(OriginGuard(inner))


def test_cross_site_picture_request_is_refused() -> None:
    r = _guarded().get("/media/pacman/boxart", headers={**LOCAL, "sec-fetch-site": "cross-site"})
    assert r.status_code == 403
    assert r.json()["code"] == "cross_site_blocked"


@pytest.mark.parametrize("site", ["same-origin", "same-site", "none"])
def test_own_picture_request_passes(site: str) -> None:
    r = _guarded().get("/media/pacman/boxart", headers={**LOCAL, "sec-fetch-site": site})
    assert r.status_code == 200


def test_cross_site_read_elsewhere_still_passes() -> None:
    """Only /media/ fetches from third parties; other cross-site reads are unchanged."""
    r = _guarded().get("/api/games", headers={**LOCAL, "sec-fetch-site": "cross-site"})
    assert r.status_code == 200


def test_served_picture_says_nosniff(client: Any) -> None:
    url = (
        "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"
        "/Named_Boxarts/Pac-Man%20%28Midway%29.png"
    )
    with respx.mock(assert_all_called=True) as mock:
        mock.get(url).mock(return_value=httpx.Response(200, content=b"\x89PNG"))
        r = client.get("/media/pacman/boxart")
    assert r.status_code == 200, r.text
    assert r.headers["x-content-type-options"] == "nosniff"


def test_media_client_refuses_private_hosts(client: Any) -> None:
    hooks = client.app.state.media_client.event_hooks["request"]
    assert refuse_private_hosts in hooks
