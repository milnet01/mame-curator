"""Entrypoint for the `mame-curator` script (per pyproject.toml [project.scripts])."""

from __future__ import annotations

import logging
import sys
from typing import TextIO

from mame_curator.cli import build_parser, run, subcommand_names
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


_ROOT_ANSWERS = frozenset({"-h", "--help", "--version"})
_ROOT_FLAGS = frozenset({"-v", "--verbose"})


def _bundle_argv(argv: list[str], commands: frozenset[str]) -> list[str]:
    """Insert ``serve`` for a bundle launched without a subcommand.

    mame-curator-1095 § 4.14: a double-click passes no arguments. Leading
    root flags stay in front of ``serve``; a help or version request is
    left for the root parser to answer.
    """
    if any(arg in commands or arg in _ROOT_ANSWERS for arg in argv):
        return argv
    lead = 0
    while lead < len(argv) and argv[lead] in _ROOT_FLAGS:
        lead += 1
    return [*argv[:lead], "serve", *argv[lead:]]


def main() -> int:
    """CLI entry: parses argv, configures logging, dispatches.

    Logging is configured *here* (not at module import) so importing
    `mame_curator.main` from tests, the future FastAPI layer, or a REPL does
    not mutate the global root logger as a side effect. The frozen-bundle
    stderr tee goes first, so every later message reaches the log file.
    """
    _tee_stderr_if_frozen()
    parser = build_parser()
    argv = sys.argv[1:]
    if getattr(sys, "frozen", False):
        argv = _bundle_argv(argv, subcommand_names(parser))
    args = parser.parse_args(argv)
    level = logging.DEBUG if getattr(args, "verbose", False) else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
