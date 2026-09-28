# Versioning overrides — MAME Curator

The project's answer to `~/.claude/standards/versioning.md` § 3, read in
place. That standard defines "breaking" (something that worked stops working
after an upgrade) and asks each project to name what its users rely on. This
file is that list. Owner decisions of 2026-09-28 (mame-curator-1119).

**No `0.x` exit condition.** The project is past `1.0.0` (`pyproject.toml`
`version`), so § 4 does not apply.

## Breaking surfaces

A change that stops any of these working for an existing user is a MAJOR
bump, unless the release migrates the old form for them.

1. **`config.yaml`.** `AppConfig` in `src/mame_curator/api/schemas.py` sets
   `extra="forbid"`, so renaming or removing a key makes an existing file fail
   to load. Changing what a key means counts too. **Rule: a key rename or
   removal either keeps reading the old form (a migration) or ships as a
   MAJOR.** A migration covers both readers: `load_app_config` in
   `src/mame_curator/api/state.py`, and `/api/config/import`, whose backup
   files carry every key. Adding an optional key is not breaking. Where the
   file is found counts too: `resolve_config_path` in
   `src/mame_curator/config_location.py` (`--config`, then `./config.yaml`,
   then the per-user folder). Saved files sit beside it, so moving it strands
   them as well.
2. **Files the app saves and reads back later.** A release must still read
   what an earlier release wrote. The candidates are every path found by
   `grep -rnE 'data_dir / "|config_path\.parent / "' src/mame_curator`, less
   the `import.in_progress` marker, which the app clears itself. The
   Settings → Backup export file counts too: `/api/config/import` reads a
   `ConfigExportBundle` a user may have kept. So does the cart the web page
   keeps in browser storage (`CART_STORAGE_KEY` in
   `frontend/src/hooks/useCart.ts`). Other browser-stored settings are not
   surfaces.
3. **The command line.** Every subcommand, its flags and its exit codes.
   `src/mame_curator/cli/spec.md` § Subcommand inventory names the spec that
   owns each one. This includes the `filter` report JSON, because
   `copy --filter-report` reads a report a user may have kept.
4. **What a copy produces.** The destination folder layout and the RetroArch
   playlist (`mame.lpl` from the CLI, `paths.retroarch_playlist` from the
   app). RetroArch and the user's own setup read these.
5. **Starting the app.** `run.sh` / `run.bat`, the `mame-curator serve`
   flags, and every environment variable found by
   `grep -rn 'os.environ' src/mame_curator`. `serve` reads `PORT` itself.
6. **Page addresses and shortcuts a user has learned.** The page paths in
   `frontend/src/App.tsx` (`/`, `/sessions`, `/activity`, `/stats`,
   `/settings`, `/help`) and the keyboard shortcuts the app registers.

## Not breaking surfaces

- **The HTTP API (`/api/...`).** The web page and the server ship together in
  every release, and nothing documents the API for outside use. The one file
  it hands the user to keep, the Backup export, is item 2's. Changes still
  follow `api/spec.md`.
- **The Python modules under `src/mame_curator/`.** The project is not
  published as a library, so nothing outside this repository imports them.

A surface missing from this list is still a surface (versioning.md § 3). If
an upgrade breaks something a user relied on, add it here in the same commit
as the fix.
