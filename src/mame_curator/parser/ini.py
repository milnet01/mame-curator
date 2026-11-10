"""Parsers for the five progettoSnaps reference INI files.

All five use `[Section]` headers and `;` or `#` comments, behind a
[FOLDER_SETTINGS] / [ROOT_FOLDER] preamble. catver.ini lists `name=category`
lines (`_parse_simple_ini`); the other four are MAME folder files listing bare
shortnames under each section (`_parse_sectioned_ini`).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

from mame_curator.parser.errors import INIError

logger = logging.getLogger(__name__)

# progettoSnaps INI files ship configuration metadata under these section headers.
# Any key=value pairs underneath are tool-config, not catver/series/etc. data;
# excluding them prevents `RootFolderIcon` and friends from being treated as machines.
_META_SECTIONS = frozenset({"FOLDER_SETTINGS", "ROOT_FOLDER"})

# catver.ini also ships [VerAdded], keyed by the same shortnames, whose values are
# the MAME version that added each machine. Reading it overwrote every category.
_CATVER_NON_CATEGORY_SECTIONS = frozenset({"VerAdded"})


def parse_catver(path: Path) -> dict[str, str]:
    """Return {shortname: category} from progettoSnaps catver.ini.

    Section headers are ignored; only `name=value` lines under non-metadata sections
    are kept, and [VerAdded] is skipped. Duplicate shortnames overwrite (last write
    wins) and emit a warning.
    """
    out: dict[str, str] = {}
    for section, key, value in _parse_simple_ini(path):
        if section in _META_SECTIONS or section in _CATVER_NON_CATEGORY_SECTIONS:
            continue
        if key in out:
            logger.warning("duplicate catver key %r in %s; overwriting", key, path)
        out[key] = value
    return out


def parse_languages(path: Path) -> dict[str, list[str]]:
    """Return {shortname: [lang, ...]} from languages.ini.

    Each section is a language and lists bare shortnames. A game listed under
    several sections gets every one, in file order; that is data, not a
    conflict, so it does not warn. Excludes progettoSnaps metadata sections.
    """
    out: dict[str, list[str]] = {}
    for section, name in _parse_sectioned_ini(path):
        if section in _META_SECTIONS or not section:
            continue
        out.setdefault(name, []).append(section)
    return out


def parse_bestgames(path: Path) -> dict[str, str]:
    """Return {shortname: band} from bestgames.ini.

    Each section is a rating band (`[90 to 100 (Best Games)]`, ...) listing bare
    shortnames; each name maps to its band's section name. A name in two bands
    warns and the last wins.
    """
    return _section_per_name(path, "bestgames")


def parse_mature(path: Path) -> set[str]:
    """Return the set of shortnames mature.ini lists.

    The real file lists them directly under [ROOT_FOLDER], so unlike the other
    parsers this one reads that section; only [FOLDER_SETTINGS] (tool config)
    and lines before any header are excluded.
    """
    return {
        name
        for section, name in _parse_sectioned_ini(path)
        if section and section != "FOLDER_SETTINGS"
    }


def parse_series(path: Path) -> dict[str, str]:
    """Return {shortname: series_name} from series.ini.

    Each section header is the series name; the bare lines under it are member
    shortnames. A name in two series warns and the last wins. Excludes
    progettoSnaps configuration-metadata sections.
    """
    return _section_per_name(path, "series")


def _section_per_name(path: Path, kind: str) -> dict[str, str]:
    """Map each listed shortname to the one non-metadata section listing it."""
    out: dict[str, str] = {}
    for section, name in _parse_sectioned_ini(path):
        if section in _META_SECTIONS or not section:
            continue
        if name in out and out[name] != section:
            logger.warning(
                "%s name %r listed under two sections in %s; keeping the last", kind, name, path
            )
        out[name] = section
    return out


def _read_ini_text(path: Path) -> str:
    """Read an INI file as text. UTF-8 strict first; latin-1 fallback with warning.

    Per parser/spec.md G4: progettoSnaps INI files are UTF-8 in practice, but
    older versions and user-edited files may be latin-1. We never silently
    substitute U+FFFD (which `errors="replace"` does); instead we surface the
    encoding fall-back via a single warning per file.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise INIError(f"failed to read INI: {exc}", path=path) from exc
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        logger.warning("invalid UTF-8 in %s; falling back to latin-1", path)
        return raw.decode("latin-1")


def _parse_sectioned_ini(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (section, line) for every content line, stripped.

    In the MAME folder format each line is a bare shortname; catver's
    `_parse_simple_ini` splits the same lines on `=`.

    Section is "" when no header has been seen. Comments (`;`, `#`) and blank
    lines are skipped; header lines set the section and are not yielded.
    """
    if not path.exists():
        raise INIError("INI path does not exist", path=path)
    section = ""
    text = _read_ini_text(path)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("["):
            # Per parser/spec.md "INI section header tolerance": tolerate
            # `[Section] ; trailing comment` and `[Section]# trailing comment`
            # by truncating at the first `]` rather than requiring it as the
            # last character. Without this, an inline-commented META header
            # (`[FOLDER_SETTINGS] ; tool config`) silently fails to filter
            # and its keys leak into the parsed output.
            end = line.find("]")
            if end == -1:
                continue  # malformed `[…` with no closing bracket — skip
            section = line[1:end].strip()
            continue
        yield (section, line)


def _parse_simple_ini(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (section, key, value) for every `key=value` line (catver.ini).

    Lines without `=`, or with an empty key, are skipped silently.
    """
    for section, line in _parse_sectioned_ini(path):
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        yield (section, key, value.strip())
