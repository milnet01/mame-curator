# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-04-30
- **Deciders:** Project lead
- **Related:** [docs/decisions/README.md](README.md)

## Context

Architectural decisions accrete invisibly. Three months after
choosing `lxml.iterparse` over `etree.parse` for the DAT, no one
remembers why; six months after sourcing parent/clone from the
official `-listxml` instead of the Pleasuredome DAT, the
gotchas that drove the choice are gone. New contributors propose
"obviously better" alternatives that were already considered
and rejected.

Without a record, the project repeats the discovery cycle every
time the choice resurfaces — wasting time and risking a worse
outcome (the old context that informed the original decision is
no longer in anyone's head).

## Decision

Capture significant architectural decisions as ADRs in
`docs/decisions/`, following Michael Nygard's lightweight
format (Cognitect, 2011). One markdown file per decision,
numbered sequentially (`0001-`, `0002-`, …), never edited after
acceptance.

The format for each ADR:

```markdown
# ADR-NNNN: <short title>

- **Status:** Proposed | Accepted | Deprecated | Superseded by ADR-NNNN
- **Date:** YYYY-MM-DD
- **Deciders:** <names / roles>
- **Related:** <links to other ADRs, ROADMAP items, etc.>

## Context

What forces are at play, what problem are we solving, what
alternatives were considered.

## Decision

The chosen approach, stated clearly. One sentence if possible.

## Consequences

What changes — positive, negative, neutral.
```

Files are checked in to `docs/decisions/`. The folder's
[README.md](README.md) explains the lifecycle and when to write
one.

## Consequences

**Positive:**

- New contributors can read the rationale for any major
  structural choice without asking the author.
- Decisions that turn out to be wrong can be superseded
  cleanly with a new ADR; the trail of reasoning is preserved.
- ADRs serve as a sanity check during design — if writing the
  ADR feels hard, the decision probably needs more thought.

**Negative:**

- Some discipline cost — writing an ADR for a "minor" decision
  that turns out to be load-bearing later is easy to skip.
- A few extra markdown files in the repo.

**Neutral:**

- ADRs are not a substitute for code comments at the call-site
  — they live at a higher level of abstraction.
