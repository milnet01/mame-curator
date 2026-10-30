The lane found one Medium and three Low findings, all in the new rule that lets the app start with a config written by a newer version. The Medium: that promise doesn't hold for the `server:` section, because the `serve` command checks it on its own first. The games, stats, copy-job and activity changes are clean.

**Subject files and the lines I read** (all with native `Read`):
- `api/state.py`: 371 lines
- `api/schemas.py`: 416
- `api/schemas_copy.py`: 96
- `api/jobs.py`: 504
- `api/routes/activity.py`: 94
- `api/routes/games.py`: lines 40–448 of 448. I did not read lines 1–39, which hold the imports, the logger and the router.
- `lane1.diff`: 338 lines

**Already in my context before I read the subject:**
- The global `~/.claude/CLAUDE.md`.
- The environment block and the user's email.
- The shared-context file, which includes excerpts of the project's `CLAUDE.md`: the architecture, its rules and the FP-ledger.

I had no memory index and no git snapshot.

**One disagreement, and how I settled it:** the shared context says "the files above are provided in full; do not re-read them". The packet only gave paths, though, so I read each subject file once, as Step 2 and this lane's rules require.

## Critical (0)

## High (0)

## Medium (1)
- [dim 2] `cli/commands/serve.py:108`: `return ServerConfig.model_validate(raw.get("server") or {})`
  - **Problem:** `api/spec.md`'s new `load_app_config` bullet says unknown keys are dropped "so a rollback to older code still starts" (mame-curator-1131). But `serve` checks the `server:` block itself, against `ServerConfig`, which refuses unknown keys (`schemas.py:68`). It does this before the startup code ever calls `load_app_config`. So if a newer version wrote a `server:` key and the user rolls back, `serve` still exits with code 1 (`cli/spec.md` exit path 4). The tolerance is never reached.
  - **Which side is wrong:** the code, since the spec's promise is unconditional. If the spec is meant to cover only the startup code, the spec is wrong instead.
  - **Fix:** drop keys `ServerConfig` doesn't know in `_load_server_config` too, by reusing `_drop_unknown_keys(ServerConfig, ...)`. Or narrow the spec sentence.

## Low / Info
- [dim 2] `schemas.py:222-224`: `if not isinstance(filters, dict): filters = {}`
  - **Problem:** when a `picker:` section is present, a `filters:` value that is not a mapping (for example `filters: 5`) is thrown away without an error or a warning. The spec says "A bad value for a known key still raises `ConfigError`". The same code already ran for `PATCH /api/config`. This change makes it reachable from `config.yaml` at startup (`state.py:94`).
  - **Fix:** leave a non-mapping `filters` in place so validation rejects it.
- [dim 2] `schemas.py:220` with `state.py:124-128`: `picker = data.pop("picker", None) if isinstance(data.get("picker"), dict) else None`
  - **Problem:** a `picker:` that is not a mapping (`picker: []`, `picker: 5`, or empty `picker:`) is not folded in. `_drop_unknown_keys` then drops it with the warning "ignoring keys this version does not recognise: picker". The warning is false, because `picker:` is a documented section (`design.md:430`). And a bad value that used to raise `ConfigError` (because `AppConfig` refuses unknown keys) now passes silently.
  - **Fix:** in `load_app_config`, treat a non-mapping `picker` as a validation error, or at least don't report it as unrecognised.
- [dim 3] `state.py:99-103`: `"%r: ignoring keys this version does not recognise: %s", ..., ", ".join(dropped)`
  - **Problem:** key names come straight from the YAML file and are logged as they are. A key containing a newline or a terminal escape sequence can forge log lines. The file is the user's own and local, so the reach is small.
  - **Fix:** log `repr(key)` for each key.
- INFO: I did not open `cli/commands/serve.py`'s caller order. The claim that `serve` exits before the startup code runs rests on `cli/spec.md:116-121`, which says so explicitly.

## Covered by spec and looks correct
- **`_drop_unknown_keys`, checked against every `AppConfig` field type:**
  - No field uses an alias.
  - No field is a `dict[str, Model]`, which the `get_args` scan would wrongly recurse into.
  - Every nested section (`PathsConfig`, `ServerConfig`, `FilterConfig`, `MediaConfig`, `UiConfig`, `UpdatesConfig`, `FsConfig`) is a plain model that refuses unknown keys.
  - Keys that are not strings are dropped and named in the warning.
- **"The next Settings save writes the file without them":** holds. `PATCH` builds its merge from `world.config.model_dump` (`routes/config.py:164-166`), not from the file on disk.
- **The spec's list of callers is accurate:** `build_world`, snapshot-restore (`config.py:236`), INI-apply (`updates_ini.py:168`) and `refresh_snaps.py:41`.
- **`activity.py`:** `_as_utc` removes the error raised when comparing a datetime that has a timezone with one that has none. Before, that error became a 500 reply. The new `isinstance(obj, dict)` guard skips lines that are valid JSON but not objects.
- **`games.py`:** the refactor keeps the same behaviour. `winners` is only iterated, never changed. `q_lower` keeps the old "empty `q` means no filter" meaning. `most_common(10)` breaks ties in the same order as the old sort, since both sorts are stable.
- **`jobs.py` and `schemas_copy.py`:** the changes are type-only. Removing the `# type: ignore` is sound because `JobState` is now the shared type.
- **Dimensions with nothing found:**
  - 2b: `merge_picker_into_filters` and `JobState` both have callers.
  - 4: nothing found. The picker fold now lives in one shared function instead of being duplicated.
  - 5: nothing found.
  - 7: nothing found.
  - 8: nothing found.
  - 9: nothing found.
  - 10: N/A, no observability contract named.
  - 11: nothing found.
  - 12: N/A, no standard named.
  - 13: the naive-as-UTC choice is under Open questions.
  - 15: nothing found.
  - 16: nothing found.
  - 17: this change is itself about rollback compatibility. Its gap is the Medium finding.

## Open questions
- **Typos are no longer refused.** A typo in a section `config.yaml` already has, like `filters: {drop_mature_: true}`, now starts with a WARNING instead of a `ConfigError`. The user's intended setting is silently ignored in the app. The spec chooses this ("drops… at any depth"), but it trades away typo detection for hand-edited files. Is that intended?
- **Log timestamps with no timezone are read as UTC.** That is only right if every writer writes UTC. I saw `datetime.now(UTC)` at `recyclebin.py:289` and in three routes. I did not open `runner.py:185` (`started_at`) or `recyclebin.py:179` (`now`).
- **Shared YAML sections.** A YAML anchor/alias shared by two sections becomes one shared object, so pruning one section also prunes the other. That is exotic, and it used to fail outright, so it is not filed.

## The 3 I would fix first
1. **The `serve` `server:` gap (Medium).** It is the one place the new rollback promise fails outright: the app doesn't start, which is exactly what mame-curator-1131 set out to stop.
2. **A non-mapping `picker:` reported as "unrecognised".** It turns a bad value into a misleading warning and breaks the spec's "still raises" sentence.
3. **A non-mapping `filters:` discarded when `picker:` is present.** It is the same contract breach and now reachable from the config file. The fix is one line.
