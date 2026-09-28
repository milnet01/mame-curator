"""Markdown to HTML, shared by the Help pages and the release notes.

Moved from ``api/routes/help.py`` by mame-curator-1010 §4.5. Raw HTML in the
source is not passed through (``"html": False``), so a release body cannot
inject markup into the page.
"""

from __future__ import annotations

from html import escape


def render_markdown(text: str) -> str:
    """Render CommonMark to HTML with raw HTML disabled."""
    try:
        from markdown_it import MarkdownIt
    except ImportError:
        return _fallback_render(text)
    md = MarkdownIt("commonmark", {"html": False})
    rendered: str = md.render(text)
    return rendered


def _fallback_render(text: str) -> str:
    """Minimal HTML rendering when markdown-it is unavailable.

    Escapes its text: a release body is outside input (mame-curator-1010).
    """
    parts: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            parts.append(f"<h1>{escape(stripped[2:].strip())}</h1>")
        elif stripped:
            parts.append(f"<p>{escape(stripped)}</p>")
    return "\n".join(parts)
