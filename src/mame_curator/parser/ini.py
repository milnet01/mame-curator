"""Parsers for the five progettoSnaps reference INI files.

All five share section + key=value structure with `;` or `#` comments.
A shared `_parse_simple_ini` walker emits (section, key, value) triples;
each public parser interprets them differently.
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


def parse_catver(path: Path) -> dict[str, str]:
    """Return {shortname: category} from progettoSnaps catver.ini.

    Section headers are ignored; only `name=value` lines under non-metadata sections
    are kept. Duplicate shortnames overwrite (last write wins) and emit a warning.
    """
    out: dict[str, str] = {}
    for section, key, value in _parse_simple_ini(path):
        if section in _META_SECTIONS:
            continue
        if key in out:
            logger.warning("duplicate catver key %r in %s; overwriting", key, path)
        out[key] = value
    return out


def parse_languages(path: Path) -> dict[str, list[str]]:
    """Return {shortname: [lang, ...]} from languages.ini.

    Comma-separated values are split and stripped. Duplicate shortnames overwrite
    (last write wins) and emit a warning.
    """
    out: dict[str, list[str]] = {}
    for _section, key, value in _parse_simple_ini(path):
        if key in out:
            logger.warning("duplicate languages key %r in %s; overwriting", key, path)
        out[key] = [part.strip() for part in value.split(",") if part.strip()]
    return out


def parse_bestgames(path: Path) -> dict[str, str]:
    """Return {shortname: tier} from bestgames.ini.

    The bestgames format uses tier *sections* (`[Best]`, `[Great]`, ...) with
    shortname keys whose values are empty. We map each shortname to its section.
    """
    valid_tiers = {"Best", "Great", "Good", "Average", "Bad", "Awful"}
    out: dict[str, str] = {}
    for section, key, _value in _parse_simple_ini(path):
        if section in valid_tiers:
            if key in out:
                logger.warning("duplicate bestgames key %r in %s; overwriting", key, path)
            out[key] = section
    return out


def parse_mature(path: Path) -> set[str]:
    """Return the set of shortnames listed under [Mature]."""
    return {key for section, key, _v in _parse_simple_ini(path) if section == "Mature"}


def parse_series(path: Path) -> dict[str, str]:
    """Return {shortname: series_name} from series.ini.

    Each section header is the series name; the keys are member shortnames.
    Excludes progettoSnaps configuration-metadata sections.
    """
    out: dict[str, str] = {}
    for section, key, _v in _parse_simple_ini(path):
        if section and section not in _META_SECTIONS:
            if key in out:
                logger.warning("duplicate series key %r in %s; overwriting", key, path)
            out[key] = section
    return out


def _parse_simple_ini(path: Path) -> Iterator[tuple[str, str, str]]:
    """Yield (section, key, value) for every `key=value` line.

    Section is "" when no header has been seen. Comments (`;`, `#`) and
    blank lines are skipped. Lines without `=` are skipped silently.
    """
    if not path.exists():
        raise INIError("INI path does not exist", path=path)
    section = ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith((";", "#")):
                    continue
                if line.startswith("[") and line.endswith("]"):
                    section = line[1:-1].strip()
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                if not key:
                    continue
                yield (section, key, value)
    except OSError as exc:
        raise INIError(f"failed to read INI: {exc}", path=path) from exc
