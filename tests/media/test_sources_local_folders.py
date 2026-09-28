"""mame-curator-1126 — artwork another tool already scraped, read from disk.

Two local-folder sources, both ``file://`` like ``ProgettoSnapsSource``:

- ``EsdeSource`` reads an ES-DE ``downloaded_media/<system>`` folder, whose
  files are named after the ROM, which for MAME is the short name:
  ``covers/`` (boxart), ``titlescreens/`` (title), ``screenshots/`` (snap).
- ``RetroArchThumbnailsSource`` reads a RetroArch ``thumbnails/<playlist>``
  folder in the libretro-thumbnails layout (``Named_Boxarts`` / ``Named_Titles``
  / ``Named_Snaps``), named by the escaped description, with the short name
  as a fallback.

Each is off until its folder is set, and never returns a path outside it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.media.conftest import _machine

PNG = b"\x89PNG\r\n\x1a\nfake"


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG)
    return path


# --- ES-DE --------------------------------------------------------------------


def test_esde_names_and_kinds() -> None:
    from mame_curator.media import EsdeSource

    assert EsdeSource.name == "esde"
    assert EsdeSource.kinds == frozenset({"boxart", "title", "snap"})


@pytest.mark.parametrize(
    ("kind", "folder"),
    [("boxart", "covers"), ("title", "titlescreens"), ("snap", "screenshots")],
)
def test_esde_maps_each_kind_to_its_folder(tmp_path: Path, kind: str, folder: str) -> None:
    from mame_curator.media import EsdeSource

    art = _touch(tmp_path / folder / "pacman.png")
    url = EsdeSource(media_dir=tmp_path).url_for(_machine(), kind)  # type: ignore[arg-type]
    assert url == art.resolve().as_uri()


def test_esde_takes_a_jpg_when_there_is_no_png(tmp_path: Path) -> None:
    from mame_curator.media import EsdeSource

    art = _touch(tmp_path / "covers" / "pacman.jpg")
    assert EsdeSource(media_dir=tmp_path).url_for(_machine(), "boxart") == art.resolve().as_uri()


def test_esde_misses_return_none(tmp_path: Path) -> None:
    from mame_curator.media import EsdeSource

    _touch(tmp_path / "covers" / "galaga.png")
    assert EsdeSource(media_dir=tmp_path).url_for(_machine(), "boxart") is None


@pytest.mark.parametrize("media_dir", [None, "missing"])
def test_esde_is_disabled_until_a_real_folder_is_set(tmp_path: Path, media_dir: str | None) -> None:
    from mame_curator.media import EsdeSource

    src = EsdeSource(media_dir=None if media_dir is None else tmp_path / media_dir)
    assert src.disabled_reason is not None
    assert "ES-DE" in src.disabled_reason


def test_esde_never_leaves_its_folder(tmp_path: Path) -> None:
    """A short name carrying ``..`` must not reach a file outside the folder."""
    from mame_curator.media import EsdeSource

    root = tmp_path / "media"
    (root / "covers").mkdir(parents=True)
    _touch(tmp_path / "secret.png")
    hostile = _machine(name="../../secret")
    assert EsdeSource(media_dir=root).url_for(hostile, "boxart") is None


# --- RetroArch thumbnails --------------------------------------------------------


def test_retroarch_names_and_kinds() -> None:
    from mame_curator.media import RetroArchThumbnailsSource

    assert RetroArchThumbnailsSource.name == "retroarchThumbnails"
    assert RetroArchThumbnailsSource.kinds == frozenset({"boxart", "title", "snap"})


def test_retroarch_matches_the_escaped_description(tmp_path: Path) -> None:
    from mame_curator.media import RetroArchThumbnailsSource

    machine = _machine(name="1943", description="1943: The Battle of Midway (Euro)")
    art = _touch(tmp_path / "Named_Boxarts" / "1943_ The Battle of Midway (Euro).png")
    url = RetroArchThumbnailsSource(thumbnails_dir=tmp_path).url_for(machine, "boxart")
    assert url == art.resolve().as_uri()


def test_retroarch_falls_back_to_the_short_name(tmp_path: Path) -> None:
    from mame_curator.media import RetroArchThumbnailsSource

    art = _touch(tmp_path / "Named_Snaps" / "pacman.png")
    src = RetroArchThumbnailsSource(thumbnails_dir=tmp_path)
    assert src.url_for(_machine(), "snap") == art.resolve().as_uri()


def test_retroarch_is_disabled_until_a_real_folder_is_set() -> None:
    from mame_curator.media import RetroArchThumbnailsSource

    src = RetroArchThumbnailsSource(thumbnails_dir=None)
    assert src.disabled_reason is not None
    assert "RetroArch" in src.disabled_reason


# --- resolve_image serves them, and still refuses a network source's file:// ---


@pytest.mark.asyncio
async def test_resolve_serves_a_local_folder_hit(tmp_path: Path) -> None:
    import httpx

    from mame_curator.media import EsdeSource, MediaSourceRegistry
    from mame_curator.media.resolve import resolve_image

    art = _touch(tmp_path / "media" / "covers" / "pacman.png")
    registry = MediaSourceRegistry(("esde",), {"esde": EsdeSource(media_dir=tmp_path / "media")})
    async with httpx.AsyncClient() as client:
        got = await resolve_image(
            _machine(), "boxart", registry=registry, cache_dir=tmp_path, client=client
        )
    assert got == art.resolve()
