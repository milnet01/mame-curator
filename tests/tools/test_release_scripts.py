"""mame-curator-1095 — static checks on the desktop-bundle packaging.

Reads ``packaging/mame-curator.spec`` (and, from later plan steps, the local
build scripts and ``release.yml``) without building anything. POSIX-only,
like ``test_run_sh_port.py``: the scripts these checks grow to cover are
bash. Contract: ``docs/specs/mame-curator-1095-desktop-bundles.md`` § 5.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="packaging checks are POSIX-only")

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "packaging" / "mame-curator.spec"
ALLOWED_DATA = {"frontend/dist", "docs/help", "config.example.yaml", "packaging"}


def _assigned_literal(name: str) -> object:
    tree = ast.parse(SPEC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{SPEC.name} assigns no literal {name}")


def test_spec_datas_are_allowlisted() -> None:
    """INV-14 — every bundled data source is on the allowlist, and lands at
    the same relative path (config.example.yaml at the bundle root)."""
    entries = _assigned_literal("DATAS")
    assert isinstance(entries, list) and entries
    for src, dest in entries:
        assert src in ALLOWED_DATA, f"{src!r} is not on the datas allowlist"
        assert dest == ("." if src == "config.example.yaml" else src), (src, dest)


def test_spec_builds_datas_only_from_the_allowlisted_literal() -> None:
    """A second route into ``datas`` (Tree, collect_data_files, an append)
    would bypass the allowlist the test above reads."""
    text = SPEC.read_text(encoding="utf-8")
    for bypass in ("Tree(", "collect_data_files", "datas +=", "datas.append", "datas.extend"):
        assert bypass not in text, bypass


# ---- INV-12 / INV-20 / INV-15: the local scripts against release.yml ---------

RELEASE = REPO / ".github" / "workflows" / "release.yml"
SCRIPT_JOBS = {
    "local-appimage.sh": "build-appimage",
    "local-exe.sh": "build-exe",
    "local-macos.sh": "build-macos",
}


def _jobs() -> dict[str, dict[str, object]]:
    import yaml

    jobs = yaml.safe_load(RELEASE.read_text(encoding="utf-8"))["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _script_stages(script: str) -> set[str]:
    text = (REPO / script).read_text(encoding="utf-8")
    # A marker is a line that IS "# stage: <name>"; prose mentioning one is not.
    marked = (line.strip() for line in text.splitlines())
    return {line.removeprefix("# stage:").strip() for line in marked if line.startswith("# stage:")}


def _job_stages(job: str) -> set[str]:
    steps = _jobs()[job]["steps"]
    assert isinstance(steps, list)
    names = (str(step.get("name", "")) for step in steps)
    return {name.removeprefix("stage:").strip() for name in names if name.startswith("stage:")}


@pytest.mark.parametrize(("script", "job"), sorted(SCRIPT_JOBS.items()))
def test_local_scripts_mirror_release_yml(script: str, job: str) -> None:
    """INV-12 — the same named build stages on both sides; host setup is
    exempt, so only ``# stage:`` lines and ``stage: <name>`` steps count."""
    stages = _script_stages(script)
    assert stages, f"{script} marks no stages"
    assert stages == _job_stages(job)


def test_appimage_builds_in_bookworm() -> None:
    """INV-20 — both sides build inside the same bookworm image."""
    text = (REPO / "local-appimage.sh").read_text(encoding="utf-8")
    image = next(
        line.split("=", 1)[1].strip().strip('"')
        for line in text.splitlines()
        if line.startswith("BUILD_IMAGE=")
    )
    assert "python:3.13-slim-bookworm" in image
    container = _jobs()["build-appimage"]["container"]
    container_image = container["image"] if isinstance(container, dict) else container
    assert container_image == image.removeprefix("docker.io/library/")


@pytest.mark.parametrize("script", ["local-appimage.sh", "local-exe.sh"])
def test_scripts_carry_a_size_ceiling(script: str) -> None:
    """INV-15 — a numeric byte ceiling and a failing exit when it is passed.
    local-macos.sh carries none until a CI run has measured a .dmg."""
    text = (REPO / script).read_text(encoding="utf-8")
    ceiling = [line for line in text.splitlines() if line.startswith("SIZE_CEILING_BYTES=")]
    assert ceiling and ceiling[0].split("=", 1)[1].isdigit(), "no numeric SIZE_CEILING_BYTES"
    assert '-gt "$SIZE_CEILING_BYTES"' in text and "exit 1" in text
