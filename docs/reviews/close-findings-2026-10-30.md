# close-findings — review-code 2026-10-30

Source: [`review-code-2026-10-30/`](review-code-2026-10-30/), Message 1 #1–#13.
User rulings 2026-10-30: fix all 13 before the release; About gets version and
licence (design.md stands); #1 is fixed in code; the FAT/exFAT case-insensitive
recycle risk is queued, not fixed.

| # | finding | dim | sev | verified | disposition | files | was → now | must_agree |
|---|---|---|---|---|---|---|---|---|
| 1 | serve refuses unknown `server:` keys | 2 | MED | yes — serve.py `_load_server_config` validated `raw.get("server")` against extra=forbid | fixed | cli/commands/serve.py, cli/spec.md, tests/cli/test_serve_config_layer.py | refused → drops with a WARNING (ff68466); spec 0ff2b1e, gated 73a12bf, af2b719 | cli/spec.md server: edge case; api/spec.md load_app_config bullet |
| 2 | other zip member errors escape DATError | 2 | MED | yes — dat.py caught only BadZipFile, zlib.error, EOFError | fixed | parser/dat.py, parser/spec.md, tests/parser/test_dat_validation.py | OSError / NotImplementedError escaped → DATError (fb9b8b1) | parser/spec.md MUST list |
| 3 | OVERWRITE-delete recycle failure aborts after copies | 7 | MED | yes — runner.py OVERWRITE block called recycle_file with no try | fixed | copy/runner.py, tests/copy/test_runner_recycle_guards.py | RecycleError aborted → warning, zip stays (ed29d22) | copy/spec.md OVERWRITE row |
| 4 | About shows no version or licence | 2 | MED | yes — AboutTab.tsx; design.md "About (version, license, links)" | fixed | api/schemas_setup.py, frontend AboutTab, api types, tests | neither shown → `SetupCheck.app_version` and an MIT line (8948775) | design.md About line; api types sync |
| 5 | non-mapping `filters:` swallowed when `picker:` present | 2 | LOW | yes — schemas.py `merge_picker_into_filters` | fixed | api/schemas.py, tests/api/test_mame_curator_1131_unknown_config_keys.py | replaced by {} → ConfigError (2d45889) | api/spec.md load_app_config bullet |
| 6 | non-mapping `picker:` dropped as unknown key | 2 | LOW | yes — same function, then `_drop_unknown_keys` | fixed | api/schemas.py, api/state.py, same test file | dropped with a false warning → ConfigError (2d45889) | api/spec.md load_app_config bullet |
| 7 | unknown key names logged unescaped | 3 | LOW→INFO | yes — state.py warning joined raw keys | fixed | api/state.py, same test file | raw → repr-quoted (2d45889); serve's warning matches (ff68466) | serve.py warning |
| 8 | OVERWRITE-delete runs after a cancel | 2 | LOW | yes — no `should_cancel()` check; copy/spec.md § Pause / resume / cancel says no recycling | fixed | copy/runner.py, tests/copy/test_runner_recycle_guards.py | ran after cancel → skipped (ed29d22) | copy/spec.md § Pause / resume / cancel |
| 9 | REPLACE_AND_RECYCLE recycles on dry run | 2 | LOW | yes — recycle preceded `if plan.dry_run` | fixed | copy/runner.py, same test file | moved the zip → moves nothing (ed29d22) | copy/spec.md dry run "No writes" |
| 10 | playlist item values unchecked | 2 | LOW | yes — read_lpl kept `{"path": 5}` | fixed | copy/playlist.py, tests/copy/test_playlist.py | kept → item dropped (ed29d22) | runner.py existing-entries loop |
| 11 | filter/spec.md says `sorted(...)[0]`, code uses `min()` | 2 | LOW | yes — filter/spec.md comparator-chain paragraph | fixed | filter/spec.md, picker.py and heuristics.py comments | sort wording → min() (a1251fb) | picker.py `pick_winner` |
| 12 | copy/spec.md says **all** zips recycled | 2 | LOW | yes — copy/spec.md OVERWRITE row | fixed | copy/spec.md | "all" → names the kept zips and the failure warning (ed29d22) | runner.py OVERWRITE delete pass |
| 13 | Sponsor link gives no new-tab cue | 12 | LOW | yes — AboutTab.tsx link text | fixed | AboutTab.tsx, strings_internal.ts | no cue → visible "(opens in a new tab)" in the link name (8948775) | `strings.common.opensInNewTab` |
| Q | FAT/exFAT case-insensitive recycle risk | — | — | not reproducible here | queued | — | filed as mame-curator-1137 | — |

## Run-level

- cited_by: a docs grep for "Support this project", `delete_existing_zips`, "zip member", `sorted(candidates`, `bogus_key` and "does not recognise". Hits only in the specs edited here, dated ROADMAP notes, journals and the review files.
- swept: copy/spec.md OVERWRITE row — fixed; parser/spec.md MUST list — fixed; filter/spec.md winner line — fixed; cli/spec.md server: edge case and § Status banner — agrees now the code landed; api/spec.md load_app_config bullet — agrees; design.md About line — agrees; ROADMAP dated notes quoting "Support this project" — frozen; docs/help — names none of the changed behaviour, agrees; CHANGELOG [Unreleased] — fixed (new 2026-10-30 entry).
- collateral: two `bogus_key` exit-1 tests pinned the old refusal; they now use a bad known value (ff68466).
- surfaced: none.
- out_of_scope: three other `target="_blank"` links lack the cue — mame-curator-1138. serve exits 3 on a lifespan failure, from the review-contract gate — mame-curator-1139. docs/standards/versioning-overrides.md § Breaking surfaces item 1 still says `extra="forbid"` refuses a renamed key — already noted on mame-curator-1131.
- falsified: none.

Counts: 13 fixed, 1 queued (mame-curator-1137), 0 dismissed.
