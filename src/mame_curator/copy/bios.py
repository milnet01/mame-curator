"""BIOS chain resolution — transitive `romof` walk keeping `isbios` machines."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from mame_curator.copy.types import BIOSResolutionWarning
from mame_curator.parser.listxml import BIOSChainEntry


def resolve_bios_dependencies(
    winners: Iterable[str],
    bios_chain: dict[str, BIOSChainEntry],
) -> tuple[frozenset[str], tuple[BIOSResolutionWarning, ...]]:
    """Walk `romof` transitively; return (BIOS set, sorted warnings).

    Only machines the listxml flags `isbios="yes"` enter the set
    (`copy/spec.md` § BIOS chain resolution, mame-curator-1109). The walk
    passes through non-BIOS parents, so a clone of a Neo Geo game still
    reaches `neogeo`, but a parent that is not a BIOS is never copied: a
    non-merged clone zip already holds its ROMs. `<biosset>` names are BIOS
    options inside one zip and are never treated as short names.

    Cycle safety is provided by the `seen` set checked at pop time. Only an
    absent WINNER warns (`kind="missing_from_listxml"`); an absent name
    reached through `romof` is skipped silently. No absent name is added.
    """
    winners_list = list(winners)
    winner_set = set(winners_list)
    bios: set[str] = set()
    seen: set[str] = set()
    warnings: list[BIOSResolutionWarning] = []
    queue: deque[tuple[str, bool]] = deque((w, True) for w in winners_list)

    while queue:
        name, is_winner = queue.popleft()
        if name in seen:
            continue
        seen.add(name)

        entry = bios_chain.get(name)
        if entry is None:
            if is_winner:
                warnings.append(BIOSResolutionWarning(name=name, kind="missing_from_listxml"))
            continue

        if entry.is_bios and name not in winner_set:
            bios.add(name)
        if entry.romof:
            queue.append((entry.romof, False))

    sorted_warnings = tuple(sorted(warnings, key=lambda w: w.name))
    return frozenset(bios), sorted_warnings
