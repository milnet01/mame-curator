# Developer commands

The commands a session or contributor runs most. Moved out of `CLAUDE.md` on 2026-10-15 so it is read when needed, not loaded on every request.

```bash
# Setup. The local hooksPath keeps pre-commit working under the global
# ~/.claude/githooks; the copied pre-push hands every push to the machine-wide
# gate (secret scan, then local-CI.sh per .ants/gate.conf).
uv sync && git config core.hooksPath .git/hooks && uv run pre-commit install \
    && cp ~/.claude/skeleton/files/.githooks/pre-push .git/hooks/pre-push

# Full CI mirror — runs every check .github/workflows/ci.yml runs, in the
# same order (backend gates + api-type-sync + frontend + gitleaks). Keep it
# in lockstep with ci.yml. `--fresh` provisions first (uv sync + npm ci).
./local-CI.sh

# Backend-only gate (must pass on `main`; a subset of the above)
uv run ruff check && uv run ruff format --check && uv run mypy \
    && uv run bandit -c pyproject.toml -r src && uv run pytest

# Single test
uv run pytest tests/parser/test_dat_basic.py::test_parse_dat_returns_dict_keyed_by_short_name -xvs

# Desktop bundles (mame-curator-1095), written to dist/
./local-appimage.sh                              # Linux AppImage, in a bookworm container (podman)
MAME_CURATOR_BUILD_SMOKE=1 scripts/build-smoke.sh   # clean-room self-test of the AppImage
./local-exe.sh                                   # Windows .exe under Wine (.wine-build/)
# local-macos.sh runs on a Mac only; CI's build-macos job is its real run.
# A manual run of release.yml (gh workflow run release.yml) rehearses all
# three builds and publishes nothing.

# CLI smoke
uv run mame-curator parse <DAT.xml-or-.zip>
uv run mame-curator filter --help
uv run mame-curator copy --help
```

**The dev tools are the `dev` dependency group** (mame-curator-1106), which
a plain `uv sync` installs. The old `uv sync --extra dev` now fails: there is
no such extra. **`uv sync --no-dev` strips them, and the next `uv run`
puts them back**: `uv run` syncs the default groups before it runs. So
`run.sh` / `run.bat` pass `--no-dev` to every `uv sync` and `uv run`, and
`--inexact` to the sync; launching the app installs no dev tools and removes
none. `tests/docs/test_dev_dependency_group.py` pins the launchers.
