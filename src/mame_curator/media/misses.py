"""mame-curator-1143 — remember for a while that a game has no picture.

Without this, a game no source has a picture for asks every source again
each time its card scrolls into view: slow, and it spends the art sources'
rate limits. A miss is remembered for ``MISS_DAYS`` (the user's choice,
2026-11-12), and ``forget_misses`` drops it at once for the "Look for a
picture again" button.

A miss is remembered only when every source answered "none". A source that
was rate-limited or failed may hold the picture, so that miss is not saved.
Each marker holds a fingerprint of the chain and the caller's picture
settings; a different fingerprint, such as a newly added folder, asks again.

Contract: ``src/mame_curator/media/spec.md`` § Remembered misses.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import get_args

import httpx

from mame_curator._atomic import atomic_write_text
from mame_curator.media.candidates import resolve_image_found
from mame_curator.media.sources import Kind, MediaSourceRegistry
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)

MISS_DAYS = 7
_MISS_SECONDS = MISS_DAYS * 24 * 60 * 60


def miss_marker(cache_dir: Path, name: str, kind: Kind) -> Path:
    """The file that remembers ``name`` has no ``kind`` picture.

    Named by a hash of the game's name, so no name can leave the folder.
    """
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()
    return cache_dir / "misses" / kind / f"{digest}.miss"


def _fingerprint(registry: MediaSourceRegistry, kind: Kind, settings: str) -> str:
    chain = [source.name for source in registry.chain_for(kind)]
    return hashlib.sha256(json.dumps([chain, settings]).encode("utf-8")).hexdigest()


def _remembered(marker: Path, fingerprint: str) -> bool:
    try:
        age = time.time() - marker.stat().st_mtime
        held = marker.read_text(encoding="utf-8")
    except OSError:
        return False
    # A marker dated in the future (the clock moved back) is asked again.
    return 0 <= age < _MISS_SECONDS and held == fingerprint


def _remember(marker: Path, fingerprint: str) -> None:
    try:
        atomic_write_text(marker, fingerprint)
    except OSError as exc:
        # Not saving a miss only costs a lookup next time; never fail the view.
        logger.warning("media: could not remember a missing picture at %s: %s", marker, exc)


def forget_misses(cache_dir: Path, name: str) -> None:
    """Drop every remembered miss for ``name``, so the next view asks again."""
    for kind in get_args(Kind):
        miss_marker(cache_dir, name, kind).unlink(missing_ok=True)


async def resolve_image_remembered(
    machine: Machine,
    kind: Kind,
    *,
    registry: MediaSourceRegistry,
    cache_dir: Path,
    client: httpx.AsyncClient,
    settings: str,
) -> Path | None:
    """``resolve_image``, but a remembered miss asks no source.

    ``settings`` is any text that changes when the picture settings do; a
    miss saved under other settings is asked again.
    """
    marker = miss_marker(cache_dir, machine.name, kind)
    fingerprint = _fingerprint(registry, kind, settings)
    if _remembered(marker, fingerprint):
        return None
    failed: set[str] = set()
    found = await resolve_image_found(
        machine, kind, registry=registry, cache_dir=cache_dir, client=client, failed=failed
    )
    if found is not None:
        return found.path
    if not failed:
        _remember(marker, fingerprint)
    return None
