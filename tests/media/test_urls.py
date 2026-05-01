"""Tests for ``urls_for`` and ``MediaUrls``.

Per ``docs/specs/P05.md`` § Public API. Builds three libretro-thumbnails URLs
per machine: boxart, title, snap. Video is intentionally absent — design §6.3
routes video through progettoSnaps; deferred to P06+.
"""

from __future__ import annotations

import pytest

from mame_curator.parser.models import Machine

_BASE = "https://raw.githubusercontent.com/libretro-thumbnails/MAME/master"


def test_urls_for_each_kind_pacman() -> None:
    """Plain description (no escapes / quoting needed beyond hyphen) → three expected URLs."""
    from mame_curator.media import urls_for

    machine = Machine(name="pacman", description="Pac-Man")
    urls = urls_for(machine)
    assert urls.boxart == f"{_BASE}/Named_Boxarts/Pac-Man.png"
    assert urls.title == f"{_BASE}/Named_Titles/Pac-Man.png"
    assert urls.snap == f"{_BASE}/Named_Snaps/Pac-Man.png"


def test_urls_for_uses_escaped_description() -> None:
    """``Q*bert's Qubes`` → escape ``*`` to ``_`` then percent-encode the apostrophe + space."""
    from mame_curator.media import urls_for

    machine = Machine(name="qbertqub", description="Q*bert's Qubes")
    urls = urls_for(machine)
    # Escape: Q*bert's Qubes -> Q_bert's Qubes
    # Quote: apostrophe -> %27, space -> %20
    expected_path = "Q_bert%27s%20Qubes.png"
    assert urls.boxart == f"{_BASE}/Named_Boxarts/{expected_path}"
    assert urls.title == f"{_BASE}/Named_Titles/{expected_path}"
    assert urls.snap == f"{_BASE}/Named_Snaps/{expected_path}"


def test_urls_for_pipe_in_description() -> None:
    """``Foo | Bar`` → escape pipe to underscore."""
    from mame_curator.media import urls_for

    machine = Machine(name="foobar", description="Foo | Bar")
    urls = urls_for(machine)
    # "Foo | Bar" -> "Foo _ Bar" (escape) -> "Foo%20_%20Bar" (quote)
    assert urls.boxart == f"{_BASE}/Named_Boxarts/Foo%20_%20Bar.png"


def test_media_urls_is_frozen() -> None:
    """``MediaUrls`` is a frozen Pydantic model (extra='forbid')."""
    from mame_curator.media import MediaUrls

    urls = MediaUrls(boxart="x", title="y", snap="z")
    with pytest.raises((ValueError, TypeError)):
        urls.boxart = "tampered"  # type: ignore[misc, unused-ignore]


def test_media_urls_has_no_video_field() -> None:
    """Load-bearing: callers dispatching on ``kind`` MUST short-circuit on ``video``
    before calling ``urls_for``, because ``MediaUrls`` has no ``video`` attribute.
    """
    from mame_curator.media import MediaUrls

    urls = MediaUrls(boxart="x", title="y", snap="z")
    with pytest.raises(AttributeError):
        getattr(urls, "video")  # noqa: B009 — explicit lookup is the test


def test_media_urls_rejects_extra_fields() -> None:
    """Forbid extra fields per project convention."""
    from mame_curator.media import MediaUrls

    with pytest.raises(ValueError):
        MediaUrls(boxart="x", title="y", snap="z", video="oops")  # type: ignore[call-arg]
