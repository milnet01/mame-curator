"""Wikipedia REST summary image source (P10 chunk 5) — boxart only.

Split out of ``sources.py`` so that file stays under the 500-line hard cap
(coding-standards § 2), as ``mobygames.py`` and ``local_folders.py`` are
(mame-curator-1255). Which title is the game's page lives in
``wikipedia_titles.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import quote

import httpx

from mame_curator.media.cache import MediaFetchError, cache_path_for
from mame_curator.media.cache_text import fetch_text_with_cache
from mame_curator.media.rate_limit import MediaRateLimited, TokenBucket
from mame_curator.media.sources import Kind
from mame_curator.media.wikipedia_titles import (
    _WIKIPEDIA_REST_SUMMARY_BASE,
    candidate_titles,
    is_game_page,
)
from mame_curator.parser.models import Machine

# P10 chunk 5 — Wikipedia REST summary endpoint. One-step lookup; the only
# image field with a documented location is ``thumbnail.source`` (the
# infobox image). Title / snap aren't reliably present and would require
# HTML scraping — explicitly out of scope per spec § "3. Wikipedia (image)".
# Which title is the game's page: media/wikipedia_titles.py (mame-curator-1140).


class WikipediaImageSource:
    """Wikipedia REST summary — boxart only, title canonicalised.

    ``prepare`` acquires from the per-source ``TokenBucket``, canonicalises
    ``machine.description`` (drops trailing parenthesised qualifier),
    URL-quotes the result, fetches the REST summary, parses
    ``thumbnail.source``, and stashes it. ``url_for(m, "boxart")`` returns
    the cached URL. ``title`` / ``snap`` always return ``None`` — the
    REST summary has no analogous field for those, and silently degrading
    to the infobox image would let the wrong-shaped image win over a
    legit downstream candidate.

    ``license_compatible = False``: Wikipedia hosts mixed-license images;
    P10 only displays the image, never redistributes. P11's contribute-back
    flow would need per-image inspection if it ever consumed this source.
    """

    name: ClassVar[str] = "wikipediaImage"
    license_compatible: ClassVar[bool] = False
    kinds: ClassVar[frozenset[Kind]] = frozenset({"boxart"})

    def __init__(self, *, limiter: TokenBucket, cache_dir: Path) -> None:
        """Bind to ``limiter`` + ``cache_dir``. Never self-disables."""
        self._limiter = limiter
        self._cache_dir = cache_dir
        self._url_cache: dict[str, str] = {}
        self.disabled_reason: str | None = None

    @staticmethod
    def _summary_url(title: str) -> str:
        return f"{_WIKIPEDIA_REST_SUMMARY_BASE}/{quote(title)}"

    async def prepare(
        self,
        machine: Machine,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        """Populate ``_url_cache[name]`` from the game's page's thumbnail.

        Raises ``MediaRateLimited`` on empty bucket; ``MediaFetchError`` on
        JSON parse failure (cache slot unlinked first). No game page, or no
        thumbnail, leaves the cache entry absent — ``url_for`` returns ``None``.
        """
        if not self._limiter.acquire():
            raise MediaRateLimited(f"wikipediaImage rate-limit exceeded for {machine.name!r}")
        # mame-curator-1140: the first title whose page is the game's.
        for title in candidate_titles(machine):
            data = await self._summary(title, machine, client)
            if data is not None and is_game_page(data):
                break
        else:
            return
        # Nested parse-before-trust (FP33 H2): a truthy-but-non-dict thumbnail
        # would make ``.get("source")`` raise before the isinstance(thumb, str)
        # guard runs. Guard the container type first.
        thumbnail = data.get("thumbnail")
        thumb = thumbnail.get("source") if isinstance(thumbnail, dict) else None
        if isinstance(thumb, str) and thumb:
            self._url_cache[machine.name] = thumb

    async def _summary(
        self, title: str, machine: Machine, client: httpx.AsyncClient
    ) -> dict[str, Any] | None:
        """One title's REST summary, or ``None`` on a 404."""
        url = self._summary_url(title)
        text = await fetch_text_with_cache(url, self._cache_dir, client=client)
        if text is None:
            return None
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, RecursionError) as exc:
            cache_path_for(url, self._cache_dir).unlink(missing_ok=True)
            raise MediaFetchError(
                f"wikipediaImage returned unparseable JSON for {machine.name!r}"
            ) from exc
        if not isinstance(data, dict):
            # Valid-but-non-object JSON — parse-before-trust, same as the
            # unparseable branch above (else `data.get("thumbnail")` throws).
            cache_path_for(url, self._cache_dir).unlink(missing_ok=True)
            raise MediaFetchError(f"wikipediaImage returned non-object JSON for {machine.name!r}")
        return data

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the cached thumbnail URL or ``None``.

        Returns ``None`` for ``kind != "boxart"`` (this source's vocabulary
        is boxart-only — see ``kinds`` ClassVar).
        """
        if kind != "boxart":
            return None
        return self._url_cache.get(machine.name)
