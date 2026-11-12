"""mame-curator-1140 — both Wikipedia lookups find the game's page, not a namesake.

Per ``src/mame_curator/media/spec.md`` § "Source contracts", wikipediaImage,
"Which page". The summaries below copy the real ones' ``type`` and
``description`` (en.wikipedia.org, read 2026-11-12).
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
import respx

from mame_curator.media import WikipediaImageSource, resolve_wikipedia_extract
from mame_curator.parser.models import Machine
from tests.media.conftest import _make_unbounded_limiter


def _url(title: str) -> str:
    return f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"


def _summary(title: str, kind: str, description: str) -> httpx.Response:
    body = {
        "type": kind,
        "title": title,
        "description": description,
        "extract": f"About {title}.",
        "content_urls": {"desktop": {"page": f"https://en.wikipedia.org/wiki/{title}"}},
        "thumbnail": {"source": f"https://upload.wikimedia.org/{quote(title)}.png"},
    }
    return httpx.Response(200, text=json.dumps(body))


# Each case: the machine, what Wikipedia answers per title, the page wanted.
CASES = {
    "a game named like a year": (
        Machine(name="1942", description="1942", year=1984),
        {
            "1942": _summary("1942", "standard", "Calendar year"),
            "1942 (video game)": _summary("1942 (video game)", "standard", "1984 video game"),
        },
        "1942 (video game)",
    ),
    "a sport whose description says game": (
        Machine(name="joust", description="Joust (White/Green)", year=1982),
        {
            "Joust": _summary("Jousting", "standard", "Martial game between two horsemen"),
            "Joust (video game)": _summary("Joust (video game)", "standard", "1982 video game"),
        },
        "Joust (video game)",
    ),
    "two disambiguation pages, then the year's page": (
        Machine(name="gauntlet", description="Gauntlet (rev 14)", year=1985),
        {
            "Gauntlet": _summary(
                "Gauntlet", "disambiguation", "Topics referred to by the same term"
            ),
            "Gauntlet (video game)": _summary("Gauntlet", "disambiguation", "Topics referred to"),
            "Gauntlet (1985 video game)": _summary(
                "Gauntlet (1985 video game)", "standard", "1985 video game"
            ),
        },
        "Gauntlet (1985 video game)",
    ),
    "the plain title is already the game": (
        Machine(name="pacman", description="Pac-Man (Midway)", year=1980),
        {"Pac-Man": _summary("Pac-Man", "standard", "1980 video game")},
        "Pac-Man",
    ),
}


def _serve(mock: respx.MockRouter, answers: dict[str, httpx.Response]) -> None:
    for title, response in answers.items():
        mock.get(_url(title)).mock(return_value=response)


@pytest.mark.parametrize("case", CASES)
async def test_the_about_text_comes_from_the_games_page(tmp_path: Path, case: str) -> None:
    machine, answers, wanted = CASES[case]
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            _serve(mock, answers)
            result = await resolve_wikipedia_extract(
                machine, cache_dir=tmp_path, client=client, limiter=_make_unbounded_limiter()
            )
    assert result is not None
    assert result.title == wanted


@pytest.mark.parametrize("case", CASES)
async def test_the_box_art_comes_from_the_games_page(tmp_path: Path, case: str) -> None:
    machine, answers, wanted = CASES[case]
    source = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            _serve(mock, answers)
            await source.prepare(machine, client=client)
    assert source.url_for(machine, "boxart") == f"https://upload.wikimedia.org/{quote(wanted)}.png"


async def test_no_game_page_means_no_text_and_no_picture(tmp_path: Path) -> None:
    """Every title names something else: show nothing rather than the wrong page."""
    machine = Machine(name="asteroid", description="Asteroids", year=1979)
    answers = {
        "Asteroids": _summary("Asteroid", "standard", "Minor planet"),
        "Asteroids (video game)": httpx.Response(404),
        "Asteroids (1979 video game)": httpx.Response(404),
    }
    source = WikipediaImageSource(limiter=_make_unbounded_limiter(), cache_dir=tmp_path)
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            _serve(mock, answers)
            text = await resolve_wikipedia_extract(
                machine, cache_dir=tmp_path, client=client, limiter=_make_unbounded_limiter()
            )
            await source.prepare(machine, client=client)
    assert text is None
    assert source.url_for(machine, "boxart") is None


async def test_a_machine_with_no_year_tries_two_titles(tmp_path: Path) -> None:
    machine = Machine(name="x", description="Defender")
    answers = {
        "Defender": _summary("Defender", "disambiguation", "Topics referred to"),
        "Defender (video game)": _summary("Defender (video game)", "standard", "1981 video game"),
    }
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True, assert_all_mocked=True) as mock:
            _serve(mock, answers)
            result = await resolve_wikipedia_extract(
                machine, cache_dir=tmp_path, client=client, limiter=_make_unbounded_limiter()
            )
    assert result is not None and result.title == "Defender (video game)"
