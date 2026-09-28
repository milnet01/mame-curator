"""Checks that a bundle still carries every stack it can silently lose.

mame-curator-1095 § 4.13 (INV-17). PyInstaller only packages what its
static analysis finds, so a bundle can start without a module uvicorn picks
at run time, or without the SPA or the Help pages. Each check imports its
stack inside the function, so this module imports cleanly when one is
missing and a test can replace a single check. ``cli/commands/self_test.py``
prints the result; library code does not print.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

from mame_curator._resources import frontend_dist


def _check_lxml() -> None:
    from lxml import etree

    etree.fromstring(b"<mame/>")


def _check_httptools() -> None:
    import httptools  # noqa: F401


def _check_websockets() -> None:
    import websockets  # noqa: F401


def _check_uvloop() -> None:
    # uvicorn[standard] does not install uvloop on Windows.
    if sys.platform != "win32":
        import uvloop  # noqa: F401


def _check_frontend_dist() -> None:
    if not (frontend_dist() / "index.html").is_file():
        raise FileNotFoundError(frontend_dist() / "index.html")


def _check_help_dir() -> None:
    from mame_curator.api.routes.help import _help_dir

    if not any(_help_dir().glob("*.md")):
        raise FileNotFoundError(_help_dir())


# (token, check) in order; the token is what a failure line names.
CHECKS: tuple[tuple[str, Callable[[], None]], ...] = (
    ("lxml", _check_lxml),
    ("httptools", _check_httptools),
    ("websockets", _check_websockets),
    ("uvloop", _check_uvloop),
    ("frontend_dist", _check_frontend_dist),
    ("help_dir", _check_help_dir),
)


def first_failure() -> str | None:
    """Token of the first failing check, or ``None`` when every check passes."""
    for token, check in CHECKS:
        try:
            check()
        except Exception:  # any failure is the answer; the token names it
            return token
    return None
