"""R37 + R38 — help index + topic.

The help directory defaults to the package install's ``docs/help/`` but can
be overridden via the ``MAME_CURATOR_HELP_DIR`` environment variable for tests.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter

from mame_curator.api.errors import HelpTopicNotFoundError
from mame_curator.api.schemas import HelpContent, HelpIndex, HelpTopic

router = APIRouter()

_SLUG_RE = re.compile(r"^[a-z0-9_-]{1,64}$")


def _help_dir() -> Path:
    override = os.environ.get("MAME_CURATOR_HELP_DIR")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3].parent / "docs" / "help"


def _read_title(md_path: Path) -> str:
    try:
        for line in md_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
    except OSError:
        return md_path.stem
    return md_path.stem


@router.get("/api/help/index", response_model=HelpIndex)
def help_index() -> HelpIndex:
    base = _help_dir()
    if not base.exists() or not base.is_dir():
        return HelpIndex(topics=())
    topics = tuple(HelpTopic(slug=p.stem, title=_read_title(p)) for p in sorted(base.glob("*.md")))
    return HelpIndex(topics=topics)


@router.get("/api/help/{topic}", response_model=HelpContent)
def help_topic(topic: str) -> HelpContent:
    if not _SLUG_RE.match(topic):
        raise HelpTopicNotFoundError(f"help topic not found: {topic!r}")
    base = _help_dir().resolve()
    candidate = (base / f"{topic}.md").resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise HelpTopicNotFoundError(f"help topic not found: {topic!r}") from exc
    if not candidate.exists():
        raise HelpTopicNotFoundError(f"help topic not found: {topic!r}")
    text = candidate.read_text(encoding="utf-8")
    title = _read_title(candidate)
    html = _render_markdown(text)
    return HelpContent(slug=topic, title=title, html=html)


def _render_markdown(text: str) -> str:
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        return _fallback_render(text)
    md = MarkdownIt("commonmark", {"html": False})
    rendered: str = md.render(text)
    return rendered


def _fallback_render(text: str) -> str:
    """Minimal HTML rendering when markdown-it is unavailable."""
    parts: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            parts.append(f"<h1>{stripped[2:].strip()}</h1>")
        elif stripped:
            parts.append(f"<p>{stripped}</p>")
    return "\n".join(parts)
