# FP06 — FP05 closing-review fold-in

- **Status:** 🚧 active (opened 2026-05-01)
- **Kind:** review-fix / refactor / test (mixed)
- **Source:** `/indie-review` 2026-05-01 closing-review pass on FP05's patches.
- **Theme:** four findings (A1, B1, B2, B3) plus one folded cleanup (R1, see Cluster R below — total 5 actionable items) on surrounding code (`cli/`, `filter/sessions.py`, `filter/_io.py`, `filter/overrides.py`) caught by the closing review on FP05. FP05-introduced drift (Cluster R, 6 items) closed inside FP05 itself per the FP02 / DS01 precedent; FP06 is the next-level batch — findings on code that *coexists* with FP05's patches but was not introduced by them.
- **Dependencies:** FP05 ✅. (FP04 — parser hardening — has no surface overlap and runs after FP06.)
- **Out of scope:** parser items (FP04 surface), `MappingProxyType` migration for `FilterContext` (FP05 B6 deferred), broader fsync audit (P09 lane), non-OSError tracebacks from `purge_recycle()` (e.g. `KeyboardInterrupt` mid-rmtree — those are runtime-level concerns and stay outside A1's narrow OSError scope; documented here so a future reviewer doesn't mis-flag the omission), **path-quoting in `cli/__init__.py` and `copy/recyclebin.py`** (same threat-model as B3 but on a different module surface — `_cmd_parse:139`, `_cmd_filter:187, 200`, `_cmd_copy:225, 233, 240, 260` build error messages with bare `f"{path}"`; explicitly deferred to whichever FP## naturally captures them post-FP06's closing audits — keeping FP06 scoped to `filter/`'s loaders means one cohesive surface per fix-pass and avoids scope creep). Closing-review minor LOWs that surface during FP06's own audits land inline as Cluster R if cheap, otherwise spawn the next-free FP## per `/close-phase`.

## Why a single fix-pass

All four findings share a small, semantic relationship to FP05:

- **A1** is a regression introduced by FP05 B9's `--purge-recycle` short-circuit, which sits *outside* the new `try/except OSError` block.
- **B1** is the verification test FP05 deferred — pinning the exception shape that `Sessions._active_must_reference_a_defined_session` actually surfaces under Pydantic v2's `model_validator(mode="after")` semantics.
- **B2** unifies the validator-raise convention that FP05 left split between `Session._validate_session` (raises `ValueError`) and `Sessions._active_must_reference_a_defined_session` (raises `SessionsError`).
- **B3** hardens user-controlled-string quoting in error messages added or rewritten by FP05's `_io.py` extraction (and by extension, sibling messages in `sessions.py` / `overrides.py` that share the f-string pattern). Covers both `{path}` (filesystem-controlled) and `{name}` (yaml-controlled).

Closing them piecemeal would mean two more `/audit` + `/indie-review` cycles for a four-bullet patch. One fix-pass is the right scope.

## Pydantic v2 validator semantics — load-bearing facts

These three facts are load-bearing for B1 + B2 and were verified at the Python prompt during Step 1 of this fix-pass; record them here so the test plan and the implementation reasoning don't drift apart.

1. **`ValidationError` IS-A `ValueError`** in Pydantic v2 (`isinstance(ValidationError(...), ValueError)` → True). This is why `pytest.raises((SessionsError, ValueError))` already absorbs B2's refactor without modification.
2. **`model_validator(mode="after")` raising `ValueError` does NOT set `__cause__` on the wrapping `ValidationError`.** The original `ValueError` lives at `validation_error.errors()[0]['ctx']['error']`; `validation_error.errors()[0]['msg']` carries the prefixed form (`"Value error, <original message>"`). `__cause__` is `None`. **Tests that assert the original exception must use `errors()[0]['ctx']['error']`, not `__cause__`.** (Verified at Python 3.13 / Pydantic 2.13.)
3. **A `model_validator(mode="after")` raising a non-`ValueError`/`AssertionError` exception propagates as-is** — Pydantic does not wrap it. Hence the current `Sessions._active_must_reference_a_defined_session` raising `SessionsError` skips the loader's `except ValidationError → SessionsError(f"{path}: ...")` rewrap entirely, surfacing without path context. B2 fixes this.

**Constraint contract.** All three facts hold for **Pydantic 2.x** as of 2.10–2.13. The project's `pyproject.toml:30` pins `pydantic>=2.10` (no upper bound). A future `pydantic>=3.0` resolve could silently invalidate fact 1 (ValidationError IS-A ValueError) and therefore break B2's "no test breakage" argument. This fix-pass does **not** tighten the pin (a `<3` cap touches dependency-resolution surface that is not part of FP06's scope), but logs the constraint here so a future `pydantic 3` upgrade is forced through a fresh re-verification of B1/B2/R1 before the upgrade lands. Whoever bumps to 3.x must re-run B1a's structural assertion (`exc.errors()[0]['ctx']['error']`) and the existing `pytest.raises((SessionsError, ValueError))` patterns to confirm they still absorb `ValidationError`.

## Scope

### Tier 1 — real bug (1)

- **A1 — `purge_recycle()` OSError leak in `_cmd_copy`.** `cli/__init__.py:215-218` calls `purge_recycle()` *before* the FP05 B9 `try/except OSError` block (which starts at line 220). A user with an unreadable recycle directory (perm-denied, broken symlink, NFS hiccup) gets a Python traceback instead of a clean `error:` line + exit 1. The DS01 C6 / FP05 B9 contract (`cli/spec.md` § "Errors the CLI catches but never raises") is broken on this single short-circuit path. **Fix:** wrap the `if args.purge_recycle:` branch in its own `try/except OSError` block that mirrors the B9 pattern (red `error:` prefix on stderr, exit 1). **Why a separate try, not relocation into B9's try:** B9's try block (lines 220-234) is reserved for parser-input loading (`parse_dat`, `parse_listxml_*`) and consumes those bound variables in subsequent code. The purge short-circuit returns *before* any parser machinery runs and shares no variables; folding it inside would expand B9's try to cover unrelated code and obscure the early-return. The flat outer try is one block per error class — easier six-month-test reading.

### Tier 2 — hardening (3)

- **B1 — Lock-in tests for `Sessions` exception-shape contract.** FP05 left the exception-shape contract underdocumented; the loader's `try: Sessions(...) except ValidationError → SessionsError` wrap at `sessions.py:132-135` may or may not fire depending on whether the validator raises `ValueError` (Pydantic-wrapped → caught) or `SessionsError` (propagates as-is → bypassed). After B2 lands, this test pins the post-B2 contract: (a) direct `Sessions(active="bogus", sessions={"only": <valid>})` raises `ValidationError` (a subclass of `ValueError` per Pydantic v2); the original message lives at `exc.errors()[0]['ctx']['error']`. (b) `load_sessions(<bad yaml>)` raises `SessionsError` whose message contains the file path. The test exists independent of B2's refactor — it documents the contract a future reader can rely on without rerunning the `model_validator(mode="after")` semantics in their head.
- **B2 — Unify validator-raise convention.** Currently `Session._validate_session` raises `ValueError`; `Sessions._active_must_reference_a_defined_session` raises `SessionsError`. Both are `model_validator(mode="after")`. Per the Pydantic facts above, `Sessions` users see `SessionsError` directly, bypassing the `try/except ValidationError → SessionsError` wrap at `sessions.py:132-135`. **Fix:** change `Sessions._active_must_reference_a_defined_session` to `raise ValueError(...)` instead of `raise SessionsError(...)` (3 raise sites: lines 70, 72, 74). Pydantic wraps; the loader's existing `except ValidationError → SessionsError(f"{path}: {exc}")` rewrap fires; user sees path-prefixed `SessionsError`. Direct construction now raises `ValidationError` matching `Session`. **Caller-impact audit (verified 2026-05-01):** no production code constructs `Sessions(...)` directly; the project-internal callers are `cli/__init__.py:177` (no-arg construction `Sessions()` — unaffected) and the `sessions.py:81, 91, 133` paths (loader-internal; the bare `Sessions()` no-arg paths are unaffected, line 133 is the loader's wrapped-construction site itself). Test callers: `tests/filter/test_runner.py:127, 204` (valid kwargs, no exception expected) and `tests/filter/test_sessions.py:99, 166` (already use `pytest.raises((SessionsError, ValueError))` which absorbs `ValidationError` since it extends `ValueError` in v2). No test breakage.
- **B3 — Quote user-controlled strings via `repr` in error messages.** Two sub-classes:
  - **Path-quoting (10 sites):** `_io.py:32, 35, 40` and `sessions.py:86, 93, 107, 135` and `overrides.py:35, 41, 45` build error messages with bare `f"{path}"`.
  - **Name-quoting (2 sites):** `sessions.py:50, 125` build messages with bare `f"'{name}'"` interpolations. The session name comes from the YAML file (user-controlled) and shares the same threat model as the path: newlines or terminal escapes break the single-line error contract and could obscure or spoof legitimate error text. (`sessions.py:115` is a static-string raise — `"session keys must be non-empty strings"` — with no interpolation; not in scope.)

  **Fix:** use `f"{path!r}"` and `f"{name!r}"` everywhere these user-controlled values appear in a typed loader error message. Python's `Path.__repr__` and `str.__repr__` quote the underlying string, escaping `\n`, `\x1b`, etc. naturally — verified at the prompt: `repr(Path('foo\nname.yaml'))` → `"PosixPath('foo\\nname.yaml')"`; `repr(Path('evil\x1b[31m.yaml'))` → `"PosixPath('evil\\x1b[31m.yaml')"`. Existing tests that match on substring (e.g. `match="failed to parse"`, `match="not a YAML mapping"`) continue to pass — none of them match on the path or name representation itself. Audit confirms no test in `tests/filter/test_sessions.py` or `tests/filter/test_overrides.py` uses `match=` against path or name content.

## Tests to write first (Step 3)

In rough TDD order (failing first):

1. **A1** — `test_cmd_copy_purge_recycle_oserror_surfaces_clean` (`tests/copy/test_cli_copy.py`). Follow the existing `test_copy_cli_purge_recycle_short_circuits` pattern at `tests/copy/test_cli_copy.py:64-86` for argparse construction. Use a plain helper for the monkeypatch — no generator-throw cleverness:

   ```python
   def _raise_oserror(*_a, **_kw):
       raise OSError("permission denied")

   def test_cmd_copy_purge_recycle_oserror_surfaces_clean(
       tmp_path, monkeypatch, capsys
   ):
       monkeypatch.setattr("mame_curator.cli.purge_recycle", _raise_oserror)
       parser = build_parser()
       args = parser.parse_args([
           "copy", "--dry-run",
           "--dat", str(tmp_path / "x.xml"),
           "--listxml", str(tmp_path / "x.xml"),
           "--filter-report", str(tmp_path / "x.json"),
           "--source", str(tmp_path),
           "--dest", str(tmp_path),
           "--purge-recycle",
       ])
       assert run(args) == 1
       err = capsys.readouterr().err
       assert "error:" in err
       assert "Traceback" not in err
   ```

   The monkeypatch target is the bound name `mame_curator.cli.purge_recycle`, not the source module `mame_curator.copy.recyclebin.purge_recycle` — the CLI imports `purge_recycle` from `mame_curator.copy` at `cli/__init__.py:24`, and it's that bound name we need to swap. The helper-function form survives future call-shape changes; a generator-throw lambda would silently no-op if `dirs, freed = purge_recycle()` were ever rewritten as `result = purge_recycle()` without iteration. Pre-fix this fails because the `OSError` propagates up to pytest as an uncaught exception (test errors out rather than getting a clean exit-1).

2. **B1a** — `test_direct_sessions_construction_raises_validation_error_on_bad_active` (`tests/filter/test_sessions.py`). Build a valid `Session(include_genres=("X*",))`. Direct-construct `Sessions(active="bogus", sessions={"only": <valid_session>})`. Assert `ValidationError` is raised. Pin two checks (loose first, strict second):

   ```python
   with pytest.raises(ValidationError) as exc_info:
       Sessions(active="bogus", sessions={"only": valid})
   # Loose primary check — survives Pydantic patch-version wrapping changes.
   assert "active session 'bogus' is not defined" in str(exc_info.value)
   # Strict structural check — pins the v2.x ctx.error shape; remove if it
   # ever breaks across a Pydantic minor without behaviour change.
   inner = exc_info.value.errors()[0]["ctx"]["error"]
   assert isinstance(inner, ValueError)
   ```

   The test pins (a) the wrapping type is `ValidationError` (not bare `ValueError`, not `SessionsError`) — the only way this can be `ValidationError` is if the validator raised `ValueError` (post-B2); pre-B2 it raises `SessionsError` and the test fails because `pytest.raises(ValidationError)` catches a different exception. (b) The original validator message survives the wrap. **Do not** assert via `__cause__` — Pydantic v2 leaves it `None` (verified at the prompt against Pydantic 2.13).

3. **B1b** — `test_load_sessions_wraps_validation_error_with_path_context` (`tests/filter/test_sessions.py`). Write a tmp YAML file with `active: bogus\nsessions: {}` content. Call `load_sessions(tmp_path)`. Assert `SessionsError` raised; `str(exc.value)` contains both `repr(tmp_path)` (path quoted) **and** the validator's "not defined" wording. This pins the loader-path post-B2 + post-B3 contract end-to-end.

4. **B3a** — `test_read_capped_text_path_with_newline_in_error_is_quoted` (`tests/filter/test_io.py` — NEW file). Construct a path whose name contains `\n` and write enough bytes to exceed the 1 MiB cap. Exact assertions (the literal-vs-escaped distinction is the bug B3 exists to catch — spell it out):

   ```python
   bad = tmp_path / "evil\nname.yaml"
   bad.write_bytes(b"0" * (1024 * 1024 + 1))  # exceed 1 MiB cap
   with pytest.raises(ValueError) as exc_info:
       read_capped_text(bad, exc_cls=ValueError)
   msg = str(exc_info.value)
   # Post-fix: message contains the escaped form `repr(path)` produces.
   assert "evil\\nname.yaml" in msg   # source `\\n` = backslash-n, 2 chars
   # Strict: no literal LF byte in the message.
   assert "\n" not in msg              # source `\n` = LF, 1 char
   ```

   The two assertions verify opposite forms: `"evil\\nname.yaml"` (Python source: `e v i l \ n n a m e . y a m l`, 14 chars) is what `repr(Path("evil\nname.yaml"))` produces; `"\n"` (Python source: one LF byte) is what the unfixed code interpolated. Pre-fix the LF assertion fails (literal LF in message); post-fix the escaped-form assertion holds.

5. **B3b** — `test_read_capped_text_size_cap_error_quotes_path_with_escape`. Same shape, path contains an ANSI escape:

   ```python
   bad = tmp_path / "evil\x1b[31m.yaml"
   bad.write_bytes(b"0" * (1024 * 1024 + 1))
   with pytest.raises(ValueError) as exc_info:
       read_capped_text(bad, exc_cls=ValueError)
   msg = str(exc_info.value)
   assert "\\x1b" in msg or "evil\\x1b[31m" in msg  # repr-escaped form
   assert "\x1b" not in msg                          # no literal ESC byte
   ```

   Verified at the prompt that `repr(Path('evil\x1b[31m.yaml'))` does escape `\x1b` → `\\x1b` (Python 3.13). The first assertion uses `or` to accommodate Python-version drift in repr's exact output formatting; the second (no literal ESC) is the load-bearing terminal-spoofing defense.

6. **B3c** — `test_load_overrides_invalid_mapping_quotes_path` (`tests/filter/test_overrides.py`). Use the same `tmp_path / "evil\nname.yaml"` pattern; write a non-mapping body (`bad.write_text("- a\n- b\n", encoding="utf-8")` — a YAML list, which trips `overrides.py:41`'s "is not a YAML mapping" path). Assert `OverridesError` message contains `"evil\\nname.yaml"` and does NOT contain a literal `\n` byte. Confirms the parallel fix in `overrides.py`.

   **Filesystem-portability skip clause** (applies to B3a + B3b + B3c — share the helper). Wrap the `bad.write_text(...)` (or `write_bytes` for B3a/B3b) call in `try: ... except OSError: pytest.skip("filesystem rejects \\n in path names")`. ext4/btrfs/xfs accept `\n` (POSIX permits any byte except `\0` and `/`); exotic FS layers (some FUSE wrappers, NTFS via `ntfs-3g`) may reject — we don't crash the suite for that.

7. **B3d (name-quoting)** — `test_session_with_control_char_in_name_quoted_in_error` (`tests/filter/test_sessions.py`). The fixture YAML must contain the two-character sequence `\n` (backslash + letter `n`) inside a double-quoted scalar — PyYAML's scanner decodes that to a literal LF at parse time. Use a Python raw-string or escaped-string to write the file:

   ```python
   fixture = (tmp_path / "sessions.yaml")
   # Note: write `\\n` in Python source so the file gets literal `\n` (backslash-n);
   # PyYAML then decodes that to one LF byte. Verified at the prompt: the resulting
   # parsed key is `'evil\nname'` (LF in the middle), tripping sessions.py:125.
   fixture.write_text(
       'active: "evil\\nname"\n'
       'sessions:\n'
       '  "evil\\nname": 42\n',     # body is non-mapping → trips sessions.py:125
       encoding="utf-8",
   )
   with pytest.raises(SessionsError) as exc_info:
       load_sessions(fixture)
   msg = str(exc_info.value)
   assert "evil\\nname" in msg  # escaped form `repr(name)` produces
   assert "\n" not in msg        # no literal LF in the rendered message
   ```

   Tests `sessions.py:125`'s `{name}` quoting. (The fixture-content gotcha — Python's `\\n` in source becomes one backslash-n in the file, which PyYAML then decodes to LF — is the kind of detail that costs 30 minutes at implement time without an explicit example.)

B2 has no dedicated test — B1a + B1b together cover the contract change. The lookup of `errors()[0]['ctx']['error']` in B1a is what verifies B2 happened (pre-B2 the validator raises `SessionsError` directly, so `Sessions(active="bogus", ...)` raises `SessionsError` instead of `ValidationError` and the test's `pytest.raises(ValidationError)` would fail).

**Coverage hold rule.** All new tests live under existing high-coverage modules (`filter/` ≥95%, `copy/` ≥85%, `cli/` is part of CLI coverage). Spot-check that `filter/_io.py`'s coverage stays at 100% — the new B3a + B3b tests should hit the size-cap branch (B3a + B3b) and the OSError branch is already covered by existing test_sessions.py / test_overrides.py tests.

### Cluster R (cold-eyes + closing-review drift, folded inline)

Two rounds folded inline per the FP02 / DS01 / FP05 precedent (FP06-introduced drift folds into the same fix-pass):

- **R1 — Fix the misleading `__cause__` docstring at `sessions.py:27-30` and add a sibling note on `_active_must_reference_a_defined_session`.** FP05 left the comment `"# 'from_raw' wraps the raised 'ValueError'/'ValidationError' into 'SessionsError'; direct callers see Pydantic's 'ValidationError' with this 'ValueError' as '__cause__'."` The `__cause__` claim is wrong (Pydantic v2 leaves `__cause__=None`; the original `ValueError` is at `errors()[0]['ctx']['error']`). Reword to: `"... direct callers see Pydantic's 'ValidationError'; the original 'ValueError' is accessible via 'exc.errors()[0]['ctx']['error']'."` **Plus, post-B2**, add a one-line comment above `Sessions._active_must_reference_a_defined_session` (lines 61-75) noting the same wrap behaviour applies — `raise ValueError(...) → ValidationError → loader rewraps to SessionsError(f"{path!r}: ...")`. Without the second note, a future maintainer reading just the `Sessions` validator would have to trace the same Pydantic semantics again. Pure docstring/comment fix; no behaviour change. Lands in the same patch as B1 + B2.

- **R2 — Quote `self.active` via `repr()` at `sessions.py:81` (B3 scope error).** The B3 audit catalogued 2 name-quoting sites (`sessions.py:50, 125`) but missed `sessions.py:81`, the `raise ValueError(f"active session '{self.active}' is not defined in 'sessions'")` site inside `_active_must_reference_a_defined_session`. `self.active` flows directly from YAML (loader passes `raw_obj.get("active")` to `Sessions(...)`), so a control byte in the active key leaks raw through Pydantic's `ValidationError.__str__`. Reproduced at the prompt: `Sessions(active="evil\nname", sessions={"other": Session(include_genres=("X*",))})` produces a `ValidationError` whose `__str__` contains a literal LF in the `active` value. **Fix:** rewrite as `raise ValueError(f"active session {self.active!r} is not defined in 'sessions'")`. Existing substring assertions (e.g. B1a's `"active session 'bogus' is not defined"`) survive — `repr("bogus")` is `"'bogus'"`, the same character sequence the bare quoting produced for path-clean names. Cluster R bullet count: 1 → 2; B3 site count: 12 → 13 (10 path + 3 name). New test `test_active_with_control_char_quoted_in_error` pins the post-R2 contract.

- **R3 — Strengthen B1b assertion against path-form fragility (M1 from closing review).** Original B1b assertion `assert repr(f) in msg or repr(str(f)) in msg` would pass on a clean path (no special chars) BOTH pre-fix and post-fix because `repr` of a clean string-path uses the same single-quote characters that a bare interpolation would produce. **Fix:** rewrite the test fixture path to contain `\n` (`tmp_path / "evil\nname.yaml"`); switch the assertion to `"evil\\nname.yaml" in msg` plus a strict "no literal LF in head" check. The fragility was that a future "I'll just simplify the f-string" refactor that drops `!r` from the loader's rewrap would still pass the original test on a clean fixture path. With the strengthened test it doesn't. Pure test hardening; no production-code change.

## Acceptance criteria

- [ ] **Tier 1 (1):** A1 — purge_recycle leak closed; test passes; `_cmd_copy` returns 1 with clean `error:` line on `OSError` from `purge_recycle()`.
- [ ] **Tier 2 (3):** B1, B2, B3 — validator convention unified; lock-in tests pass; user-controlled-string quoting applied at all 13 sites (10 path + 3 name, post-R2).
- [ ] **Cluster R (3):** R1 — docstring fix; R2 — `sessions.py:81` `self.active` quoting (B3 scope error caught by closing review); R3 — B1b assertion hardening against path-form fragility.
- [ ] All 7 actionable items shipped; coverage ≥ project-wide 85% holds; per-module gates respected.
- [ ] All five CI gates green (`pytest`, `ruff check`, `ruff format --check`, `mypy`, `bandit`).
- [ ] Closing `/audit` returns clean (or only confirmed false positives in allowlist).
- [ ] Closing `/indie-review` returns clean (FP06-introduced drift folds inline as a second-round Cluster R per FP02 / DS01 / FP05 precedent; net-new findings on surrounding code spawn the next-free FP## per `/close-phase`).
- [ ] CHANGELOG `[Unreleased]` updated with FP06 highlight; ROADMAP FP06 ticked ✅; journal at `docs/journal/FP06.md` written.
- [ ] Tagged `FP06-complete` (annotated); pushed to `origin/main` (PUBLIC repo per `.claude/workflow.md` § 1).

## Architecture notes

- **No new modules.** Small fix-pass; all changes land in existing files.
- **B2 surface change:** direct `Sessions(...)` construction now raises `ValidationError` instead of `SessionsError`. Production callers unaffected (audit shows none beyond no-arg `Sessions()`). Test surface absorbs via `pytest.raises((SessionsError, ValueError))` patterns already in place — `ValidationError` is a `ValueError` subclass in Pydantic v2.
- **B3 message-format change:** `f"{path}"` → `f"{path!r}"` and `f"'{name}'"` → `f"{name!r}"`. Existing `match=` patterns in tests don't reference path or name content, so no test breakage. Output format is observable to humans (now quoted) but not to machine-readable consumers (no caller in the project parses these strings).
- **A1 implementation choice:** flat top-level `try/except OSError` around the purge branch, *not* nested inside the broader B9 block. Reasoning: B9's try-block is scoped to parser-input loading and binds variables consumed downstream; the purge short-circuit returns before any of that runs. Flat outer try keeps each block focused on one error class.
- **No public API rename or removal.** All changes are additive (path/name quoting), narrowing (validator raise type), or new test coverage.

## Deliberately not in scope

- **The parser items (FP04 surface).** Different module; FP04 has its own placeholder.
- **`MappingProxyType` migration for `FilterContext`.** Deferred from FP05 B6; needs round-trip-safe serializer support.
- **Broader fsync audit at every atomic-write site.** Power-cut robustness is a P09 review lane, not FP06.
- **Refactoring `sessions.py` for readability.** Several functions could split (load_sessions has a dense main loop) but this fix-pass stays scoped to the four findings.
- **Non-OSError error handling in `purge_recycle()`.** A1's narrow OSError catch is the right scope for this fix; deeper exception coverage (e.g. `KeyboardInterrupt` mid-rmtree, or future non-OSError raises from `recyclebin.py`) is a separate exercise — flagged here so a future reviewer doesn't mis-attribute the omission.
