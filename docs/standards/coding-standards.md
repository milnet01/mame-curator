# Coding Standards — MAME Curator

**Date:** 2026-04-27
**Status:** Authoritative — all code in this repository must conform.
**Audience:** Anyone (human or AI) writing or reviewing code in this repo.

---

These standards are enforced by tooling where possible (CI gates) and by code review where not. **A pull request that violates a standard cannot merge until either the code is fixed or the standard is amended (with reasoning) in this document.**

## 0. Guiding principles

The five principles every other rule descends from:

1. **Correctness over cleverness.** A simple, obviously-correct implementation beats a clever, opaque one. If you can't explain in one sentence why the code is correct, it isn't.
2. **Shortest correct implementation.** 50 lines beats 250. No scaffolding for hypothetical futures, no abstractions where a direct call works, no error paths for impossible scenarios. Every line pays rent in legibility or function.
3. **Reuse before rewriting.** Before writing new code, look for code that does the same or similar thing. In order of preference: (a) call it directly, (b) refactor it to cover the new case then call it, (c) only if neither fits, write new code and document why.
4. **No workarounds without a root-cause fix.** Silencing warnings, `try/except: pass`, `--no-verify`, commenting out broken code, disabling checks — last resort, not default. When a workaround is genuinely the only option, leave a comment naming the underlying constraint.
5. **The six-month test.** If someone opens this file six months from now, can they understand *why* the code looks this way without the author present? If not, simplify or comment the *why* (never the *what*).

The Rule of Three: **extract a helper on the third call-site, not the first or second.** Premature DRY costs more than duplication.

---

## 1. Security

| Rule | Enforcement |
|---|---|
| No hardcoded secrets, tokens, or credentials anywhere | `gitleaks` in pre-commit + CI |
| Validate every input crossing a system boundary (HTTP, filesystem path, subprocess arg) | Pydantic models for HTTP; explicit `Path.resolve()` + allowlist for filesystem; `shlex.quote` for subprocess |
| Path-traversal protection: reject any user-supplied path that resolves outside the configured roots | Unit tests with adversarial inputs (`../../etc/passwd`, symlink chains) |
| Subprocess: never `shell=True` with interpolated input | `bandit` rule B602 in CI |
| Bandit suppressions (`# nosec BNNN`) require an inline comment naming the threat model and why it doesn't apply. Bare `# nosec` is forbidden | code review |
| Network: validate URL schemes (only `http`/`https`), pin TLS, set explicit timeouts | `httpx` with `timeout=` mandatory; CI grep blocks bare `requests.get` |
| Dependencies: pinned versions, audited weekly | `uv lock` committed; `pip-audit` + `npm audit` in CI weekly |
| No `eval`, `exec`, `pickle.loads` of untrusted data | `bandit` + grep gate in CI |
| File operations: prefer `pathlib.Path` over string paths; never use `os.path.join` with user input without resolution | Code review |
| All file writes use atomic-write pattern (write to `.tmp`, rename) where corruption matters | Code review on `copy/` and `media/` modules |

## 2. Project structure & file size

- **`src/` layout, single `pyproject.toml`.** Created with `uv init --package`. Tests in `tests/`, never inside `src/`.
- **Backend Python file size:** soft cap **300 lines**, hard cap **500 lines**. Hitting the hard cap means the file does too much — split it before adding more.
- **Frontend React component file size:** soft cap **200 lines**, hard cap **350 lines**. Hitting the hard cap means the component has too many responsibilities — extract sub-components or hooks.
- **Function size:** soft cap **50 lines**, hard cap **80 lines**. A function over 80 lines almost always wants to be 2-3 functions with intent-revealing names.
- **One concept per file.** A module named `parser.py` parses things. If you find yourself adding a `notify_user()` helper to it, it belongs elsewhere.

## 3. Python language & style

