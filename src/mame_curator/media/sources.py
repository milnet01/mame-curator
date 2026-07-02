"""Media-source protocol + concrete implementations for the P10 fallback chain.

Per ``docs/specs/P10.md`` § "Public API" + § "Source contracts". Chunk 2
lands the protocol, the ``Kind`` literal, and ``LibretroSource`` (the
P05 baseline carried under the new shape). Chunk 3b adds
``ProgettoSnapsSource`` (file:// model, snap kind only — upstream no
longer publishes flyers / titles; see 2026-05-18 spec amendment).
Chunk 4 adds ``ArcadeDBSource`` (two-step JSON lookup with
parse-before-trust). Chunk 5 adds ``WikipediaImageSource`` (REST
summary endpoint, boxart only, title canonicalisation).

Every concrete source implements two methods:

- ``async prepare(machine, *, client)`` — populate any per-machine lookup
  state the source needs (two-step sources hit JSON endpoints here).
  Single-shot sources implement it as a one-line ``return``. The
  Protocol's ``...`` body is a typing stub, not an inheritable default.
- ``def url_for(machine, kind)`` — sync. Returns the candidate URL for
  ``(machine, kind)`` or ``None`` if the source has no candidate for
  this lookup (distinct from a 404 at fetch time).

Sources also carry an instance-level ``disabled_reason: str | None``;
the orchestrator's registry filters out sources where it's non-None
so the readiness endpoint can surface the reason to the UI without
ever attempting a fetch.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from pathlib import Path
from typing import ClassVar, Literal, Protocol, runtime_checkable
from urllib.parse import quote

import httpx

from mame_curator.media.cache import MediaFetchError, cache_path_for
from mame_curator.media.cache_text import fetch_text_with_cache
from mame_curator.media.rate_limit import MediaRateLimited, TokenBucket
from mame_curator.media.urls import urls_for
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)

# The source-chain kind vocabulary. Excludes ``video`` deliberately —
# ``MediaUrls`` has no video field (P05 spec § "class MediaUrls"), so no
# source can ever cover that kind. The route's ``_VALID_KINDS`` set
# (which includes ``video``) is the user-input gate, not the source-chain
# vocabulary; the two are separate by design.
Kind = Literal["boxart", "title", "snap"]


@runtime_checkable
class MediaSource(Protocol):
    """Common shape every source in ``media.sources`` implements.

    ``@runtime_checkable`` lets the registry call ``isinstance(x, MediaSource)``
    at registration time — per PEP 544 this verifies attribute presence
    only (the four names below exist on the object), not method signatures
    or ``ClassVar`` types. Signature correctness is enforced by ``mypy`` at
    build time; the runtime check is defence-in-depth against truly-
    malformed extensions, not a typed contract.
    """

    name: ClassVar[str]
    license_compatible: ClassVar[bool]
    kinds: ClassVar[frozenset[Kind]]

    disabled_reason: str | None
    """Non-None means the source is gated off — registry filters it out
    of the fallback chain; readiness endpoint surfaces the string to UI.
    """

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        """Populate any per-machine lookup state the source needs."""
        ...

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the candidate URL for ``(machine, kind)``, or ``None``."""
        ...


