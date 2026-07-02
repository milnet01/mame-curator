"""P10 chunk 9 — readiness surface + secret write route tests.

Per ``docs/specs/P10.md`` § "Readiness surface" + § "Readiness-surface tests".
``GET /api/media/sources`` reports every known source's real constructed state
(surface-only, no upstream hits); ``PUT /api/media/sources/{name}/secret``
atomically writes the MobyGames key dotfile at mode 0600.

All tests are isolated by the ``_isolate_secrets`` autouse fixture: no
``MOBYGAMES_API_KEY`` env, CWD chdir'd to a tmpdir so the CWD-relative
``data/secrets`` + ``data/snaps`` land under tmp (never the repo), and the
process-wide keyless-WARNING dedup guard reset.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

from mame_curator.media import mobygames_key_path

_ALL_FIVE = ["libretro", "progettoSnaps", "arcadeDB", "wikipediaImage", "mobyGames"]
_WINDOWS = sys.platform == "win32"
_all_configured = pytest.mark.parametrize("configured_media_sources", [_ALL_FIVE], indirect=True)


@pytest.fixture(autouse=True)
def _isolate_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate every chunk-9 test from the real environment + repo tree."""
    monkeypatch.delenv("MOBYGAMES_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    from mame_curator.media import mobygames

    mobygames._reset_missing_key_warn_dedup()


def _rows_by_name(response: Any) -> dict[str, Any]:
    return {r["name"]: r for r in response.json()["sources"]}


# --- readiness: GET /api/media/sources -------------------------------------


@_all_configured
def test_media_sources_endpoint_returns_all_known_sources(client: Any) -> None:
    """All five sources are returned, in configured (media.sources) order."""
    response = client.get("/api/media/sources")
    assert response.status_code == 200
    names = [r["name"] for r in response.json()["sources"]]
    assert names == _ALL_FIVE  # configured order


@_all_configured
def test_media_sources_endpoint_marks_mobygames_disabled_without_key(client: Any) -> None:
    """No key → mobyGames disabled, reason populated, needs_config, in_chain."""
    moby = _rows_by_name(client.get("/api/media/sources"))["mobyGames"]
    assert moby["enabled"] is False
    assert moby["disabled_reason"]
    assert moby["needs_config"] is True
    assert moby["in_chain"] is True


@_all_configured
def test_media_sources_endpoint_marks_never_disabling_sources_enabled(client: Any) -> None:
    """libretro / arcadeDB / wikipediaImage never self-disable."""
    rows = _rows_by_name(client.get("/api/media/sources"))
    for name in ("libretro", "arcadeDB", "wikipediaImage"):
        assert rows[name]["enabled"] is True, name
        assert rows[name]["disabled_reason"] is None, name
        assert rows[name]["needs_config"] is False, name


@_all_configured
def test_media_sources_endpoint_marks_progettosnaps_disabled_without_pack(
    client: Any, tmp_path: Path
) -> None:
    """progettoSnaps self-disables with no pack, and enables once one exists."""
    ps = _rows_by_name(client.get("/api/media/sources"))["progettoSnaps"]
    assert ps["enabled"] is False  # no pack on disk (default)
    assert ps["disabled_reason"]
    assert ps["needs_config"] is False  # its fix is a pack download, not a value

    # Now drop a pack file (CWD is tmp_path; the source reads data/snaps/snap).
    snap_dir = tmp_path / "data" / "snaps" / "snap"
    snap_dir.mkdir(parents=True)
    (snap_dir / "pacman.png").write_bytes(b"\x89PNG")
    ps2 = _rows_by_name(client.get("/api/media/sources"))["progettoSnaps"]
    assert ps2["enabled"] is True
    assert ps2["disabled_reason"] is None


def test_media_sources_endpoint_marks_in_chain_false_for_unconfigured(client: Any) -> None:
    """Default config = ("libretro",): libretro in_chain, the rest listed but not."""
    rows = _rows_by_name(client.get("/api/media/sources"))
    assert set(rows) == set(_ALL_FIVE)  # all five still listed
    assert rows["libretro"]["in_chain"] is True
    for name in ("progettoSnaps", "arcadeDB", "wikipediaImage", "mobyGames"):
        assert rows[name]["in_chain"] is False, name


# --- secret write: PUT /api/media/sources/{name}/secret --------------------


def test_put_source_secret_writes_dotfile(client: Any) -> None:
    """Valid PUT → 204; the dotfile holds the secret verbatim (no newline)."""
    response = client.put("/api/media/sources/mobyGames/secret", json={"secret": "abc123"})
    assert response.status_code == 204
    keyfile = mobygames_key_path()
    assert keyfile.read_text(encoding="utf-8") == "abc123"


def test_put_source_secret_strips_surrounding_whitespace(client: Any) -> None:
    """FP33 L4: a pasted key with a trailing newline / surrounding spaces is
    stripped before the 0600 write — a stray byte would break the upstream
    Authorization header."""
    response = client.put("/api/media/sources/mobyGames/secret", json={"secret": "  abc123\n"})
    assert response.status_code == 204
    assert mobygames_key_path().read_text(encoding="utf-8") == "abc123"


def test_put_source_secret_whitespace_only_returns_422(client: Any) -> None:
    """FP33 L4: a whitespace-only secret strips to empty → 422 (min_length=1);
    no dotfile written."""
    response = client.put("/api/media/sources/mobyGames/secret", json={"secret": "   "})
    assert response.status_code == 422
    assert not mobygames_key_path().exists()


@pytest.mark.skipif(_WINDOWS, reason="POSIX mode bits don't apply on Windows")
def test_put_source_secret_writes_dotfile_with_0600(client: Any) -> None:
    """The written key dotfile is owner-only (mode 0600) on POSIX."""
    client.put("/api/media/sources/mobyGames/secret", json={"secret": "abc123"})
    assert mobygames_key_path().stat().st_mode & 0o777 == 0o600


def test_put_source_secret_atomic_write_last_wins_no_tmp(client: Any) -> None:
    """Two sequential writes → the last secret wins atomically, no .tmp left."""
    client.put("/api/media/sources/mobyGames/secret", json={"secret": "first"})
    client.put("/api/media/sources/mobyGames/secret", json={"secret": "second"})
    keyfile = mobygames_key_path()
    assert keyfile.read_text(encoding="utf-8") == "second"
    leftover = list(keyfile.parent.glob("*.tmp"))
    assert leftover == [], f"atomic write left tmp files: {leftover}"


def test_put_source_secret_unknown_name_returns_422(client: Any) -> None:
    """An unknown source name → 422 media_source_unknown; no dotfile written."""
    response = client.put("/api/media/sources/notarealsource/secret", json={"secret": "x"})
    assert response.status_code == 422
    assert response.json()["code"] == "media_source_unknown"
    assert not mobygames_key_path().exists()


def test_put_source_secret_empty_body_returns_422(client: Any) -> None:
    """An empty secret → 422 (SourceSecret min_length=1); no dotfile written."""
    response = client.put("/api/media/sources/mobyGames/secret", json={"secret": ""})
    assert response.status_code == 422
    assert not mobygames_key_path().exists()


def test_put_source_secret_does_not_log_value(
    client: Any, caplog: pytest.LogCaptureFixture
) -> None:
    """The secret value never appears in any log line (only the source name)."""
    key_value = "super-secret-key-value-9f3a"
    with caplog.at_level("INFO"):
        client.put("/api/media/sources/mobyGames/secret", json={"secret": key_value})
    assert key_value not in caplog.text
    assert "mobyGames" in caplog.text  # the name IS logged


@_all_configured
def test_put_source_secret_flips_disabled_reason_on_next_construct(client: Any) -> None:
    """Pre: mobyGames disabled (no key). PUT a key → next GET shows it enabled,
    with no process restart or app-state reset."""
    before = _rows_by_name(client.get("/api/media/sources"))["mobyGames"]
    assert before["enabled"] is False
    client.put("/api/media/sources/mobyGames/secret", json={"secret": "valid-looking-key"})
    after = _rows_by_name(client.get("/api/media/sources"))["mobyGames"]
    assert after["enabled"] is True
    assert after["disabled_reason"] is None


def test_put_source_secret_does_not_round_trip_through_config_export(client: Any) -> None:
    """The secret + its dotfile path stay out of GET /api/config/export."""
    key_value = "export-leak-canary-7c21"
    client.put("/api/media/sources/mobyGames/secret", json={"secret": key_value})
    export = client.post("/api/config/export")
    assert export.status_code == 200
    assert key_value not in export.text
    assert "mobygames.key" not in export.text


def test_put_source_secret_loopback_only(client: Any) -> None:
    """Soft regression guard: the server still binds loopback by default, which
    is the threat model the secret route trusts (§ Open verification items #5)."""
    from mame_curator.api.schemas import ServerConfig

    assert ServerConfig().host == "127.0.0.1"
