"""BIOS chain resolution — transitive `romof` + `<biosset>` walk."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from mame_curator.copy.types import BIOSResolutionWarning
from mame_curator.parser.listxml import BIOSChainEntry


def resolve_bios_dependencies(
    winners: Iterable[str],
    bios_chain: dict[str, BIOSChainEntry],
) -> tuple[frozenset[str], tuple[BIOSResolutionWarning, ...]]:
    """Walk romof + biosset chains transitively; return (bios set, sorted warnings).

    Cycle safety is provided by the `seen` set checked at pop time;
    self-referencing romof entries (an unusual but possible MAME shape)
    are dropped on their second pop without further enqueue.

    Only top-level winners absent from `bios_chain` produce a warning
    (`kind="missing_from_listxml"`). Transitive descendants absent from
    `bios_chain` are silently treated as leaf BIOS files — the real
    "missing BIOS" failure mode is surfaced later as
    `SKIPPED_MISSING_SOURCE` during the copy phase if the `.zip` is
    absent from the source directory.
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

        for b in entry.biossets:
            if b not in winner_set:
                bios.add(b)
            queue.append((b, False))

        # Closing-review R2: no `entry.romof != name` guard — a self-
        # referencing romof is caught on its second pop by the `seen`
        # check (matches `copy/spec.md` § Cycle safety wording).
        if entry.romof:
            if entry.romof not in winner_set:
                bios.add(entry.romof)
            queue.append((entry.romof, False))

    sorted_warnings = tuple(sorted(warnings, key=lambda w: w.name))
    return frozenset(bios), sorted_warnings
