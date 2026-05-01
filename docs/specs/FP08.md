# FP08 — `runner.py:233` warning path-quoting

- **Status:** 🚧 active (opened 2026-05-01)
- **Kind:** review-fix (single-site path-quoting; same threat-model as FP06 B3 / FP07 A4)
- **Source:** FP07 closing `/indie-review` 2026-05-01 (M2).
- **Theme:** smallest fix-pass yet — one source edit + one regression test. The site `copy/runner.py:233` interpolates `old_zip.name` raw into a warning message; `old_zip` flows from `plan.dest_dir / f"{replaced_short}.zip"` where `replaced_short = decision.replaces` is an `AppendDecision.replaces` value sourced from DAT machine short names. Same value-flow class as the FP06 B3 path-quoting and FP07 A4 typed-error rendering, just at a different output surface (warning list serialised into the JSON copy report and rendered in the CLI status line).
- **Dependencies:** FP07 ✅. (FP04 — parser hardening — has no overlap.)
- **Out of scope:** parser items (FP04 surface); the sibling warning at `copy/runner.py:140` (`f"existing playlist could not be parsed (will be overwritten): {exc}"`) — `{exc}` is a `PlaylistError` whose path component is now repr-quoted post-FP07 A4 and whose message component is a literal string ("failed to parse playlist:" etc.), so no user-controlled string flows in raw; out of scope on threat-model grounds.

## Why a single-bullet fix-pass

One actionable finding from FP07's closing review. Folding into a fresh fix-pass (rather than back into FP07 as Cluster R) because FP07's commit + tag already shipped — the `runner.py:233` site is *surrounding code* that FP07's audit didn't catch and FP07's patches didn't introduce. Per the FP06/FP07 precedent, surrounding-code findings spawn the next-free FP##; fix-pass-internal drift folds inline as Cluster R.

## Audit pattern that produced this

The FP07 indie-review audit traced value flow rather than grep pattern. For `runner.py:233`:

1. **Output destination?** `warnings: list[str]` accumulates messages that are stored in `CopyReport.warnings: tuple[str, ...]` (frozen Pydantic model), serialised to JSON in the copy report file, and rendered in the CLI status line via `console.print(f"  warnings: {len(report.warnings)}")` (count only — but the JSON report is the load-bearing surface).
2. **Where does the interpolated value come from?** `old_zip.name` is `f"{replaced_short}.zip"`'s basename → `replaced_short` → `decision.replaces` (an `AppendDecision` Pydantic-validated field) → constructed by the caller of `run_copy(plan)` who builds `AppendDecision(kind=..., replaces=<short_name>)` from DAT machine short-name strings.
3. **Could the value contain a control byte?** Yes — the path-component is constrained to filesystem-valid bytes (which include LF on POSIX), and the basename embedding goes through `f"{replaced_short}.zip"` raw. Plus the JSON serialisation of a literal LF in a warning string round-trips through `json.dumps` as the escaped form `"\n"`, so consumers reading the JSON report see escaped LF — but the *in-memory* warning list and the *CLI rendering* both hold the raw byte. A future `--report-warnings` CLI flag, a future log line that does `for w in report.warnings: logger.warning(w)`, or a future GUI panel that renders the warning list to a terminal-styled view would all leak the raw byte.

The fix at the call site (`{old_zip.name!r}`) is one line.

## Scope

### Tier 1 — single site (1)

- **A1 — `copy/runner.py:233` `recycle of {old_zip.name} failed` warning quoting.** `warnings.append(f"recycle of {old_zip.name} failed: {exc}")` → `warnings.append(f"recycle of {old_zip.name!r} failed: {exc}")`. `old_zip.name` is a `str` (the basename component of a `Path`); `repr(str)` returns the bare-quoted form (e.g. `'evil\\nname.zip'` for a name with embedded LF). The `{exc}` portion is a post-FP07-A4 `CopyError` subclass that already renders any embedded path via `repr()`; no further changes needed there.

## Tests to write first (Step 3)

