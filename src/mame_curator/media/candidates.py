"""mame-curator-1146 — every picture a game has, and one chosen picture.

``resolve_pair`` asks one source for one kind. ``resolve_image_found`` is the
fallback-chain walk, reporting which source answered. ``list_candidates``
asks every source for every kind, for the picture guide, holding back the
rate-limited sources unless asked.

Per ``docs/specs/mame-curator-1146-picture-choice.md`` §4.3. The per-source
step (``answer_from``) lives in ``resolve.py`` beside the ``file://`` rule.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from mame_curator.media import resolve as _resolve
from mame_curator.media.cache import MediaFetchError
from mame_curator.media.rate_limit import MediaRateLimited
from mame_curator.media.sources import Kind, MediaSource, MediaSourceRegistry
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)

# The sources with a token bucket: each `prepare` spends from a limit.
LIMITED_SOURCES: frozenset[str] = frozenset({"arcadeDB", "wikipediaImage", "mobyGames"})

_KINDS: tuple[Kind, ...] = ("boxart", "title", "snap")


@dataclass(frozen=True)
class Found:
    """A picture one source answered for one kind."""

    source: str
    kind: Kind
    path: Path


@dataclass(frozen=True)
class CandidateList:
    """``list_candidates``' answer.

    ``found``: the pictures, without byte-equal repeats. ``not_asked``: the
    limited sources held back. ``not_answered``: the sources that raised.
    """

    found: tuple[Found, ...]
    not_asked: tuple[str, ...]
    not_answered: tuple[str, ...]


def _in_chain(registry: MediaSourceRegistry, source: str, kind: Kind) -> MediaSource | None:
    return next((s for s in registry.chain_for(kind) if s.name == source), None)


async def resolve_pair(
    machine: Machine,
    source: str,
    kind: Kind,
    *,
    registry: MediaSourceRegistry,
    cache_dir: Path,
    client: httpx.AsyncClient,
) -> Path | None:
    """The pair ``(source, kind)``'s image, or ``None``.

    ``None`` when ``source`` is not in ``registry.chain_for(kind)``, has no
    candidate, or the upstream 404s. Raises ``MediaRateLimited`` and
    ``MediaFetchError``; callers decide.
    """
    found = _in_chain(registry, source, kind)
    if found is None:
        return None
    await found.prepare(machine, client=client)
    return await _resolve.answer_from(found, machine, kind, cache_dir=cache_dir, client=client)


async def resolve_image_found(
    machine: Machine,
    kind: Kind,
    *,
    registry: MediaSourceRegistry,
    cache_dir: Path,
    client: httpx.AsyncClient,
) -> Found | None:
    """``resolve_image`` saying which source answered; ``None`` when all miss."""
    for source in registry.chain_for(kind):
        try:
            await source.prepare(machine, client=client)
        except MediaRateLimited:
            logger.info("media: %s rate-limited during prepare; falling through", source.name)
            continue
        except MediaFetchError:
            logger.warning(
                "media: %s prepare failed for %s; falling through", source.name, machine.name
            )
            continue
        try:
            path = await _resolve.answer_from(
                source, machine, kind, cache_dir=cache_dir, client=client
            )
        except MediaFetchError:
            logger.warning(
                "media: %s fetch failed for %s/%s; falling through",
                source.name,
                machine.name,
                kind,
            )
            continue
        if path is not None:
            return Found(source=source.name, kind=kind, path=path)
    return None


def file_digest(path: Path) -> str:
    """The sha256 of a picture's bytes, to tell two pictures apart."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _Listing:
    """The running state of one ``list_candidates`` call."""

    def __init__(self) -> None:
        self.found: list[Found] = []
        self.digests: set[str] = set()
        self.prepared: set[str] = set()
        self.failed: set[str] = set()
        self.not_asked: list[str] = []
        self.not_answered: list[str] = []

    def note(self, names: list[str], name: str) -> None:
        if name not in names:
            names.append(name)

    async def ready(self, source: MediaSource, machine: Machine, client: httpx.AsyncClient) -> bool:
        """Prepare ``source`` once per listing; False when it raised, now or before."""
        if source.name in self.failed:
            return False
        if source.name in self.prepared:
            return True
        try:
            await source.prepare(machine, client=client)
        except (MediaRateLimited, MediaFetchError) as exc:
            logger.info("media: %s did not answer the listing: %s", source.name, exc)
            self.failed.add(source.name)
            self.note(self.not_answered, source.name)
            return False
        self.prepared.add(source.name)
        return True

    async def keep(self, found: Found) -> None:
        digest = await asyncio.to_thread(file_digest, found.path)
        if digest not in self.digests:
            self.digests.add(digest)
            self.found.append(found)


async def list_candidates(
    machine: Machine,
    *,
    registry: MediaSourceRegistry,
    ask_limited: bool,
    cache_dir: Path,
    client: httpx.AsyncClient,
) -> CandidateList:
    """Every picture the chain holds for ``machine``, boxart then title then snap.

    Skips ``LIMITED_SOURCES`` unless ``ask_limited``. Each source's ``prepare``
    runs at most once; a source whose ``prepare`` raised is not asked again.
    A picture whose bytes equal an earlier one's is dropped.
    """
    run = _Listing()
    for kind in _KINDS:
        for source in registry.chain_for(kind):
            if source.name in LIMITED_SOURCES and not ask_limited:
                run.note(run.not_asked, source.name)
                continue
            if not await run.ready(source, machine, client):
                continue
            try:
                path = await _resolve.answer_from(
                    source, machine, kind, cache_dir=cache_dir, client=client
                )
            except MediaFetchError as exc:
                logger.info("media: %s fetch failed in the listing: %s", source.name, exc)
                run.note(run.not_answered, source.name)
                continue
            if path is not None:
                await run.keep(Found(source=source.name, kind=kind, path=path))
    return CandidateList(
        found=tuple(run.found),
        not_asked=tuple(run.not_asked),
        not_answered=tuple(run.not_answered),
    )
