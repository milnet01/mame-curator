"""Tests for ``mame_curator.updates.ini.refresh_inis`` (P07 § B)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from mame_curator.updates import refresh_inis


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ``asyncio.sleep`` so retry-path tests don't actually wait."""

    async def _instant(*_a: Any, **_kw: Any) -> None:
        return None

    monkeypatch.setattr("mame_curator.downloads.asyncio.sleep", _instant)


@pytest.mark.asyncio
async def test_refresh_inis_writes_all_files_and_returns_report(
    tmp_path: Path,
) -> None:
    """All sources succeed → report.updated lists each filename; failed is empty."""
    sources = {
        "catver.ini": "https://example.com/catver.ini",
        "languages.ini": "https://example.com/languages.ini",
    }
    bodies = {url: f"# {name}".encode() for name, url in sources.items()}

    with respx.mock(assert_all_called=True) as mock:
        for url, body in bodies.items():
            mock.get(url).mock(return_value=httpx.Response(200, content=body))
        async with httpx.AsyncClient() as client:
            report = await refresh_inis(dest_dir=tmp_path, sources=sources, client=client)

    assert report.all_succeeded
    assert set(report.updated) == set(sources.keys())
    assert (tmp_path / "catver.ini").read_bytes() == bodies["https://example.com/catver.ini"]


@pytest.mark.asyncio
async def test_refresh_inis_collects_failures(tmp_path: Path) -> None:
    """One source 503s → that name in report.failed with its URL; others succeed."""
    sources = {
        "good.ini": "https://example.com/good.ini",
        "bad.ini": "https://example.com/bad.ini",
    }

    with respx.mock(assert_all_called=True) as mock:
        mock.get(sources["good.ini"]).mock(return_value=httpx.Response(200, content=b"# good"))
        mock.get(sources["bad.ini"]).mock(return_value=httpx.Response(503))
        async with httpx.AsyncClient() as client:
            report = await refresh_inis(dest_dir=tmp_path, sources=sources, client=client)

    assert not report.all_succeeded
    assert report.updated == ["good.ini"]
    assert report.failed == [("bad.ini", sources["bad.ini"])]


@pytest.mark.asyncio
async def test_refresh_inis_creates_dest_dir(tmp_path: Path) -> None:
    """Dest directory is created if missing."""
    dest = tmp_path / "nested" / "dir"
    sources = {"x.ini": "https://example.com/x.ini"}

    with respx.mock(assert_all_called=True) as mock:
        mock.get(sources["x.ini"]).mock(return_value=httpx.Response(200, content=b"x"))
        async with httpx.AsyncClient() as client:
            report = await refresh_inis(dest_dir=dest, sources=sources, client=client)

    assert dest.is_dir()
    assert report.all_succeeded


def test_default_sources_covers_five_mandatory_inis() -> None:
    """Sanity: ``INI_DEFAULT_SOURCES`` ships URLs for the five INIs the
    project parses (v1.0.1: ``mature.ini`` was added once we discovered
    it lives at ``catver.ini/mature.ini`` in AntoPISA's repo)."""
    from mame_curator.updates import INI_DEFAULT_SOURCES

    assert set(INI_DEFAULT_SOURCES) == {
        "catver.ini",
        "languages.ini",
        "bestgames.ini",
        "series.ini",
        "mature.ini",
    }
    for url in INI_DEFAULT_SOURCES.values():
        assert url.startswith("https://")
        # v1.0.1 fix: AntoPISA's repo uses per-file subdirectories
        # (catver.ini/catver.ini), not flat files — guard against a
        # regression that drops the subdirectory pattern.
        assert "/AntoPISA/MAME_SupportFiles/" in url
        assert url.count("/") >= 7  # baseline + repo + main + subdir + file
