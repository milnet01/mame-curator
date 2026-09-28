"""mame-curator-1010 §4.6 — an INI refresh previews before it applies.

The INI fixtures are copied under ``tmp_path`` (these fixtures override the
session-scoped ones in conftest), because apply writes over the configured
files. The download source is an ``httpx.MockTransport``.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.api.conftest import PARSER_FIXTURES


@pytest.fixture(autouse=True)
def _no_sleep(no_sleep: None) -> None:
    """A failed download retries with back-off; do not actually sleep."""


INIS = ("catver.ini", "languages.ini", "bestgames.ini", "mature.ini", "series.ini")


def _copy(tmp_path: Path, name: str) -> Path:
    dest = tmp_path / "inis" / name
    dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(PARSER_FIXTURES / name, dest)
    return dest


@pytest.fixture
def catver_ini(tmp_path: Path) -> Path:
    return _copy(tmp_path, "catver.ini")


@pytest.fixture
def languages_ini(tmp_path: Path) -> Path:
    return _copy(tmp_path, "languages.ini")


@pytest.fixture
def bestgames_ini(tmp_path: Path) -> Path:
    return _copy(tmp_path, "bestgames.ini")


@pytest.fixture
def mature_ini(tmp_path: Path) -> Path:
    return _copy(tmp_path, "mature.ini")


@pytest.fixture
def series_ini(tmp_path: Path) -> Path:
    return _copy(tmp_path, "series.ini")


@pytest.fixture
def winner(client: Any) -> str:
    """A current winner, with mature games now dropped by the filter."""
    response = client.patch("/api/config", json={"filters": {"drop_mature": True}})
    assert response.status_code == 200, response.text
    return str(sorted(client.app.state.world.filter_result.winners)[0])


@pytest.fixture
def upstream(client: Any, winner: str) -> dict[str, bytes]:
    """Serves the live files unchanged, except a mature.ini flagging ``winner``."""
    files = {name: (PARSER_FIXTURES / name).read_bytes() for name in INIS}
    files["mature.ini"] += f"{winner}=\n".encode()
    client.app.state.ini_sources = {name: f"https://ini.test/{name}" for name in INIS}
    client.app.state.updates_client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: (
                httpx.Response(200, content=files[name])
                if (name := r.url.path.lstrip("/")) in files
                else httpx.Response(404)
            )
        )
    )
    return files


def test_preview_changes_nothing(
    client: Any, winner: str, upstream: dict[str, bytes], mature_ini: Path
) -> None:
    """INV-11."""
    live_before = mature_ini.read_bytes()
    winners_before = client.app.state.world.filter_result.winners

    response = client.post("/api/updates/ini/preview")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["changed_files"] == ["mature.ini"]
    assert body["winners_removed"] == [winner]
    assert body["failed"] == []
    assert mature_ini.read_bytes() == live_before
    assert client.app.state.world.filter_result.winners == winners_before


def test_apply_needs_preview_and_matches_it(
    client: Any, winner: str, upstream: dict[str, bytes], mature_ini: Path
) -> None:
    """INV-12."""
    refused = client.post("/api/updates/ini/apply")
    assert refused.status_code == 409
    assert refused.json()["code"] == "ini_preview_missing"

    preview = client.post("/api/updates/ini/preview").json()
    applied = client.post("/api/updates/ini/apply")

    assert applied.status_code == 200, applied.text
    world = client.app.state.world
    assert winner not in world.filter_result.winners
    assert applied.json() == preview
    assert mature_ini.read_bytes() == upstream["mature.ini"]
    snapshots = list((world.data_dir / "ini-snapshots").iterdir())
    assert len(snapshots) == 1
    assert "ini_refreshed" in (world.data_dir / "activity.jsonl").read_text()
    # The preview is spent: a second apply needs a new one.
    assert client.post("/api/updates/ini/apply").json()["code"] == "ini_preview_missing"


def test_a_failed_download_is_reported_and_left_out(
    client: Any, winner: str, upstream: dict[str, bytes]
) -> None:
    del upstream["series.ini"]
    body = client.post("/api/updates/ini/preview").json()
    assert [name for name, _ in body["failed"]] == ["series.ini"]
    assert "series.ini" not in body["changed_files"]


def test_an_unset_path_lands_in_data_ini_and_the_config_gains_it(
    client: Any, winner: str, upstream: dict[str, bytes]
) -> None:
    response = client.patch("/api/config", json={"paths": {"mature": None}})
    assert response.status_code == 200, response.text
    assert client.app.state.world.config.paths.mature is None

    assert "mature.ini" in client.post("/api/updates/ini/preview").json()["changed_files"]
    assert client.post("/api/updates/ini/apply").status_code == 200

    world = client.app.state.world
    landed = world.data_dir / "ini" / "mature.ini"
    assert landed.read_bytes() == upstream["mature.ini"]
    assert world.config.paths.mature == landed
    assert str(landed) in world.config_path.read_text(encoding="utf-8")


class _Held:
    """Stands in for an INI lock another request is holding."""

    def locked(self) -> bool:
        return True


def test_preview_and_apply_refuse_while_another_runs(
    client: Any, winner: str, upstream: dict[str, bytes]
) -> None:
    """review-code 2026-09-28 L2-1 — preview rewrites the staging folder
    apply reads, so neither may run while the other does."""
    client.post("/api/updates/ini/preview")
    client.app.state.ini_lock = _Held()
    for path in ("/api/updates/ini/preview", "/api/updates/ini/apply"):
        response = client.post(path)
        assert response.status_code == 409, path
        assert response.json()["code"] == "update_in_progress"


def test_a_failed_preview_spends_the_old_one(
    client: Any, winner: str, upstream: dict[str, bytes], monkeypatch: pytest.MonkeyPatch
) -> None:
    """L2-4 — a failed preview deletes its files, so apply must not use its
    predecessor's record of them."""
    import mame_curator.api.routes.updates_ini as ini_routes
    from mame_curator.parser import INIError

    assert client.post("/api/updates/ini/preview").status_code == 200

    def unreadable(**_kw: Any) -> None:
        raise INIError("bad file")

    monkeypatch.setattr(ini_routes, "ini_context_fields", unreadable)
    assert client.post("/api/updates/ini/preview").json()["code"] == "ini_parse_failed"
    assert client.post("/api/updates/ini/apply").json()["code"] == "ini_preview_missing"


