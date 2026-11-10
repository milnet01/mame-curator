"""mame-curator-1217: the languages a user can keep, and the filter applying them."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

# The real languages.ini's shape: a [Section] per language, bare short names.
_LANGUAGES_INI = """[FOLDER_SETTINGS]
RootFolderIcon mame

[ROOT_FOLDER]

[English]
brokensim
pacman
pacmanf

[French]
brokensim

[Spanish]
brokensim
pacmanf
"""


@pytest.fixture
def languages_ini(tmp_path: Path) -> Path:
    path = tmp_path / "languages.ini"
    path.write_text(_LANGUAGES_INI, encoding="utf-8")
    return path


def test_languages_lists_each_language_most_games_first(client: Any) -> None:
    """Most games first, ties by name; spelled as languages.ini spells them."""
    response = client.get("/api/languages")
    assert response.status_code == 200
    assert response.json() == {
        "languages": [
            {"name": "English", "games": 3},
            {"name": "Spanish", "games": 2},
            {"name": "French", "games": 1},
        ]
    }


def test_keep_languages_reaches_the_games_list(client: Any) -> None:
    """The server applies the saved choice: the pacman family has no French."""
    names = {g["short_name"] for g in client.get("/api/games").json()["items"]}
    assert "pacman" in names

    filters = client.get("/api/config").json()["filters"]
    client.patch("/api/config", json={"filters": {**filters, "keep_languages": ["French"]}})

    names = {g["short_name"] for g in client.get("/api/games").json()["items"]}
    assert not names & {"pacman", "pacmanf"}
