"""FP28 C1 — `_validate_paths` must reject bad `retroarch` / `retroarch_core` paths.

``api/routes/config.py:60-83`` checks ``source_roms``, ``source_dat``,
``dest_roms``, and ``retroarch_playlist.parent`` but **not**
``paths.retroarch`` or ``paths.retroarch_core``. A malicious PATCH to
``/api/config`` could swap ``retroarch`` to ``/usr/bin/evil-thing``; the
RetroArch launch endpoint at ``api/routes/games.py:275`` then runs
``subprocess.run([str(paths.retroarch), ..., str(paths.retroarch_core), ...])``
on the unvalidated path — a local-exec primitive.

C1 extends ``_validate_paths`` to gate both fields:
- POSIX: ``p.retroarch`` must ``.exists()`` AND be ``os.X_OK``.
- Windows: ``p.retroarch`` must resolve via ``shutil.which`` (extension-based).
- ``p.retroarch_core`` must ``.exists()`` on both platforms (cores are
  shared libraries loaded by RetroArch, not directly executable).

Pre-fix: PATCH with a bogus ``paths.retroarch`` returns 200 (validator
silent) — the assertion of 422 fails.
Post-fix: validator emits a ``FieldError`` whose ``loc == "paths.retroarch"``
and ``type == "path_invalid"``; response is 422.

See ``docs/specs/FP28.md`` § C1.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest


def test_config_patch_rejects_nonexistent_retroarch(client: Any, tmp_path: Path) -> None:
    """Bogus ``paths.retroarch`` → 422 with ``loc == "paths.retroarch"``."""
    response = client.patch(
        "/api/config",
        json={"paths": {"retroarch": str(tmp_path / "does-not-exist")}},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "config_invalid"
    assert any(
        f["loc"] == "paths.retroarch" and f["type"] == "path_invalid" for f in body["fields"]
    ), f"FP28 C1 — expected paths.retroarch path_invalid in {body!r}"


def test_config_patch_rejects_nonexistent_retroarch_core(client: Any, tmp_path: Path) -> None:
    """Bogus ``paths.retroarch_core`` → 422 with ``loc == "paths.retroarch_core"``."""
    response = client.patch(
        "/api/config",
        json={"paths": {"retroarch_core": str(tmp_path / "does-not-exist.so")}},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "config_invalid"
    assert any(
        f["loc"] == "paths.retroarch_core" and f["type"] == "path_invalid" for f in body["fields"]
    )


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="os.X_OK semantics differ; the Windows shutil.which branch is exercised "
    "by a follow-up test out of FP28 scope (FP09 precedent).",
)
def test_config_patch_accepts_executable_retroarch(client: Any, tmp_path: Path) -> None:
    """POSIX happy-path: existing + executable file accepted."""
    ra = tmp_path / "ra"
    ra.touch()
    ra.chmod(0o755)
    response = client.patch("/api/config", json={"paths": {"retroarch": str(ra)}})
    assert response.status_code == 200, response.text


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="os.X_OK semantics differ; Windows uses the shutil.which branch.",
)
def test_config_patch_rejects_non_executable_retroarch(client: Any, tmp_path: Path) -> None:
    """POSIX: an existing-but-non-executable file (mode 0o644) must 422, not
    200 — this is the ``os.X_OK`` branch the happy/missing pair doesn't reach.
    Without it the validator could regress to a bare ``.exists()`` check and
    still pass every other test."""
    ra = tmp_path / "ra"
    ra.touch()
    ra.chmod(0o644)
    response = client.patch("/api/config", json={"paths": {"retroarch": str(ra)}})
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "config_invalid"
    assert any(
        f["loc"] == "paths.retroarch" and f["type"] == "path_invalid" for f in body["fields"]
    ), f"FP28 C1 — expected paths.retroarch path_invalid in {body!r}"
