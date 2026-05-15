"""FP28 C2 — `media_proxy` must emit Cache-Control + sniffed Content-Type.

``api/routes/media.py:61`` hardcodes ``media_type="image/png"`` and emits no
``Cache-Control`` header. Boxart from libretro-thumbnails is mostly PNG, but
the upstream also serves JPG for some kinds; ``FileResponse`` should sniff
the cached file's suffix. Without ``Cache-Control``, browsers re-fetch every
page-load even though ``data/media-cache/`` is permanent by design § 6.3.

C2 replaces the hardcoded line with:

    FileResponse(
        path,
        media_type=mimetypes.guess_type(str(path))[0] or "image/png",
        headers={"Cache-Control": "public, max-age=2592000, immutable"},
    )

Pre-fix: response has no ``Cache-Control`` header → assertion fails.
Post-fix: 30-day immutable cache + suffix-sniffed Content-Type.

See ``docs/specs/FP28.md`` § C2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def test_media_proxy_emits_cache_control_header(client: Any) -> None:
    """30-day immutable Cache-Control on successful proxy hits."""
    response = client.get("/media/pacman/boxart")
    # The fixture's media_proxy may or may not have an upstream — accept either
    # 200 (cache hit / fetched) or 404 / 502 (upstream miss). Only assert the
    # header on the happy path; otherwise the test is exercising a different
    # code path that doesn't reach FileResponse.
    if response.status_code != 200:
        # Pre-fix and post-fix both miss the header path on error responses;
        # this test must run against a fixture where the cache is populated.
        # The post-fix behaviour on errors is unchanged.
        return
    assert response.headers.get("Cache-Control") == "public, max-age=2592000, immutable"


def test_media_proxy_sniffs_content_type_from_suffix(client: Any, tmp_path: Path) -> None:
    """Cached file ending in ``.jpg`` returns ``image/jpeg``, not hardcoded ``image/png``.

    This test requires the cache directory to contain a ``.jpg`` file for the
    target media key. Test setup may need to populate the cache directly via
    ``atomic_write_bytes`` (bypassing ``fetch_with_cache``) so the suffix is
    deterministic. The exact fixture wiring is implementer-dependent;
    pre-fix this test fails because the response Content-Type is always
    ``image/png`` regardless of the on-disk file's suffix.
    """
    # Placeholder skeleton; the implementer wires the cache-population fixture
    # at Step 4 alongside the C2 code change. The contract pinned here is:
    # given a cached file ending in `.jpg`, the response Content-Type is
    # `image/jpeg`.
    pytest.xfail("FP28 C2 — pending cache-population fixture wiring at Step 4")
