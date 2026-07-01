# MAME Curator — Audit allowlist

> **Status:** Empty until first confirmed false positive.
> **Bar for entry:** high — every entry requires written
> reasoning. Future audits re-verify the suppression is still
> warranted.
> **Scope:** project-specific.

This file is the **closed-loop memory** for `/audit` and
`/indie-review` false positives. Without it, the same false
positive gets surfaced and dismissed every audit run, burning
tokens and tempting "skip without thinking" reflexes.

The
[app-workflow skill](~/.claude/skills/app-workflow/SKILL.md)
reads this file **before** triaging audit findings, so
already-confirmed false positives are discarded without
re-evaluating.


## How entries are added

When `/audit` or `/indie-review` produces a finding F that
triage classifies as a tool false positive (verified, not just
dismissed):

1. Add an entry to this file with the rule, location,
   reasoning, date, and confirming phase.
2. Apply a tool-level suppression where the toolchain supports
   it — `# noqa: <RULE>` for ruff, `# nosec BNNN  # <reason>`
   for bandit (the project's coding-standards § 1 already
   requires the inline reason on bandit suppressions) — and
   cite this allowlist entry by number in the suppression
   comment.
3. Log the false positive inline in the active phase's
   `docs/journal/<ID>.md`.


## How entries are revoked

If a previously-allowlisted finding turns out to be a real
issue:

1. Update the entry's `Status:` to `revoked YYYY-MM-DD` with
   reasoning.
2. Remove the tool-level suppression in code.
3. Fold the finding into the next fix-pass like any actionable
   issue.

Do not delete revoked entries — the history is the value.


## Format

```markdown
## allowlist-NNN — <rule>:<location> short summary

- **Status:** active | revoked YYYY-MM-DD (<reason>)
- **Tool / rule:** e.g. ruff:S301, bandit:B410, indie-review:R-7
- **Location:** file:line, or finding signature
- **Why this is a false positive:** one paragraph. Be specific.
- **Suppression applied:** none | inline (cite syntax used)
- **Logged:** YYYY-MM-DD
- **Confirmed by phase:** P##/FP##/etc.
```


## Entries


## allowlist-001 — indie-review:`_preferred_score` substring vs fnmatch