class LibretroSource:
    """libretro-thumbnails MAME catalog — the P05 baseline.

    No per-machine lookup; ``prepare`` is a one-line no-op. ``url_for``
    delegates to ``urls_for(machine)`` (the existing P05 helper) and
    returns the URL matching the requested kind. ``disabled_reason``
    is permanently ``None`` — this source has no config that could
    be missing.
    """

    name: ClassVar[str] = "libretro"
    license_compatible: ClassVar[bool] = True
    kinds: ClassVar[frozenset[Kind]] = frozenset({"boxart", "title", "snap"})

    def __init__(self) -> None:
        """Construct a LibretroSource. No config to read — never disabled."""
        self.disabled_reason: str | None = None

    async def prepare(
        self,
        machine: Machine,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        """No-op: libretro is a direct-URL source with no per-machine state."""
        return

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the libretro thumbnail URL for ``kind`` on ``machine``.

        Always returns a string (every kind is covered); the ``str | None``
        in the signature exists for sources that may not have a candidate.
        """
        urls = urls_for(machine)
        # MediaUrls has exactly ``boxart`` / ``title`` / ``snap`` attributes
        # by construction (P05 spec). ``Kind`` is the exact same set.
        url: str = getattr(urls, kind)
        return url


# P10 chunk 3b — progettoSnaps local-pack source. Snap kind only; flyers
# and titles aren't published upstream anymore (see 2026-05-18 spec
# amendment in ``docs/specs/P10.md`` § "1. progettoSnaps — local pack
# model"). The pack is downloaded by ``mame-curator refresh-snaps``
# (chunk 3a) into ``<dest>/snap/<name>.png``.


class ProgettoSnapsSource:
    """Serves progettoSnaps snap PNGs from a local pack directory.

    Never hits the network; ``prepare`` is a no-op. ``url_for`` returns a
    ``file://`` URL when ``<snap_dir>/<machine.name>.png`` exists, else
    ``None``. The orchestrator's ``file://`` short-circuit (P10 spec §
    "Orchestrator amendment") returns the path directly without routing
    through ``fetch_with_cache`` (whose ``_ALLOWED_URL_SCHEMES`` guard
    rejects ``file://`` by design).

    ``disabled_reason`` is set at construction if ``snap_dir`` doesn't
    exist or is empty — the registry filters disabled sources out of the
    chain, and the readiness endpoint surfaces the reason to the UI as
    a prompt to run ``mame-curator refresh-snaps``.

    Existence checks against per-machine PNGs are cached on the instance
    so repeated ``url_for`` calls within one request don't ``stat()``
    repeatedly. Cache lifetime matches the per-request source-instance
    model (see § Architecture notes).
    """

    name: ClassVar[str] = "progettoSnaps"
    license_compatible: ClassVar[bool] = True
    kinds: ClassVar[frozenset[Kind]] = frozenset({"snap"})

    _DISABLED_REASON = (
        "Pack not downloaded. Run `mame-curator refresh-snaps` to fetch "
        "the latest progettoSnaps snap pack."
    )

    def __init__(self, *, snap_dir: Path) -> None:
        """Bind the source to ``snap_dir`` (typically ``data/snaps/snap``).

        Construction probes the directory once; if absent or empty, the
        source self-disables via ``disabled_reason``. The path is
        resolved to an absolute form so the produced ``file://`` URLs are
        unambiguous regardless of the caller's CWD.
        """
        self._present: set[str] = set()
        self._missing: set[str] = set()

        # Probe the pack dir once. Gate on ``is_dir()`` (not ``exists()``): a
        # ``snap_dir`` that is a regular FILE passes ``exists()`` but makes
        # ``iterdir()`` raise NotADirectoryError. And wrap the whole probe in
        # ``except OSError`` (FP33 M1): ``is_dir()`` re-raises EACCES and
        # ``iterdir()`` raises PermissionError on an execute-but-not-read dir —
        # an unhandled OSError here crashes build_registry → 500s every media
        # request. Any inaccessible / non-directory path simply self-disables.
        try:
            is_dir = snap_dir.is_dir()
            self._snap_dir = snap_dir.resolve() if is_dir else snap_dir
            empty = not is_dir or not any(snap_dir.iterdir())
        except OSError:
            self._snap_dir = snap_dir
            empty = True
        self.disabled_reason: str | None = self._DISABLED_REASON if empty else None

    async def prepare(
        self,
        machine: Machine,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        """No-op: progettoSnaps is a disk-only source."""
        return

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return ``file://<abs-snap_dir>/<machine.name>.png`` if present.

        Returns ``None`` when ``kind != "snap"`` (this source only covers
        snap), or when the file isn't on disk for this machine.
        """
        if kind != "snap":
            return None

        name = machine.name
        if name in self._missing:
            return None

        if name not in self._present:
            candidate = self._snap_dir / f"{name}.png"
            if candidate.is_file():
                self._present.add(name)
            else:
                self._missing.add(name)
                return None

        return (self._snap_dir / f"{name}.png").as_uri()


# P10 chunk 4 — ArcadeDB JSON scraper. Two-step lookup; parse-before-trust
# guards against cache-poisoning when upstream returns truncated TLS bodies
# or mid-deploy HTML-instead-of-JSON. See spec § "2. ArcadeDB" step 3.
_ARCADEDB_SCRAPER_BASE = "http://adb.arcadeitalia.net/service_scraper.php"


class ArcadeDBSource:
    """ArcadeDB scraper — JSON-driven URL lookups for boxart/title/snap.

    ``prepare`` acquires one token from the per-source ``TokenBucket``,
    fetches the scraper response via ``fetch_text_with_cache`` (HTTP 301 →
    HTTPS handled by the lifespan client's ``follow_redirects=True``),
    parses ``{"release": N, "result": [...]}``, and stashes the
    redirector-form URLs from ``result[0]`` (``url_image_flyer`` →
    ``boxart``, ``url_image_title`` → ``title``, ``url_image_ingame`` →
    ``snap``). Empty ``result`` array leaves ``_url_cache[name]`` absent
    — uniform negative-cache shape, ``url_for`` returns ``None``.

    Parse-before-trust: ``json.JSONDecodeError`` unlinks the offending
    cache slot via ``cache_path_for(url, cache_dir).unlink(missing_ok=True)``
    and raises ``MediaFetchError`` chained from the original exception.
    The next request re-fetches; transient bad upstream doesn't
    permanently disable the source.
    """

    name: ClassVar[str] = "arcadeDB"
    license_compatible: ClassVar[bool] = True
    kinds: ClassVar[frozenset[Kind]] = frozenset({"boxart", "title", "snap"})

    def __init__(self, *, limiter: TokenBucket, cache_dir: Path) -> None:
        """Bind to ``limiter`` (rate-limit) + ``cache_dir`` (JSON slot).

        ``disabled_reason`` is permanently ``None`` — ArcadeDB has no
        config that could be missing.
        """
        self._limiter = limiter
        self._cache_dir = cache_dir
        self._url_cache: dict[str, dict[str, str]] = {}
        self.disabled_reason: str | None = None

    @staticmethod
    def _scraper_url(machine: Machine) -> str:
        return f"{_ARCADEDB_SCRAPER_BASE}?ajax=query_mame&game_name={machine.name}"

    async def prepare(
        self,
        machine: Machine,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        """Populate the per-machine URL triple from one scraper hit.

        Raises ``MediaRateLimited`` on empty bucket; ``MediaFetchError``
        on JSON parse failure (cache slot unlinked first).
        """
        if not self._limiter.acquire():
            raise MediaRateLimited(f"arcadeDB rate-limit exceeded for {machine.name!r}")
        url = self._scraper_url(machine)
        text = await fetch_text_with_cache(url, self._cache_dir, client=client)
        if text is None:
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            cache_path_for(url, self._cache_dir).unlink(missing_ok=True)
            raise MediaFetchError(
                f"arcadeDB returned unparseable JSON for {machine.name!r}"
            ) from exc
        if not isinstance(data, dict):
            # Valid JSON but not an object (`[]` / `null` / a bare string) —
            # `data.get(...)` would raise AttributeError past the fallback
            # chain. Treat it like unparseable: unlink the poisoned slot + raise
            # MediaFetchError (resolve_image swallows it → next source).
            cache_path_for(url, self._cache_dir).unlink(missing_ok=True)
            raise MediaFetchError(f"arcadeDB returned non-object JSON for {machine.name!r}")
        # Nested parse-before-trust (FP33 H2): the top-level dict guard above
        # doesn't cover the shape UNDER it. A non-list/empty result is a legit
        # no-match; a non-dict result[0] or non-string URL field is upstream
        # drift — treat as no-match rather than let an AttributeError/TypeError
        # escape to the route as a 500.
        result = data.get("result")
        if not isinstance(result, list) or not result:
            return
        first = result[0]
        if not isinstance(first, dict):
            return
        urls: dict[str, str] = {}
        flyer = first.get("url_image_flyer")
        title = first.get("url_image_title")
        ingame = first.get("url_image_ingame")
        if isinstance(flyer, str) and flyer:
            urls["boxart"] = flyer
        if isinstance(title, str) and title:
            urls["title"] = title
        if isinstance(ingame, str) and ingame:
            urls["snap"] = ingame
        if urls:
            self._url_cache[machine.name] = urls

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the cached URL for ``(machine, kind)`` or ``None``."""
        return self._url_cache.get(machine.name, {}).get(kind)


# P10 chunk 5 — Wikipedia REST summary endpoint. One-step lookup; the only
# image field with a documented location is ``thumbnail.source`` (the
# infobox image). Title / snap aren't reliably present and would require
# HTML scraping — explicitly out of scope per spec § "3. Wikipedia (image)".
_WIKIPEDIA_REST_SUMMARY_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"
_TRAILING_PARENS = re.compile(r"\s*\([^)]*\)\s*$")


def _canonicalise_wikipedia_title(description: str) -> str:
    """Strip trailing parenthesised qualifier + outer whitespace.

    ``"Pac-Man (Midway)"`` → ``"Pac-Man"``. No fuzzy match, no second
    attempt — the source's value is the head of the catalog (Pac-Man,
    Tetris, Donkey Kong), not full coverage.
    """
    return _TRAILING_PARENS.sub("", description).strip()


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
        """Populate ``_url_cache[name]`` from the REST summary's thumbnail.

        Raises ``MediaRateLimited`` on empty bucket; ``MediaFetchError`` on
        JSON parse failure (cache slot unlinked first). 404 / missing
        thumbnail leave the cache entry absent — ``url_for`` returns ``None``.
        """
        if not self._limiter.acquire():
            raise MediaRateLimited(f"wikipediaImage rate-limit exceeded for {machine.name!r}")
        title = _canonicalise_wikipedia_title(machine.description)
        if not title:
            return
        url = self._summary_url(title)
        text = await fetch_text_with_cache(url, self._cache_dir, client=client)
        if text is None:
            return
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            cache_path_for(url, self._cache_dir).unlink(missing_ok=True)
            raise MediaFetchError(
                f"wikipediaImage returned unparseable JSON for {machine.name!r}"
            ) from exc
        if not isinstance(data, dict):
            # Valid-but-non-object JSON — parse-before-trust, same as the
            # unparseable branch above (else `data.get("thumbnail")` throws).
            cache_path_for(url, self._cache_dir).unlink(missing_ok=True)
            raise MediaFetchError(f"wikipediaImage returned non-object JSON for {machine.name!r}")
        # Nested parse-before-trust (FP33 H2): a truthy-but-non-dict thumbnail
        # would make ``.get("source")`` raise before the isinstance(thumb, str)
        # guard runs. Guard the container type first.
        thumbnail = data.get("thumbnail")
        thumb = thumbnail.get("source") if isinstance(thumbnail, dict) else None
        if isinstance(thumb, str) and thumb:
            self._url_cache[machine.name] = thumb

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the cached thumbnail URL or ``None``.

        Returns ``None`` for ``kind != "boxart"`` (this source's vocabulary
        is boxart-only — see ``kinds`` ClassVar).
        """
        if kind != "boxart":
            return None
        return self._url_cache.get(machine.name)


# P10 chunk 7 — the registry. Orders + filters configured sources into a
# per-kind fallback chain. See spec § "class MediaSourceRegistry" + § chunk-7
# notes. The orchestrator (resolve_image) and the composition-root factory
# (build_registry) live in resolve.py.

# Process-wide dedup for the "unknown source name in media.sources" WARNING.
# The registry is rebuilt per request (spec § Architecture notes), so without
# this a misconfigured name would log on every media request. Cleared by
# tests via ``_reset_unknown_source_warn_dedup()``.
_warned_unknown_sources: set[str] = set()


def _reset_unknown_source_warn_dedup() -> None:
    """Test hook — clear the process-wide unknown-source WARNING dedup set."""
    _warned_unknown_sources.clear()


class MediaSourceRegistry:
    """Resolves configured source names + a kind → an ordered MediaSource chain.

    Built per request from ``world.config.media.sources`` plus a
    ``name → MediaSource`` map the composition root (``build_registry`` in
    ``resolve.py``) assembles with the app-state limiters + the injected
    ``SourceDisabledFlag``. The registry is a pure filter/orderer — no
    app-state, no HTTP — so tests construct one from fake sources directly.
    """

    _BASELINE = "libretro"

    def __init__(
        self,
        configured: tuple[str, ...],
        available: Mapping[str, MediaSource],
    ) -> None:
        """Bind the configured order tuple + the ``name → instance`` map."""
        self._configured = configured
        self._available = available

    def chain_for(self, kind: Kind) -> tuple[MediaSource, ...]:
        """Sources that cover ``kind`` AND are ready, in the configured order.

        Filtering, in order: unknown names dropped (one-time WARNING, deduped
        process-wide); ``libretro`` appended if absent from the configured
        tuple; kind-mismatch filtered; ``disabled_reason``-set filtered.
        """
        names = list(self._configured)
        if self._BASELINE not in names:
            names.append(self._BASELINE)
        chain: list[MediaSource] = []
        for name in names:
            source = self._available.get(name)
            if source is None:
                if name not in _warned_unknown_sources:
                    _warned_unknown_sources.add(name)
                    logger.warning("media: unknown source %r in media.sources — skipping", name)
                continue
            if kind not in source.kinds:
                continue
            if source.disabled_reason is not None:
                continue
            chain.append(source)
        return tuple(chain)
