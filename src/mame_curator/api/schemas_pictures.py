"""mame-curator-1146 — wire models for the picture-choice routes.

Per ``docs/specs/mame-curator-1146-picture-choice.md`` §4.4. Re-exported from
``mame_curator.api.schemas``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from mame_curator.api.pictures import PictureChoice
from mame_curator.media import Kind


class PictureCandidate(BaseModel):
    """One picture a source holds for the game; ``in_use`` marks the one shown."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    source: str
    kind: Kind
    in_use: bool


class PictureCandidates(BaseModel):
    """The picture guide's list, in-use picture first.

    ``chosen_found`` is False only when a stored choice did not resolve now.
    ``not_asked`` names the rate-limited sources held back; ``not_answered``
    the sources that raised.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    chosen: PictureChoice | None
    chosen_found: bool
    candidates: tuple[PictureCandidate, ...]
    not_asked: tuple[str, ...]
    not_answered: tuple[str, ...]


class PictureChoiceView(BaseModel):
    """A game's stored choice after a save or clear."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    chosen: PictureChoice | None
