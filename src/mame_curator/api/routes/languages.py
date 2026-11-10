"""mame-curator-1217 — the languages a user can choose to keep."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends

from mame_curator.api.routes._deps import get_world
from mame_curator.api.schemas_games import LanguageChoice, LanguageChoices
from mame_curator.api.state import WorldState

router = APIRouter()


@router.get("/api/languages", response_model=LanguageChoices)
def list_languages(world: WorldState = Depends(get_world)) -> LanguageChoices:
    """Each language languages.ini names, most games first, ties by name."""
    counts = Counter(lang for langs in world.ctx.languages.values() for lang in set(langs))
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return LanguageChoices(
        languages=tuple(LanguageChoice(name=name, games=games) for name, games in ranked)
    )