1. **A1** — `test_recycle_failure_warning_quotes_path` (`tests/copy/test_fp01_fixes.py` — extend, since the recycle-failure-path warning logic lives near the existing FP02 fix-tests there). Construct a `CopyPlan` whose `append_decisions` triggers the recycle path; mock `recycle_file` to raise `RecycleError`; build a winner whose `replaced_short` contains `\n`; run via `run_copy`. Assert (a) the resulting `report.warnings` list contains exactly one warning; (b) the warning string contains `"evil\\nname.zip"` (escaped form what `repr()` produces); (c) the warning string does NOT contain a literal LF byte (`assert "evil\nname.zip" not in warning`).

   This is more setup than the typical FP## test — `run_copy` is the integration-shaped entry point — so reuse the existing `test_overwrite_replace_with_recycle_*` fixtures from `test_fp01_fixes.py` as the scaffold and override the LF-bearing `replaced_short`.

   **Alternative simpler unit-level test** (acceptable; choose one): bypass `run_copy` and directly call the warning-construction site in isolation. Per the FP06 R2 lesson on test-fragility — *audit by value flow, not by grep pattern* — the right test is the one that exercises the actual contract under the actual call path. The integration test is preferred. **Decision: integration test in `tests/copy/test_fp01_fixes.py`**.

   ```python
   def test_recycle_failure_warning_quotes_short_name_with_control_byte(
       tmp_path, source_dir, dest_dir, monkeypatch,
   ):
       """FP08 A1 — `runner.py:233`'s recycle-failure warning must quote
       the offending zip's basename via `repr()` so a control byte in a
       DAT machine short-name can't leak into the JSON copy report or the
       CLI status line as a literal LF.
       """
       from mame_curator.copy import run_copy, RecycleError
       from mame_curator.copy.types import (
           AppendDecision, AppendDecisionKind, ConflictStrategy, CopyPlan,
       )

       # Pre-create the existing zip the recycle-replace path will try to
       # move out of the way — its basename embeds a literal LF.
       evil_short = "evil\nname"
       (dest_dir / f"{evil_short}.zip").write_bytes(b"old")

       # Stage a winner whose append_decision REPLACE_AND_RECYCLE points at
       # the LF-bearing existing zip; force `recycle_file` to fail so the
       # warning fires.
       def _fail_recycle(*_a, **_kw):
           raise RecycleError("simulated", path=Path("simulated"))

       monkeypatch.setattr(
           "mame_curator.copy.runner.recycle_file", _fail_recycle,
       )

       # Build a minimal CopyPlan whose append_decisions set causes the
       # runner to enter the REPLACE_AND_RECYCLE branch on the LF-bearing
       # short-name. (Reuses test_overwrite_replace_with_recycle scaffold
       # patterns from this same file; details elided.)
       # ... plan construction ...

       report = run_copy(plan)
       assert len(report.warnings) == 1
       w = report.warnings[0]
       # Post-fix: repr-escaped form (Python source `\\n` = backslash + n).
       assert "evil\\nname.zip" in w
       # Strict: literal-LF form must NOT appear (FP07 R1 contract).
       assert "evil\nname.zip" not in w
   ```

   **Implementation note:** the test scaffold may be heavier than the fix itself; that's accepted given the integration-shaped contract under test. If the existing `test_fp01_fixes.py` already has a `_make_replace_recycle_plan(...)` helper (or equivalent), reuse it with the LF-bearing short-name. If not, add a small helper inline.

### Cluster R — closing-review drift (1)

- **R1 — `runner.py:92` BIOS-warning list-comp quoting (scope error caught by closing review).** FP08's initial audit grepped `warnings.append(f"...")` and found 2 hits (lines 140, 233 — A1 fixed 233, 140 was correctly out-of-scope). The closing `/audit` + `/indie-review` pass flagged a third site at `runner.py:92`: `warnings: list[str] = [f"{w.name}: {w.kind}" for w in bios_warnings]` — same value-flow class as A1 (BIOS short-name from DAT data → `warnings` list → JSON copy report + CLI status line) but using the list-comprehension form rather than `.append`. Same fix shape: `f"{w.name!r}: {w.kind}"`. Folded inline as Cluster R per the FP06 R2 precedent (scope errors in the same fix-pass's audit fold inline; surrounding-code drift spawns the next FP##). New regression test `test_bios_resolution_warning_quotes_short_name_with_control_byte`. **Audit-pattern lesson** (logged for future fix-passes): grep for `warnings: list[str]\s*=` and `warnings.append` *both*; or trace the value-flow into `CopyReport.warnings` to find every emit-site.

## Acceptance criteria

- [ ] **Tier 1 (1):** A1 — `runner.py:233` quoted; test passes.
- [ ] **Cluster R (1):** R1 — `runner.py:92` quoted; regression test pins the contract.
- [ ] All 2 actionable items shipped; coverage holds (`copy/` ≥85%; both sites are on warning-emit branches that pre-existing tests already exercise).
- [ ] All five CI gates green.
- [ ] Closing `/audit` returns clean.
- [ ] Closing `/indie-review` returns clean.
- [ ] CHANGELOG `[Unreleased]` updated; ROADMAP FP08 ticked ✅; journal at `docs/journal/FP08.md`.
- [ ] Tagged `FP08-complete`; pushed.

## Architecture notes

- **No new modules.** Smallest fix-pass yet — 1 source line + 1 test.
- **Test scope.** Integration test that exercises the real warning-emit path in `run_copy`. Test fixture pre-creates the LF-bearing existing zip; production code remains unaware of the LF (the runner just sees `Path` objects).
- **No public API change.** Warning string format is observable to humans (path now visibly quoted) but no caller in the project parses warning strings. JSON serialisation of the warning round-trips through `json.dumps`, which already escapes control bytes — so the JSON report is unchanged for clean-name cases and now safer for control-byte cases.

## Deliberately not in scope

- **The FP04 parser items** (`parser/dat.py` `_resolve_xml`).
- **Sibling warning at `runner.py:140`** (`{exc}` is a typed-error already repr-quoted post-FP07 A4; literal-message component is constant; no user-controlled string flows in raw).
- **A `runner.py`-wide audit for other warning emits with user-controlled value flow.** Verified by grep: `warnings.append(f"...")` returns exactly two hits at lines 140 and 233. Out-of-scope sweep complete.
- **Refactoring the warning-emit shape across `copy/`.** Out of scope; threading user-friendly warnings through a structured `Warning` model instead of free-form strings is a post-v1 enhancement.
