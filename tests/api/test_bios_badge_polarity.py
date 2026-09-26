"""Regression tests for mame-curator-1109 -- BIOS_MISSING badge + `only_bios_missing`
filter polarity.

Per ``src/mame_curator/copy/spec.md`` § "Source of BIOS-chain relationships":
membership in ``world.bios_chain`` is NOT a BIOS signal. ``Badge.BIOS_MISSING``
must be set exactly when ``resolve_bios_dependencies([short], bios_chain)``
returns a non-empty set for the game's own short name, and
``only_bios_missing=True`` must keep exactly the games carrying that badge.

``src/mame_curator/api/routes/games.py`` currently tests raw membership
instead (``_parent_of(short, world) in world.bios_chain``): that produces a
false-positive badge for any machine whose ``romof`` chain reaches a
non-BIOS parent, and an *inverted* ``only_bios_missing`` filter (it keeps the
games that do NOT need a BIOS -- see the ``keep()`` closure's final
``return`` line).

Uses a private 3-machine DAT/listxml pair (``bios_polarity_dat.xml`` /
``bios_polarity_listxml.xml``), independent of the shared 6-machine
``tests/api/fixtures/api_listxml.xml`` fixture other games-route tests rely
on, so the three cases below are unambiguous:

- ``needsbios``      -- romof -> realbios (``isbios="yes"``)     -- genuinely BIOS-dependent.
- ``nobios``          -- no romof, no biosset                    -- no BIOS dependency at all.
- ``falsepositive``   -- romof -> regularparent (not a BIOS)      -- has a romof, but the
  chain never reaches an ``is_bios`` machine; the pre-fix membership-only
  signal badges this one anyway.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

API_FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def mini_dat() -> Path:
    """Override the shared session-scoped 6-machine DAT with the private
    3-machine BIOS-polarity fixture (see module docstring)."""
    return API_FIXTURES / "bios_polarity_dat.xml"


@pytest.fixture
def listxml() -> Path:
    """Override the shared session-scoped listxml with the matching
    BIOS-chain listxml (see module docstring)."""
    return API_FIXTURES / "bios_polarity_listxml.xml"


def _badges_by_name(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {item["short_name"]: item["badges"] for item in items}


def test_bios_missing_badge_true_positive(client: Any) -> None:
    """A machine whose romof chain reaches a real BIOS (``isbios="yes"``)
    carries ``bios_missing``."""
    resp = client.get("/api/games", params={"page_size": 500})
    assert resp.status_code == 200
    badges = _badges_by_name(resp.json()["items"])
    assert "bios_missing" in badges["needsbios"], (
        f"expected needsbios to carry bios_missing, got {badges['needsbios']!r}"
    )


def test_bios_missing_badge_absent_when_no_dependency(client: Any) -> None:
    """A machine with no romof and no biosset never carries ``bios_missing``."""
    resp = client.get("/api/games", params={"page_size": 500})
    assert resp.status_code == 200
    badges = _badges_by_name(resp.json()["items"])
    assert "bios_missing" not in badges["nobios"], (
        f"expected nobios to carry no bios_missing badge, got {badges['nobios']!r}"
    )


def test_bios_missing_badge_false_positive_regression(client: Any) -> None:
    """Regression: a ``romof`` pointing at an ordinary, non-BIOS parent must
    NOT set ``bios_missing``. Membership in ``bios_chain`` alone (the
    pre-fix signal) says yes; ``resolve_bios_dependencies`` says no because
    the chain never reaches an ``is_bios=True`` entry.

    Expected (fixed): "bios_missing" not in badges["falsepositive"].
    Actual (live defect): membership-based ``_badges()`` sets it anyway,
    because ``falsepositive`` is present in ``world.bios_chain`` (it has a
    non-empty ``romof``) even though that romof never reaches a BIOS.
    """
    resp = client.get("/api/games", params={"page_size": 500})
    assert resp.status_code == 200
    badges = _badges_by_name(resp.json()["items"])
    assert "bios_missing" not in badges["falsepositive"], (
        "falsepositive carries bios_missing -- membership-based badge logic "
        f"is still live (got {badges['falsepositive']!r})"
    )


def test_only_bios_missing_filter_keeps_exactly_badged_games(client: Any) -> None:
    """Regression: ``only_bios_missing=True`` must keep exactly the games
    carrying ``bios_missing``.

    Expected (fixed): {"needsbios"} -- the one machine that actually needs
    a BIOS.
    Actual (live defect): ``keep()``'s last line is
    ``return not (only_bios_missing and short in world.bios_chain)``, which
    keeps the games NOT in the chain (``nobios``) and drops the ones that
    are (``needsbios``, ``falsepositive``) -- the opposite set.
    """
    resp = client.get("/api/games", params={"only_bios_missing": "1", "page_size": 500})
    assert resp.status_code == 200
    names = {item["short_name"] for item in resp.json()["items"]}
    assert names == {"needsbios"}, (
        f"expected only_bios_missing=1 to keep exactly {{'needsbios'}}, got {names!r}"
    )
