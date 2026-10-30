I found no Critical or High defects in this change. The changed lines look correct. Two Medium gaps remain on error paths the change only half-closed, and the OVERWRITE-delete path has two latent problems that no shipped caller reaches today.

**Line counts as read (native `Read`, whole files):** `parser/dat.py` 292 · `filter/picker.py` 202 · `filter/heuristics.py` 88 · `copy/runner.py` 562 · `copy/playlist.py` 76.

**In context when I arrived:** the global `~/.claude/CLAUDE.md`, the review-lane agent prompt, and a startup message advertising the Ants MCP tools. I had no project `CLAUDE.md`, no memory index and no git snapshot. The shared context then gave me extracts of the project `CLAUDE.md` (architecture section and project overrides) and the false-positive ledger. I did not open any test files.

**Where my instructions disagreed:** the shared brief says the provided files should not be re-read. Step 2 and the lane file both say to read the subject in full with `Read`. I read the five lane files in full. I did not re-read anything from Step 1.

## Critical (0)

## High (0)

## Medium (2)

- **[dim 2] `parser/dat.py:127`** — `except (zipfile.BadZipFile, zlib.error, EOFError) as exc:` — **The code is wrong.** The parser spec says every CLI-visible error must stay inside `ParserError`. `zf.extract` can still escape with other exception types:
  - `NotImplementedError`: an unsupported compression method, such as Deflate64 (method 9).
  - `RuntimeError`: an encrypted member.
  - `lzma.LZMAError`: a corrupt LZMA member.
  - `OSError`: a corrupt bzip2 member, or the temp directory filling up (ENOSPC) while writing up to 256 MiB.

  The CLI catches only `ParserError` (`cli/commands/copy.py:46`, `filter.py:56`, `parse.py:17`). `api/routes/stubs.py:50` catches only `ParserError` too. So each of these reaches the user as a traceback. The corrupt-bzip2 and corrupt-LZMA cases are the same defect the diff fixes, just under a different compression method.
  - fix: also catch `OSError`, `NotImplementedError`, `RuntimeError` and `lzma.LZMAError` around `zf.extract`, and wrap each in `DATError`. Widen the spec sentence to match.

- **[dim 7] `copy/runner.py:403`** — `new_path = recycle_file(existing, reason="OVERWRITE_DELETE_EXISTING", ...)` — this call has no `try`. The cancel-partial loop at `:439` catches `(OSError, RecycleError)` and continues, and the REPLACE_AND_RECYCLE path at `:324` catches `CopyError` and adds a warning. That is three call sites with three different policies (dim 4 also applies). If one move fails (read-only file, permission denied), `RecycleError` escapes `run_copy` after every file has been copied:
  - no playlist is written (`:460`);
  - no `copy_finished` or `copy_aborted` activity event is logged;
  - the report is lost.

  The CLI turns this into "copy failed" (`cli/commands/copy.py:82`), even though the copies happened. This change edits this block, so the gap is in scope.
  - fix: wrap it like the cancel loop, and add a warning naming the file.

## Low / Info

- **[dim 2] `copy/runner.py:390–394`** — `plan.conflict_strategy is ConflictStrategy.OVERWRITE and plan.delete_existing_zips and not plan.dry_run` — this block has no cancel check. A cancel part-way through still recycles every destination zip not processed so far. That includes winners that would have been skipped as already present. Then no playlist is written (`:458`), so the old playlist now points at recycled files. The spec says `recycle_partial=False` means "no recycling". **Latent:** the CLI passes no controller (`cli/commands/copy.py:81`), and the API never sets `delete_existing_zips` (`api/routes/copy.py:37–47`). fix: add `and not ctl.should_cancel()`.

- **[dim 2] `copy/runner.py:304–332` vs `:334`** — the REPLACE_AND_RECYCLE recycle runs before the `if plan.dry_run` check. So a library-level dry run with append decisions moves real files. The spec says `--dry-run` means "No writes". **Latent:** the CLI passes no `append_decisions`, and the API never sets `dry_run`. fix: skip the recycle when `plan.dry_run` is set.

