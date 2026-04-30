# Architecture Decision Records (ADRs)

This folder holds architecture decision records — short markdown
files capturing **why** a significant architectural choice was
made, what alternatives were considered, and what the trade-offs
were.

Format: Michael Nygard's lightweight pattern (see
[ADR-0001](0001-record-architecture-decisions.md)). One file per
decision, numbered sequentially, never edited after acceptance
(superseded decisions get a new ADR that references the prior
one).

## When to write an ADR

Write one when a decision:

- Has long-term consequences (months or years).
- Closes off alternatives that future contributors might propose.
- Reflects a trade-off that isn't obvious from the code alone.
- Required real research / debate to settle.

Don't write one for:

- Small refactors that anyone might revisit on a Tuesday.
- Choices forced by external constraints — the constraint *is*
  the rationale; mention it in code comments instead.
- Decisions captured fully in `CLAUDE.md` or
  `coding-standards.md`.

## Numbering

Sequential, zero-padded to 4 digits:
`0001-record-architecture-decisions.md`,
`0002-cloneof-from-listxml.md`, …

Append-only — once an ADR has a number, it keeps it forever,
even if superseded.

## Lifecycle

| Status | Meaning |
|--------|---------|
| Proposed | Drafted; under discussion. |
| Accepted | Decision made; in effect. |
| Deprecated | No longer applies; new code shouldn't follow it. |
| Superseded by ADR-NNNN | Replaced by a later decision. |

## Index

- [ADR-0001](0001-record-architecture-decisions.md) —
  Record architecture decisions (this template). **Accepted.**
- [ADR-0002](0002-cloneof-from-listxml.md) — Source parent/clone
  relationships from official MAME `-listxml`, not Pleasuredome
  DAT. **Accepted.**
- [ADR-0003](0003-listxml-tiered-acquisition.md) — Tiered
  acquisition for `mame -listxml` (no checksum pinning).
  **Accepted.**