- **Status:** active
- **Tool / rule:** indie-review (pre-P03 sweep round 3, 2026-04-27); also flaggable by readers comparing against `drop_*` rules.
- **Location:** `src/mame_curator/filter/picker.py:61-67` (`_preferred_score`).
- **Why this is a false positive:** the picker's `_preferred_score`
  intentionally uses substring (`patterns in name.lower()`) rather than
  `fnmatch`. The project's filter spec pins this as an intentional
  asymmetry against `drop_*` rules (which do use `fnmatch`): preferred
  scoring is a soft, descriptive boost ("does the name *contain* the
  preferred token") whereas drop predicates are strict pattern matches
  ("does the name match this glob"). The intent comment lives at
  `picker.py:64-65`. Future audits should pre-discard this finding.
- **Suppression applied:** none (no inline marker; this allowlist entry
  IS the suppression mechanism for design-intent false positives).
- **Logged:** 2026-05-01
- **Confirmed by phase:** DS01.


## allowlist-002 — eslint `react-hooks/incompatible-library` on `useVirtualizer`

- **Status:** active
- **Tool / rule:** eslint `react-hooks/incompatible-library` (FP11 closing /audit, 2026-05-02).
- **Location:** `frontend/src/components/library/LibraryGrid.tsx:35` (`useVirtualizer({ ... })`).
- **Why this is a false positive:** the lint rule warns that `@tanstack/react-virtual`'s `useVirtualizer` returns functions that cannot be safely memoized by the React Compiler. This is documented and intentional behaviour of the library — every grid + list virtualizer has the same shape (the returned `getVirtualItems()` is intentionally non-stable so consumers re-render on scroll). The warning is a generic library-compat advisory, not a project-level defect; the spec mandates `@tanstack/react-virtual` (P06.md § Toolchain).
- **Suppression applied:** none — the rule emits only a `warning`, not an `error`, and is correct to surface as a project-onboarding hint. Future contributors who pipe values from the virtualizer through a `useMemo`-d child should heed the warning; the audit-fold check should pre-discard it.
- **Logged:** 2026-05-02
- **Confirmed by phase:** FP11.


## allowlist-003 — eslint `react-refresh/only-export-components` on shadcn-generated UI primitives

- **Status:** active
- **Tool / rule:** eslint `react-refresh/only-export-components` (FP11 closing /audit, 2026-05-02).
- **Location:** `frontend/src/components/ui/button.tsx:64`, `frontend/src/components/ui/tabs.tsx:89`.
- **Why this is a false positive:** these files are generated verbatim by `npx shadcn add` and ship with both the React component AND a sibling `cva()` variants helper or sub-component constant. The Fast-Refresh-only-components rule fires because of the non-component co-export. The project does not author these files — they are vendored as-is per shadcn's distribution model — so refactoring them to satisfy the lint rule diverges from the upstream registry and breaks the next `shadcn add`'s diff. Project-authored files MUST follow the rule; shadcn-generated files in `src/components/ui/` are exempt by virtue of being vendored.
- **Suppression applied:** none — the lint rule's noise on vendored output is the cost of using shadcn; this allowlist entry IS the suppression mechanism.
- **Logged:** 2026-05-02
- **Confirmed by phase:** FP11.


## allowlist-004 — semgrep `dangerouslySetInnerHTML` on FP16 § D DOMPurify-sanitized HelpPage render

- **Status:** active
- **Tool / rule:** semgrep `dangerouslySetInnerHTML from non-constant definition` (ants-audit v0.7.77, 2026-05-04).
- **Location:** `frontend/src/pages/HelpPage.tsx` — the `dangerouslySetInnerHTML` call inside the `<article>` block (grep `dangerouslySetInnerHTML` in the file for the current line). FP25-I (2026-05-11) refactored from the global `DOMPurify` to a scoped `helpSanitizer = DOMPurify(window)` factory, so the call now reads `helpSanitizer.sanitize(topicHtml, HELP_SANITIZE_CONFIG)`; line citations rot fast as the surrounding hooks evolve.
- **Why this is a false positive:** the value passed to `dangerouslySetInnerHTML` is `sanitizedHtml`, computed via `useMemo(() => helpSanitizer.sanitize(topicHtml, HELP_SANITIZE_CONFIG), [topicHtml])`. FP16 § D added DOMPurify@3.4 to close the FP11 § H4 security debt this rule re-flags; FP20-L tightened the config (`ALLOWED_URI_REGEXP = /^(?:https?|mailto):/i`, `FORBID_TAGS = ['style', 'form']`, `FORBID_ATTR = ['style']`, `forceKeepAttr` hook for `target="_blank"` paired with an `afterSanitizeAttributes` hook setting `rel="noopener noreferrer"`, plus a `data:` URL strip on IMG/SOURCE/AUDIO/VIDEO/TRACK closing the DOMPurify `DATA_URI_TAGS` bypass). FP25-I scoped those hooks to the `helpSanitizer` instance so they don't leak to the global default; FP25-J strengthened the data-URL test to a deterministic outcome. FP26-Q/R/S/T Playwright walkthroughs additionally verify the sanitization end-to-end against the rendered DOM. Migrating to react-markdown would clear the rule but adds dependency churn for the same security guarantee.
- **Suppression applied:** none — the runtime DOMPurify call IS the suppression. This allowlist entry documents that the project's mitigation is in place.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage; re-confirmed FP20 closing-audit (2026-05-11) after FP20-L hardened the DOMPurify config; re-confirmed FP25 closing-audit (2026-05-11) after FP25-I scoped the sanitizer + FP25-J strengthened the data-URL assertion.


## allowlist-005 — grep "Weak Cryptography" on `sha1` field used as MAME ROM identifier

- **Status:** active
- **Tool / rule:** generic grep "weak cryptography" pattern (ants-audit v0.7.77, 2026-05-04).
- **Location:** `src/mame_curator/parser/models.py:26` (`sha1: str | None`), `frontend/src/api/types.ts:81/89` (mirroring schema).
- **Why this is a false positive:** the `sha1` field carries the canonical SHA-1 hash MAME embeds in every DAT entry to identify ROM dumps. Every MAME-ecosystem tool — ClrMamePro, RomVault, Pleasuredome DATs, libretro-thumbnails URL keys — uses SHA-1 the same way. It is **not** used for authentication, password hashing, signing, or any security boundary; it's a content-hash for ROM-set verification. Switching to SHA-256 would break interop with the entire ecosystem since DATs ship SHA-1.
- **Suppression applied:** none — the field name `sha1` is the file-format contract; renaming it would break parsing.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage.


## allowlist-006 — grep "Debug / Temp Code (print)" in `tools/check_api_types_sync.py`

- **Status:** active
- **Tool / rule:** generic grep "Debug / Temp Code" — print() statement detection (ants-audit v0.7.77, 2026-05-04).
- **Location:** `tools/check_api_types_sync.py:281, 288, 290`.
- **Why this is a false positive:** the project rule "print() is forbidden outside cli/" scopes RUNTIME code (where `print` bypasses the structured logging layer). `tools/` is a developer-tooling directory whose scripts are CLI-shaped utilities run from the terminal — same role as `cli/`, just lives at a separate path because it's not part of the shipped wheel. `tools/check_api_types_sync.py` is the CI-time API-types-drift gate; its prints go to stdout (success line) and stderr (per-finding line via `file=sys.stderr`) by design. The script's role IS to print to humans.
- **Suppression applied:** none — this allowlist entry IS the suppression. If `tools/` ever houses runtime code, the entry should be revoked.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage.


## allowlist-007 — grep "Test-Health (skipped)" on `pytest.mark.skipif sys.platform == "win32"`

- **Status:** active
- **Tool / rule:** generic grep "Test-Health (skipped / disabled / only)" (ants-audit v0.7.77, 2026-05-04).
- **Location:** `tests/api/test_fp09_fixes.py:284`.
- **Why this is a false positive:** the skip is a documented cross-platform conditional — Windows doesn't support `fsync(dir_fd)`, and `_atomic.atomic_write_bytes` short-circuits the parent-dir fsync on `OSError` for that exact reason. The test verifies the file fsync count remains ≥1 on POSIX where the dir fsync DOES work; running it on Windows would assert against a code path that doesn't exist there. The `reason=` argument cites the constraint directly. This is the correct shape for a platform-conditional regression test.
- **Suppression applied:** none — `pytest.mark.skipif(...)` with a `reason=` is the canonical mechanism the audit rule should respect.
- **Logged:** 2026-05-04
- **Confirmed by phase:** FP19 audit-triage.


## allowlist-008 — test-audit:`assert not event.wait(timeout=0.1/0.2)` negative-wait pattern

- **Status:** active
- **Tool / rule:** test-audit chunk-2 (2026-05-18) flagged HIGH "negative-wait timing assertion" in `tests/copy/test_controller.py:63, 83`.
- **Location:** `tests/copy/test_controller.py:63, 83` (`assert not unblocked.wait(timeout=0.2)`, `assert not released.wait(timeout=0.1)`).
- **Why this is a false positive:** the chunk's rationale was that a CPU-loaded CI runner could delay the worker thread's entry into `wait_if_paused()` and thus make the negative-wait return False "for the wrong reason." Analysed: when scheduling delay does occur, the worker has NOT yet set the event → `event.wait(timeout=…)` returns False → negative-wait still passes. The test's actual flake mode is in the false-pass direction (test passes even if the worker is blocked at the wrong point), not in the test-failure direction. The bug the test is designed to catch — `wait_if_paused()` failing to block when the controller is paused — would set the event during the timeout window and cause `event.wait()` to return True → negative-wait fails → bug detected. The pattern is correct as written; the chunk's HIGH rating mis-identified the failure mode.
- **Suppression applied:** none — the test pattern itself is the correct shape for a blocking-behaviour assertion absent an explicit "worker reached `wait_if_paused()`" hook (which would require modifying the SUT for testability).
- **Logged:** 2026-05-18
- **Confirmed by phase:** test-audit fold-in (2026-05-18).


## allowlist-009 — test-audit:`new Date().toISOString()` in `useCopySession.test.tsx` SSE mocks

- **Status:** active
- **Tool / rule:** grep "Determinism — wall-clock in test" pre-pass + test-audit chunk-7 (2026-05-18).
- **Location:** `frontend/src/hooks/__tests__/useCopySession.test.tsx:144, 171, 176, 181, 207` (the `ts` field of `MockEventSource.emit(...)` event payloads).
- **Why this is a false positive:** the `ts` field is passed to the mock as part of the SSE event envelope but is never asserted on. `useCopySession` itself only reads `msg.event` and `msg.payload` (confirmed by reading `useCopySession.ts`); the timestamp is unused state. No flake risk because the value is never compared to anything.
- **Suppression applied:** none — the call sites are obviously inside mock-event setup, not assertions, and the chunk agent already confirms this on a per-call-site read.
- **Logged:** 2026-05-18
- **Confirmed by phase:** test-audit fold-in (2026-05-18).


## allowlist-010 — test-audit:`regex.exec(...)` in `strings_loading.test.ts` + `LibraryPage_error_boundary.test.ts`

- **Status:** active
- **Tool / rule:** grep "Dangerous patterns (eval/exec)" pre-pass.
- **Location:** `frontend/src/__tests__/strings_loading.test.ts:53`, `frontend/src/__tests__/LibraryPage_error_boundary.test.ts:42, 57`.
- **Why this is a false positive:** these are `RegExp.prototype.exec(...)` calls, not `eval(...)` or `exec(...)` on test data. The pre-pass grep `\beval\(|\bexec\(` is over-broad. Both call-sites use `exec` on a source-code regex (`re.exec(appTsxSource)` / `openTagRe.exec(before)`) — pure string scanning, no JavaScript evaluation.
- **Suppression applied:** none — the call-site context makes the false positive obvious to a human reader. Tightening the grep pattern to `(?<![A-Za-z_])exec\(` would still match `RegExp.prototype.exec`; the right pattern would require AST-level disambiguation.
- **Logged:** 2026-05-18
- **Confirmed by phase:** test-audit fold-in (2026-05-18).


## allowlist-011 — test-audit:`@pytest.mark.parametrize(..., _COUPLED_TOOLS)` on `test_dep_pin_coupling.py:54`

- **Status:** active
- **Tool / rule:** test-audit chunk-6 (2026-05-18) flagged "collection-time file read" as part of FP04 (HIGH).
- **Location:** `tests/docs/test_dep_pin_coupling.py:54` (the `@pytest.mark.parametrize(("tool", "repo"), _COUPLED_TOOLS)` decorator).
- **Why this is a false positive:** `_COUPLED_TOOLS` is a module-level
  static tuple literal (lines 28–32) — `(("ruff", "..."), ("mypy", "..."),
  ("bandit", "..."))`. No I/O happens at parametrize-collection time. The
  reader functions `_read_uv_lock_versions()` / `_read_precommit_revs()`
  ARE called inside the test body (lines 57–58), which would surface a
  named test failure on missing files — not the unhandled collection
  exception the FP04 grouping warned about. The chunk lumped both files
  together because both live under `tests/docs/`; the real finding
  applied only to `test_no_pre_release_pins.py` (fixed in FP04).
- **Suppression applied:** none — the parametrize source IS a static tuple, which is the canonical "safe at collection" pattern.
- **Logged:** 2026-05-18
- **Confirmed by phase:** test-audit fold-in (2026-05-18).


## allowlist-012 — test-audit:`_seed_existing_playlist` + `_machine` 2-place in `test_fp01_fixes.py` / `test_fp02_fixes.py`

- **Status:** active
- **Tool / rule:** test-audit chunk-2/4 (2026-05-18) flagged as part of FP05 (MEDIUM) "fixture / handler dedup follow-ups".
- **Location:** `tests/api/test_fp01_fixes.py`, `tests/api/test_fp02_fixes.py` (cited locations).
- **Why this is a false positive:** neither file exists in the repository.
  `find tests/api -name "test_fp01*"` and `find tests/api -name "test_fp02*"`
  both return empty. The chunk may have hallucinated the file names from
  the FP## phase-ID convention common elsewhere in the project (`test_fp09_fixes.py`,
  `test_fp21_fixes.py`, etc. DO exist). There is nothing to extract.
