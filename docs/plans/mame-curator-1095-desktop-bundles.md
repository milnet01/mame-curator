# mame-curator-1095 — desktop bundles — build plan

**Spec:** [docs/specs/mame-curator-1095-desktop-bundles.md](../specs/mame-curator-1095-desktop-bundles.md)
**Status:** in progress — steps 1–2 done (2026-08-04, 9842a86).

Two halves, in this order: the app must survive a first run (steps 1–7)
before there is any point wrapping it (steps 8–15). Every step's tests
land before its implementation, per the project's TDD default.

## Steps

1. **[done]** `src/mame_curator/config_location.py` — `ConfigSource`,
   `user_config_path`, `user_data_path`, `user_log_path`,
   `resolve_config_path`, `ensure_starter_config`; `STARTER_HEADER`
   moves here from `cli/commands/setup.py::_SETUP_HEADER`, which imports
   it. → **verify:** `uv run pytest tests/cli/test_config_location.py`
   passes 6 new tests, red before the module exists (satisfies INV-1,
   INV-4, INV-5, INV-6).

2. **[done]** Wire resolution into `_cmd_serve`: `--config` default → `None`, and
   `resolve_config_path` / `ensure_starter_config` run in **stage 2**,
   after `$PORT` validation, with the resolved path reaching
   `_load_server_config` and `create_app`. → **verify:**
   `uv run pytest tests/cli/` green, including the untouched
   `test_invalid_port_checked_before_config` (satisfies INV-2, INV-3).

3. `src/mame_curator/_resources.py` — `bundle_root()`, `frontend_dist()`;
   `api/app.py`'s module-level `_FRONTEND_DIST` becomes a call inside
   `create_app`. → **verify:**
   `uv run pytest tests/test_resources.py` passes with `sys.frozen` and
   `sys._MEIPASS` monkeypatched both ways (satisfies INV-11).

4. `build_world` catches `(ParserError, OSError)` around `parse_dat` →
   empty `machines` + `WorldState.setup_required = True`; the remaining
   world construction runs unchanged. → **verify:**
   `uv run pytest tests/api/test_setup_mode.py -k "missing or malformed"`
   green, and the returned world has every field populated (satisfies
   INV-7, INV-8).

5. `_validate_paths(config, *, setup_required=False)` skips the
   `source_dat` existence check in setup mode; `patch_config` passes
   `world.setup_required` and sets
   `restart_required = server_changed or world.setup_required`. →
   **verify:** `uv run pytest tests/api/test_setup_mode.py` fully green
   (satisfies INV-9, INV-10).

6. `setup_required` on `SetupCheck` in `api/schemas_setup.py`, populated
   in `routes/stubs.py::setup_check`; mirrored in
   `frontend/src/api/schemas.ts` and `types.ts`. → **verify:**
   `python3 tools/check_api_types_sync.py` exits 0 and
   `cd frontend && npm run build` type-checks.

7. `main()` tees stderr to `user_log_path()` when
   `getattr(sys, "frozen", False)`. → **verify:** a source-tree run's
   stderr is unchanged (existing CLI tests stay green); the frozen branch
   is exercised in step 12.

8. `packaging/icon.svg` + render script producing `.png` / `.ico` /
   `.icns`. → **verify:** all three files exist and `file` reports the
   expected format for each.

9. `packaging/mame-curator.spec` — hidden imports for uvicorn's `.auto`
   selectors and their `[standard]` implementations plus `sse-starlette`;
   `datas` for `frontend/dist` → `frontend/dist`, `config.example.yaml`,
   `packaging/`. → **verify:**
   `uv run pytest tests/tools/test_release_scripts.py -k datas` green
   (satisfies INV-14).

10. `local-appimage.sh` — frontend build, PyInstaller one-dir, AppDir
    assembly, sha256-pinned `appimagetool`. → **verify:** the script runs
    to completion and `dist/MAME_Curator-1.2.0-x86_64.AppImage` exists.

11. `local-exe.sh` — provisions `.wine-build/`, installs Windows CPython
    under Wine, runs PyInstaller through the shared spec. → **verify:**
    the script completes and `dist/MAME_Curator-1.2.0-x86_64.exe` is a PE
    binary (`file` reports `PE32+ executable`); then the INV-16 recipe
    prints `PASS` (satisfies INV-16).

11b. `local-macos.sh`. → **verify:** `shellcheck` clean. **Not executed** —
    building a macOS bundle on Linux is impossible, not merely
    unavailable (spec §4.7); its first real run is step 14's CI.

12. Run the spec's INV-13 recipe against the built AppImage. →
    **verify:** it prints `PASS`, and the log file from step 7 exists at
    `user_log_path()`.

13. Record the measured artefact size in spec §10 and add the 1.5×
    ceiling check to each local script. → **verify:**
    `uv run pytest tests/tools/test_release_scripts.py` fully green
    (satisfies INV-12, INV-15).

14. `release.yml` — three build jobs uploading `bundle-linux` /
    `bundle-windows` / `bundle-macos`, and `publish` gaining the matching
    `needs` and one `download-artifact` per bundle into `dist/`. →
    **verify:** `actionlint` clean, and
    `uv run pytest tests/tools/test_release_scripts.py` green.

15. Docs: README download-and-run per platform including the macOS
    right-click step and the log paths; CHANGELOG entry; `CLAUDE.md`
    § Common commands; the DS05 declaration-count pin. → **verify:**
    `/doc-lint` reports 0 findings across the touched docs.

## Definition of done

`./local-CI.sh` passes, `./local-appimage.sh` produces an AppImage, and
the INV-13 recipe against that AppImage prints `PASS`. No release is
tagged — spec §3 decision 3.
