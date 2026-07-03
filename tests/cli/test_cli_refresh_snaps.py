"""``mame-curator refresh-snaps`` dest-resolution tests (mame-curator-1081).

When ``--dest`` is omitted, the downloader binds to ``media.snaps_dir`` from
``--config`` so it can't diverge from the folder the progettoSnaps media
source reads. ``--dest`` still wins when given; an absent config falls back to
the ``MediaConfig`` default; a broken config fails loudly (the user can pass
``--dest`` to bypass it).
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from mame_curator.cli import build_parser


def _write_config(path: Path, *, snaps_dir: str | None) -> None:
    """Write a minimal-but-valid config.yaml (only the four required paths)."""
    media = f"\nmedia:\n  snaps_dir: {snaps_dir}\n" if snaps_dir is not None else ""
    path.write_text(
        "paths:\n"
        "  source_roms: /x/roms\n"
        "  source_dat: /x/dat.xml\n"
        "  dest_roms: /x/dest\n"
        "  retroarch_playlist: /x/mame.lpl\n" + media,
        encoding="utf-8",
    )


@pytest.fixture
def captured_dest(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stub ``updates.refresh_snaps`` to capture the ``dest_dir`` it's handed."""
    captured: dict[str, Any] = {}

    async def _fake_refresh_snaps(*, dest_dir: Path, client: Any, **_: Any) -> Any:
        captured["dest_dir"] = dest_dir
        return SimpleNamespace(
            error=None, downloaded=False, pack_url="http://x", files_extracted=0, files_skipped=0
        )

    monkeypatch.setattr("mame_curator.updates.refresh_snaps", _fake_refresh_snaps)
    return captured


def _run(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    rc: int = args.func(args)
    return rc


def test_dest_defaults_to_config_snaps_dir(tmp_path: Path, captured_dest: dict[str, Any]) -> None:
    """Bare ``refresh-snaps`` uses ``media.snaps_dir`` from ``--config``."""
    cfg = tmp_path / "config.yaml"
    _write_config(cfg, snaps_dir="/packs/custom")
    assert _run(["refresh-snaps", "--config", str(cfg)]) == 0
    assert captured_dest["dest_dir"] == Path("/packs/custom")


def test_explicit_dest_overrides_config(tmp_path: Path, captured_dest: dict[str, Any]) -> None:
    """``--dest`` wins over ``media.snaps_dir`` when both are present."""
    cfg = tmp_path / "config.yaml"
    _write_config(cfg, snaps_dir="/packs/custom")
    assert _run(["refresh-snaps", "--dest", "/explicit", "--config", str(cfg)]) == 0
    assert captured_dest["dest_dir"] == Path("/explicit")


def test_missing_config_falls_back_to_default(
    tmp_path: Path, captured_dest: dict[str, Any]
) -> None:
    """No config file → the MediaConfig default (./data/snaps)."""
    missing = tmp_path / "nope.yaml"
    assert _run(["refresh-snaps", "--config", str(missing)]) == 0
    assert captured_dest["dest_dir"] == Path("./data/snaps")


def test_broken_config_fails_loudly(tmp_path: Path, captured_dest: dict[str, Any]) -> None:
    """A present-but-invalid config → non-zero exit, no download attempted."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text("paths: {}\n", encoding="utf-8")  # missing required path fields
    assert _run(["refresh-snaps", "--config", str(cfg)]) == 1
    assert "dest_dir" not in captured_dest  # never reached the download
