# ADR-0003: Tiered acquisition for `mame -listxml` — no checksum pinning

- **Status:** Accepted
- **Date:** 2026-04-27
- **Deciders:** Project lead
- **Related:** ADR-0002, P08 (setup wizard),
  [docs/superpowers/specs/2026-04-27-mame-curator-design.md § 6.1](../superpowers/specs/2026-04-27-mame-curator-design.md)

## Context

Per ADR-0002, Phase 2 needs the official MAME `-listxml` as
input. P08's setup wizard must acquire this for the user. Two
properties make `-listxml` different from the five INI files:

- **Version is per-user.** Each MAME release ships its own
  `-listxml`. A 0.284 user needs the 0.284 listxml; a 0.290
  user needs the 0.290 listxml. There is no single "current"
  version to pin.
- **Size is large.** ~30-40 MB compressed; ~200 MB uncompressed
  on recent MAME versions. Hosting it on a single CDN with a
  pinned sha256 (the pattern P07's `downloads.py` uses for
  INIs) would either need per-version mirrors (operational
  burden) or skip checksumming.

Three alternatives were considered for the wizard's listxml
flow:

1. **Bundle a single version.** Rejected: traps users on
   whatever version we ship; breaks for users who upgrade MAME.
2. **Download from a community mirror with sha256 pinning, per
   MAME version.** Rejected: would need to publish (and host) a
   manifest that maps every MAME version → mirror URL + hash.
   Operationally expensive, and the project doesn't control any
   such mirror.
3. **Tiered acquisition with no checksum pinning** — try local
   `mame -listxml` first (cheapest, most-current); fall back to
   user-supplied path; last resort, a community-mirror link the
   user opts into.

## Decision

The setup wizard acquires `mame -listxml` in three tiers,
ordered by reliability and currency:

1. **Run `mame -listxml`** if a `mame` binary is on PATH or at a
   user-supplied install path. The wizard captures stdout to a
   file under `data/listxml/<mame-version>.xml`. This is the
   gold-standard source — it matches the user's MAME exactly.
2. **Accept a user-supplied `-listxml` file path.** For users
   without MAME installed (frontend-only setups) or users with
   an existing dump.
3. **Opt-in community-mirror link.** Surfaced only if tiers 1
   and 2 fail. The wizard renders a clickable link to the
   community mirror, asks the user to download and place the
   file at a specific path, then resumes. **No automated
   download from the mirror; no checksum pinning.** The user
   takes responsibility.

The five INI files use a different flow (single canonical
mirror at progettoSnaps, sha256 pinning, automated download
with retry). P07's shared `downloads.py` primitive serves the
INI flow; the listxml flow is implemented separately in the
wizard.

`setup/spec.md` (P08) documents both flows.

## Consequences

**Positive:**

- Most users hit tier 1 — the wizard runs `mame -listxml`
  locally and gets a perfectly-current result with no network
  involved.
- Users who don't have MAME installed locally still have a path
  via tier 2 (manual file) or tier 3 (link to community mirror).
- The project doesn't need to host or mirror `-listxml`.
- No checksum-pinning operational burden for a per-user-version
  artefact.

**Negative:**

- Tier 3 (community mirror) is a manual step — the user must
  download and drop the file in the right place. The wizard
  guides this but can't automate it.
- No integrity check on the listxml content. A corrupted or
  tampered file would be detected only when Phase 2 fails to
  parse it (lxml will raise `XMLSyntaxError`); a *valid but
  wrong* listxml (e.g. version mismatch) silently produces
  wrong cloneof groupings. **Mitigation:** Phase 2 logs the
  MAME version field from the `-listxml` header and the wizard
  surfaces it in the filter-preview step so the user can spot
  obvious mismatches.

**Neutral:**

- Tier 1 requires running a subprocess. P08's setup module
  already calls `subprocess.run([cmd, arg])` (no `shell=True`)
  per `coding-standards.md` § 1.