def test_a_failed_write_puts_back_what_it_replaced(
    client: Any,
    winner: str,
    upstream: dict[str, bytes],
    catver_ini: Path,
    mature_ini: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """L2-2 — the INIs are all replaced or none are."""
    import mame_curator.api.routes.updates_ini as ini_routes

    upstream["catver.ini"] += b"\n"
    catver_before, mature_before = catver_ini.read_bytes(), mature_ini.read_bytes()
    assert client.post("/api/updates/ini/preview").json()["changed_files"] == [
        "catver.ini",
        "mature.ini",
    ]
    from mame_curator._atomic import atomic_write_bytes as real

    calls: list[Path] = []

    def second_write_fails(path: Path, data: bytes) -> None:
        calls.append(path)
        if len(calls) == 2:
            raise OSError(28, "No space left on device")
        real(path, data)

    monkeypatch.setattr(ini_routes, "atomic_write_bytes", second_write_fails)
    with pytest.raises(OSError):
        client.post("/api/updates/ini/apply")
    monkeypatch.setattr(ini_routes, "atomic_write_bytes", real)
    assert catver_ini.read_bytes() == catver_before
    assert mature_ini.read_bytes() == mature_before


def test_config_yaml_is_snapshotted_before_apply_rewrites_it(
    client: Any, winner: str, upstream: dict[str, bytes]
) -> None:
    """L2-3 — api/spec.md: a snapshot precedes every config mutation."""
    assert client.patch("/api/config", json={"paths": {"mature": None}}).status_code == 200
    world = client.app.state.world
    before = world.config_path.read_bytes()
    snaps = world.data_dir / "snapshots"
    had = set(snaps.iterdir()) if snaps.exists() else set()
    client.post("/api/updates/ini/preview")
    assert client.post("/api/updates/ini/apply").status_code == 200
    new = set(snaps.iterdir()) - had
    assert any((s / "config.yaml").read_bytes() == before for s in new)
