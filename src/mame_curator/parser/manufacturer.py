"""Split a MAME `<manufacturer>` field into (publisher, developer)."""

from __future__ import annotations

import re

# Matches "... ( ... license)" — only the US spelling, only when "license" is the LAST
# word inside the trailing parenthetical, and we keep the publisher = everything before.
# MAME's <manufacturer> field uses the US "license" spelling consistently across DAT
# versions; "licence" (UK) does not appear in real DATs and is deliberately not handled.
_LICENSE_RE = re.compile(r"^\s*(?P<publisher>.+?)\s*\((?P<developer>.+?)\s+license\)\s*$")


def split_manufacturer(raw: str | None) -> tuple[str | None, str | None]:
    """Split a manufacturer field into (publisher, developer).

    `"Capcom (Sega license)"` -> `("Capcom", "Sega")`.
    `"Capcom"` -> `("Capcom", "Capcom")`.
    `None` / empty / whitespace -> `(None, None)`.
    """
    if raw is None:
        return (None, None)
    cleaned = raw.strip()
    if not cleaned:
        return (None, None)
    match = _LICENSE_RE.match(cleaned)
    if match is None:
        return (cleaned, cleaned)
    return (match.group("publisher").strip(), match.group("developer").strip())