- **Suppression applied:** none — no source to suppress against.
- **Logged:** 2026-05-18
- **Confirmed by phase:** test-audit fold-in (2026-05-18).


## allowlist-013 — test-audit:"pacman GameCard fixture 2+ copies" across frontend tests

- **Status:** active
- **Tool / rule:** test-audit chunk-7/8 (2026-05-18) flagged as part of FP05 (MEDIUM) "fixture / handler dedup follow-ups".
- **Location:** `frontend/src/components/library/__tests__/GameCard.test.tsx` (`baseCard`
  with `short_name: 'pacman'`) and `frontend/src/components/library/__tests__/CopyModal.test.tsx`
  (an unrelated `conflict: { short_name: 'pacman', existing: 'pacmanf' }` shape).
- **Why this is a false positive:** the `baseCard` `GameCardType` value in
  `GameCard.test.tsx:9-17` appears in exactly ONE file. The `'pacman'`
  occurrences in `CopyModal.test.tsx` are inside a `conflict` envelope on a
  copy-job event, not a card fixture — different type, different field
  layout, different test surface. Conflating them on the string `'pacman'`
  is a false grouping; below the Rule-of-Three threshold either way.
- **Suppression applied:** none — fixtures are correctly scoped to where
  they're used; no shared-fixture extraction is warranted.
