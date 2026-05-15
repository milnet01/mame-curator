"""FP28 D3 — `_cmd_refresh_inis` must surface ImportError with an actionable message.

``cli/__init__.py:573-577`` has three inline imports (``asyncio``, ``httpx``,
``mame_curator.updates``); none are wrapped in a try/except. The matching
``_cmd_serve`` at L473-481 *does* wrap its imports in ``except ImportError``.
The inconsistency is the bug — defense-in-depth for exotic install states
(``pip install --no-deps``, broken wheel, partial editable install) where
the import chain might fail.

D3 lifts the three inline imports into a ``try: ... except ImportError as
exc:`` block matching ``_cmd_serve``'s shape. On ImportError, print an
actionable message (``"failed to import dependencies ({exc}); reinstall ..."``)
and ``return 1``.

The trigger site is the inline ``import httpx`` at L575 — it runs *before*
``from mame_curator.updates import refresh_inis`` at L577. A single
``monkeypatch.setitem(sys.modules, "httpx", None)`` forces that line to fail
with ``ImportError`` (Python's import machinery raises when a ``sys.modules``
slot is ``None``).

Pre-fix: the ImportError leaks as a traceback to stderr; ``_cmd_refresh_inis``
crashes with a non-zero exit but the message format doesn't contain "failed
to import dependencies" → assertion fails.
Post-fix: typed exit 1 with the stable error string.

See ``docs/specs/FP28.md`` § D3.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest


def test_refresh_inis_surfaces_missing_httpx(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Force ``import httpx`` to fail; assert typed error + exit 1."""
    from mame_curator.cli import _cmd_refresh_inis

    # Force httpx import to raise ImportError. The L575 inline `import httpx`
    # is the trigger site — no transitive importer invalidation needed
    # because the failure happens at the CLI's own line before reaching
    # `mame_curator.updates.ini`.
    monkeypatch.setitem(sys.modules, "httpx", None)

    args = argparse.Namespace(
        dest=tmp_path / "inis",
        config=tmp_path / "config.yaml",
        no_config=False,
    )

    exit_code = _cmd_refresh_inis(args)
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "failed to import dependencies" in captured.err, (
        f"FP28 D3 — expected 'failed to import dependencies' in stderr; got: {captured.err!r}"
    )