- **Python 3.12+ only.** Use modern typing syntax: `list[Foo]` not `List[Foo]`, `dict[str, int]` not `Dict[str, int]`, `X | None` not `Optional[X]`.
- **Type hints on every public function and method.** Internal helpers should still be hinted unless the inference is trivially obvious (one-line lambdas).
- **Ty / mypy strict mode** in CI. No `# type: ignore` without an inline comment naming the reason.
- **Ruff** is the only formatter and linter. Configured in `pyproject.toml`. CI runs `ruff check` and `ruff format --check`.
- **No bare `except:`**. Catch the specific exception. If catching `Exception`, log it with `logger.exception()` and re-raise or convert to a typed app-level error.
- **No silent failures.** `try: ... except: pass` is forbidden. If a failure is genuinely safe to ignore, the comment must explain *why* and the rule still applies that the exception type is named.
- **No globals, no module-level mutable state.** Use dependency injection (FastAPI's `Depends`, constructors, function parameters).
- **Prefer dataclasses / Pydantic models** over loose dicts for structured data. Use `frozen=True` on dataclasses where mutation isn't needed.
- **`async def` for I/O-bound** (network, disk where it's worth it), regular `def` for pure CPU work. Don't `async`-color a function unless it actually awaits.
- **No `print()` in source code.** Use `logging` with the module's logger. CLI surfaces use `rich` or `print()` only in dedicated `cli.py` files.
- **Constants in UPPER_SNAKE_CASE** at module top. No magic numbers / strings inline.
- **Naming:** descriptive over short. `machines_by_short_name` beats `m`. Verbs for functions (`load_dat`), nouns for data (`Machine`, `FilterDecision`).

## 4. Frontend (React/TypeScript)

- **TypeScript strict mode** (`"strict": true`). No `any` without an inline `// FIXME(type): <reason>` comment.
- **React 19 + Tailwind v4 + shadcn/ui** baseline (per research, current as of 2026).
- **Functional components only.** No class components.
- **State management:** local `useState` first, `useReducer` for complex local state, `zustand` only when state is shared across non-adjacent components. No Redux.
- **Data fetching:** `@tanstack/react-query` for all backend calls. No raw `fetch` in components.
- **Error boundaries** at major surface boundaries (route, modal, drawer).
- **Accessibility:** every interactive element keyboard-reachable; ARIA labels on icon-only buttons; `axe-core` test in CI for the main pages.
- **No inline styles** beyond one-off positional tweaks. Tailwind classes via `className`. Reusable patterns extracted into shadcn primitives.
- **No emojis as functional UI** (decorative only); use proper icons (`lucide-react`).
- **Use shadcn `Switch` for binary preferences, not `Checkbox`.** Mac-style on/off switches are clearer for "this setting is on or off" semantics. Reserve `Checkbox` for cases where checkbox semantics genuinely fit — multi-selecting items in a list, "I have read the terms" affirmations.
- **Destructive actions require an `AlertDialog` confirmation** with: the exact thing being destroyed, whether/how it's reversible, and a distinct primary button label (never just "OK"). Examples: "Delete 3 files from drive", "Discard playlist and overwrite". Drive-side deletes go to a 30-day recycle directory, never directly unlinked.
- **All user-facing strings live in a single module/file** (`frontend/src/strings.ts` or similar) so a future i18n pass is a config change, not a refactor.

## 5. Comments and documentation

- **Default to writing no comments.** Code with intent-revealing names is self-documenting.
- **Comments answer *why*, never *what*.** "// increment counter" is forbidden. "// retry up to 4 times — progettoSnaps mirrors are flaky on weekends" is good.
- **Module docstrings** are required at the top of every backend module: one paragraph stating the module's single responsibility and the contract it exposes.
- **Public function docstrings** are required when (a) the function has non-obvious preconditions, (b) the function has non-obvious side effects, (c) the function is part of the API layer. Otherwise, types + name carry the meaning.
- **No multi-paragraph docstrings.** If you need three paragraphs to explain a function, the function is too complex.
- **No "this method does X" docstrings** if X is the function's name.
- **TODO / FIXME / HACK comments** must include a date and reason. `# TODO(2026-04-27): replace once progettoSnaps adds the 0.284 INI`. Stale TODOs older than 6 months are bugs.

## 6. Testing

- **Test-driven development** is the default for non-trivial logic. Write a failing test, write the minimum code to pass, refactor.
- **Coverage targets:**
  - Backend overall: **≥85%** lines.
  - `filter/` (rule chain): **≥95%** — every branch of every rule has a test.
  - `parser/`: **≥90%**.
  - `copy/`: **≥85%** (filesystem-heavy, integration tests carry weight).
  - `api/`: **≥80%**.
  - Frontend components: **≥70%** (visual concerns harder to test).
- **Every feature ships with a `spec.md` next to its code.** The spec states the contract in prose; the tests in `tests/<feature>/` enforce every clause in it. The spec is the audit surface — a reviewer reads it and verifies the test file covers each clause. See §7.
- **Test types:**
  - **Unit:** pure functions, fast, no I/O. Default tier.
  - **Integration:** modules + filesystem in `tmp_path`. Slower but representative.
  - **API smoke:** FastAPI `TestClient` hitting every route.
  - **E2E:** one Playwright happy-path test only — full stack from browser to disk.
- **Property-based tests** (`hypothesis`) for the rule chain — assert determinism and override-correctness.
- **No tests against live network.** Mock with `respx` (for `httpx`) or use recorded fixtures.
- **Snapshot tests** for the curated-set output: a hand-picked fixture DAT (~30 machines), expected JSON checked into `tests/snapshots/`, regenerated only intentionally.

## 7. Specs and feature audits

Every feature ships with a `spec.md` next to its code:

```
src/mame_curator/filter/
├── __init__.py
├── rules.py
├── chain.py
├── spec.md          ← contract: what filter does, what it doesn't, edge cases
└── tests/
    └── test_chain.py
```

The spec is the audit surface. A reviewer (or future auditor, or AI agent) reads `spec.md` and verifies the tests cover every clause in it. **No feature merges without its spec.md.**

Spec template (kept short — it is documentation, not prose):

```markdown
# <feature> spec

## Contract
- <one-line bullets stating what this feature guarantees>

## Inputs
- <typed inputs, where they come from>

## Outputs
- <typed outputs, where they go>

## Edge cases
- <known edge cases and how they're handled>

## Out of scope
- <things this feature explicitly does not do>
```

## 8. Dependencies and tooling

- **Pinned and locked.** `uv.lock` (Python) and `package-lock.json` (frontend) are committed. CI fails if they drift.
- **Phase-staged dependency declaration.** Runtime deps for not-yet-implemented phases live in `[project.optional-dependencies].<feature>` (e.g. `api = ["fastapi", ...]`) until the importing code ships. Promote to `[project.dependencies]` in the same commit as the first `import` of the package. Rationale: declaring deps before any `import` confuses dependency-audit tools, surfaces deprecation warnings against unused code, and inflates fresh-install footprint for users who only need an early-phase subcommand. The exception is anything imported by Phase 0 tooling itself (test/lint/type/security), which lives in `[project.optional-dependencies].dev`.
- **No deprecated APIs.** Pre-commit + CI run a deprecation scanner. If a dep announces deprecation, file an issue tagged `deprecation` with the migration deadline.
- **Weekly automated dep audit.** `pip-audit` + `npm audit` + Dependabot.
- **Tooling stack (locked):**
  - **uv** — Python project + dependency management.
  - **Ruff** — Python linter + formatter (replaces black, flake8, isort, pyupgrade).
  - **mypy (strict)** — Python type checker. Astral's Ty was considered but not yet 1.0; revisit when it stabilizes. The migration is a tooling swap (config in `pyproject.toml`), not a code change.
  - **pytest** + `pytest-cov` + `hypothesis` + `respx`.
  - **Vite** + **React 19** + **TypeScript** + **Tailwind v4** + **shadcn/ui**.
  - **Vitest** + `@testing-library/react` + **Playwright** (one E2E).
  - **pre-commit** hooks: `ruff check`, `ruff format`, `mypy`, `pytest -q -x` (fast subset), `gitleaks`, frontend `eslint`/`prettier`.
- **No lock-pinning to bleeding-edge zero-x releases** unless the feature is essential. Pin to the most recent stable.

## 9. Errors, logging, observability

- **Error messages are actionable.** Bad: `"Could not load file"`. Good: `"Could not load DAT XML at /mnt/Games/MAME/MAME 0.284 ROMs (non-merged).zip — file is corrupt or not a zip. Re-download from <link> or set paths.source_dat in config.yaml."`
- **Errors at trust boundaries (CLI, API, file I/O) MUST include the offending input identifier** — the path, URL, key, or line number that failed. The "actionable" criterion above isn't optional once a trust boundary is crossed; users debugging at 3am can't act on a message that doesn't name what broke.
- **Errors go to stderr, success / summary output goes to stdout.** Standard UNIX convention; lets `2>err.log` and pipe-to-`jq` patterns work as users expect. Library code logs via `logger.error()` (which the application configures to route appropriately); CLI code that prints user-facing errors must construct a stderr-attached `rich.Console(stderr=True)` or use `print(..., file=sys.stderr)`. **Never** print errors to stdout.
- **Typed exceptions per module.** `parser/` raises `parser.ParserError`; `filter/` raises `filter.FilterError`. Never raise a bare `Exception`.
- **Logging:** stdlib `logging` configured once in `main.py`. Modules use `logger = logging.getLogger(__name__)`. Levels respected: `DEBUG` for trace, `INFO` for milestones, `WARNING` for recoverable, `ERROR` for non-recoverable, `CRITICAL` for "the app is going down."
- **No `print()` in library code.** Only the CLI entrypoints print.
- **Structured logging** (key/value pairs) on the API layer for grep-ability.

## 10. Performance

- **Profile before optimizing.** Premature optimization is forbidden. If a path becomes slow, profile (cProfile / py-spy) and target the actual hotspot.
- **Streaming over loading.** The DAT XML is 48 MB; use `lxml.iterparse` (streaming), not `lxml.etree.parse` (full-tree).
- **Async only where it pays.** Background copy + SSE progress: yes. Pure XML parse: no — use sync, run on a worker.
- **Cache references that don't change within a run.** `catver.ini` parsed once, not per game.
- **Frontend:** virtualize the game grid (`@tanstack/react-virtual`) — never render 3,000 cards at once.
- **Lazy-load images.** `loading="lazy"` on every `<img>`. Image fetching does not block initial render.

## 11. Code ordering & flow

- **Modules at the top of a file:** `import`s in PEP-8 groups (stdlib, third-party, local), `__all__` if applicable, constants, types, classes, public functions, private functions (prefixed `_`).
- **No forward references inside a file.** Functions are defined before they're called within the same file. Type-only forward refs (`from __future__ import annotations`) are fine.
- **Module dependency graph is acyclic.** `parser/` does not import `filter/`. `filter/` does not import `api/`. CI enforces with `import-linter`.
- **Layer order, top to bottom:**
  - `parser/` — pure, no deps on other internal modules.
  - `filter/` — depends on `parser/`.
  - `media/` — depends on `parser/` (for descriptions).
  - `copy/` — depends on `parser/` + `filter/`.
  - `updates/` — depends on `parser/` (for INI re-parse on refresh) + a shared `downloads.py` primitive.
  - `help/` — depends on filesystem only (loads bundled markdown).
  - `api/` — depends on all of the above.
  - `setup/` — orchestrates downloads + config; depends on `parser/` (for filter preview) + `downloads.py`.
  - `main.py` — wires it all together.

## 12. Git, commits, and CI

- **Conventional Commits** for commit messages: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `perf:`, `ci:`. Subject ≤ 72 chars; body explains *why*, not *what*.
- **Semantic versioning** (`MAJOR.MINOR.PATCH`). v0.x.y while pre-release.
- **Branches:** `main` is always green. Feature work in branches; PR with checks before merge.
- **CI matrix:**
  - Lint: `ruff check`, `ruff format --check`, frontend `eslint`.
  - Types: `mypy`, `tsc --noEmit`.
  - Test: `pytest --cov`, `vitest run`, one Playwright smoke.
  - Security (per push): `bandit -c pyproject.toml -r src`, `gitleaks`.
  - Security (weekly scheduled — wired in Phase 9 polish): `pip-audit`, `npm audit`. Until Phase 9 these are not enforced; the standard exists so reviewers know the future gate.
  - Build: frontend `vite build` produces `dist/` (committed result must match for v1.0.0+).
- **Pre-commit hooks** mirror the CI lint+type+fast-test gates.
- **No `--no-verify` on commits or pushes** unless the user explicitly authorizes it for one specific commit.
- **Releases gate on green CI.** A tagged release (`vX.Y.Z`) triggers `.github/workflows/release.yml`, whose first job is `verify-ci` — it re-runs the full CI gate against the tag's commit. The `publish` job depends on `verify-ci`; if any check fails, the GitHub Release is **never created**. This rule is enforced in the workflow itself; do not skip or work around it (see the "No workarounds without root-cause fix" rule in §0).

## 13. Frontend-specific quality

- **No client-side filesystem access** beyond what the browser allows. All disk operations cross the API.
- **API responses Pydantic-validated**, surfaced as auto-generated TS types via `pydantic-to-typescript` or hand-mirrored `interface`s with a CI check that they match.
- **Loading and error states** for every async UI element. No silent spinners that never resolve.
- **Component composition over prop-drilling.** Three or more levels of prop-drilling means the data should live in a context or `react-query` cache.
- **Animation budget.** Use `framer-motion` sparingly. Animations should clarify, not decorate. No animation longer than 300ms on UI feedback.

## 14. Things to NOT do

- Don't add features the spec doesn't list. Surface scope creep via a new spec or a TODO ticket — never bury it in a PR.
- Don't add backwards-compatibility shims for code that hasn't shipped yet. Until v1.0.0, breaking is fine.
- Don't add error handling for impossible scenarios. Trust internal-call invariants.
- Don't add abstractions you don't immediately need. Bare functions are great. A class is justified by state or polymorphism, not by anticipation.
- Don't comment out code. Delete it. Git remembers.
- Don't introduce a new dependency without justifying it in the PR. Each new dep is a maintenance and security cost.
- Don't write code your future self will struggle to read. Six-month test.

## 15. When standards conflict

If two standards in this document appear to conflict for a real piece of code, **the one earlier in this document wins** (lower-numbered section is more fundamental). If the conflict is real and persistent, fix the document — do not work around it silently in code.

## 16. Amendments

This document changes by PR like any other code, with two extra rules:

1. The PR description must state *what changed and why*.
2. If the change tightens a rule, existing code that violates the new rule must either be fixed in the same PR or have explicit `# noqa` / spec exception with a fix-by date.
