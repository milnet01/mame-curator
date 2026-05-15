# ADR-0004: INI refresh trust model — wizard vs runtime, sha256 deferred

- **Status:** Accepted
- **Date:** 2026-05-15
- **Deciders:** Project lead
- **Related:** ADR-0003 (listxml acquisition),
  [docs/superpowers/specs/2026-04-27-mame-curator-design.md § 6.6](../superpowers/specs/2026-04-27-mame-curator-design.md)
  (wizard bootstrap),
  [§ 6.7](../superpowers/specs/2026-04-27-mame-curator-design.md)
  (runtime refresh),
  FP28 § E1.

## Context

The 2026-05-14 indie-review flagged `updates/ini.py` (the
runtime refresh path) for lacking mirrors and sha256 pinning
"as promised in design § 6.6". A closer read of the design
exposes a wizard-vs-refresh split that the review conflated:

- **§ 6.6 — Wizard bootstrap (stage-2 step 4).** Promises
  "primary URL plus at least two mirrors" and "validates
  checksum (SHA-256 pinned in the wizard for the targeted MAME
  version)". This is the *first-run* bootstrap a user goes
  through when they install the project — the wizard fetches
  the canonical INIs once, validates them, and lays them down
  on disk.
- **§ 6.7 — Runtime refresh path.** Documents `updates/ini.py`
  (P07). No mirrors, no sha256 — silent on integrity. The
  refresh is opportunistic (`mame-curator refresh-inis`); the
  user runs it when they want fresher data than the wizard
  installed.

The wizard package itself does not exist on disk yet — `setup/`
was confirmed absent at FP27 § C2. Stages 1 and 2 of the
wizard are documented in design § 6.6 but not implemented.

Three alternatives were considered for closing the gap:

1. **Retrofit mirrors + sha256 to the runtime refresh path
   now.** Would mean publishing a per-version manifest of
   sha256 hashes for every INI file the project knows about,
   maintaining mirror lists, and adding downgrade-attack
   reasoning (a tampered mirror serving an older valid-but-bad
   INI). Roughly P12-class scope.
2. **Match what § 6.6 promises but defer to wizard
   implementation.** Document the split, defer the work, write
   it down so the next reviewer doesn't re-raise the same flag.
3. **Loosen § 6.6's promise to match § 6.7's silence.** Would
   weaken the wizard contract that the project hasn't even
   shipped yet — wrong direction.

## Decision

The runtime refresh path stays as-is for v1.0.0. The wizard's
mirrors + sha256 promise ships with the wizard, whenever the
wizard ships.

Current trust posture for `updates/ini.py`:

- **HTTPS-only.** All URLs in `INI_DEFAULT_SOURCES` route
  through TLS. The integrity guarantee is whatever GitHub's TLS
  certificate offers.
- **Single canonical mirror per file** (AntoPISA's
  `progettoSnaps` GitHub repo). No mirror failover.
- **No per-file sha256.** A corrupted or maliciously-modified
  INI would be detected only at parse-time (`parser/ini.py`
  surfaces malformed lines as warnings) or at filter-time (a
  filter run with wrong INI data silently produces wrong
  results).

This is appropriate for a *refresh* operation — the wizard
already vetted a known-good baseline; refresh is a
convenience that the user explicitly opts into.

## Consequences

**Positive:**

- No infrastructure to host or maintain — no mirror list, no
  manifest of sha256 hashes, no per-version pinning.
- Refresh stays simple; the user can opt out by never running
  `mame-curator refresh-inis`.
- The wizard's stronger contract (§ 6.6) is preserved as the
  target shape for first-run bootstrap.

**Negative:**

- A compromised AntoPISA repo or a TLS-cert mis-issuance could
  serve tampered INIs to a refresh-running user. Mitigation:
  the user retains the wizard-installed baseline at
  `data/inis/<sha256>.ini` (FP27 introduced per-file
  immutability via content-addressed paths) until they
  explicitly accept the refresh — a malicious update doesn't
  silently overwrite the wizard's baseline.
- The split is non-obvious to a reader of `updates/ini.py`
  alone; the missing `updates/spec.md` (called out as a
  follow-up in FP28 § E1) makes it worse.

**Neutral:**

- The post-v1 hardening path is a P12-class feature pass:
  per-version sha256 manifest + at-least-two mirrors + a
  downgrade-attack reasoning section. Scoped when the wizard
  implementation lands.

## Post-v1 hardening path

When the wizard package ships (post-v1.0.0, scheduled under
P12 or a dedicated INI-trust feature pass):

1. Author the missing `updates/spec.md` so the runtime contract
   is documented next to its code.
2. Publish a per-version sha256 manifest at a project-controlled
   location (matches design § 6.6's "pinned in the wizard for
   the targeted MAME version" wording).
3. Add at-least-two mirrors per INI file; the refresh path
   falls back across mirrors on 4xx/5xx + sha256 mismatch.
4. Document downgrade-attack reasoning: a mirror serving a
   valid-but-older INI should be detectable via a
   monotonically-increasing version tag in the manifest.

Until then, this ADR is the source of truth: refresh trusts
HTTPS + AntoPISA repo integrity, no per-file sha256.
