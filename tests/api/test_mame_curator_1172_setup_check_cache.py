"""mame-curator-1172 — ``/api/setup/check`` must not re-read an unchanged game list.

Each check used to run ``parse_dat`` over the whole DAT, so finishing the
setup wizard read the list twice: once for the save, once for the check.
These tests count the probe's parse calls rather than timing them.
"""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from mame_curator.parser import parse_dat


def _count_probe_parses(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    calls: list[Path] = []

    def counting_parse_dat(path: Path) -> Any:
        calls.append(path)
        return parse_dat(path)

    monkeypatch.setattr("mame_curator.api.routes.stubs.parse_dat", counting_parse_dat)
    return calls


def _dat_parses(client: Any) -> Any:
    reply = client.get("/api/setup/check")
    assert reply.status_code == 200, reply.text
    return reply.json()["paths"]["source_dat"]["dat_parses"]


def _restart_with_dat(config_file: Path, dat: Path, start: Callable[[Path], Any]) -> Any:
    text = config_file.read_text(encoding="utf-8")
    patched, count = re.subn(r"(?m)^  source_dat: .*$", lambda _m: f"  source_dat: {dat}", text)
    assert count == 1
    config_file.write_text(patched, encoding="utf-8")
    return start(config_file)


def test_check_does_not_reread_the_dat_the_world_loaded(
    client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = _count_probe_parses(monkeypatch)
    assert _dat_parses(client) is True
    # A save swaps the world; the new one still knows the DAT it holds.
    assert client.patch("/api/config", json={"ui": {"theme": "light"}}).status_code == 200
    assert _dat_parses(client) is True
    assert calls == []


def test_check_rereads_the_dat_once_it_changes(
    config_file: Path,
    tmp_path: Path,
    mini_dat: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Correctness: a DAT that changed on disk since it was read is read again."""
    from fastapi.testclient import TestClient

    from mame_curator.api import create_app

    dat = tmp_path / "copy.dat.xml"
    shutil.copyfile(mini_dat, dat)
    _restart_with_dat(config_file, dat, lambda p: None)
    calls = _count_probe_parses(monkeypatch)
    with TestClient(create_app(config_file)) as client:
        assert _dat_parses(client) is True
        assert calls == []
        dat.write_text("<datafile><machine name='x'", encoding="utf-8")
        assert _dat_parses(client) is False
        assert _dat_parses(client) is False
        assert len(calls) == 1, "an unchanged bad DAT is not re-read either"
        shutil.copyfile(mini_dat, dat)
        stamp = dat.stat()
        os.utime(dat, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 5_000_000_000))
        assert _dat_parses(client) is True
        assert len(calls) == 2


def test_finishing_the_wizard_reads_the_dat_once(
    config_file: Path,
    tmp_path: Path,
    mini_dat: Path,
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The save's read is the check's: the check after it parses nothing."""
    from fastapi.testclient import TestClient

    from mame_curator.api import create_app

    _restart_with_dat(config_file, tmp_path / "does-not-exist.xml", lambda p: None)
    calls = _count_probe_parses(monkeypatch)
    with TestClient(create_app(config_file)) as client:
        saved = client.patch("/api/config", json={"paths": {"source_dat": str(mini_dat)}})
        assert saved.status_code == 200, saved.text
        assert saved.json()["setup_ended"] is True
        assert _dat_parses(client) is True
        assert calls == []


def test_a_failed_read_is_not_kept(
    client: Any, mini_dat: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An OSError (no scratch space) may pass next time, so the next check reads again."""
    other = tmp_path / "other.dat.xml"
    other.write_bytes(mini_dat.read_bytes())
    assert (
        client.patch("/api/config", json={"paths": {"source_dat": str(other)}}).status_code == 200
    )
    failures = [OSError("no space left on device")]

    def flaky_parse_dat(path: Path) -> Any:
        if failures:
            raise failures.pop()
        return parse_dat(path)

    monkeypatch.setattr("mame_curator.api.routes.stubs.parse_dat", flaky_parse_dat)
    assert _dat_parses(client) is False
    assert _dat_parses(client) is True
