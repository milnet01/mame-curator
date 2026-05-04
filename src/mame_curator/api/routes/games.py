"""R01-R07 — games, alternatives, explanation, notes, stats."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, Query, Request

from mame_curator.api.errors import GameNotFoundError
from mame_curator.api.persist import write_json_atomic
from mame_curator.api.routes._deps import get_world, set_world
from mame_curator.api.schemas import (
    Alternatives,
    Badge,
    Explanation,
    GameCard,
    GameDetail,
    GamesPage,
    LibraryFacets,
    Notes,
    NotesPutRequest,
    Stats,
)
from mame_curator.api.state import WorldState, replace_world
from mame_curator.filter.picker import explain_pick
from mame_curator.parser.models import Machine

router = APIRouter()


def _badges(short: str, world: WorldState) -> tuple[Badge, ...]:
    out: list[Badge] = []
    fr = world.filter_result
    if any(g.parent == _parent_of(short, world) for g in fr.contested_groups):
        out.append(Badge.CONTESTED)
    if _parent_of(short, world) in world.overrides.entries:
        out.append(Badge.OVERRIDDEN)
    if short in world.chd_required:
        out.append(Badge.CHD_MISSING)
    if world.notes.get(short):
        out.append(Badge.HAS_NOTES)
    return tuple(out)


def _parent_of(short: str, world: WorldState) -> str:
    return world.cloneof_map.get(short, short)


def _card(machine: Machine, world: WorldState) -> GameCard:
    return GameCard(
        short_name=machine.name,
        description=machine.description,
        year=machine.year,
        manufacturer=machine.manufacturer_raw,
        publisher=machine.publisher,
        developer=machine.developer,
        badges=_badges(machine.name, world),
    )


@router.get("/api/games", response_model=GamesPage)
def list_games(
    request: Request,
    q: str | None = None,
    genre: str | None = None,
    publisher: str | None = None,
    developer: str | None = None,
    letter: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    only_contested: bool = False,
    only_overridden: bool = False,
    only_chd_missing: bool = False,
    only_bios_missing: bool = False,
    world: WorldState = Depends(get_world),
) -> GamesPage:
    winners = list(world.filter_result.winners)
    contested_parents = {g.parent for g in world.filter_result.contested_groups}

    # FP17: ``letter='#'`` selects the digits bucket (game names starting
    # with 0-9) since MAME has plenty of those (1942, 1943, 005, ...).
    # Other single-character values match case-insensitively against the
    # description's first character.
    letter_norm = (letter or "").strip().lower() or None

    def matches_letter(m: Machine) -> bool:
        if letter_norm is None:
            return True
        first = m.description[:1].lower()
        if letter_norm == "#":
            return first.isdigit()
        return first == letter_norm

    def keep(short: str) -> bool:
        m = world.machines.get(short)
        if m is None:
            return False
        if q and q.lower() not in m.description.lower() and q.lower() not in short.lower():
            return False
        if genre is not None and world.ctx.category.get(short, "") != genre:
            return False
        if publisher is not None and (m.publisher or "") != publisher:
            return False
        if developer is not None and (m.developer or "") != developer:
            return False
        if not matches_letter(m):
            return False
        if year_min is not None and (m.year is None or m.year < year_min):
            return False
        if year_max is not None and (m.year is None or m.year > year_max):
            return False
        parent = _parent_of(short, world)
        if only_contested and parent not in contested_parents:
            return False
        if only_overridden and parent not in world.overrides.entries:
            return False
        if only_chd_missing and short not in world.chd_required:
            return False
        return not (only_bios_missing and short in world.bios_chain)

    filtered = [s for s in winners if keep(s)]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = tuple(_card(world.machines[s], world) for s in filtered[start:end])
    return GamesPage(items=page_items, page=page, page_size=page_size, total=total)


@router.get("/api/library/facets", response_model=LibraryFacets)
def library_facets(world: WorldState = Depends(get_world)) -> LibraryFacets:
    """FP17: discrete facet values for FiltersSidebar dropdowns.

    Drawn from the ``winners`` set so the dropdowns only offer values
    that actually filter to non-empty results. Empty / None values are
    elided.
    """
    genres: set[str] = set()
    publishers: set[str] = set()
    developers: set[str] = set()
    letters: set[str] = set()
    for short in world.filter_result.winners:
        m = world.machines.get(short)
        if m is None:
            continue
        cat = world.ctx.category.get(short)
        if cat:
            genres.add(cat)
        if m.publisher:
            publishers.add(m.publisher)
        if m.developer:
            developers.add(m.developer)
        first = m.description[:1].lower()
        if first.isdigit():
            letters.add("#")
        elif first.isalpha():
            letters.add(first)
    return LibraryFacets(
        genres=tuple(sorted(genres)),
        publishers=tuple(sorted(publishers)),
        developers=tuple(sorted(developers)),
        letters=tuple(sorted(letters)),
    )


@router.get("/api/games/{name}", response_model=GameDetail)
def get_game(name: str, world: WorldState = Depends(get_world)) -> GameDetail:
    machine = world.machines.get(name)
    if machine is None:
        raise GameNotFoundError(f"game not found: {name!r}")
    parent = _parent_of(name, world)
    languages = world.ctx.languages.get(name, ())
    return GameDetail(
        short_name=name,
        machine=machine,
        category=world.ctx.category.get(name),
        languages=languages,
        bestgames_tier=world.ctx.bestgames_tier.get(name),
        mature=name in world.ctx.mature,
        chd_required=name in world.chd_required,
        badges=_badges(name, world),
        override=world.overrides.entries.get(parent),
        parent=parent,
    )


@router.get("/api/games/{name}/alternatives", response_model=Alternatives)
def get_alternatives(name: str, world: WorldState = Depends(get_world)) -> Alternatives:
    if name not in world.machines:
        raise GameNotFoundError(f"game not found: {name!r}")
    parent = _parent_of(name, world)
    siblings = [m for m in world.machines.values() if _parent_of(m.name, world) == parent]
    return Alternatives(items=tuple(_card(m, world) for m in siblings))


@router.get("/api/games/{name}/explanation", response_model=Explanation)
def get_explanation(name: str, world: WorldState = Depends(get_world)) -> Explanation:
    if name not in world.machines:
        raise GameNotFoundError(f"game not found: {name!r}")
    parent = _parent_of(name, world)
    candidates = [m for m in world.machines.values() if _parent_of(m.name, world) == parent]
    if len(candidates) <= 1:
        return Explanation(
            short_name=name,
            parent=parent,
            candidates=tuple(c.name for c in candidates),
            hits=(),
        )
    hits = explain_pick(candidates, parent, world.ctx, world.config.filters)
    return Explanation(
        short_name=name,
        parent=parent,
        candidates=tuple(sorted(c.name for c in candidates)),
        hits=hits,
    )


@router.get("/api/games/{name}/notes", response_model=Notes)
def get_notes(name: str, world: WorldState = Depends(get_world)) -> Notes:
    if name not in world.machines:
        raise GameNotFoundError(f"game not found: {name!r}")
    return Notes(notes=world.notes.get(name, ""))


@router.put("/api/games/{name}/notes", response_model=Notes)
def put_notes(
    name: str,
    body: NotesPutRequest,
    request: Request,
    world: WorldState = Depends(get_world),
) -> Notes:
    if name not in world.machines:
        raise GameNotFoundError(f"game not found: {name!r}")
    notes = dict(world.notes)
    if body.notes:
        notes[name] = body.notes
    else:
        notes.pop(name, None)
    write_json_atomic(world.data_dir / "notes.json", notes)
    new_world = replace_world(base=world, notes=notes)
    set_world(request, new_world)
    return Notes(notes=body.notes)


@router.get("/api/stats", response_model=Stats)
def get_stats(world: WorldState = Depends(get_world)) -> Stats:
    winners = world.filter_result.winners
    by_genre: Counter[str] = Counter()
    by_decade: Counter[str] = Counter()
    by_publisher: Counter[str] = Counter()
    by_driver_status: Counter[str] = Counter()
    total_bytes = 0
    for short in winners:
        m = world.machines.get(short)
        if m is None:
            continue
        by_genre[world.ctx.category.get(short, "")] += 1
        if m.year is not None:
            by_decade[f"{(m.year // 10) * 10}s"] += 1
        by_publisher[m.publisher or ""] += 1
        by_driver_status[m.driver_status.value if m.driver_status else "unknown"] += 1
        total_bytes += sum(r.size or 0 for r in m.roms)
    top_publishers = dict(sorted(by_publisher.items(), key=lambda x: -x[1])[:10])
    return Stats(
        by_genre=dict(by_genre),
        by_decade=dict(by_decade),
        by_publisher=top_publishers,
        by_driver_status=dict(by_driver_status),
        total_bytes=total_bytes,
    )
