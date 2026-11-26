# CLAUDE.md — rule history

Pedigree and reasoning moved out of [`CLAUDE.md`](../../CLAUDE.md) so the file
read every session holds only live rules. Each entry names the rule it belongs
to by section and opening words, and quotes the moved clause verbatim.
Moved 2026-09-27 (roadmap CFG-0492, applied to this repo).

## § Session start — read & summarise, item 2 ("Summarise back to the user")

Followed **Never skip this step**:

> — state-recovery errors are cheaper to catch before working than to undo after.

## § Authoritative docs, the `src/mame_curator/<module>/spec.md` bullet ("per-feature contract for shipped modules")

Followed the sentence allowing a multi-tier fold-in its own long-form spec:

> In practice the larger ones (FP05, FP27, FP28, DS01–DS05) have, and their journals credit the spec for catching highest-leverage drift early.

## § Project-specific overrides, "No `# nosec` without an inline threat-model comment"

> Refines global rule 1 for the project's preferred suppression form.

## § Project-specific overrides, "Direct push to `main`"

The reason the rule was settled, between the rule and the visibility note:

> solo development; no PR-workflow opt-in signals (no `CODEOWNERS`, no branch protection, no `Merge pull request` history).

## Opening paragraph ("This project follows the global workflow")

Moved 2026-11-26, the startup-cost trim:

> The App-Build phase workflow it replaced was retired 2026-09-28; its state file is kept as history at [`docs/history/app-build-workflow-state.md`](docs/history/app-build-workflow-state.md).

## § Project-specific overrides, "Direct push to `main`"

Moved 2026-11-26, the startup-cost trim:

> Repo is **PUBLIC** (checked 2026-04-30 via `gh repo view`), so push freely per global rule 6.

## § Karpathy clarity — where it lands here

Deleted 2026-11-26, the startup-cost trim. Each bullet repeated a global rule (rule 9, `testing.md` § 1, `coding.md` § 1.7), and "`review-contract` reads [every spec] cold before user sign-off" predated global rule 14, which reviews only a new spec that is expensive to build wrong.
