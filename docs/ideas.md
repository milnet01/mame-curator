# MAME Curator — Ideas

> **Status:** Empty until first new idea is captured.
> **Purpose:** mid-flight ideas the user proposes during an
> active phase. Captured here so they're never lost; sized
> against the current architecture; **only added to the
> roadmap on user say-so**.

The
[app-workflow skill](~/.claude/skills/app-workflow/SKILL.md)
"New ideas" section governs the flow: capture here →
recommend a placement → user decides → either insert into
ROADMAP.md as a new item, or leave here until later.

Long-running post-v1 ideas (software-list routing,
EmulationStation export, LaunchBox interop, DAT-version-upgrade
workflow, cloud sync, multi-user, i18n) are already captured in
the roadmap doc's "Future enhancements" section
(`docs/superpowers/specs/2026-04-27-roadmap.md` — bottom). This
file is for new ideas that surface mid-phase, not for the
already-known post-v1 backlog.


## Format

```markdown
## idea-NNN — One-line summary

- **Captured:** YYYY-MM-DD during <active phase ID>
- **From:** user request | observation during work | external
  prompt
- **Recommendation:** "Insert as <ID> after <ID>" |
  "Hold until <dependency>" | "Won't fit current architecture
  — needs design refresh"
- **Why:** one paragraph reasoning the recommendation
- **User decision:** pending | accepted YYYY-MM-DD (became
  <roadmap ID>) | declined YYYY-MM-DD (reason)
```

## Ideas

(none yet)

## What does NOT belong here

- **Already-decided roadmap items.** Those go straight into
  `ROADMAP.md`.
- **Audit findings.** Those go into a fix-pass.
- **Bugs.** Those become roadmap items immediately.
- **The post-v1 backlog.** Already captured in the long-form
  roadmap doc's "Future enhancements" list.
