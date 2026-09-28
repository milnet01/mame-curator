"""mame-curator-1083 — app-wide cross-site request guard.

The API trusts loopback and binds 127.0.0.1, so the remaining risk is a
page in the user's own browser: a cross-site form or fetch that changes
state (CSRF), or a hostile domain re-pointed at 127.0.0.1 (DNS
rebinding). Only BROWSER requests are judged — they are the ones that
carry ``Origin`` / ``Sec-Fetch-Site`` — so the CLI, curl and the test
suite's own clients pass untouched. Contract: ``api/spec.md``
§ Cross-site guard.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mame_curator.api.origin_guard import OriginGuard


async def _ok(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _guarded(bind_host: str | None = None) -> TestClient:
    inner = Starlette(routes=[Route("/x", _ok, methods=["GET", "POST", "PUT", "PATCH", "DELETE"])])
    return TestClient(OriginGuard(inner, bind_host=bind_host))


LOCAL = {"host": "127.0.0.1:8080"}


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_cross_site_origin_blocks_every_unsafe_method(method: str) -> None:
    r = _guarded().request(method, "/x", headers={**LOCAL, "origin": "https://evil.example"})
    assert r.status_code == 403
    body = r.json()
    assert body["code"] == "cross_site_blocked"
    assert "evil.example" in body["detail"]


def test_opaque_null_origin_is_blocked() -> None:
    r = _guarded().post("/x", headers={**LOCAL, "origin": "null"})
    assert r.status_code == 403


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:8080",  # the SPA served by the app itself
        "http://localhost:5173",  # the Vite dev server, proxying to the API
        "http://[::1]:8080",
    ],
)
def test_loopback_origin_is_allowed(origin: str) -> None:
    assert _guarded().post("/x", headers={**LOCAL, "origin": origin}).status_code == 200


def test_ip_literal_same_origin_is_allowed() -> None:
    """A LAN user on http://192.168.1.5:8080 — an IP cannot be DNS-rebound."""
    lan = {"host": "192.168.1.5:8080", "origin": "http://192.168.1.5:8080"}
    assert _guarded().post("/x", headers=lan).status_code == 200


def test_foreign_ip_origin_is_blocked() -> None:
    r = _guarded().post("/x", headers={**LOCAL, "origin": "http://1.2.3.4"})
    assert r.status_code == 403


def test_configured_bind_hostname_is_trusted() -> None:
    headers = {"host": "arcade.local:8080", "origin": "http://arcade.local:8080"}
    assert _guarded("arcade.local").post("/x", headers=headers).status_code == 200
    assert _guarded().post("/x", headers=headers).status_code == 403


@pytest.mark.parametrize("site", ["cross-site", "same-site"])
def test_fetch_metadata_without_origin_blocks_foreign_sites(site: str) -> None:
    r = _guarded().post("/x", headers={**LOCAL, "sec-fetch-site": site})
    assert r.status_code == 403


@pytest.mark.parametrize("site", ["same-origin", "none"])
def test_fetch_metadata_same_origin_or_typed_url_is_allowed(site: str) -> None:
    assert _guarded().post("/x", headers={**LOCAL, "sec-fetch-site": site}).status_code == 200


def test_non_browser_request_is_untouched() -> None:
    """No Origin, no Sec-Fetch-*: the CLI, curl, scripts. Nothing to judge."""
    assert _guarded().post("/x", headers={"host": "anything.example"}).status_code == 200


def test_rebound_hostname_is_blocked_even_on_reads() -> None:
    """evil.example re-pointed at 127.0.0.1: same-origin to the browser."""
    r = _guarded().get("/x", headers={"host": "evil.example:8080", "sec-fetch-site": "same-origin"})
    assert r.status_code == 403
    assert r.json()["code"] == "cross_site_blocked"


def test_cross_site_read_is_left_to_the_browser() -> None:
    """A cross-site GET changes nothing, and without CORS headers the page
    cannot read the response, so the guard does not refuse it."""
    r = _guarded().get("/x", headers={**LOCAL, "origin": "https://evil.example"})
    assert r.status_code == 200


def test_create_app_installs_the_guard(client: Any) -> None:
    """Refused before routing: an unknown path answers 403, not 404."""
    r = client.post("/api/no-such-route", headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    assert r.json()["code"] == "cross_site_blocked"


def test_create_app_guard_passes_the_spa(client: Any) -> None:
    r = client.post("/api/no-such-route", headers={**LOCAL, "origin": "http://127.0.0.1:8080"})
    assert r.status_code != 403
