"""Which Wikipedia page is a game's (mame-curator-1140).

A game's name can be another page's: ``1942`` is the year, ``Joust`` the
sport. Both Wikipedia lookups try ``candidate_titles`` in order and take the
first summary ``is_game_page`` accepts. ``media/spec.md`` § "Source
contracts", wikipediaImage, "Which page".
"""

from __future__ import annotations

import re
from typing import Any

from mame_curator.parser.models import Machine

_WIKIPEDIA_REST_SUMMARY_BASE = "https://en.wikipedia.org/api/rest_v1/page/summary"
_TRAILING_PARENS = re.compile(r"\s*\([^)]*\)\s*$")
# A page's Wikidata short description: "1984 video game", "Puzzle video game".
# Not plain "game": jousting is a "Martial game between two horsemen".
_GAME_DESCRIPTION = re.compile(r"\b(?:video|arcade) game\b", re.IGNORECASE)


def _canonicalise_wikipedia_title(description: str) -> str:
    """Strip a trailing parenthesised qualifier and outer whitespace.

    ``"Pac-Man (Midway)"`` → ``"Pac-Man"``. No fuzzy match.
    """
    return _TRAILING_PARENS.sub("", description).strip()


def candidate_titles(machine: Machine) -> tuple[str, ...]:
    """The titles to try, in order: plain, ``(video game)``, ``(<year> video game)``."""
    base = _canonicalise_wikipedia_title(machine.description)
    if not base:
        return ()
    titles = [base, f"{base} (video game)"]
    if machine.year is not None:
        titles.append(f"{base} ({machine.year} video game)")
    return tuple(titles)


def is_game_page(summary: dict[str, Any]) -> bool:
    """A normal article (not a disambiguation page) described as a video or arcade game."""
    description = summary.get("description")
    return (
        summary.get("type") == "standard"
        and isinstance(description, str)
        and _GAME_DESCRIPTION.search(description) is not None
    )