- **Logged:** 2026-05-18
- **Confirmed by phase:** test-audit fold-in (2026-05-18).


## allowlist-014 — test-audit:`assert not done.wait(timeout=0.2)` in test_runner_lifecycle.py:51

- **Status:** active
- **Tool / rule:** test-audit chunk-5 (2026-05-18 FP31 sweep) flagged HIGH "timing-based negative assertion".
- **Location:** `tests/copy/test_runner_lifecycle.py:51` (`assert not done.wait(timeout=0.2)`).
- **Why this is a false positive:** same shape and reasoning as allowlist-008.
  The chunk's worry was that BIOS resolution + plan summary construction +
  `append_activity` + preflight inside `run_copy` could exceed 200 ms on a
  slow CI runner, racing the pause-gate check. Analysed: `done` is only
  set INSIDE the runner function AFTER `run_copy()` returns. For
  `done.set()` to fire within 200 ms, `run_copy` must have RETURNED — but
  if the controller is paused, `wait_if_paused()` blocks `run_copy` from
  returning, so `done` cannot be set. The slow-runner scenario the chunk
  imagined doesn't make the test fail; the worker just takes longer to
  REACH the pause gate, where it then blocks. The bug-detection direction
  still works: if `wait_if_paused()` is broken and doesn't block, `run_copy`
  returns and `done` is set within 200 ms → `event.wait()` returns True →
  negative-wait fails → bug detected.
