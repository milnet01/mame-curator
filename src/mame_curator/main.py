"""Entrypoint for the `mame-curator` script (per pyproject.toml [project.scripts])."""

from __future__ import annotations

import logging
import sys

from mame_curator.cli import build_parser, run


def main() -> int:
    """CLI entry: parses argv, configures logging, dispatches.

    Logging is configured *here* (not at module import) so importing
    `mame_curator.main` from tests, the future FastAPI layer, or a REPL does
    not mutate the global root logger as a side effect.
    """
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
