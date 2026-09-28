"""`mame-curator self-test` subcommand handler (mame-curator-1095 § 4.13)."""

from __future__ import annotations

import argparse

from rich.console import Console

from mame_curator import _selftest


def _cmd_self_test(args: argparse.Namespace) -> int:
    # One plain line a script can match exactly: no markup, no wrapping.
    console = Console(highlight=False, soft_wrap=True)
    failed = _selftest.first_failure()
    if failed is None:
        console.print("MAME_CURATOR_SELFTEST_OK", markup=False)
        return 0
    console.print(f"MAME_CURATOR_SELFTEST_FAIL: {failed}", markup=False)
    return 1