- **[dim 2] `copy/playlist.py:75`** — `return [it for it in items if isinstance(it, dict)]` — values are still not type-checked, despite the `list[dict[str, str]]` annotation. An item like `{"path": 5}` passes the filter. `runner.py:123` then does `Path(raw_path)`, which raises `TypeError`. That happens after the copies, outside any catch, and it is APPEND-only. RetroArch writes `path` as a string, so this needs a hand-edited or corrupt playlist. fix: also drop items whose `path` is not a `str`.

- **[dim 2] `filter/spec.md` (line ~56)** — the spec says "The winner is `sorted(candidates, key=cmp_to_key(chain))[0]`". The code now uses `min(...)` (`picker.py:168`). **The document is wrong, not the code.** The results are the same: every comparator is a sign of a per-machine key difference, and the alphabetical fallback is strict on unique names, so the chain is a total order. `min` and the first element of a stable sort agree under that, and also on ties. Comments in the code are stale for the same reason: `picker.py:38–41` and `heuristics.py:65–68` still say "sort". For `review-contract`.

- **[dim 2] `copy/spec.md:187`** — "**all** existing dest `.zip` files are moved to the recycle bin" — the code keeps the files it wrote and the already-present ones it skipped. The code is right, because those files are playlist entries (spec § "Which winners become entries"). **The document is wrong.**

- **INFO:** I read the spec sections relevant to the changed paths (`copy/spec.md` 170–278 and 420–470, `filter/spec.md` 45–70, `parser/spec.md` 69–100, plus the diff hunk), not the whole spec files. I did not open `docs/design.md`, `copy/executor.py` or `copy/recyclebin.py`. My statements about what `zf.extract` raises come from CPython's `zipfile` source as I know it. I did not run anything to confirm them.

## Covered by spec and looks correct

- `dat.py` 72–135: the zip-slip check, the size cap and the new member-corruption wrapper are right for the three exception types they name. CPython's `ZipExtFile` cuts output at `file_size`, so the cap holds while decompressing.
- `picker.py` `pick_winner`: `min` gives the same winner as before (reasoning above). It is never called with an empty group (`filter/runner.py:52`, per the spec).
- `heuristics.py` `region_of`: a pure function of a `str` returning an enum, so caching it is safe, bounded and thread-safe.
- `runner.py` dry-run block: `stat` is now called once instead of three times, with the same result. `wrote` now includes files skipped as already present, which matches the playlist-entry rule.
- `playlist.py`: `ValueError` covers both `JSONDecodeError` and `UnicodeDecodeError`. The new root-object check is correct.

All other dimensions (5, 8, 9, 10, 11, 12, 13, 15, 16, 17): nothing found in the changed code. Dimension 3 is answered by the first Medium (zip handling). The cache size is fixed, so it adds no resource risk.

## Open questions

- On a case-insensitive destination drive (FAT/exFAT), suppose an old `Pacman.zip` keeps its stored capitals after `pacman.zip` is copied over it. Then `glob("*.zip")` returns `Pacman.zip`, which is not in `wrote`, so the file just written gets recycled. I could not settle this, and the tests cannot reach such drives.
- Is `run_copy` a public library API whose `dry_run` and cancel contracts bind on their own? Or is the spec bound only to the CLI and API callers? That decides whether the two latent items count.

## Top 3 to fix first

1. **The unguarded recycle in OVERWRITE-delete (`runner.py:403`).** It is reachable from the CLI. One failure throws away the playlist write, the activity log and the report after the files have already been copied.
2. **The remaining exception types escaping `zf.extract` (`dat.py:127`).** The diff set out to stop raw errors from DAT extraction and missed several, so the CLI can still show a traceback.
3. **The missing cancel check before OVERWRITE-delete (`runner.py:390`).** It is a one-line fix and stops a cancel from recycling a whole library before the playlist is rewritten.
