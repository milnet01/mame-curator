"""Split a MAME `<manufacturer>` field into (publisher, developer)."""

from __future__ import annotations

# Splits "... ( ... license)" — only the US spelling, only when "license" is the
# LAST word inside the trailing parenthetical, and the publisher is everything
# before. MAME's <manufacturer> field uses the US "license" spelling
# consistently across DAT versions; "licence" (UK) does not appear in real DATs
# and is deliberately not handled. The developer holds no parentheses, so on
# "Atari (JSA III) (Williams license)" the split is on the LAST "(" —
# publisher = "Atari (JSA III)", developer = "Williams" (FP28 B1).
# mame-curator-1225: string methods, not a regex, so a crafted field cannot
# make the split backtrack in quadratic time.
_LICENSE_TAIL = "license)"


def _split_license(cleaned: str) -> tuple[str, str] | None:
    """``(publisher, developer)`` for a ``"<pub> (<dev> license)"`` field, else None."""
    if not cleaned.endswith(_LICENSE_TAIL):
        return None
    publisher, paren, inner = cleaned[: -len(_LICENSE_TAIL)].rpartition("(")
    # inner is the developer (at least one character) plus the whitespace
    # before "license".
    if not paren or ")" in inner or len(inner) < 2 or not inner[-1].isspace():
        return None
    publisher = publisher.strip()
    # The old regex's "." stopped at a newline, so a publisher holding one did
    # not split; kept so no field splits differently.
    if not publisher or "\n" in publisher:
        return None
    return (publisher, inner.strip())


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
    split = _split_license(cleaned)
    return (cleaned, cleaned) if split is None else split