- **Suppression applied:** none — the test pattern is the correct shape for a
  blocking-behaviour assertion absent an explicit "worker reached
  `wait_if_paused()`" hook (which would require modifying the SUT for
  testability — same trade-off as allowlist-008).
- **Logged:** 2026-05-18
- **Confirmed by phase:** FP31 test-audit fold-in (2026-05-18).


## allowlist-015 — audit-env `mypy` "cannot find module fastapi / yaml" across `api/`

- **Status:** active
- **Tool / rule:** `mypy` via `/audit` `audit_run` (P10 `/close-phase`, 2026-07-01).
- **Location:** every `fastapi` / `fastapi.responses` / `fastapi.exceptions` import under `src/mame_curator/api/` (e.g. `app.py:15`, `errors.py:12`, `routes/*.py`), plus `import yaml` in `api/persist.py`, `api/state.py`, `cli/commands/*.py`, `filter/*.py` (`error: Cannot find implementation or library stub for module named "fastapi" [import-not-found]` / `Library stubs not installed for "yaml" [import-untyped]`).
- **Why this is a false positive:** `audit_run` executes `mypy` server-side in a scrubbed environment **without** the project's installed dependencies (`fastapi`, `types-PyYAML`, etc. are never `uv sync`-ed into the audit runner). So `mypy` can't resolve `fastapi`/`yaml` and flags every import. The project's real type check — `uv run mypy` with deps installed, run in pre-commit AND in the CI `Lint, type-check, test` job on all 8 platform/version combos — passes clean (0 errors). These are audit-infrastructure artifacts, not type errors in the code. Every full `/audit` sweep will re-surface them until the audit runner installs project deps before invoking `mypy` (or `mypy` is dropped from the audit tool set, since CI already runs the real one).
- **Suppression applied:** none — this is a tool-environment artifact, not a real finding on real code, so there is nothing to suppress in-source. This allowlist entry IS the pre-discard mechanism for future closes.
- **Logged:** 2026-07-01
- **Confirmed by phase:** P10 `/close-phase` (folded remaining actionable findings into FP32; these 29 `mypy` warnings were the only audit output and are all this artifact).


## What does NOT belong here

- **Findings that are real but blocked by a missing feature.**
  Those go in `docs/known-issues.md`.
- **Findings the user wants to defer.** No deferral disposition
  exists outside of "blocked by dependency" — every actionable
  finding becomes a fix-pass.
- **Findings the user accepts as a permanent trade-off.**
  Those become an ADR in `docs/decisions/`.
