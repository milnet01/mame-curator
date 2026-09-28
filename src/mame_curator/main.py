"""Entrypoint for the `mame-curator` script (per pyproject.toml [project.scripts])."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

from mame_curator.cli import build_parser, run
from mame_curator.config_location import user_log_path


class _Tee:
    """A text stream writing to the console (if any) and a log file."""

    def __init__(self, console: TextIO | None, log: TextIO) -> None:
        self._console = console
        self._log = log

    def write(self, text: str) -> int:
        if self._console is not None:
            self._console.write(text)
        self._log.write(text)
        return len(text)

    def flush(self) -> None:
        if self._console is not None:
            self._console.flush()
        self._log.flush()


def _tee_stderr_if_frozen() -> None:
    """Copy stderr into ``user_log_path()`` when running as a bundle.

    mame-curator-1095 § 4.11: a double-clicked bundle has no terminal, so
    an exit-1 message would vanish with the process. The log is truncated
    per run. A windowed build starts with ``sys.stderr`` None, so only the
    file is written; an unwritable log directory leaves stderr as it was.
    """
    if not getattr(sys, "frozen", False):
        return
    path = user_log_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        log = path.open("w", encoding="utf-8", buffering=1)
    except OSError:
        return
    sys.stderr = _Tee(sys.stderr, log)


def main() -> int:
    """CLI entry: parses argv, configures logging, dispatches.

    Logging is configured *here* (not at module import) so importing
    `mame_curator.main` from tests, the future FastAPI layer, or a REPL does
    not mutate the global root logger as a side effect. The frozen-bundle
    stderr tee goes first, so every later message reaches the log file.
    """
    _tee_stderr_if_frozen()
    parser = build_parser()
    args = parser.parse_args()
    level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
