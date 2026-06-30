"""Tests for ``MobyGamesSource`` (P10 chunk 6) — key resolution + disabled states.

Per ``docs/specs/P10.md`` § "4. MobyGames". Chunk 6 ships the *key-handling*
half of the source:

- API-key resolution: ``MOBYGAMES_API_KEY`` env var first, then a mode-0600
  ``data/secrets/mobygames.key`` dotfile (a group/other-readable file is
  rejected with a WARNING and the source stays disabled).
- Missing key → ``disabled_reason`` set at construction + exactly one WARNING.
- Runtime disable on a 401/403 from a *configured* key — the reason lives on
  the injected process-wide ``SourceDisabledFlag`` so it survives the
  per-request re-creation of source instances (``media/`` stays
  HTTP-agnostic — it never imports ``api/``).
- The lookup request carries the key in its query string, so any error /
  log message redacts it.

DEFERRED to a follow-up gated on a real MobyGames API key (no key on this
machine to capture ``tests/fixtures/mobygames_pacman.json``): the
success-path cover-URL parse + JSON-body caching. Until then ``url_for``
returns ``None`` for every machine even when a key resolves and the lookup
returns 200 — MobyGames participates in the chain (when keyed) but yields no
covers. See ``test_mobygames_source_200_does_not_populate_cover_yet`` (the
delete-point for the follow-up) and the ROADMAP follow-up bullet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx
import pytest
import respx

from tests.media.conftest import _machine, _make_unbounded_limiter

_MOBY_ENV = "MOBYGAMES_API_KEY"
_API_HOST = "api.mobygames.com"
_API_PATH = "/v1/games"


def _write_key(secrets_dir: Path, content: str = "secret-key-123", mode: int = 0o600) -> Path:
    """Create ``<secrets_dir>/mobygames.key`` with ``content`` at ``mode``."""
    secrets_dir.mkdir(parents=True, exist_ok=True)
    keyfile = secrets_dir / "mobygames.key"
    keyfile.write_text(content, encoding="utf-8")
    keyfile.chmod(mode)
    return keyfile


def test_mobygames_source_classvars() -> None:
    """ClassVars pin identity / coverage / license."""
    from mame_curator.media import MobyGamesSource

    assert MobyGamesSource.name == "mobyGames"
    assert MobyGamesSource.license_compatible is False
    assert MobyGamesSource.kinds == frozenset({"boxart"})


def test_mobygames_source_disabled_without_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No env var and no dotfile → ``disabled_reason`` set; ``url_for`` ``None``."""
    monkeypatch.delenv(_MOBY_ENV, raising=False)
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "secrets",  # absent → no dotfile
    )
    assert src.disabled_reason is not None
    assert "API key" in src.disabled_reason
    assert src.url_for(_machine(), "boxart") is None


def test_mobygames_source_reads_dotfile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A mode-0600 dotfile resolves → source enabled (``disabled_reason`` ``None``)."""
    monkeypatch.delenv(_MOBY_ENV, raising=False)
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    secrets = tmp_path / "secrets"
    _write_key(secrets, mode=0o600)
    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=secrets,
    )
    assert src.disabled_reason is None


def test_mobygames_source_env_var_takes_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``MOBYGAMES_API_KEY`` resolves even with no dotfile present."""
    monkeypatch.setenv(_MOBY_ENV, "env-key-xyz")
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "nonexistent",
    )
    assert src.disabled_reason is None


def test_mobygames_source_dotfile_wrong_mode_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A group/other-readable (0644) dotfile is rejected with a WARNING; the
    source stays disabled (an attacker-readable key file is treated as no key)."""
    monkeypatch.delenv(_MOBY_ENV, raising=False)
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    secrets = tmp_path / "secrets"
    _write_key(secrets, mode=0o644)
    with caplog.at_level(logging.WARNING, logger="mame_curator.media.sources"):
        src = MobyGamesSource(
            limiter=_make_unbounded_limiter(),
            cache_dir=tmp_path,
            disabled_flag=SourceDisabledFlag(),
            secrets_dir=secrets,
        )
    assert src.disabled_reason is not None
    assert "mode" in caplog.text.lower()


@pytest.mark.asyncio
async def test_mobygames_source_logs_warning_once_per_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Disabled-without-key path emits exactly one WARNING at construction;
    a subsequent ``prepare`` on the disabled source emits nothing (it
    short-circuits before any I/O)."""
    monkeypatch.delenv(_MOBY_ENV, raising=False)
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    with caplog.at_level(logging.WARNING, logger="mame_curator.media.sources"):
        src = MobyGamesSource(
            limiter=_make_unbounded_limiter(),
            cache_dir=tmp_path,
            disabled_flag=SourceDisabledFlag(),
            secrets_dir=tmp_path / "secrets",  # absent
        )
        assert len([r for r in caplog.records if r.levelno == logging.WARNING]) == 1
        caplog.clear()
        async with httpx.AsyncClient() as client:
            await src.prepare(_machine(), client=client)
        assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


