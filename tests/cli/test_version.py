"""FP27 A7 — `mame-curator --version` prints package version + exit 0.

`cli/spec.md:37` advertises a `--version` flag with a "(Future, not yet
implemented.)" caveat that has carried through three releases. A7 wires
the flag and removes the caveat.

Pre-fix: argparse rejects the unknown `--version` flag → exit 2 with
"unrecognized arguments" on stderr. Post-fix: argparse's
`action="version"` prints `mame-curator <version>` to stdout and exits 0.
"""

from __future__ import annotations

import re

import pytest

from mame_curator.cli import build_parser


def test_cli_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """`build_parser().parse_args(["--version"])` must print version
    and exit 0. argparse's `action="version"` raises SystemExit(0)
    after writing to stdout.
    """
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])

    # argparse's `action="version"` exits 0.
    assert exc_info.value.code == 0, f"--version must exit 0, got {exc_info.value.code}"

    captured = capsys.readouterr()
    # argparse writes to stdout for version action.
    output = captured.out or captured.err
    # Match `mame-curator <semver>` (semver-ish: digits, dots, optional
    # pre-release / metadata suffix like 1.2.0a1 or 1.2.0.dev0).
    pattern = r"^mame-curator \d+\.\d+\.\d+(?:[.a-zA-Z0-9+-]+)?\s*$"
    assert re.match(pattern, output.strip()), (
        f"--version output {output!r} did not match {pattern!r}"
    )


def test_cli_spec_md_version_caveat_removed() -> None:
    """`cli/spec.md:37` (the "Future, not yet implemented" caveat) must
    be deleted as part of A7. Mirror assertion on the doc surface so a
    future revert can't accidentally re-introduce the caveat without
    breaking this test.
    """
    from pathlib import Path

    spec_path = Path(__file__).resolve().parents[2] / "src" / "mame_curator" / "cli" / "spec.md"
    text = spec_path.read_text(encoding="utf-8")
    assert "Future, not yet implemented" not in text, (
        "cli/spec.md must no longer carry the '(Future, not yet "
        "implemented.)' caveat on the --version flag. "
        "See `docs/specs/FP27.md` § A7."
    )
