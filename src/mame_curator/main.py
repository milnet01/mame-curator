"""Entrypoint for the `mame-curator` script (per pyproject.toml [project.scripts])."""

from __future__ import annotations

import logging
import sys

from mame_curator.cli import build_parser, run

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> int:
    """CLI entry: parses argv and dispatches."""
    parser = build_parser()
    args = parser.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
