r"""URL builder for libretro-thumbnails MAME images.

Per ``docs/specs/P05.md`` § Public API. Mirrors the upstream filename rule:
characters in ``& * / : \ < > ? | "`` are escaped to ``_``; the result is
percent-encoded for URL safety.
"""

from __future__ import annotations

from urllib.parse import quote

from pydantic import BaseModel, ConfigDict

from mame_curator.parser.models import Machine

_BASE_URL = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"

# The 10 characters libretro-thumbnails escapes from descriptions to filenames.
# Matches the upstream rule for the MAME repo; see design §6.4 line 732 and
# roadmap line 396 (both intend the same set despite a markdown-rendering bug).
_ESCAPE_CHARS = frozenset('&*/:\\<>?|"')

_KIND_FOLDER = {
    "boxart": "Named_Boxarts",
    "title": "Named_Titles",
    "snap": "Named_Snaps",
}


class MediaUrls(BaseModel):
    """Three libretro-thumbnails URLs for one machine.

    No ``video`` field — design §6.3 routes video through progettoSnaps, which
    is a P06+ Settings-page concern. Callers dispatching on ``kind`` MUST
    short-circuit on ``video`` BEFORE invoking ``urls_for``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    boxart: str
    title: str
    snap: str


def escape_libretro(name: str) -> str:
    """Replace libretro-illegal filename characters with ``_``.

    Idempotent (``_`` is not in the special set). Empty input returns empty.
    """
    return "".join("_" if ch in _ESCAPE_CHARS else ch for ch in name)


def urls_for(machine: Machine) -> MediaUrls:
    """Build boxart / title / snap URLs for ``machine``.

    Escape rule is applied BEFORE percent-encoding. ``urllib.parse.quote``
    handles apostrophes, spaces, and other URL-reserved characters that
    libretro doesn't escape but the GitHub raw-content URL still needs.
    """
    encoded = quote(escape_libretro(machine.description))
    return MediaUrls(
        boxart=f"{_BASE_URL}/{_KIND_FOLDER['boxart']}/{encoded}.png",
        title=f"{_BASE_URL}/{_KIND_FOLDER['title']}/{encoded}.png",
        snap=f"{_BASE_URL}/{_KIND_FOLDER['snap']}/{encoded}.png",
    )
