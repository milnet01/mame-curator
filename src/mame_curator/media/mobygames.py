"""MobyGames port-cover source (P10 chunk 6) — key resolution + disabled states.

Split out of ``sources.py`` so that file stays under the 500-line hard cap
(coding-standards § 2). MobyGames is the only P10 source that can be
*disabled* (it needs an API key the others don't), so it carries the most
machinery; keeping it here also isolates the deliberate divergence from the
``fetch_text_with_cache`` path the other two-step sources use.

Per ``docs/specs/P10-media-coverage.md`` § "4. MobyGames" + § "Disabled-source mechanism".

**Chunk 6 scope (key-handling).** Resolve the API key (``MOBYGAMES_API_KEY``
env var, then a mode-0600 ``<secrets_dir>/mobygames.key`` dotfile),
self-disable with a user-readable reason when no key resolves, and flip the
injected process-wide ``SourceDisabledFlag`` on a 401/403.

**Cover lookup (mame-curator-1079).** A title search, then the covers of
the result's Arcade platform, the front cover preferred. Built from the
published API shape as Skyscraper's working parser uses it, because no key
is available to capture a real response: unverified against the live
service. Each JSON body is cached on disk under a key-free name, written
only after it parses, so a repeat lookup makes no request.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import stat
import sys
from pathlib import Path
from typing import ClassVar
from urllib.parse import quote

import httpx

from mame_curator.media.cache import MediaFetchError
from mame_curator.media.rate_limit import MediaRateLimited, TokenBucket
from mame_curator.media.sources import Kind
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)


class SourceDisabledFlag:
    """Process-wide mutable holder for a source's runtime-disabled reason.

    ``MobyGamesSource`` flips ``reason`` on the first 401/403 from a
    *configured* key (the key is invalid or revoked — retrying won't help
    until a server restart). Because source instances are re-created per
    request (the registry is per-request), this holder lives on
    ``app.state`` so the disabled state survives, while the source itself
    stays free of any ``api/`` import.

    The spec's § "Disabled-source mechanism" places the reason on
    ``app.state.mobygames_disabled_reason``, but ``media/`` is HTTP-agnostic
    and ``prepare`` only receives an httpx client — it has no app handle to
    write back to a bare ``str`` attribute. So the reason is carried by this
    holder, injected at construction exactly as the token buckets are.
    (Spec amendment 2026-07-01 — chunk 6.)
    """

    def __init__(self, reason: str | None = None) -> None:
        """Start ready (``reason=None``) unless a prior failure is replayed."""
        self.reason = reason


_MOBYGAMES_API_BASE = "https://api.mobygames.com/v1/games"
_MOBYGAMES_ENV_VAR = "MOBYGAMES_API_KEY"
_MOBYGAMES_KEY_FILENAME = "mobygames.key"
_MOBYGAMES_DEFAULT_SECRETS_DIR = Path("data/secrets")


def mobygames_key_path(secrets_dir: Path = _MOBYGAMES_DEFAULT_SECRETS_DIR) -> Path:
    """Path to the MobyGames key dotfile under ``secrets_dir``.

    Single source of truth for the dotfile location, shared by
    ``MobyGamesSource._resolve_key`` (read) and the P10 chunk-9
    ``PUT /api/media/sources/{name}/secret`` route (write) so the written
    key is exactly what the next source construction reads.
    """
    return secrets_dir / _MOBYGAMES_KEY_FILENAME


# Process-wide dedup for the "MobyGames disabled — no key" WARNING. Source
# instances are re-created per request (P10 § Architecture notes), so without
# this guard a keyless MobyGames would log on every thumbnail request. Chunk 7
# owns this cross-request dedup (the chunk-6 note anticipated it). Cleared by
# tests via ``_reset_missing_key_warn_dedup()``.
_missing_key_warned = False


def _reset_missing_key_warn_dedup() -> None:
    """Test hook — clear the process-wide missing-key WARNING dedup guard."""
    global _missing_key_warned
    _missing_key_warned = False


_MOBYGAMES_NO_KEY_REASON = (
    "No API key configured. Set MOBYGAMES_API_KEY env var, or paste a key "
    "into Settings → Media (writes data/secrets/mobygames.key, mode 0600)."
)
_MOBYGAMES_BAD_KEY_REASON = (
    "MobyGames rejected the configured API key (HTTP 401/403). The key is "
    "invalid or revoked — fix it and restart the server."
)


class MobyGamesSource:
    """MobyGames port covers — boxart only, requires an API key.

    This source resolves the API key, self-disables with a user-readable
    ``disabled_reason`` when no key resolves, and flips the injected
    process-wide ``SourceDisabledFlag`` on a 401/403 from a configured key.
    The lookup request carries the key in its query string, so any error /
    log message redacts it.

    **Deliberate divergence from ArcadeDB/Wikipedia.** Those route through
    ``fetch_text_with_cache``, which collapses every non-200/404 into one
    generic ``MediaFetchError`` *embedding the full URL* — both fatal here:
    we must tell 401 (disable) from 429 (rate-limit) apart, and we must not
    leak the keyed URL into logs. So ``prepare`` makes its own ``client.get``
    to inspect the status code and redact the key.

    **Cover lookup.** ``prepare`` searches by title, takes the first result
    with an Arcade platform, fetches that platform's covers and keeps the
    front cover (else the first image). Both JSON bodies are cached under
    ``<cache_dir>/mobygames/`` by a hash of a key-free name.
    """

    name: ClassVar[str] = "mobyGames"
    license_compatible: ClassVar[bool] = False
    kinds: ClassVar[frozenset[Kind]] = frozenset({"boxart"})

    def __init__(
        self,
        *,
        limiter: TokenBucket,
        cache_dir: Path,
        disabled_flag: SourceDisabledFlag,
        secrets_dir: Path = _MOBYGAMES_DEFAULT_SECRETS_DIR,
    ) -> None:
        """Resolve the key and set ``disabled_reason`` accordingly.

        If ``disabled_flag.reason`` is already set (a 401 happened earlier
        this process), the source stays disabled regardless of whether a key
        now resolves — a restart is required to clear it. Otherwise the key
        is resolved from env / dotfile; a missing key sets ``disabled_reason``
        and emits exactly one WARNING.
        """
        self._limiter = limiter
        self._cache_dir = cache_dir
        self._disabled_flag = disabled_flag
        self._secrets_dir = secrets_dir
        self._url_cache: dict[str, str] = {}
        self._api_key: str = ""

        if disabled_flag.reason is not None:
            self.disabled_reason: str | None = disabled_flag.reason
            return

        key = self._resolve_key()
        if not key:
            self.disabled_reason = _MOBYGAMES_NO_KEY_REASON
            global _missing_key_warned
            if not _missing_key_warned:
                _missing_key_warned = True
                logger.warning("media/sources: MobyGames disabled — %s", _MOBYGAMES_NO_KEY_REASON)
        else:
            self._api_key = key
            self.disabled_reason = None

    def _resolve_key(self) -> str | None:
        """Return the API key from env var or 0600 dotfile, else ``None``.

        Env var wins. A dotfile that is group/other-readable (any of the
        ``0o077`` bits set) is rejected with a WARNING — an attacker-readable
        secret is treated as no secret.
        """
        env_key = os.environ.get(_MOBYGAMES_ENV_VAR, "").strip()
        if env_key:
            return env_key

        keyfile = mobygames_key_path(self._secrets_dir)
        try:
            st = keyfile.stat()
        except OSError:
            return None
        if not stat.S_ISREG(st.st_mode):
            return None
        # POSIX mode bits are the security boundary on Unix only — Windows
        # reports a synthetic 0o666 regardless of chmod (NTFS ACLs are the
        # real gate there), so the same `sys.platform != "win32"` guard the
        # atomic-write path uses applies. On Windows the key is accepted on
        # mode grounds; refusing it would make MobyGames permanently
        # unusable for no security gain.
        if sys.platform != "win32" and st.st_mode & 0o077 != 0:
            logger.warning(
                "media/sources: MobyGames key file %s has insecure mode %04o "
                "(must be 0600); ignoring it",
                keyfile,
                stat.S_IMODE(st.st_mode),
            )
            return None
        try:
            return keyfile.read_text(encoding="utf-8").strip() or None
        except (OSError, UnicodeDecodeError):
            # A corrupt / non-UTF-8 key file — or a TOCTOU delete/perm-change
            # between the stat() above and this read — must self-disable, not
            # crash __init__ → build_registry → 500 every media request. Treat
            # an unreadable key the same as a missing one. (FP34 M1)
            logger.warning(
                "media/sources: MobyGames key file %s is unreadable; ignoring it",
                keyfile,
            )
            return None

    def _lookup_url(self, machine: Machine) -> str:
        return f"{_MOBYGAMES_API_BASE}?title={quote(machine.description)}&api_key={self._api_key}"

    def _redact(self, url: str) -> str:
        """Replace the API key in ``url`` with ``***`` for safe logging."""
        return url.replace(self._api_key, "***") if self._api_key else url

    def _cache_file(self, name: str) -> Path:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
        return self._cache_dir / "mobygames" / f"{digest}.json"

    async def _get_json(
        self, url: str, cache_name: str, machine: Machine, *, client: httpx.AsyncClient
    ) -> object | None:
        """The parsed body for ``url``, from disk when cached.

        ``None`` means no candidate: a 404, or a 401/403 that disabled the
        source. Raises ``MediaRateLimited`` on an empty bucket or a 429, and
        ``MediaFetchError`` (key redacted) on a network error, another
        status, or a body that is not JSON. Only a parsed body is cached.
        """
        cache_file = self._cache_file(cache_name)
        try:
            cached: object = json.loads(cache_file.read_text(encoding="utf-8"))
            return cached
        except (OSError, ValueError):
            pass
        if not self._limiter.acquire():
            raise MediaRateLimited(f"mobyGames rate-limit exceeded for {machine.name!r}")
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise MediaFetchError(
                f"mobyGames network error for {self._redact(url)}: {exc}"
            ) from exc

        status = resp.status_code
        if status in (401, 403):
            if self._disabled_flag.reason is None:
                self._disabled_flag.reason = _MOBYGAMES_BAD_KEY_REASON
                logger.warning(
                    "media/sources: MobyGames rejected the API key (HTTP %d); "
                    "disabling for this process — %s",
                    status,
                    _MOBYGAMES_BAD_KEY_REASON,
                )
            self.disabled_reason = self._disabled_flag.reason
            return None
        if status == 429:
            raise MediaRateLimited(f"mobyGames rate-limited (HTTP 429) for {machine.name!r}")
        if status == 404:
            return None
        if status != 200:
            raise MediaFetchError(f"mobyGames upstream {status} for {self._redact(url)}")
        try:
            body: object = json.loads(resp.text)
        except ValueError as exc:
            raise MediaFetchError(
                f"mobyGames sent a non-JSON body for {self._redact(url)}"
            ) from exc
        return body

    def _store(self, cache_name: str, body: object) -> None:
        cache_file = self._cache_file(cache_name)
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps(body), encoding="utf-8")
        except OSError:
            logger.warning("media/sources: could not cache a MobyGames response at %s", cache_file)

    async def prepare(
        self,
        machine: Machine,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        """Look up the arcade front cover for ``machine`` and cache its URL.

        Raises ``MediaRateLimited`` on an empty bucket or a 429. A 401/403
        flips the process-wide disabled flag (one WARNING) and returns. A
        404, or no Arcade version, returns with no candidate. A malformed
        body raises ``MediaFetchError`` and is not cached. Network / other
        non-200 errors raise ``MediaFetchError`` with the key redacted.
        """
        if self.disabled_reason is not None:
            return  # registry already filters these out; defensive no-op

        search_name = f"search:{machine.description}"
        search = await self._get_json(
            self._lookup_url(machine), search_name, machine, client=client
        )
        if search is None:
            return
        games = search.get("games") if isinstance(search, dict) else None
        if not isinstance(games, list):
            raise MediaFetchError(f"mobyGames search body has no games list for {machine.name!r}")
        self._store(search_name, search)

        arcade = _arcade_platform(games)
        if arcade is None:
            return
        game_id, platform_id = arcade
        covers_name = f"covers:{game_id}:{platform_id}"
        covers_url = (
            f"{_MOBYGAMES_API_BASE}/{game_id}/platforms/{platform_id}/covers"
            f"?api_key={self._api_key}"
        )
        covers = await self._get_json(covers_url, covers_name, machine, client=client)
        if covers is None:
            return
        groups = covers.get("cover_groups") if isinstance(covers, dict) else None
        if not isinstance(groups, list):
            raise MediaFetchError(f"mobyGames covers body has no cover_groups for {machine.name!r}")
        self._store(covers_name, covers)

        image = _front_cover(groups)
        if image is not None:
            self._url_cache[machine.name] = image

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        """Return the cached cover URL or ``None``.

        Returns ``None`` for ``kind != "boxart"`` (boxart-only source), and
        for a machine ``prepare`` found no cover for.
        """
        if kind != "boxart":
            return None
        return self._url_cache.get(machine.name)


def _arcade_platform(games: list[object]) -> tuple[int, int] | None:
    """(game_id, platform_id) of the first search result with an Arcade platform."""
    for game in games:
        if not isinstance(game, dict):
            continue
        for platform in game.get("platforms") or ():
            if (
                isinstance(platform, dict)
                and str(platform.get("platform_name", "")).lower() == "arcade"
                and isinstance(game.get("game_id"), int)
                and isinstance(platform.get("platform_id"), int)
            ):
                return game["game_id"], platform["platform_id"]
    return None


def _front_cover(groups: list[object]) -> str | None:
    """The first front cover's image URL, else the first image at all."""
    images: list[tuple[bool, str]] = []
    for group in groups:
        covers = group.get("covers") if isinstance(group, dict) else None
        for cover in covers or ():
            if isinstance(cover, dict) and isinstance(cover.get("image"), str):
                is_front = "front cover" in str(cover.get("scan_of", "")).lower()
                images.append((is_front, cover["image"].replace("http://", "https://", 1)))
    for is_front, url in images:
        if is_front:
            return url
    return images[0][1] if images else None
