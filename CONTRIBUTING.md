# Contributing to MAME Curator

Thanks for taking the time. The project is solo-maintained but PRs and
issues are welcome — this file is the short guide for getting a change in.

## Quick start

```bash
git clone https://github.com/milnet01/mame-curator.git
cd mame-curator
uv sync --extra dev
uv run pre-commit install
( cd frontend && npm install )
```

Two ways to run the app locally:

```bash
./run.sh                           # production-mode (serves frontend/dist)
./scripts/dev.sh                   # dev-mode (backend :8080 + Vite HMR :5173)
```

`./scripts/dev.sh` is the one you want when iterating on the SPA.

## Reporting bugs

Open an issue at
[github.com/milnet01/mame-curator/issues](https://github.com/milnet01/mame-curator/issues)
with:

- **What you did.** The exact command, button, or URL.
- **What happened.** Error message verbatim, plus the surrounding lines of
  stderr / browser console / network panel if available.
- **What you expected.** One sentence.
- **Your environment.** OS, Python version (`python --version`), browser
  version, and the app version (footer of `/library` page, or
  `cat pyproject.toml | grep '^version'`).

A failing repro recipe (DAT slice + INIs + config) is gold. If your DAT is
private, a minimal anonymised XML excerpt that triggers the bug is enough.

## The local CI gate

Run this before every commit. All five backend checks plus the three
frontend checks must be green before you push; CI on `main` fails
loudly if it has to repeat the run:

```bash
# Backend
uv run pytest && uv run ruff check && uv run ruff format --check \
    && uv run mypy && uv run bandit -c pyproject.toml -r src

# Frontend (only if you touched anything under frontend/)
( cd frontend && npx vitest run && npx tsc --noEmit && npm run build )
```

`pre-commit install` (above) wires a subset (ruff, ruff-format, mypy,
bandit, a few project hooks) so most regressions get caught at `git commit`
time. **Don't use `--no-verify` to bypass a failing hook** — fix the
underlying issue. If a hook is genuinely wrong, raise it in an issue.

End-to-end tests (Playwright) are opt-in:

```bash
( cd frontend && npm run e2e )
```

These spin up a real backend + frontend pair, so they take ~1 min and need
a free port 5173.

## Tests come first

**TDD is the default for non-trivial logic.** That means:

1. Write a test that fails with a clear message describing the bug or the
   missing behaviour.
2. Run the test, confirm it fails for the reason you expected (not, e.g.,
   an import error you didn't notice).
3. Write the *shortest correct* implementation that makes the test pass.
4. Refactor only if needed; tests stay green.

Typo fixes, one-line constant changes, and pure renames are exempt — but
anything that adds or changes a behaviour gets a test first.

Coverage targets per module (enforced by `pytest-cov` in CI):

| Module      | Floor |
|-------------|-------|
| `parser/`   | ≥ 90% |
| `filter/`   | ≥ 95% |
| `copy/`     | ≥ 85% |
| `api/`      | ≥ 80% |
| frontend    | ≥ 70% |
| overall     | ≥ 85% |

See [`docs/standards/coding-standards.md`](docs/standards/coding-standards.md) § 6
for the full testing policy.

## Every feature ships with a `spec.md`

Each module under `src/mame_curator/` carries a `spec.md` alongside its
code — see `src/mame_curator/parser/spec.md` for the shape. The spec is
the **audit surface**: every clause is a contract the test file enforces.

When you add or change behaviour, update the relevant `spec.md` *first*,
then write the test that pins the new clause, then the code. A change that
contradicts the spec is treated as a bug regardless of whether the test
suite passes — see [`CLAUDE.md`](CLAUDE.md) § "Authoritative docs".

For in-flight work (not-yet-shipped phases), the spec lives at
`docs/specs/<ID>.md` instead; it graduates to `<module>/spec.md` when the
work ships.

## Commit conventions

The project uses [Conventional Commits](https://www.conventionalcommits.org/)
— subjects are `feat(scope):`, `fix(scope):`, `docs:`, `chore:`, `test:`,
`refactor:`, `perf:`, `ci:`. Examples from `git log`:

```
feat(filter): run_filter orchestrator with overrides and session-slice
fix(copy): pass-3 C1 — picker uses functools.cmp_to_key per spec line 55
docs(roadmap): tick Phase 2 acceptance — pass-3 Tier 1 findings closed
```

If your work is part of a tracked roadmap item (`P##`, `FP##`, `DS##`,
`mame-curator-NNNN`), **cite the ID in the commit body**, not the subject.
Full details in [`docs/standards/commits.md`](docs/standards/commits.md).

## The 9-step phase loop

Larger pieces of work (anything that ships under its own phase ID
`P##` / `FP##` / `DS##`) flow through the **App-Build 9-step loop**:

1. **Verify spec** — does `docs/specs/<ID>.md` exist and is it
   implementable as-written?
2. **Verify dependencies** — every roadmap item this depends on is ✅.
3. **Write tests first.** Per the TDD section above.
4. **Implement** until tests pass. Shortest correct implementation.
5. **`/audit`** — static-analysis sweep (ruff, mypy, bandit, semgrep,
   gitleaks). Findings against `docs/audit-allowlist.md` are pre-cleared.
6. **`/indie-review`** — independent multi-agent code review. Runs in
   parallel with step 5.
7. **Fold findings** from steps 5 and 6 into a single fix-pass
   (`FP##` / `DS##`) that goes through this same loop.
8. **Update** `CHANGELOG.md` (under `[Unreleased]`) + `ROADMAP.md` (flip
   the status emoji) + write `docs/journal/<ID>.md`.
9. **Commit, tag** the close (annotated tag `<ID>-complete`), and ask
   about pushing.

The full rules live in `~/.claude/skills/app-workflow/SKILL.md` (a
Claude Code skill that auto-loads when `.claude/workflow.md` is present).
Drive-by contributions don't need to follow this loop — single bug fixes
ship via a normal PR.

## What goes where (the four authoritative docs)

If two docs disagree, the lower-numbered section in
[`docs/standards/coding-standards.md`](docs/standards/coding-standards.md)
wins (§ 15 precedence rule). The rough layout:

- [`docs/standards/coding-standards.md`](docs/standards/coding-standards.md)
  — the single source for code rules (style, security, errors, perf).
- [`docs/decisions/`](docs/decisions/) — ADRs for non-obvious trade-offs
  (e.g. why parent/clone reconstruction reads MAME `-listxml` rather than
  the DAT).
- `src/mame_curator/<module>/spec.md` — per-module contract.
- [`CLAUDE.md`](CLAUDE.md) — project rules for AI-assisted work
  (overrides the global `~/.claude/CLAUDE.md` where they differ).

## Things this project deliberately does not do

Don't open a PR for these — they're rejected on sight:

- Telemetry, analytics, or any outbound network call from the running app
  beyond the explicit `downloads/` and `media/` paths
  (grep-gated; see `coding-standards.md` § 1).
- Client-side filesystem access in the frontend — every disk operation
  crosses the API.
- Software-list routing, LaunchBox / EmulationStation export, or cloud
  sync. These are explicitly post-v1 (see
  [`ROADMAP.md`](ROADMAP.md) § "Future enhancements").
- Backwards-compat shims for the config format. Pre-v1.x is unstable by
  design; we'll add migration shims once the config schema stops moving.

## License

By contributing you agree your changes ship under the project's
[MIT license](LICENSE).
