"""Download progettoSnaps reference INIs to a local directory.

Canonical sources mirror AntoPISA's GitHub repo
(`https://github.com/AntoPISA/MAME_SupportFiles`) for stability — direct
progettoSnaps URLs are versioned per MAME release (no permanent paths)
and AntoPISA publishes the same files at stable raw GitHub URLs.

The repo organises files under per-file subdirectories
(`catver.ini/catver.ini`, `languages.ini/languages.ini`, etc.) — the
v1 default URLs reflect that layout. Five files are wired by default:
the four mandatory ones (``catver`` / ``languages`` / ``bestgames`` /
``series``) plus ``mature.ini`` which lives inside ``catver.ini/``
alongside the main catver file.

A bad URL or upstream 404 surfaces as a ``failed`` entry in
``INIRefreshReport`` (with the URL for the user to grab manually) — not
a raised exception. The CLI prints both the success and failure lists
so the user always sees what landed and what didn't.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from mame_curator.downloads import ManualFallback, download

logger = logging.getLogger(__name__)


_BASE = "https://raw.githubusercontent.com/AntoPISA/MAME_SupportFiles/main"

INI_DEFAULT_SOURCES: dict[str, str] = {
    "catver.ini": f"{_BASE}/catver.ini/catver.ini",
    "languages.ini": f"{_BASE}/languages.ini/languages.ini",
    "bestgames.ini": f"{_BASE}/bestgames.ini/bestgames.ini",
    "series.ini": f"{_BASE}/series.ini/series.ini",
    "mature.ini": f"{_BASE}/catver.ini/mature.ini",
}


@dataclass(frozen=True)
class INIRefreshReport:
    """Outcome of ``refresh_inis``: which files updated, which failed."""

    updated: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    """``[(filename, manual_fallback_url), ...]`` for the CLI to surface URLs."""

    @property
    def all_succeeded(self) -> bool:
        """``True`` iff every configured source downloaded successfully."""
        return not self.failed


async def refresh_inis(
    *,
    dest_dir: Path,
    client: httpx.AsyncClient,
    sources: Mapping[str, str] = INI_DEFAULT_SOURCES,
) -> INIRefreshReport:
    """Download each ``(name, url)`` to ``dest_dir / name`` atomically.

    Failures are collected in the report, not raised — the CLI surfaces
    each failed file's URL so the user can fetch it manually if a mirror
    is blocked or temporarily unavailable.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    updated: list[str] = []
    failed: list[tuple[str, str]] = []

    for name, url in sources.items():
        result = await download(url=url, dest=dest_dir / name, client=client)
        if isinstance(result, ManualFallback):
            failed.append((name, result.url))
            logger.warning("refresh_inis: %s failed (%s)", name, result.reason)
        else:
            updated.append(name)
            logger.info("refresh_inis: %s updated", name)

    return INIRefreshReport(updated=updated, failed=failed)
