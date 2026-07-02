"""P10 chunk 8 — Wikipedia extract (flavor text) endpoint backend.

``WikipediaExtract`` is the frozen wire model for the one-paragraph "About"
text the Alternatives drawer shows. ``resolve_wikipedia_extract`` fetches the
same Wikipedia REST summary the chunk-5 image source uses (shared cache slot
+ shared rate-limit bucket — same URL, same SHA-256 key), parses the
extract / title / canonical URL, and returns the model — or ``None`` on a
genuine upstream 404 or a summary that lacks the fields we need.

Per ``docs/specs/P10.md`` § "async resolve_wikipedia_extract" +
§ "Wikipedia flavor-text surface". The route (``GET /media/{name}/wiki``)
catches ``MediaError`` and degrades to ``null`` — the About paragraph is
non-essential, so a rate-limit / network / parse failure never 500s.
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict

from mame_curator.media.cache import MediaFetchError, cache_path_for
from mame_curator.media.cache_text import fetch_text_with_cache
from mame_curator.media.rate_limit import MediaRateLimited, TokenBucket
from mame_curator.media.sources import (
    _WIKIPEDIA_REST_SUMMARY_BASE,
    _canonicalise_wikipedia_title,
)
from mame_curator.parser.models import Machine


class WikipediaExtract(BaseModel):
    """Frozen wire model for the Wikipedia "About" paragraph.

    ``license`` is a client-side constant (the REST summary response carries
    no license field — verified against ``tests/fixtures/wikipedia_pacman.json``);
    a plain ``str`` (not ``Literal``) so a future CC-BY-SA bump isn't a
    schema-breaking change.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    title: str
    extract: str
    url: str
    license: str = "CC-BY-SA-4.0"


async def resolve_wikipedia_extract(
    machine: Machine,
    *,
    cache_dir: Path,
    client: httpx.AsyncClient,
    limiter: TokenBucket,
) -> WikipediaExtract | None:
    """Fetch + parse the Wikipedia REST summary into a ``WikipediaExtract``.

    Acquires one token first (empty bucket → ``MediaRateLimited`` *before* any
    upstream hit), canonicalises ``machine.description`` (drops a trailing
    parenthesised qualifier), and fetches the REST summary via
    ``fetch_text_with_cache`` — the same URL, and therefore the same cache
    slot, the chunk-5 ``WikipediaImageSource`` uses. A genuine upstream 404
    (or an empty canonical title, or a summary missing the fields we map)
    returns ``None``. Malformed JSON raises ``MediaFetchError`` after
    invalidating the poisoned cache slot (parse-before-trust, matching the
    ArcadeDB / Wikipedia-image sources).
    """
    if not limiter.acquire():
        raise MediaRateLimited(f"wikipediaExtract rate-limit exceeded for {machine.name!r}")
    title = _canonicalise_wikipedia_title(machine.description)
    if not title:
        return None
    url = f"{_WIKIPEDIA_REST_SUMMARY_BASE}/{quote(title)}"
    text = await fetch_text_with_cache(url, cache_dir, client=client)
    if text is None:
        return None  # upstream 404 — no wiki page
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        cache_path_for(url, cache_dir).unlink(missing_ok=True)
        raise MediaFetchError(
            f"wikipediaExtract returned unparseable JSON for {machine.name!r}"
        ) from exc
    if not isinstance(data, dict):
        # Valid-but-non-object JSON (`[]` / `null` / a bare string) would make
        # `data.get("extract")` raise AttributeError → route 500. The About
        # paragraph is non-essential, so degrade to None (unlinking the
        # poisoned slot so the next request re-fetches).
        cache_path_for(url, cache_dir).unlink(missing_ok=True)
        return None
    extract = data.get("extract")
    page_title = data.get("title")
    page_url = (data.get("content_urls") or {}).get("desktop", {}).get("page")
    if not (
        isinstance(extract, str)
        and extract
        and isinstance(page_title, str)
        and page_title
        and isinstance(page_url, str)
        and page_url
    ):
        return None  # summary present but missing a field we surface
    return WikipediaExtract(title=page_title, extract=extract, url=page_url)
