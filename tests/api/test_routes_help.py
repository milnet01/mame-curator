"""R37 / R38 shape tests + L14 (help index renders) behavioral test.

Per ``docs/specs/P04.md`` § Help routes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def test_route_r37_shape_help_index_empty(client: Any) -> None:
    """R37 — empty docs/help/ returns {topics: ()}."""
    response = client.get("/api/help/index")
    assert response.status_code == 200
    body = response.json()
    assert "topics" in body


def test_route_r38_shape_help_topic_invalid_slug(client: Any) -> None:
    """R38 — slug not matching the regex returns 404 (not 500)."""
    response = client.get("/api/help/INVALID_UPPERCASE")
    assert response.status_code == 404


def test_route_r38_shape_help_topic_unknown(client: Any) -> None:
    response = client.get("/api/help/no_such_topic")
    assert response.status_code == 404
    assert response.json()["code"] == "help_topic_not_found"


def test_help_index_renders(client: Any, tmp_path: Path, monkeypatch: Any) -> None:
    """L14 — fixture docs/help/quickstart.md → R37 lists it; R38 returns rendered HTML."""
    help_dir = tmp_path / "docs" / "help"
    help_dir.mkdir(parents=True)
    (help_dir / "quickstart.md").write_text("# Quickstart\n\nWelcome to MAME Curator.\n")

    # The help dir is resolved relative to the package install; tests need to
    # monkeypatch the resolver. Implementation detail: a fixture or env var
    # such as MAME_CURATOR_HELP_DIR could expose this for tests. The
    # assertion shape matters more than the wiring detail at Step 3.
    monkeypatch.setenv("MAME_CURATOR_HELP_DIR", str(help_dir))

    index = client.get("/api/help/index")
    assert index.status_code == 200
    topics = index.json()["topics"]
    assert any(t["slug"] == "quickstart" and t["title"] == "Quickstart" for t in topics)

    rendered = client.get("/api/help/quickstart")
    assert rendered.status_code == 200
    body = rendered.json()
    assert body["slug"] == "quickstart"
    assert body["title"] == "Quickstart"
    assert "Welcome to MAME Curator" in body["html"]
