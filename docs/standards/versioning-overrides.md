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
   to load. Changing what a key means, or a default the user never wrote down,
   counts too. **Rule: a key rename or removal either keeps reading the old
   form (a migration) or ships as a MAJOR.** Adding an optional key is not
   breaking.
2. **Saved user data** next to the config and in the data directory:
   `overrides.yaml`, `sessions.yaml`, `state.yaml` (review marks) and
   `notes.json`. A release must still read the files an earlier release wrote.
3. **The command line.** The subcommands, flags and exit codes in
   `src/mame_curator/cli/spec.md`. This includes the `filter` report JSON,
   because `copy --filter-report` reads a report a user may have kept.
4. **What a copy produces.** The destination folder layout and the RetroArch
   playlist (`mame.lpl` from the CLI, `paths.retroarch_playlist` from the
   app). RetroArch and the user's own setup read these.
5. **Starting the app.** `run.sh` / `run.bat`, the `PORT` variable they honour,
   and the `mame-curator serve` flags.
6. **Page addresses and shortcuts a user has learned.** The page paths in
   `frontend/src/App.tsx` (`/`, `/sessions`, `/activity`, `/stats`,
   `/settings`, `/help`) and the keyboard shortcuts the app registers.

## Not breaking surfaces

- **The HTTP API (`/api/...`).** The web page and the server ship together in
  every release, and nothing documents the API for outside use. Changing it
  cannot break an installed copy. Changes still follow `api/spec.md`, and
  `check-api-types-sync` keeps the two halves in step.
- **The Python modules under `src/mame_curator/`.** The project is not
  published as a library, so nothing outside this repository imports them.

A surface missing from this list is still a surface (versioning.md § 3). If
an upgrade breaks something a user relied on, add it here in the same commit
as the fix.
