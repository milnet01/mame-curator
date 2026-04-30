# ADR-0002: Source parent/clone relationships from official MAME `-listxml`

- **Status:** Accepted
- **Date:** 2026-04-27
- **Deciders:** Project lead
- **Related:** P02 (filter rule chain), `parser/spec.md`,
  `filter/spec.md`,
  [docs/superpowers/specs/2026-04-27-roadmap.md § Phase 2](../superpowers/specs/2026-04-27-roadmap.md)

## Context

Phase 2's filter rule chain groups machines by parent/clone and
picks one winner per group. MAME's DAT format carries this
relationship in the `cloneof` attribute on each `<machine>` —
e.g. `<machine name="sf2ce" cloneof="sf2">`.

The user's chosen DAT source is **Pleasuredome** (a community-
maintained ROM-set archive, source for the 0.284 non-merged
release this project targets). Pleasuredome strips both
`cloneof` and `romof` attributes from its DATs. This was
verified directly: `grep -c cloneof= MAME\ 0.284\ ROMs\ \(non-merged\).xml`
returned `0` on both the Pleasuredome 0.284 DAT and the prior
0.282 DAT.

The `Machine` records produced by Phase 1's parser therefore
have `cloneof=None` for **every** machine. Phase 2 cannot rely
on `Machine.cloneof` to group parents and clones.

Three alternatives were considered:

1. **Reconstruct cloneof from description heuristics** — group
   by stripping region/revision tokens from `<description>`
   and clustering. Rejected: lossy (synonymous descriptions
   like "Pac-Man" and "Pac Man" collide; intentionally distinct
   games like "Street Fighter II" and "Street Fighter II'"
   merge), brittle, and produces non-deterministic groupings.
2. **Ship a pre-baked cloneof map** with the project. Rejected:
   the map goes stale every MAME release; users on different
   versions get wrong groupings; the project would need to
   re-bake on every MAME bump (~monthly).
3. **Source cloneof from the official MAME `-listxml`.** This
   is the canonical authority for the parent/clone graph —
   it's literally what MAME outputs from its own database.
   The user already needs the `-listxml` for CHD detection in
   Phase 1 (`parse_listxml_disks`), so it's already in the
   acquisition flow.

## Decision

Phase 2 builds a `cloneof_map: dict[str, str]` from the
official MAME `-listxml` and joins it onto the Pleasuredome
machines by short name.

A new helper `parse_listxml_cloneof(path: Path) -> dict[str, str]`
lives in `src/mame_curator/parser/listxml.py`, mirroring the
`lxml.iterparse + # nosec B410` pattern from the existing
`parse_listxml_disks`. Returns `{clone_short_name:
parent_short_name}`. The filter takes the cloneof map as an
explicit input to `run_filter()`; the picker treats
`parent_of(x) = cloneof_map.get(x, x)`.

`filter/spec.md` documents this explicitly so reviewers know
parent/clone is **not** sourced from `Machine.cloneof`.

## Consequences

**Positive:**

- Parent/clone groupings match MAME's authoritative graph
  exactly — no heuristic risk.
- Pleasuredome stays usable as the primary DAT source (it's
  the most up-to-date community archive; not switching to a
  different distributor preserves the user's existing workflow).
- Re-uses an artefact (`-listxml`) the project already needs
  for CHD detection — no new acquisition step.
- Deterministic across MAME versions (each MAME release ships
  with its own `-listxml`; map regenerates from it).

**Negative:**

- Phase 2 has a new mandatory input. The `mame-curator filter`
  CLI takes `--listxml` as a required flag.
- The `-listxml` must be acquired somehow. ADR-0003 covers the
  tiered acquisition strategy.

**Neutral:**

- `Machine.cloneof` remains a field on the model, populated
  faithfully (always `None` for Pleasuredome DATs). Phase 1's
  parser doesn't need a special case; Phase 2 just doesn't
  consume that field.
