"""P10 chunk 7 — ``MediaSourceRegistry`` ordering + filtering tests.

Per ``docs/specs/P10.md`` § "class MediaSourceRegistry" + § "Registry tests".
The registry is a pure filter/orderer: it maps a configured name tuple through
a ``name → MediaSource`` map, drops unknown names (one-time WARNING, deduped
process-wide), appends the ``libretro`` baseline if absent, and filters out
kind-mismatched or ``disabled_reason``-set sources. Tests build it from fake
sources directly — no app-state, no HTTP.
"""

from __future__ import annotations

import logging
from typing import cast

import httpx

from mame_curator.media import Kind, LibretroSource, MediaSource, MediaSourceRegistry
from mame_curator.parser.models import Machine


def _reg(configured: tuple[str, ...], available: dict[str, object]) -> MediaSourceRegistry:
    """Build a registry, casting the fake-source map to the protocol type.

    The fakes are structural ``MediaSource`` s at runtime (``isinstance``
    accepts them); the cast bridges the instance-var-vs-ClassVar gap mypy
    flags on the ``ClassVar`` protocol members.
    """
    return MediaSourceRegistry(configured, cast("dict[str, MediaSource]", available))


class _FakeSource:
    """Minimal object satisfying the ``MediaSource`` protocol shape."""

    def __init__(
        self,
        name: str,
        kinds: frozenset[Kind],
        *,
        disabled_reason: str | None = None,
    ) -> None:
        self.name = name
        self.license_compatible = True
        self.kinds = kinds
        self.disabled_reason = disabled_reason

    async def prepare(self, machine: Machine, *, client: httpx.AsyncClient) -> None:
        return

    def url_for(self, machine: Machine, kind: Kind) -> str | None:
        return None


def test_fake_source_satisfies_protocol() -> None:
    """Guard: the test double really is a structural ``MediaSource``."""
    assert isinstance(_FakeSource("x", frozenset({"boxart"})), MediaSource)


def test_registry_filters_kinds_per_source() -> None:
    """A source that doesn't cover the requested kind is filtered out."""
    wiki = _FakeSource("wikipediaImage", frozenset({"boxart"}))
    lib = LibretroSource()
    reg = _reg(("wikipediaImage", "libretro"), {"wikipediaImage": wiki, "libretro": lib})
    # wikipediaImage covers boxart only → excluded for snap; libretro remains.
    assert [s.name for s in reg.chain_for("snap")] == ["libretro"]


def test_registry_appends_libretro_if_missing() -> None:
    """``libretro`` is appended (defensive baseline) when omitted from config."""
    prog = _FakeSource("progettoSnaps", frozenset({"snap"}))
    lib = LibretroSource()
    reg = _reg(("progettoSnaps",), {"progettoSnaps": prog, "libretro": lib})
    names = [s.name for s in reg.chain_for("snap")]
    assert names == ["progettoSnaps", "libretro"]


def test_registry_silently_drops_unknown_source(caplog: object) -> None:
    """An unknown configured name is dropped with a WARNING; chain stays valid."""
    lib = LibretroSource()
    reg = _reg(("nonsense", "libretro"), {"libretro": lib})
    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        chain = reg.chain_for("boxart")
    assert [s.name for s in chain] == ["libretro"]
    assert any("nonsense" in r.message for r in caplog.records)  # type: ignore[attr-defined]


def test_registry_unknown_name_warns_once(caplog: object) -> None:
    """The unknown-name WARNING is deduped process-wide, not per-registry.

    Two fresh registries built with the same bogus name log exactly one
    WARNING between them (the conftest autouse fixture clears the dedup set
    before this test).
    """
    lib = LibretroSource()
    with caplog.at_level(logging.WARNING):  # type: ignore[attr-defined]
        _reg(("nonsense", "libretro"), {"libretro": lib}).chain_for("boxart")
        _reg(("nonsense", "libretro"), {"libretro": lib}).chain_for("boxart")
    hits = [r for r in caplog.records if "nonsense" in r.message]  # type: ignore[attr-defined]
    assert len(hits) == 1


def test_registry_preserves_user_order() -> None:
    """Chain order matches the configured tuple order."""
    arc = _FakeSource("arcadeDB", frozenset({"boxart", "title", "snap"}))
    lib = LibretroSource()
    reg = _reg(("arcadeDB", "libretro"), {"arcadeDB": arc, "libretro": lib})
    assert [s.name for s in reg.chain_for("boxart")] == ["arcadeDB", "libretro"]


def test_registry_filters_disabled_source() -> None:
    """A source with a non-None ``disabled_reason`` is dropped from the chain."""
    moby = _FakeSource("mobyGames", frozenset({"boxart"}), disabled_reason="no key configured")
    lib = LibretroSource()
    reg = _reg(("mobyGames", "libretro"), {"mobyGames": moby, "libretro": lib})
    # mobyGames covers boxart but is disabled → filtered; libretro remains.
    assert [s.name for s in reg.chain_for("boxart")] == ["libretro"]
