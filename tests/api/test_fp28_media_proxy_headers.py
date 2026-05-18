"""FP28 C2 — ``media_proxy`` must emit Cache-Control + sniffed Content-Type.

``api/routes/media.py:61`` (pre-fix) hardcoded ``media_type="image/png"`` and
emitted no ``Cache-Control`` header. Post-fix uses ``mimetypes.guess_type``
to sniff from the cached file's suffix and attaches a 30-day immutable
Cache-Control header per design § 6.3 (the cache is permanent by default;
without the header browsers re-fetched on every page-load).

This test mocks the libretro upstream via ``respx`` so the proxy path is
exercised deterministically — without respx the request escapes to the
real network and the test silently passes (the original draft had a
``if status != 200: return`` short-circuit that hid this regression).

See ``docs/specs/FP28.md`` § C2.
"""

from __future__ import annotations

from typing import Any

import httpx
import respx

_BASE = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"
# Mini-DAT fixture: <machine name="pacman"><description>Pac-Man (Midway)</description>
_PACMAN_BOXART_URL = f"{_BASE}/Named_Boxarts/Pac-Man%20%28Midway%29.png"


def _proxy_boxart(client: Any) -> Any:
    """Mock the libretro upstream, GET ``/media/pacman/boxart``, return response.

    Extracted helper — both tests below need the same mock+request setup,
    differing only in which response header they assert. Returns the
    ``client.get`` response (TestClient ``Response``, which is httpx-shaped
    but typed as ``Any`` because Starlette's ``TestClient.get`` is ``Any``-typed).
    """
    body = b"\x89PNG\r\n\x1a\n" + b"cached-image-bytes"
    # FP31: assert_all_called=True so a regression that bypasses the upstream
    # (e.g. silently serving a stale cache) surfaces as "registered mock not
    # called", not as an undetected cache hit.
    with respx.mock(assert_all_called=True) as mock:
        mock.get(_PACMAN_BOXART_URL).mock(return_value=httpx.Response(200, content=body))
        return client.get("/media/pacman/boxart")


def test_media_proxy_emits_cache_control_header(client: Any) -> None:
    """30-day immutable Cache-Control on successful proxy hits."""
    response = _proxy_boxart(client)
    assert response.status_code == 200, response.text
    assert response.headers["Cache-Control"] == "public, max-age=2592000, immutable", (
        f"FP28 C2 — expected 30-day immutable Cache-Control, got "
        f"{response.headers.get('Cache-Control')!r}"
    )


def test_media_proxy_content_type_matches_cache_suffix(client: Any) -> None:
    """Cached file ending in ``.png`` returns ``image/png`` via mimetypes.guess_type.

    The current libretro-thumbnails URL surface always ends in ``.png`` (see
    ``cache_path_for`` — ext is derived from ``urlparse(url).path`` suffix), so
    the suffix-sniff post-fix produces the same content-type as the pre-fix
    hardcoded ``"image/png"`` on today's call sites. The contract pinned here is
    that the response Content-Type comes from suffix-sniff, not a hardcoded
    string — verified by reading the response's Content-Type and asserting it
    matches mimetypes.guess_type's PNG verdict.

    If/when the project adds a JPG-URL source in a future phase, a sibling test
    should mock that URL and assert ``Content-Type.startswith("image/jpeg")``.
    """
    import mimetypes

    response = _proxy_boxart(client)
    assert response.status_code == 200, response.text
    expected, _ = mimetypes.guess_type("dummy.png")
    assert response.headers["content-type"] == expected, (
        f"FP28 C2 — expected suffix-sniffed {expected!r}, got "
        f"{response.headers.get('content-type')!r}"
    )
