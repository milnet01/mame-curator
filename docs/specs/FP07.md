# FP07 — `cli/` + typed-error path-quoting sweep

- **Status:** 🚧 active (opened 2026-05-01)
- **Kind:** review-fix (path-quoting only — same threat-model as FP06 B3, different module surface)
- **Source:** FP06 closing `/indie-review` 2026-05-01 explicitly deferred these sites; FP06 spec § "Out of scope" calls them out by file:line.
- **Theme:** complete the path-quoting sweep that FP06 scoped to `filter/`. FP06 fixed loaders (`_io.py`, `sessions.py`, `overrides.py`) and added `repr`-quoting at 13 user-controlled-string interpolations there. FP07 closes the remaining surface: 3 f-strings in `cli/__init__.py` plus the typed-error `__str__` rendering at `copy/errors.py:26` and `parser/errors.py:14` (one fix-each that covers every `CopyError`/`ParserError` subclass at every raise site, since both base classes funnel through their own `__str__`).
- **Dependencies:** FP06 ✅. (FP04 — parser hardening — has surface adjacency at `parser/errors.py` but no overlap with `parser/dat.py`'s OSError/fd-leak items; FP07's `parser/errors.py` fix is a 1-line `__str__` change that does not touch FP04's scope.)
- **Out of scope:** the FP04 parser items (`parser/dat.py` `_resolve_xml` OSError + fd-leak — different code path, different module file); per-call-site f-string changes in `recyclebin.py`, `playlist.py`, `executor.py` (deliberately *not* in scope — fixing the `__str__` at the base class covers every raise site without 5+ duplicate edits, single-point-of-change wins on Rule of Three intent); informational console output that interpolates paths (e.g. `cli/__init__.py:148, 207`'s `console.print(f"DAT: {args.dat}")` style — those are not error messages and don't need to defend the single-line error contract; `rich` styles them visibly; flagging on principle would be scope creep).

## Why a single fix-pass

Five surgical edits, two test files. All share the FP06 B3 threat model: user-controlled paths interpolated raw into error messages can break the single-line error contract or spoof terminal output via embedded ANSI escapes. The fix-shape is identical to FP06 B3 (`{path}` → `{path!r}`) but at module surfaces FP06 deliberately deferred. Closing piecemeal would mean three more `/audit` + `/indie-review` cycles for a five-edit patch.

## Audit pattern that produced the FP07 site list

FP06's R2 lesson: audit by *value flow*, not by *grep pattern*. Re-applied for FP07:

1. **Where do user-controlled paths flow into error messages?**
   - CLI: argparse-bound `args.<flag>` (e.g. `args.dat`, `args.out`, `args.filter_report`) → f-string in error console output.
   - Copy module: `path` argument passed to `CopyError(..., path=path)` → stored in `self.path` → rendered by `CopyError.__str__`.
   - Parser module: `path` argument passed to `ParserError(message, path)` → interpolated directly inside `super().__init__(...)` (the message is *frozen at construction time*, not rendered lazily).
2. **Where are the actual interpolation sites?**
   - `cli/__init__.py:139, 200, 249` — three error-output f-strings (verified by grep for `f".*\{path` patterns + manual filter against informational `console.print` output).
   - `copy/errors.py:26` — `CopyError.__str__` does `f"{base} (path={self.path})"`. Single rendering site for every `CopyError` / `PreflightError` / `PlaylistError` / `RecycleError` / `CopyExecutionError` instance constructed anywhere in `copy/`.
   - `parser/errors.py:14` — `ParserError.__init__` does `f"{message} (path={path})" if path else message`. Single message-construction site for every `ParserError` / `DATError` / `INIError` / `ListxmlError`.

The `__str__` / `__init__` strategy is **strictly better** than per-raise-site edits: 1 line of code change in each base class covers ~10 raise sites between `recyclebin.py:27, 46`, `playlist.py:55, 61, 66, 69`, `executor.py:75`, plus every parser call site. Future raise sites added to either module inherit the fix automatically.

## Scope

### Tier 1 — closing FP06's deferred surface (5 sites)

- **A1 — `cli/__init__.py:139` `_cmd_parse`'s `failed to parse` error.** `args.dat` is a user-controlled CLI path; if it contains a control byte (newline, ANSI escape) the error message breaks the single-line contract. **Fix:** `f"...failed to parse {args.dat!r}: {exc}"`.
- **A2 — `cli/__init__.py:200` `_cmd_filter`'s atomic-write OSError.** `args.out` user-controlled; same threat model. **Fix:** `f"...failed to write {args.out!r}: {exc}"`.
- **A3 — `cli/__init__.py:249` `_cmd_copy`'s filter-report load failure.** `args.filter_report` user-controlled. **Fix:** `f"...failed to read filter report {args.filter_report!r}: {exc}"`.
- **A4 — `copy/errors.py:26` `CopyError.__str__` `(path=...)` rendering.** Single rendering site for every `CopyError` subclass; `self.path` flows from `RecycleError(..., path=path)` etc. across all 7 raise sites in `copy/`. **Fix:** `f"{base} (path={self.path!r})"`. **Caller-impact:** `cli/__init__.py:269` does `f"copy failed: {exc}"` which triggers `CopyError.__str__`; the rendered path is now repr-quoted. No production code parses these strings; existing tests that match on substring (e.g. `match="path="`, `match="failed to move"`) continue to pass — none match on the path content.
- **A5 — `parser/errors.py:14` `ParserError.__init__` `(path=...)` interpolation.** Single message-construction site for every `ParserError` subclass; raised across `parser/dat.py`, `parser/listxml.py`, `parser/ini.py`. **Fix:** `f"{message} (path={path!r})" if path else message`. **Type-contract note:** every `ParserError(...)` call site in `src/` passes `path=<Path>` or `path=Path(...)`; signature declares `path: Path | None = None` but does not enforce. `repr(Path("x"))` renders `PosixPath('x')` while `repr("x")` renders `'x'` — both safe re. control bytes (no literal LF in either case), and the A5 test's `evil\\nname.xml` substring assertion is satisfied by either form, so the test is robust to a future caller drifting to `path=str(...)`. Worth pinning the contract in the docstring as part of this change.

## Tests to write first (Step 3)

In rough TDD order (failing first):

1. **A1** — `test_cmd_parse_quotes_path_with_control_byte` (`tests/parser/test_cli_parse.py` — extend if exists, or NEW). Pass `--dat` pointing at a non-existent path with `\n` in the name. Assert `_cmd_parse` returns 1, stderr contains the escaped form `evil\nname.xml` (literal `\` + `n`), no literal LF byte in the path-bearing portion of stderr.

   ```python
   def test_cmd_parse_quotes_path_with_control_byte(
       tmp_path, capsys
   ):
       # Path object construction is pure — no syscall, so no OSError
       # surface to skip on. parse_dat checks `path.exists()` and raises
       # DATError("DAT path does not exist", path=path) without touching
       # the filesystem; the test fires on the cli/_cmd_parse f-string
       # at line 139, which is the surface under test.
       bad = tmp_path / "evil\nname.xml"
       parser = build_parser()
       args = parser.parse_args(["parse", str(bad)])
       assert run(args) == 1
       err = capsys.readouterr().err
       # Escaped form (Python source `\\n` = 2 chars).
       assert "evil\\nname.xml" in err
       # Strict: no literal LF in the path-bearing portion.
       # err looks like "error: failed to parse PosixPath('evil\\nname.xml'): ..."
       # split on "error:" + slice up to the first colon after the path.
       assert "\n" not in err.split("error:", 1)[1].split(":", 1)[0] if "error:" in err else False
   ```

   Trace: `parse_dat` opens with a `path.exists()` gate — file not on disk → `DATError("DAT path does not exist", path=path)` → caught at `cli/__init__.py:138` `ParserError` clause → rendered via the L139 f-string. **Pre-fix** the bare `{args.dat}` interpolation drops a literal LF into stderr; the strict assertion fails. **Post-fix** `{args.dat!r}` renders `PosixPath('evil\\nname.xml')` (with backslash-n, 2 chars) — both assertions pass. (The `args.dat` argparse type is `Path`, so `repr` produces `PosixPath('...')`. The `evil\\nname.xml` substring appears inside both `PosixPath('...')` and bare `'...'` forms, so the substring assertion is robust to call-site type drift.)

2. **A2** — `test_cmd_filter_quotes_out_path_with_control_byte` (`tests/filter/test_cli_filter.py` — extend). Use `monkeypatch.setattr("mame_curator.cli.atomic_write_text", ...)` to force `OSError`. **Patch the cli-side binding** `mame_curator.cli.atomic_write_text`, **not** the source module `mame_curator._atomic.atomic_write_text` — `cli/__init__.py:18` does `from mame_curator._atomic import atomic_write_text`, so the name is bound into the `cli` namespace at import time and the call site looks up the cli-side binding. Patching the source module won't intercept. Assert error message quotes `args.out`.

3. **A3** — `test_cmd_copy_quotes_filter_report_with_control_byte` (`tests/copy/test_cli_copy.py`). Pass `--filter-report` pointing at a non-existent file with `\n`. Assert exit 1 + stderr contains escaped form.

4. **A4** — `test_copy_error_str_quotes_path` (`tests/copy/test_errors.py` — NEW or extend). Construct `RecycleError("test", path=Path("evil\nname.zip"))`; assert `str(exc)` contains `"evil\\nname.zip"` and not a literal LF. Single test covers every CopyError subclass via the shared `__str__`.

5. **A5** — `test_parser_error_str_quotes_path` (`tests/parser/test_errors.py` — NEW or extend). Construct `DATError("test", Path("evil\nname.xml"))`; assert `str(exc)` contains `"evil\\nname.xml"` and not a literal LF. Single test covers every ParserError subclass.

**Coverage hold rule.** New tests live under existing high-coverage modules (`copy/` ≥85%, `parser/` ≥90%). All Tier 1 fixes are 1-line edits; each test exercises the fix's load-bearing branch.

### Cluster R — closing-review drift (1)

- **R1 — Tighten CLI test assertions to literal-LF-form check (M1).** Closing `/indie-review` flagged that the original `assert "\n" not in err.rstrip("\n")` only strips trailing LFs; if any future `{exc}` value contains an embedded LF (e.g. a Pydantic `ValidationError.__str__` which is multi-line) the assertion fires on the exception body, not on the path. Today no such `{exc}` propagates through these three call sites (`OSError`/`JSONDecodeError`/`ParserError` all stringify to single lines), but the assertion is making a stronger claim than the FP07 contract requires. **Fix:** narrow each of the 3 CLI test assertions (`tests/parser/test_cli_parse.py`, `tests/filter/test_cli_filter.py`, `tests/copy/test_cli_copy.py`) to `assert "evil\nname.<ext>" not in err` — the literal-LF form of the path. Directly tests the contract "the path did not leak with a literal LF" without making claims about the rest of the message.

## Acceptance criteria

- [ ] **Tier 1 (5):** A1, A2, A3, A4, A5 — path-quoting applied at all 5 sites; tests pass.
- [ ] **Cluster R (1):** R1 — CLI test assertions tightened.
- [ ] All 6 actionable items shipped; coverage ≥ 85% project-wide (≥90% on parser/, ≥85% on copy/).
- [ ] All five CI gates green (pytest, ruff check, ruff format --check, mypy, bandit).
- [ ] Closing `/audit` returns clean.
- [ ] Closing `/indie-review` returns clean (FP07-introduced drift folds inline as Cluster R per FP02 / DS01 / FP05 / FP06 precedent; net-new findings on surrounding code spawn the next-free FP## per `/close-phase`).
- [ ] CHANGELOG `[Unreleased]` updated with FP07 highlight; ROADMAP FP07 ticked ✅; journal at `docs/journal/FP07.md` written.
- [ ] Tagged `FP07-complete` (annotated); pushed to `origin/main` (PUBLIC repo).

## Architecture notes

- **No new modules.** Smallest fix-pass yet (5 one-line edits + 5 tests).
- **A4/A5 single-point-of-change.** Fixing the `__str__` / `__init__` rendering at the base class covers ~10 raise sites without per-site edits. Future call sites added to either module inherit the fix automatically; this is the *right* level of abstraction for the change (Rule of Three's intent — when 5+ near-identical sites would be touched, fix at the base instead).
- **No public API rename or removal.** Path-quoting is observable to humans (paths now visibly quoted) but not to machine-readable consumers (no caller in the project parses these strings; `match=` patterns in tests don't reference path content).
- **Forward-compatibility.** This batch lands the path-quoting contract uniformly across `cli/`, `filter/`, `copy/`, `parser/`. P04's HTTP API (FastAPI) will inherit the contract: any error message returned in a JSON response stays single-line and free of terminal control bytes. **Codebase precedent already exists:** `cli/__init__.py:127`'s assertion-message uses `{args.command!r}` for the dispatch-table guard — FP07 is making the convention uniform across the error-message surface, not introducing it.

- **PreflightError audit.** A4's "covers every CopyError subclass" claim is technically true via inheritance; in practice `PreflightError` is exported from `copy/__init__.py` but never `raise`-d in `src/` at HEAD (verified by grep). Flagged here so a future reviewer doesn't read "covers PreflightError" as evidence of a real raise site.

## Deliberately not in scope

- **Per-raise-site f-string edits in `recyclebin.py`, `playlist.py`, `executor.py`.** A4's `__str__` fix covers them; touching each raise site would be 7+ duplicate edits with no behavior change.
- **The FP04 parser items** (`parser/dat.py` `_resolve_xml` OSError + fd-leak). Different surface; FP04 has its own placeholder.
- **`MappingProxyType` migration for `FilterContext`** (FP05 B6 deferred).
- **Broader fsync audit** (P09 lane).
- **Refactoring `parser/errors.py` to share a base with `copy/errors.py`.** The two hierarchies are intentionally separate (different fault domains, different per-subclass docstrings); merging is post-v1.
- **Informational `console.print(f"DAT: {args.dat}")` style output.** Rich renders these and they're not error messages — out of scope for the single-line-error-contract threat model.
