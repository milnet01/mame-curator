<!-- ants-roadmap-format-spec: 1 -->
# ROADMAP.md & CHANGELOG.md format spec (v1)

> Detailed format spec for the two files the Ants Terminal Roadmap
> dialog parses deterministically. **Structure verbatim from the
> App-Build template (the format spec is cross-project shared, not
> MAME-Curator-specific); examples customised to MAME Curator's
> ID prefix (`mame-curator-NNNN`).** Edits should track upstream
> template revisions.
>
> Read this file when authoring a `ROADMAP.md` bullet, a `CHANGELOG.md`
> entry, or any tooling that consumes either format. Skip otherwise.
>
> **About the missing §§1-2.** The upstream App-Build template
> ships §§1-2 covering the broader workflow context that the
> top-level [`app-workflow` skill](~/.claude/skills/app-workflow/SKILL.md)
> documents directly. This file ships only §§3-4 (ROADMAP.md
> and CHANGELOG.md sub-specs) so it does not duplicate the skill.
> Numbering preserved for cross-template consistency.

## 3. ROADMAP.md format spec

A shareable contract for `ROADMAP.md` files. Following this
sub-spec is **required** for any roadmap intended to render
correctly in the Ants Terminal Roadmap dialog or be parsed
deterministically by LLM agents.

The roadmap is the single place to track unshipped work. Released
work moves out of the roadmap into the CHANGELOG.

### 3.1 File header

A conforming file declares the format version with an HTML
comment in the **first five lines**:

```markdown
<!-- ants-roadmap-format: 1 -->
# MyProject — Roadmap
```

### 3.2 Heading hierarchy

| Level | Use | Example |
|-------|-----|---------|
| `#` | File title (one per file) | `# MAME Curator — Roadmap` |
| `##` | Release block (post-1.0) **or** phase block (pre-1.0) | `## P03 — Copy + BIOS + .lpl` |
| `###` | Theme group within a release/phase | `### 🎨 Features` |
| `####` | Optional subgroup | `#### Tier 1 — ship-this-week` |

### 3.3 Status emojis

| Emoji | Meaning |
|-------|---------|
| ✅ | Done / shipped |
| 🚧 | In progress (being tackled now) |
| 📋 | Planned (next up) |
| 💭 | Considered (research phase; scope or feasibility uncertain) |

Status transitions follow `💭 → 📋 → 🚧 → ✅`.

### 3.4 Theme emojis

| Emoji | Theme |
|-------|-------|
| 🎨 | Features (user-visible capabilities) |
| ⚡ | Performance |
| 🔌 | Plugins / extensibility |
| 🖥 | Platform (ports, accessibility, OS-specific) |
| 🔒 | Security |
| 🧰 | Dev experience (tooling, tests, build, CI) |
| 📚 | Documentation |
| 📦 | Packaging & distribution |
| 🐛 | Bug fixes / regressions |
| 🔍 | Audit / review findings fold-in |
| 🧹 | Cleanup / debt |

### 3.5 Bullet structure

```markdown
- 📋 [mame-curator-0123] **One-line headline ending with a period.** Body
  spanning as many lines as needed; lines wrapped to roughly 70
  columns. Cite `file:line` in backticks when relevant.
  Kind: implement.
  Lanes: filter, tests.
```

Required pieces:

- **Status emoji** — first character after `- `.
- **Stable ID** — `[mame-curator-NNNN]` immediately after the emoji
  (assigned lazily via `.roadmap-counter` — only for items that
  really need cross-referenced identity).
- **Bold headline ending in a period.**
- **`Kind: <kind>.`** — declares the type of work.

Optional pieces: body prose, `Lanes:` line, `Source:` line,
sub-bullets.

#### 3.5.1 Stable IDs

Project prefix: `mame-curator`. Counter file:
`.roadmap-counter` at repo root. Allocate via:

```bash
echo $(($(cat .roadmap-counter) + 1)) > .roadmap-counter
printf "mame-curator-%04d\n" $(cat .roadmap-counter)
```

Append-only — once assigned, an ID never changes.

#### 3.5.2 Insertion order vs numbering

> **Execution order is positional. Numbering is identity.**

Items execute top-to-bottom regardless of ID order.

#### 3.5.3 Kinds and Sources

**Kind values:**

| Kind | Meaning | Follow-through |
|------|---------|----------------|
| `implement` | New code for a planned feature | tests + changelog + docs |
| `fix` | Code change to repair a bug | regression test + changelog |
| `audit-fix` | Code change in response to an audit finding | regression test + changelog |
| `review-fix` | Code change in response to indie/peer review | regression test + changelog |
| `doc` | New / updated documentation, no code | changelog if user-facing |
| `doc-fix` | Documentation correction | no test, changelog optional |
| `refactor` | Code reshape with no behavior change | tests must still pass |
| `test` | Test-only change | no changelog |
| `chore` | Housekeeping (deps, build flags) | no test, changelog optional |
| `release` | Version bump, packaging, tag | drives `/release` skill |

**Source values:**

| Source | Meaning |
|--------|---------|
| `planned` | On the roadmap from project design (default; usually omitted) |
| `user-YYYY-MM-DD` | User report on date YYYY-MM-DD |
| `audit-YYYY-MM-DD` | `/audit` skill output on date YYYY-MM-DD |
| `indie-review-YYYY-MM-DD` | `/indie-review` skill output on date YYYY-MM-DD |
| `debt-sweep-YYYY-MM-DD` | `/debt-sweep` skill output on date YYYY-MM-DD |
| `static-analysis` | cppcheck / clazy / semgrep / ruff / bandit ad-hoc |
| `regression` | Item was previously ✅ but a later change broke it |
| `external-CVE-NNNN-NNNN` | Public CVE / advisory triggering this work |

### 3.6 Findings fold-in subsections

When an external review produces new items, fold them into a
dedicated `###` subsection inside the active phase block:

```markdown
### 🔍 Audit fold-in (2026-04-28)

- 📋 [mame-curator-0042] **CRITICAL — copy-step .tmp file leak.** …

### 🔍 Indie-review fold-in (2026-04-28)

- 📋 [mame-curator-0043] **HIGH — playlist conflict prompt missing.** …
```

### 3.7 Anti-patterns

- ❌ Status emoji other than ✅ 🚧 📋 💭.
- ❌ Renumbering items when inserting.
- ❌ Reordering bullets by ID — position is priority.
- ❌ More than ~3 🚧 bullets simultaneously.

## 4. CHANGELOG.md format spec

Keep-a-Changelog format. `[Unreleased]` block always at top.
Dated sections in reverse chronological order. Bullets
categorical: Added / Changed / Fixed / Removed / Security.

When a release ships:

1. `[Unreleased]` contents move to `## [X.Y.Z] — YYYY-MM-DD`.
2. Empty `[Unreleased]` left at top.
3. ROADMAP bullets that were 🚧 flip to ✅.
4. Released ROADMAP block changes from `(target: YYYY-MM)` to
   `shipped (YYYY-MM-DD)`.

The `/release` skill automates these steps.