@pytest.mark.asyncio
async def test_mobygames_source_sets_disabled_reason_on_401(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 401 from a configured key flips the process-wide flag + the source's
    own ``disabled_reason`` (key is invalid; retrying won't help)."""
    monkeypatch.setenv(_MOBY_ENV, "bad-key")
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    flag = SourceDisabledFlag()
    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=flag,
        secrets_dir=tmp_path / "none",
    )
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host=_API_HOST, path=_API_PATH).mock(return_value=httpx.Response(401))
            await src.prepare(_machine(), client=client)
    assert src.disabled_reason is not None
    assert flag.reason is not None
    assert src.url_for(_machine(), "boxart") is None


@pytest.mark.asyncio
async def test_mobygames_source_redacts_key_in_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The API key rides in the query string — it must never leak into an
    error message (which would land in logs)."""
    monkeypatch.setenv(_MOBY_ENV, "supersecret999")
    from mame_curator.media import MediaFetchError, MobyGamesSource, SourceDisabledFlag

    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "none",
    )
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host=_API_HOST, path=_API_PATH).mock(return_value=httpx.Response(500))
            with pytest.raises(MediaFetchError) as exc_info:
                await src.prepare(_machine(), client=client)
    assert "supersecret999" not in str(exc_info.value)
    assert "***" in str(exc_info.value)


@pytest.mark.asyncio
async def test_mobygames_source_rate_limit_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty bucket → ``MediaRateLimited`` before any upstream I/O.

    No respx mock — an actual HTTP call would 502 against the unmocked
    client, so passing proves we short-circuited on the limiter."""
    monkeypatch.setenv(_MOBY_ENV, "k")
    from mame_curator.media import (
        MediaRateLimited,
        MobyGamesSource,
        SourceDisabledFlag,
        TokenBucket,
    )

    bucket = TokenBucket(rate=1.0, capacity=1)
    assert bucket.acquire() is True  # drain the only token
    src = MobyGamesSource(
        limiter=bucket,
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "none",
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(MediaRateLimited):
            await src.prepare(_machine(), client=client)


@pytest.mark.asyncio
async def test_mobygames_source_429_raises_rate_limited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 429 from upstream → ``MediaRateLimited`` so the orchestrator falls
    through to the next source (not a hard disable — the key is fine)."""
    monkeypatch.setenv(_MOBY_ENV, "k")
    from mame_curator.media import MediaRateLimited, MobyGamesSource, SourceDisabledFlag

    flag = SourceDisabledFlag()
    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=flag,
        secrets_dir=tmp_path / "none",
    )
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host=_API_HOST, path=_API_PATH).mock(return_value=httpx.Response(429))
            with pytest.raises(MediaRateLimited):
                await src.prepare(_machine(), client=client)
    assert flag.reason is None  # 429 is transient — must NOT disable the source


@pytest.mark.asyncio
async def test_mobygames_source_404_no_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 404 (title not found) → no candidate, no raise, no disable."""
    monkeypatch.setenv(_MOBY_ENV, "k")
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "none",
    )
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host=_API_HOST, path=_API_PATH).mock(return_value=httpx.Response(404))
            await src.prepare(_machine(), client=client)
    assert src.disabled_reason is None
    assert src.url_for(_machine(), "boxart") is None


def test_mobygames_source_only_covers_boxart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``url_for`` returns ``None`` for non-boxart kinds (boxart-only source)."""
    monkeypatch.setenv(_MOBY_ENV, "k")
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "none",
    )
    assert src.url_for(_machine(), "title") is None
    assert src.url_for(_machine(), "snap") is None


def test_mobygames_source_constructed_disabled_when_flag_already_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A prior 401 this process (flag.reason set) keeps a freshly-constructed
    source disabled even if a key now resolves — process restart required."""
    monkeypatch.setenv(_MOBY_ENV, "good-key")
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    flag = SourceDisabledFlag(reason="already disabled from a prior 401")
    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=flag,
        secrets_dir=tmp_path / "none",
    )
    assert src.disabled_reason == "already disabled from a prior 401"


@pytest.mark.asyncio
async def test_mobygames_source_200_does_not_populate_cover_yet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DEFERRED contract (delete when the cover-parse follow-up lands): a 200
    response does NOT yet populate a cover URL — the field path is unverified
    until a real-key fixture is captured. ``url_for`` stays ``None``; a 200
    proves the key works so the source is NOT disabled."""
    monkeypatch.setenv(_MOBY_ENV, "k")
    from mame_curator.media import MobyGamesSource, SourceDisabledFlag

    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "none",
    )
    async with httpx.AsyncClient() as client:
        with respx.mock(assert_all_called=True) as mock:
            mock.get(host=_API_HOST, path=_API_PATH).mock(
                return_value=httpx.Response(200, json={"games": [{"title": "Pac-Man"}]})
            )
            await src.prepare(_machine(), client=client)
    assert src.url_for(_machine(), "boxart") is None
    assert src.disabled_reason is None


def test_mobygames_source_satisfies_media_source_protocol(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Runtime-checkable Protocol — attribute presence."""
    monkeypatch.setenv(_MOBY_ENV, "k")
    from mame_curator.media import MediaSource, MobyGamesSource, SourceDisabledFlag

    src = MobyGamesSource(
        limiter=_make_unbounded_limiter(),
        cache_dir=tmp_path,
        disabled_flag=SourceDisabledFlag(),
        secrets_dir=tmp_path / "none",
    )
    assert isinstance(src, MediaSource)
