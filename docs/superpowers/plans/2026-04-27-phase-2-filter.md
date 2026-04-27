# Phase 2 — Filter Rule Chain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Given parsed data from Phase 1, produce a deterministic curated set: a list of winner short-names plus a `dropped` map (reason per non-winner) plus a `contested_groups` list (parent/clone groups where the picker chose between candidates). The output is consumable by Phase 3 (`copy/`) and Phase 4 (`api/`).

**Architecture:** Four sequential phases, each pure (no I/O beyond reading parsed structures and YAML files):

- **Phase A — drop:** small `(Machine, FilterConfig) -> bool` predicates; first match drops the machine with a typed reason.
- **Phase B — pick:** comparators of the form `(Machine, Machine, FilterConfig) -> int` composed via `functools.cmp_to_key`. Within each parent/clone group the highest-ranked machine wins.
- **Phase C — overrides:** `parent → winner` map from `overrides.yaml` overrides Phase B's pick (unknown short names warn but don't crash).
- **Phase D — session focus:** when a session is active in `sessions.yaml`, slice the winner set to the include patterns.

Parent/clone relationships are sourced from the official MAME `-listxml`, **not** the Pleasuredome DAT (which strips `cloneof`/`romof`); see Phase 1's empirical finding. Phase 2 adds `parse_listxml_cloneof()` to the existing `parser/listxml.py` and joins onto the parsed machines by short name.

**Tech Stack:** Python 3.12+, Pydantic 2 (frozen models everywhere), `functools.cmp_to_key`, stdlib `fnmatch` for glob patterns, `re` for region/revision heuristics, `hypothesis` for property tests, no new runtime deps.

**Companion docs:**
- [Design spec §6.2](../specs/2026-04-27-mame-curator-design.md#62-filter--the-rule-chain)
- [Roadmap Phase 2](../specs/2026-04-27-roadmap.md#phase-2--filter-rule-chain-filter)
- [Coding standards](../../standards/coding-standards.md)
- [Phase 1 plan](2026-04-27-phase-1-parser.md) (parser API the filter consumes)

**Acceptance (lifted from roadmap):**
- [ ] All listed tests pass.
- [ ] Coverage on `filter/` ≥ 95%.
- [ ] Snapshot test passes; `tests/snapshots/filter_smoke.json` is committed.
- [ ] CLI run on user's real DAT produces deterministic output (run twice, diff is empty).
- [ ] No public function exceeds 50 lines (per coding standards §2).

---

## File Structure

| Path | Responsibility |
|---|---|
| `src/mame_curator/filter/__init__.py` | Public re-exports: `run_filter`, `FilterResult`, `FilterConfig`, `Overrides`, `Sessions`, `DroppedReason`, `ContestedGroup`, `explain_pick`, `FilterError`. |
| `src/mame_curator/filter/spec.md` | Audit surface: full Phase A/B/C/D contract + YAML schemas + heuristic regexes. |
| `src/mame_curator/filter/errors.py` | `FilterError` (subclasses: `ConfigError`, `OverridesError`, `SessionsError`). |
| `src/mame_curator/filter/config.py` | Pydantic models for `config.yaml`'s `filters:` and `picker:` sections. |
| `src/mame_curator/filter/overrides.py` | Pydantic model for `overrides.yaml` + loader/saver. |
| `src/mame_curator/filter/sessions.py` | Pydantic model for `sessions.yaml` + loader/saver + `apply_session()`. |
| `src/mame_curator/filter/heuristics.py` | Pure functions: `region_of(description) -> Region` (enum), `revision_key_of(description) -> tuple`. |
| `src/mame_curator/filter/types.py` | `DroppedReason` enum + `FilterDecision` + `ContestedGroup` + `FilterResult` Pydantic models. |
| `src/mame_curator/filter/drops.py` | Phase A: list of drop predicates. |
| `src/mame_curator/filter/picker.py` | Phase B: list of tiebreaker comparators + `pick_winner()` per group + `explain_pick()`. |
| `src/mame_curator/filter/runner.py` | `run_filter()` orchestrator (composes A → B → C → D). |
| `src/mame_curator/parser/listxml.py` | **Modify:** add `parse_listxml_cloneof(path) -> dict[str, str]`. |
| `src/mame_curator/parser/__init__.py` | **Modify:** re-export `parse_listxml_cloneof`. |
| `src/mame_curator/cli.py` | **Modify:** add `filter` subcommand. |
| `tests/filter/__init__.py` | Test package marker. |
| `tests/filter/conftest.py` | Shared fixtures (synthetic Machine builders + sample configs). |
| `tests/filter/fixtures/listxml_cloneof.xml` | 6-machine fragment with parent/clone relationships. |
| `tests/filter/fixtures/snapshot_dat.xml` | 30-machine hand-picked DAT exercising every rule. |
| `tests/filter/fixtures/snapshot_listxml.xml` | Matching listxml for cloneof + CHD detection. |
| `tests/filter/fixtures/snapshot_catver.ini` | Categories for the 30 fixture machines. |
| `tests/filter/fixtures/snapshot_languages.ini` | Languages for the fixture. |
| `tests/filter/fixtures/snapshot_bestgames.ini` | Tiers for the fixture. |
| `tests/filter/fixtures/snapshot_overrides.yaml` | Overrides exercising Phase C. |
| `tests/filter/fixtures/snapshot_sessions.yaml` | Session exercising Phase D. |
| `tests/snapshots/filter_smoke.json` | Expected curated output for the snapshot DAT. |
| `tests/filter/test_heuristics.py` | Region + revision heuristics. |
| `tests/filter/test_listxml_cloneof.py` | Cloneof map parsed correctly. |
| `tests/filter/test_config.py` | FilterConfig schema validation. |
| `tests/filter/test_overrides.py` | Overrides schema + loader. |
| `tests/filter/test_sessions.py` | Sessions schema + loader + slice. |
| `tests/filter/test_drops.py` | One test per Phase A predicate. |
| `tests/filter/test_picker.py` | One test per Phase B comparator + `pick_winner` integration. |
| `tests/filter/test_runner.py` | `run_filter` end-to-end on synthetic input + idempotency. |
| `tests/filter/test_property.py` | Hypothesis: determinism + override-locality. |
| `tests/filter/test_snapshot.py` | 30-machine snapshot regression test. |
| `tests/filter/test_cli_filter.py` | `mame-curator filter` CLI test. |

---

## Pre-flight check (before Task 1)

- [ ] **Step 0a: Verify Phase 1 is committed and green**

```bash
cd /mnt/Storage/Scripts/Linux/MAME_Curator
git log --oneline -3
uv run pytest -q --no-cov
uv run ruff check && uv run ruff format --check && uv run mypy && uv run bandit -c pyproject.toml -r src
```

Expected: log shows the Phase-1 commit; pytest shows 51 passed; every gate green.

- [ ] **Step 0b: Verify the user's real DAT and a `-listxml` are reachable for the smoke run (Task 15)**

```bash
ls -la "/mnt/Games/MAME/MAME 0.284 ROMs (non-merged).zip"
```

If a `-listxml` is not yet available locally, Task 15's smoke run is skipped and Phase 2 acceptance ticks the "deterministic CLI output" item via the snapshot test only. (Real-DAT smoke is best-effort; the snapshot test is binding.)

---

## Task 1: Write `filter/spec.md`

**Files:**
- Create: `src/mame_curator/filter/__init__.py` (placeholder docstring; populated by later tasks)
- Create: `src/mame_curator/filter/spec.md`

The spec is the audit surface. It is written first so every subsequent test and implementation can be verified against a stable contract. The roadmap requires this spec to pin the YAML schemas for `overrides.yaml` and `sessions.yaml` (currently only example-defined).

- [ ] **Step 1: Create the package directory and placeholder `__init__.py`**

```bash
mkdir -p src/mame_curator/filter
```

Create `src/mame_curator/filter/__init__.py` with exactly:

```python
"""Filter rule chain — drop, pick, override, session-slice.

Public API surface — see spec.md for the full contract.
"""
```

- [ ] **Step 2: Write `src/mame_curator/filter/spec.md`**

Create the file with this exact content:

````markdown
# filter/ spec

## Contract

Given parsed Phase-1 data (`dict[str, Machine]`), an INI-augmented context (catver / languages / bestgames / mature / chd_required / cloneof_map), a `FilterConfig`, an `Overrides` map, and an active `Session` (or none), produce a deterministic `FilterResult`:

- `winners: list[str]` — short names of machines that survived all four phases, alphabetically sorted.
- `dropped: dict[str, DroppedReason]` — one entry per dropped machine, with the typed reason it was dropped.
- `contested_groups: list[ContestedGroup]` — one entry per parent/clone group where Phase B had to choose between ≥2 candidates; records the winner, the candidates, and the tiebreaker chain that produced the result. Used by `/api/games/{name}/explanation` (Phase 4).

Re-running the filter on the same input produces byte-identical output (verified by `test_idempotency` and a hypothesis property test).

## Source of parent/clone relationships

The Pleasuredome ROM-set DAT strips `cloneof` / `romof` attributes (verified empirically — see `parser/spec.md` "Edge cases handled"). Phase 2 sources parent/clone relationships from the **official MAME `-listxml`**, parsed via `parse_listxml_cloneof(path) -> dict[str, str]` in `parser/listxml.py` (extends the existing module). The returned map is `{clone_short_name: parent_short_name}`. Phase 2 joins by short name; machines absent from the cloneof map are treated as their own parent (`parent_of(x) = cloneof_map.get(x, x)`).

## Phase A — drop

Each rule is a small predicate `(machine, ctx, config) -> bool`. Predicates are evaluated in this exact order; the first one to match drops the machine with the corresponding `DroppedReason`. Predicates after a hit are skipped.

| # | Reason | Trigger |
|---|---|---|
| 1 | `BIOS` | `machine.is_bios` |
| 2 | `DEVICE` | `machine.is_device` or `machine.runnable is False` |
| 3 | `MECHANICAL` | `machine.is_mechanical` |
| 4 | `CATEGORY` | `ctx.category[name]` matches any pattern in `config.drop_categories` (fnmatch, case-sensitive) |
| 5 | `MATURE` | `name in ctx.mature` and `config.drop_mature` (default `True`; bound to `Mature*` category fallback) |
| 6 | `JAPANESE_ONLY` | `ctx.languages[name] == ["Japanese"]` and `config.drop_japanese_only_text` |
| 7 | `PRELIMINARY_DRIVER` | `machine.driver_status is DriverStatus.PRELIMINARY` and `config.drop_preliminary_emulation` |
| 8 | `CHD_REQUIRED` | `name in ctx.chd_required` and `config.drop_chd_required` |
| 9 | `GENRE` | derived genre matches any `config.drop_genres` pattern (genre = part after last `/` in category) |
| 10 | `PUBLISHER` | `machine.publisher` matches any `config.drop_publishers` pattern |
| 11 | `DEVELOPER` | `machine.developer` matches any `config.drop_developers` pattern |
| 12 | `YEAR_BEFORE` | `machine.year is not None` and `machine.year < config.drop_year_before` |
| 13 | `YEAR_AFTER` | `machine.year is not None` and `machine.year > config.drop_year_after` |

Patterns use `fnmatch.fnmatchcase()` (case-sensitive glob: `*` matches any sequence, `?` any single char, `[abc]` character class). `None` values for `publisher`/`developer`/`year` never match.

## Phase B — pick

For each parent group `{parent + clones}`, choose one winner. The candidate set is the **survivors of Phase A** (machines dropped in A do not enter Phase B). If a group is empty after Phase A, no winner is produced for that group.

Tiebreakers in order; later rules only run when earlier rules tie:

| # | Comparator | Direction |
|---|---|---|
| 1 | `bestgames.ini` tier rank: `Best > Great > Good > Average > Bad > Awful > unrated` | higher wins |
| 2 | preferred-genre / preferred-publisher / preferred-developer boost: `+1` per match in `config.preferred_*` | higher wins |
| 3 | parent over clone (when `config.prefer_parent_over_clone`) | parent wins |
| 4 | driver status: `good > imperfect > preliminary` (when `config.prefer_good_driver`) | higher wins |
| 5 | region priority: index in `config.region_priority`; unspecified-region machines rank last | lower index wins |
| 6 | revision key: `revision_key_of(description)` produces a tuple, lexicographic order | higher wins (later revision) |
| 7 | alphabetical short name | lower wins (deterministic fallback) |

Composed via `functools.cmp_to_key`. Each comparator returns `-1`, `0`, or `+1`. The final winner is the maximum element.

`explain_pick(group, config) -> list[TiebreakerHit]` runs the same comparators in order and records which one(s) actually decided the winner. A tiebreaker that returned 0 across the entire candidate set is omitted.

## Phase C — overrides

`apply_overrides(decisions, overrides)` replaces the Phase B winner of any group whose **parent short name** is a key in `overrides.entries`. Validation:

- The override value must exist in the parsed DAT and must belong to the same parent/clone group (i.e. either is the parent or has `cloneof_map[value] == parent`). If not: log a warning, skip the override, and surface in `FilterResult.warnings`. **Never crash.**
- Override-target machines that were dropped in Phase A are still allowed as winners (per design — user choice trumps community filters). The dropped reason is removed from `dropped` for that machine.

## Phase D — session focus

When `sessions.active` is non-null and points at a defined session, the winner set is filtered to machines matching **all** non-empty include rules:

- `include_genres: list[str]` — fnmatch against derived genre.
- `include_publishers: list[str]` — fnmatch against `machine.publisher`.
- `include_developers: list[str]` — fnmatch against `machine.developer`.
- `include_year_range: [int, int] | null` — closed interval `[lo, hi]`; `null` means unconstrained.

Empty session (no include rules and no active key) is **not** the same as "no session" — an empty session validation-errors at load time. `sessions.active = null` means "no session, return full winner set."

Sessions slice; they do **not** drop. A session-excluded winner remains a winner in the underlying `FilterResult` but is filtered from the visible set returned by `apply_session()`. This preserves "yesterday's session, today's different session" workflows (design §6.2 Phase D).

## YAML schemas

### `overrides.yaml`

```yaml
overrides:
  sf2: sf2ce          # parent → chosen winner short name
  pacman: pacmanf
```

Pydantic model:

```python
class Overrides(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    entries: dict[str, str] = Field(default_factory=dict, alias="overrides")
```

Constraints:
- Keys and values are non-empty strings.
- Single winner per parent (no multi-winner support in v1; keep "always include both versions" as a future enhancement — see design §3 future enhancements).

### `sessions.yaml`

```yaml
active: shoot_em_ups       # null or a key in `sessions:`
sessions:
  shoot_em_ups:
    include_genres: ["Shooter*", "Shoot 'em Up*"]
  capcom_fighters_early_90s:
    include_publishers: ["Capcom*"]
    include_genres: ["Fighter*"]
    include_year_range: [1991, 1995]
```

Pydantic models:

```python
class Session(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    include_genres: tuple[str, ...] = ()
    include_publishers: tuple[str, ...] = ()
    include_developers: tuple[str, ...] = ()
    include_year_range: tuple[int, int] | None = None

class Sessions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    active: str | None = None
    sessions: dict[str, Session] = Field(default_factory=dict)
```

Validation:
- A `Session` must have at least one non-empty include rule (else `SessionsError`).
- `include_year_range` must satisfy `lo <= hi`.
- `active`, when non-null, must be a key in `sessions`.

### `FilterConfig` (subset of `config.yaml` consumed by the filter)

```python
class FilterConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # filters: section
    drop_bios_devices_mechanical: bool = True
    drop_categories: tuple[str, ...] = ()
    drop_genres: tuple[str, ...] = ()
    drop_publishers: tuple[str, ...] = ()
    drop_developers: tuple[str, ...] = ()
    drop_year_before: int | None = None
    drop_year_after: int | None = None
    drop_japanese_only_text: bool = True
    drop_preliminary_emulation: bool = True
    drop_chd_required: bool = True
    drop_mature: bool = True

    # picker: section
    region_priority: tuple[str, ...] = ("World", "USA", "Europe", "Japan", "Asia", "Brazil")
    preferred_genres: tuple[str, ...] = ()
    preferred_publishers: tuple[str, ...] = ()
    preferred_developers: tuple[str, ...] = ()
    prefer_parent_over_clone: bool = True
    prefer_good_driver: bool = True
```

## Heuristic regexes

### Region detection (`heuristics.region_of`)

Match the **first** parenthesized group whose first token is a known region tag:

```python
REGION_RE = re.compile(
    r"\(\s*(?P<region>World|USA|Europe|Japan|Asia|Brazil|Korea|Spain|Italy|"
    r"Germany|France|UK|Australia|Taiwan|Hong Kong)\b"
)
```

Returns a `Region` enum (`WORLD`, `USA`, `EUROPE`, ..., `UNKNOWN` for no match). Description tokens after the region (`World 910411`, `USA, Set 2`, `Europe v2.1`) are ignored. The regex deliberately does not match free-text manufacturer parentheticals like `(Midway)`.

### Revision detection (`heuristics.revision_key_of`)

Returns a tuple suitable for lexicographic comparison; higher = later. Three forms recognized:

| Pattern | Example | Returned key |
|---|---|---|
| `(rev <letter>)` | `Foo (rev A)` | `(2, ord('A'))` |
| `(Set <n>)` or `(set <n>)` | `Foo (Set 2)` | `(1, n)` |
| `v<major>.<minor>` (loose) | `Foo v1.5` | `(3, 1, 5)` |
| (none of the above) | `Foo` | `(0,)` |

The leading int is a **family rank** so different revision-encoding styles compare consistently (revision letters > set numbers > unmarked, with explicit `v` versions ranked highest as the most recent convention). Tied family ranks fall through to subsequent tuple elements.

## Errors

`FilterError(Exception)` base. Subclasses:
- `ConfigError` — invalid `FilterConfig` values (e.g. unknown region in `region_priority`).
- `OverridesError` — malformed `overrides.yaml`.
- `SessionsError` — malformed or empty session.

## Out of scope

- File copying or BIOS resolution (Phase 3).
- HTTP API exposure (Phase 4).
- Media URL building (Phase 5).
- Multi-winner overrides ("always include both versions") — future enhancement.
- Localized matching (e.g. fuzzy publisher matches across `Capcom` / `CAPCOM`) — exact `fnmatch` only.
````

- [ ] **Step 3: Run linters and commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/filter/__init__.py src/mame_curator/filter/spec.md
git commit -m "docs(filter): phase-2 spec — drop/pick/override/session contract + yaml schemas"
```

Expected: gates pass; one new commit.

---

## Task 2: Pydantic config / overrides / sessions models

**Files:**
- Create: `src/mame_curator/filter/errors.py`
- Create: `src/mame_curator/filter/config.py`
- Create: `src/mame_curator/filter/overrides.py`
- Create: `src/mame_curator/filter/sessions.py`
- Create: `tests/filter/__init__.py`
- Create: `tests/filter/conftest.py`
- Create: `tests/filter/test_config.py`
- Create: `tests/filter/test_overrides.py`
- Create: `tests/filter/test_sessions.py`

- [ ] **Step 1: Create the test package + conftest**

```bash
mkdir -p tests/filter/fixtures
touch tests/filter/__init__.py
```

Write `tests/filter/conftest.py`:

```python
"""Shared fixtures for filter tests."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """Path to the filter test fixtures directory."""
    return FIXTURES
```

- [ ] **Step 2: Write `tests/filter/test_config.py` (failing)**

```python
"""Tests for FilterConfig."""

import pytest
from pydantic import ValidationError

from mame_curator.filter.config import FilterConfig


def test_defaults_match_design_spec() -> None:
    cfg = FilterConfig()
    assert cfg.drop_bios_devices_mechanical is True
    assert cfg.drop_japanese_only_text is True
    assert cfg.drop_preliminary_emulation is True
    assert cfg.drop_chd_required is True
    assert cfg.drop_mature is True
    assert cfg.prefer_parent_over_clone is True
    assert cfg.prefer_good_driver is True
    assert cfg.region_priority == ("World", "USA", "Europe", "Japan", "Asia", "Brazil")


def test_immutable() -> None:
    cfg = FilterConfig()
    with pytest.raises(ValidationError):
        cfg.drop_chd_required = False  # type: ignore[misc]


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        FilterConfig(bogus_key=True)  # type: ignore[call-arg]


def test_year_range_independent_of_each_other() -> None:
    cfg = FilterConfig(drop_year_before=1980)
    assert cfg.drop_year_before == 1980
    assert cfg.drop_year_after is None
```

- [ ] **Step 3: Run, expect failure (ModuleNotFoundError)**

```bash
uv run pytest tests/filter/test_config.py -v --no-cov
```

- [ ] **Step 4: Implement `src/mame_curator/filter/errors.py`**

```python
"""Typed filter exceptions."""

from __future__ import annotations


class FilterError(Exception):
    """Base for all filter-related errors."""


class ConfigError(FilterError):
    """Invalid FilterConfig values."""


class OverridesError(FilterError):
    """Malformed overrides.yaml."""


class SessionsError(FilterError):
    """Malformed or empty session configuration."""
```

- [ ] **Step 5: Implement `src/mame_curator/filter/config.py`**

```python
"""Pydantic schema for the filter+picker subset of config.yaml."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FilterConfig(BaseModel):
    """The `filters:` and `picker:` sections of config.yaml.

    Defaults match the example config and the design spec §6.2.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    drop_bios_devices_mechanical: bool = True
    drop_categories: tuple[str, ...] = ()
    drop_genres: tuple[str, ...] = ()
    drop_publishers: tuple[str, ...] = ()
    drop_developers: tuple[str, ...] = ()
    drop_year_before: int | None = None
    drop_year_after: int | None = None
    drop_japanese_only_text: bool = True
    drop_preliminary_emulation: bool = True
    drop_chd_required: bool = True
    drop_mature: bool = True

    region_priority: tuple[str, ...] = ("World", "USA", "Europe", "Japan", "Asia", "Brazil")
    preferred_genres: tuple[str, ...] = ()
    preferred_publishers: tuple[str, ...] = ()
    preferred_developers: tuple[str, ...] = ()
    prefer_parent_over_clone: bool = True
    prefer_good_driver: bool = True
```

- [ ] **Step 6: Tests pass**

```bash
uv run pytest tests/filter/test_config.py -v --no-cov
```

Expected: 4 passed.

- [ ] **Step 7: Write `tests/filter/test_overrides.py` (failing)**

```python
"""Tests for the Overrides schema and loader."""

from pathlib import Path

import pytest

from mame_curator.filter.errors import OverridesError
from mame_curator.filter.overrides import Overrides, load_overrides


def test_empty_overrides_is_valid() -> None:
    o = Overrides()
    assert o.entries == {}


def test_overrides_round_trips_via_yaml(tmp_path: Path) -> None:
    f = tmp_path / "overrides.yaml"
    f.write_text("overrides:\n  sf2: sf2ce\n  pacman: pacmanf\n")
    o = load_overrides(f)
    assert o.entries == {"sf2": "sf2ce", "pacman": "pacmanf"}


def test_missing_file_returns_empty_overrides(tmp_path: Path) -> None:
    o = load_overrides(tmp_path / "nope.yaml")
    assert o.entries == {}


def test_malformed_yaml_raises(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text("overrides: [this, is, not, a, mapping]")
    with pytest.raises(OverridesError):
        load_overrides(f)


def test_unknown_top_level_key_raises(tmp_path: Path) -> None:
    f = tmp_path / "wrong.yaml"
    f.write_text("garbage: true\n")
    with pytest.raises(OverridesError):
        load_overrides(f)
```

- [ ] **Step 8: Run, expect failure**

```bash
uv run pytest tests/filter/test_overrides.py -v --no-cov
```

- [ ] **Step 9: Implement `src/mame_curator/filter/overrides.py`**

```python
"""Schema + loader for overrides.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter.errors import OverridesError


class Overrides(BaseModel):
    """User-supplied parent → winner short-name pinning.

    Loaded from `overrides.yaml`; missing file is treated as no overrides.
    Single winner per parent (multi-winner is a post-v1 enhancement).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    entries: dict[str, str] = Field(default_factory=dict, alias="overrides")


def load_overrides(path: Path) -> Overrides:
    """Read and validate `overrides.yaml`. Missing file → empty Overrides."""
    if not path.exists():
        return Overrides()
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise OverridesError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise OverridesError(f"{path} is not a YAML mapping")
    try:
        return Overrides.model_validate(raw)
    except ValidationError as exc:
        raise OverridesError(f"{path} failed schema validation: {exc}") from exc
```

- [ ] **Step 10: Tests pass**

```bash
uv run pytest tests/filter/test_overrides.py -v --no-cov
```

Expected: 5 passed.

- [ ] **Step 11: Write `tests/filter/test_sessions.py` (failing)**

```python
"""Tests for the Sessions schema, loader, and slicer."""

from pathlib import Path

import pytest

from mame_curator.filter.errors import SessionsError
from mame_curator.filter.sessions import Session, Sessions, load_sessions


def test_session_requires_at_least_one_include_rule() -> None:
    with pytest.raises(SessionsError):
        Session.from_raw(name="empty", raw={})


def test_session_year_range_lo_must_not_exceed_hi() -> None:
    with pytest.raises(SessionsError):
        Session.from_raw(name="bad", raw={"include_year_range": [1995, 1990]})


def test_active_must_reference_a_defined_session(tmp_path: Path) -> None:
    f = tmp_path / "sessions.yaml"
    f.write_text("active: missing\nsessions: {}\n")
    with pytest.raises(SessionsError):
        load_sessions(f)


def test_minimal_session_round_trip(tmp_path: Path) -> None:
    f = tmp_path / "sessions.yaml"
    f.write_text(
        "active: null\n"
        "sessions:\n"
        "  shooters:\n"
        "    include_genres: ['Shooter*']\n"
    )
    s = load_sessions(f)
    assert s.active is None
    assert s.sessions["shooters"].include_genres == ("Shooter*",)


def test_missing_file_returns_empty_sessions(tmp_path: Path) -> None:
    s = load_sessions(tmp_path / "nope.yaml")
    assert s.active is None
    assert s.sessions == {}


def test_full_session_with_all_includes(tmp_path: Path) -> None:
    f = tmp_path / "sessions.yaml"
    f.write_text(
        "active: capcom_fighters\n"
        "sessions:\n"
        "  capcom_fighters:\n"
        "    include_publishers: ['Capcom*']\n"
        "    include_genres: ['Fighter*']\n"
        "    include_year_range: [1991, 1995]\n"
    )
    s = load_sessions(f)
    cf = s.sessions["capcom_fighters"]
    assert cf.include_publishers == ("Capcom*",)
    assert cf.include_genres == ("Fighter*",)
    assert cf.include_year_range == (1991, 1995)
```

- [ ] **Step 12: Run, expect failure**

```bash
uv run pytest tests/filter/test_sessions.py -v --no-cov
```

- [ ] **Step 13: Implement `src/mame_curator/filter/sessions.py`**

```python
"""Schema + loader for sessions.yaml (continuation-mode session focuses)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from mame_curator.filter.errors import SessionsError


class Session(BaseModel):
    """A named filter that slices the visible set to a working subset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    include_genres: tuple[str, ...] = ()
    include_publishers: tuple[str, ...] = ()
    include_developers: tuple[str, ...] = ()
    include_year_range: tuple[int, int] | None = None

    @classmethod
    def from_raw(cls, name: str, raw: dict[str, Any]) -> Session:
        """Validate one session block from the YAML and reject empty ones."""
        try:
            session = cls.model_validate(raw)
        except ValidationError as exc:
            raise SessionsError(f"session '{name}': {exc}") from exc
        if (
            not session.include_genres
            and not session.include_publishers
            and not session.include_developers
            and session.include_year_range is None
        ):
            raise SessionsError(f"session '{name}' has no include rules")
        if session.include_year_range is not None:
            lo, hi = session.include_year_range
            if lo > hi:
                raise SessionsError(f"session '{name}' year range {lo}..{hi} is reversed")
        return session


class Sessions(BaseModel):
    """Top-level sessions.yaml: a name → Session map plus the active key."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    active: str | None = None
    sessions: dict[str, Session] = Field(default_factory=dict)


def load_sessions(path: Path) -> Sessions:
    """Read and validate `sessions.yaml`. Missing file → empty Sessions."""
    if not path.exists():
        return Sessions()
    try:
        raw: Any = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SessionsError(f"failed to parse {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SessionsError(f"{path} is not a YAML mapping")

    active = raw.get("active")
    sessions_raw = raw.get("sessions") or {}
    if not isinstance(sessions_raw, dict):
        raise SessionsError(f"{path} 'sessions' must be a mapping")

    validated: dict[str, Session] = {
        name: Session.from_raw(name, body or {}) for name, body in sessions_raw.items()
    }
    if active is not None and active not in validated:
        raise SessionsError(f"active session '{active}' is not defined in 'sessions'")
    return Sessions(active=active, sessions=validated)
```

- [ ] **Step 14: Tests pass**

```bash
uv run pytest tests/filter/test_sessions.py -v --no-cov
```

Expected: 6 passed.

- [ ] **Step 15: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/filter/errors.py src/mame_curator/filter/config.py \
        src/mame_curator/filter/overrides.py src/mame_curator/filter/sessions.py \
        tests/filter/
git commit -m "feat(filter): pydantic schemas for FilterConfig, Overrides, Sessions"
```

---

## Task 3: `parse_listxml_cloneof` (extends `parser/listxml.py`)

**Files:**
- Modify: `src/mame_curator/parser/listxml.py` — add `parse_listxml_cloneof`
- Modify: `src/mame_curator/parser/__init__.py` — re-export
- Create: `tests/filter/fixtures/listxml_cloneof.xml`
- Create: `tests/filter/test_listxml_cloneof.py`

- [ ] **Step 1: Create the cloneof fixture**

Write `tests/filter/fixtures/listxml_cloneof.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<mame build="0.284-fixture">
    <machine name="sf2"><description>Street Fighter II: World Warrior</description></machine>
    <machine name="sf2ce" cloneof="sf2" romof="sf2"><description>SF II: Champion Edition</description></machine>
    <machine name="sf2t" cloneof="sf2" romof="sf2"><description>SF II: Hyper Fighting</description></machine>
    <machine name="pacman"><description>Pac-Man</description></machine>
    <machine name="pacmanf" cloneof="pacman"><description>Pac-Man (speedup)</description></machine>
    <machine name="standalone"><description>Standalone</description></machine>
</mame>
```

- [ ] **Step 2: Write `tests/filter/test_listxml_cloneof.py` (failing)**

```python
"""Tests for parse_listxml_cloneof."""

from pathlib import Path

import pytest

from mame_curator.parser.errors import ListxmlError
from mame_curator.parser.listxml import parse_listxml_cloneof


def test_returns_clone_to_parent_map(fixtures_dir: Path) -> None:
    cloneof = parse_listxml_cloneof(fixtures_dir / "listxml_cloneof.xml")
    assert cloneof == {
        "sf2ce": "sf2",
        "sf2t": "sf2",
        "pacmanf": "pacman",
    }


def test_parents_and_standalones_excluded(fixtures_dir: Path) -> None:
    """Machines without a cloneof attribute do not appear in the map."""
    cloneof = parse_listxml_cloneof(fixtures_dir / "listxml_cloneof.xml")
    for parent in ("sf2", "pacman", "standalone"):
        assert parent not in cloneof


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(ListxmlError, match="not exist"):
        parse_listxml_cloneof(tmp_path / "nope.xml")


def test_malformed_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xml"
    bad.write_text("<mame><machine name='x' cloneof='y'>")
    with pytest.raises(ListxmlError):
        parse_listxml_cloneof(bad)
```

- [ ] **Step 3: Run, expect failure**

```bash
uv run pytest tests/filter/test_listxml_cloneof.py -v --no-cov
```

- [ ] **Step 4: Add `parse_listxml_cloneof` to `src/mame_curator/parser/listxml.py`**

Append (after `parse_listxml_disks`):

```python
def parse_listxml_cloneof(path: Path) -> dict[str, str]:
    """Return {clone_short_name: parent_short_name} from MAME `-listxml`.

    Pleasuredome ROM-set DATs strip the `cloneof` attribute, so Phase 2 of the
    filter sources parent/clone relationships from the official MAME XML. Only
    machines with a non-empty `cloneof` attribute are included; parents and
    standalone machines are absent from the returned map.
    """
    if not path.exists():
        raise ListxmlError("listxml path does not exist", path=path)

    cloneof: dict[str, str] = {}
    try:
        for _event, elem in etree.iterparse(str(path), events=("end",), tag="machine"):
            name = elem.get("name")
            parent = elem.get("cloneof")
            if name and parent:
                cloneof[name] = parent
            elem.clear()
    except etree.XMLSyntaxError as exc:
        raise ListxmlError(f"XML parse failed: {exc}", path=path) from exc
    return cloneof
```

- [ ] **Step 5: Update `src/mame_curator/parser/__init__.py` to re-export**

Replace the file with this exact content (preserves alphabetical order in `__all__`):

```python
"""DAT XML and INI reference-file parsers.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.parser.dat import parse_dat
from mame_curator.parser.errors import DATError, INIError, ListxmlError, ParserError
from mame_curator.parser.ini import (
    parse_bestgames,
    parse_catver,
    parse_languages,
    parse_mature,
    parse_series,
)
from mame_curator.parser.listxml import parse_listxml_cloneof, parse_listxml_disks
from mame_curator.parser.manufacturer import split_manufacturer
from mame_curator.parser.models import BiosSet, DriverStatus, Machine, Rom

__all__ = [
    "BiosSet",
    "DATError",
    "DriverStatus",
    "INIError",
    "ListxmlError",
    "Machine",
    "ParserError",
    "Rom",
    "parse_bestgames",
    "parse_catver",
    "parse_dat",
    "parse_languages",
    "parse_listxml_cloneof",
    "parse_listxml_disks",
    "parse_mature",
    "parse_series",
    "split_manufacturer",
]
```

- [ ] **Step 6: Tests pass**

```bash
uv run pytest tests/filter/test_listxml_cloneof.py tests/parser/ -v --no-cov
```

Expected: every test passes including pre-existing parser tests (regression).

- [ ] **Step 7: Update `parser/spec.md` to document the new function**

In `src/mame_curator/parser/spec.md`, find the "Public functions" section and add (after `parse_listxml_disks`):

```markdown
### `parse_listxml_cloneof(path: Path) -> dict[str, str]`

- Returns `{clone_short_name: parent_short_name}` for every machine with a non-empty `cloneof` attribute. Parents and standalone machines are absent from the map.
- Used by `filter/` to reconstruct parent/clone relationships that the Pleasuredome DAT strips.
- Same `lxml.iterparse` streaming pattern as `parse_listxml_disks`.
```

- [ ] **Step 8: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/parser/listxml.py src/mame_curator/parser/__init__.py \
        src/mame_curator/parser/spec.md \
        tests/filter/fixtures/listxml_cloneof.xml tests/filter/test_listxml_cloneof.py
git commit -m "feat(parser): parse_listxml_cloneof for parent/clone reconstruction"
```

---

## Task 4: Heuristics — `region_of` + `revision_key_of`

**Files:**
- Create: `src/mame_curator/filter/heuristics.py`
- Create: `tests/filter/test_heuristics.py`

- [ ] **Step 1: Write `tests/filter/test_heuristics.py` (failing)**

```python
"""Tests for region and revision heuristics."""

import pytest

from mame_curator.filter.heuristics import Region, region_of, revision_key_of


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Street Fighter II (World 910411)", Region.WORLD),
        ("Galaxian (USA, Set 2)", Region.USA),
        ("Sonic (Europe v2.1)", Region.EUROPE),
        ("Strider (Japan, prototype)", Region.JAPAN),
        ("Mahjong (Asia)", Region.ASIA),
        ("Mortal Kombat (Brazil)", Region.BRAZIL),
        ("Pac-Man (Midway)", Region.UNKNOWN),  # manufacturer parenthetical, not region
        ("Standalone Game", Region.UNKNOWN),
        ("Game (Germany 1998)", Region.GERMANY),
    ],
)
def test_region_of(description: str, expected: Region) -> None:
    assert region_of(description) is expected


def test_region_picks_first_match_only() -> None:
    """If two parentheticals look like regions, the first one wins."""
    assert region_of("Foo (World) (Japan)") is Region.WORLD


@pytest.mark.parametrize(
    ("description", "left_expected_higher_than"),
    [
        ("Foo (rev B)", "Foo (rev A)"),
        ("Foo (Set 3)", "Foo (Set 2)"),
        ("Foo v2.0", "Foo v1.5"),
        ("Foo v1.5", "Foo (rev Z)"),  # v-version family > rev-letter family
        ("Foo (rev A)", "Foo (Set 9)"),  # rev-letter family > set-number family
        ("Foo (Set 1)", "Foo"),  # any family > unmarked
    ],
)
def test_revision_key_orders_correctly(description: str, left_expected_higher_than: str) -> None:
    assert revision_key_of(description) > revision_key_of(left_expected_higher_than)


def test_revision_key_equal_for_no_marker() -> None:
    assert revision_key_of("Foo") == revision_key_of("Bar")
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/filter/test_heuristics.py -v --no-cov
```

- [ ] **Step 3: Implement `src/mame_curator/filter/heuristics.py`**

```python
"""Pure heuristics on machine descriptions: region + revision key.

These are best-effort string parsers — MAME descriptions are free-form text.
The recognized patterns are documented in spec.md and pinned by tests.
"""

from __future__ import annotations

import re
from enum import StrEnum

REGION_RE = re.compile(
    r"\(\s*(?P<region>"
    r"World|USA|Europe|Japan|Asia|Brazil|Korea|Spain|Italy|"
    r"Germany|France|UK|Australia|Taiwan|Hong Kong"
    r")\b"
)

_REV_LETTER_RE = re.compile(r"\(\s*rev\s+(?P<letter>[A-Z])\s*\)")
_SET_NUMBER_RE = re.compile(r"\(\s*[Ss]et\s+(?P<n>\d+)\s*\)")
_V_VERSION_RE = re.compile(r"\bv(?P<major>\d+)(?:\.(?P<minor>\d+))?\b")


class Region(StrEnum):
    """Parsed region tag from a machine description."""

    WORLD = "World"
    USA = "USA"
    EUROPE = "Europe"
    JAPAN = "Japan"
    ASIA = "Asia"
    BRAZIL = "Brazil"
    KOREA = "Korea"
    SPAIN = "Spain"
    ITALY = "Italy"
    GERMANY = "Germany"
    FRANCE = "France"
    UK = "UK"
    AUSTRALIA = "Australia"
    TAIWAN = "Taiwan"
    HONG_KONG = "Hong Kong"
    UNKNOWN = "Unknown"


def region_of(description: str) -> Region:
    """Return the first recognized region tag in the description, or UNKNOWN."""
    match = REGION_RE.search(description)
    if match is None:
        return Region.UNKNOWN
    return Region(match.group("region"))


def revision_key_of(description: str) -> tuple[int, ...]:
    """Return a tuple sortable lexicographically; higher = later revision.

    Family ranks: v-version (3) > rev-letter (2) > set-number (1) > unmarked (0).
    """
    if (m := _V_VERSION_RE.search(description)) is not None:
        major = int(m.group("major"))
        minor = int(m.group("minor")) if m.group("minor") is not None else 0
        return (3, major, minor)
    if (m := _REV_LETTER_RE.search(description)) is not None:
        return (2, ord(m.group("letter")))
    if (m := _SET_NUMBER_RE.search(description)) is not None:
        return (1, int(m.group("n")))
    return (0,)
```

- [ ] **Step 4: Tests pass**

```bash
uv run pytest tests/filter/test_heuristics.py -v --no-cov
```

Expected: all parametrized cases pass.

- [ ] **Step 5: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/filter/heuristics.py tests/filter/test_heuristics.py
git commit -m "feat(filter): region and revision-key heuristics"
```

---

## Task 5: Result types — `DroppedReason`, `FilterDecision`, `ContestedGroup`, `FilterResult`

**Files:**
- Create: `src/mame_curator/filter/types.py`

(No tests in this task — types are exercised by every subsequent test.)

- [ ] **Step 1: Implement `src/mame_curator/filter/types.py`**

```python
"""Result types for the filter rule chain."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DroppedReason(StrEnum):
    """Why a machine was dropped in Phase A.

    Order matches the spec's drop-rule ordering. The first rule to match wins.
    """

    BIOS = "bios"
    DEVICE = "device"
    MECHANICAL = "mechanical"
    CATEGORY = "category"
    MATURE = "mature"
    JAPANESE_ONLY = "japanese_only"
    PRELIMINARY_DRIVER = "preliminary_driver"
    CHD_REQUIRED = "chd_required"
    GENRE = "genre"
    PUBLISHER = "publisher"
    DEVELOPER = "developer"
    YEAR_BEFORE = "year_before"
    YEAR_AFTER = "year_after"


class TiebreakerHit(BaseModel):
    """One step in the picker chain that influenced the winner."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str  # e.g. "tier", "preferred_genre", "parent_over_clone"
    detail: str  # e.g. "Best beats Great", "World beats USA"


class ContestedGroup(BaseModel):
    """A parent/clone group with ≥2 Phase-A survivors; records how the winner was chosen."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    parent: str
    candidates: tuple[str, ...]
    winner: str
    chain: tuple[TiebreakerHit, ...]


class FilterResult(BaseModel):
    """Output of `run_filter`. Frozen and deterministic for a given input."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    winners: tuple[str, ...]
    dropped: dict[str, DroppedReason]
    contested_groups: tuple[ContestedGroup, ...]
    warnings: tuple[str, ...] = ()
```

- [ ] **Step 2: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/filter/types.py
git commit -m "feat(filter): result types — DroppedReason, ContestedGroup, FilterResult"
```

---

## Task 6: Phase A drop predicates

**Files:**
- Create: `src/mame_curator/filter/drops.py`
- Create: `tests/filter/test_drops.py`

The `FilterContext` carries the INI-augmented data (categories, languages, mature set, chd-required set) keyed by short name. Predicates are evaluated in spec order; the first hit wins.

- [ ] **Step 1: Add `FilterContext` to `src/mame_curator/filter/types.py`**

Append to `types.py` (and add `Field` to the existing `from pydantic import ...`):

```python
class FilterContext(BaseModel):
    """INI-augmented per-machine context consumed by Phase A predicates."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: dict[str, str] = Field(default_factory=dict)
    languages: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    mature: frozenset[str] = Field(default_factory=frozenset)
    chd_required: frozenset[str] = Field(default_factory=frozenset)
    cloneof_map: dict[str, str] = Field(default_factory=dict)
    bestgames_tier: dict[str, str] = Field(default_factory=dict)
```

- [ ] **Step 2: Write `tests/filter/test_drops.py` (failing)**

```python
"""Tests for Phase A drop predicates — one test per rule."""

from __future__ import annotations

import pytest

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.drops import drop_reason
from mame_curator.filter.types import DroppedReason, FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def m(**kw: object) -> Machine:
    """Minimal Machine builder; description defaults to name."""
    name = str(kw.pop("name", "x"))
    description = str(kw.pop("description", name))
    return Machine(name=name, description=description, **kw)  # type: ignore[arg-type]


def test_bios_dropped() -> None:
    assert drop_reason(m(name="ng", is_bios=True), FilterContext(), FilterConfig()) is DroppedReason.BIOS


def test_device_dropped() -> None:
    assert drop_reason(m(name="z80", is_device=True), FilterContext(), FilterConfig()) is DroppedReason.DEVICE


def test_non_runnable_dropped_as_device() -> None:
    assert drop_reason(m(name="z80", runnable=False), FilterContext(), FilterConfig()) is DroppedReason.DEVICE


def test_mechanical_dropped() -> None:
    assert drop_reason(m(name="x", is_mechanical=True), FilterContext(), FilterConfig()) is DroppedReason.MECHANICAL


def test_category_pattern_dropped() -> None:
    ctx = FilterContext(category={"slot1": "Casino / Slot Machine"})
    cfg = FilterConfig(drop_categories=("Casino*",))
    assert drop_reason(m(name="slot1"), ctx, cfg) is DroppedReason.CATEGORY


def test_mature_dropped() -> None:
    ctx = FilterContext(mature=frozenset({"adultx"}))
    assert drop_reason(m(name="adultx"), ctx, FilterConfig()) is DroppedReason.MATURE


def test_japanese_only_dropped() -> None:
    ctx = FilterContext(languages={"jp": ("Japanese",)})
    assert drop_reason(m(name="jp"), ctx, FilterConfig()) is DroppedReason.JAPANESE_ONLY


def test_japanese_with_other_language_kept() -> None:
    ctx = FilterContext(languages={"x": ("Japanese", "English")})
    assert drop_reason(m(name="x"), ctx, FilterConfig()) is None


def test_preliminary_driver_dropped() -> None:
    assert drop_reason(
        m(name="b", driver_status=DriverStatus.PRELIMINARY),
        FilterContext(),
        FilterConfig(),
    ) is DroppedReason.PRELIMINARY_DRIVER


def test_chd_required_dropped() -> None:
    ctx = FilterContext(chd_required=frozenset({"kinst"}))
    assert drop_reason(m(name="kinst"), ctx, FilterConfig()) is DroppedReason.CHD_REQUIRED


def test_genre_pattern_dropped() -> None:
    ctx = FilterContext(category={"x": "Maze / Collect"})
    cfg = FilterConfig(drop_genres=("Collect",))
    assert drop_reason(m(name="x"), ctx, cfg) is DroppedReason.GENRE


def test_publisher_pattern_dropped() -> None:
    cfg = FilterConfig(drop_publishers=("Aristocrat*",))
    assert drop_reason(
        m(name="x", publisher="Aristocrat", developer="Aristocrat"), FilterContext(), cfg
    ) is DroppedReason.PUBLISHER


def test_developer_pattern_dropped() -> None:
    cfg = FilterConfig(drop_developers=("Bad*",))
    assert drop_reason(
        m(name="x", publisher="Good", developer="BadStudio"), FilterContext(), cfg
    ) is DroppedReason.DEVELOPER


def test_year_before_dropped() -> None:
    cfg = FilterConfig(drop_year_before=1980)
    assert drop_reason(m(name="x", year=1979), FilterContext(), cfg) is DroppedReason.YEAR_BEFORE


def test_year_after_dropped() -> None:
    cfg = FilterConfig(drop_year_after=2010)
    assert drop_reason(m(name="x", year=2011), FilterContext(), cfg) is DroppedReason.YEAR_AFTER


def test_clean_machine_not_dropped() -> None:
    assert drop_reason(
        m(name="pacman", year=1980, publisher="Namco", developer="Namco"),
        FilterContext(category={"pacman": "Maze / Collect"}),
        FilterConfig(),
    ) is None
```

- [ ] **Step 3: Run, expect failure**

```bash
uv run pytest tests/filter/test_drops.py -v --no-cov
```

- [ ] **Step 4: Implement `src/mame_curator/filter/drops.py`**

```python
"""Phase A drop predicates.

Each predicate returns the matching DroppedReason or None. The public
`drop_reason()` runs them in spec order and returns the first hit.
"""

from __future__ import annotations

from collections.abc import Callable
from fnmatch import fnmatchcase

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.types import DroppedReason, FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def _matches_any(value: str | None, patterns: tuple[str, ...]) -> bool:
    if value is None or not patterns:
        return False
    return any(fnmatchcase(value, p) for p in patterns)


def _genre_of(category: str | None) -> str | None:
    if category is None:
        return None
    return category.rsplit("/", 1)[-1].strip()


def _bios(m: Machine, _c: FilterContext, _f: FilterConfig) -> DroppedReason | None:
    return DroppedReason.BIOS if m.is_bios else None


def _device(m: Machine, _c: FilterContext, _f: FilterConfig) -> DroppedReason | None:
    return DroppedReason.DEVICE if (m.is_device or not m.runnable) else None


def _mechanical(m: Machine, _c: FilterContext, _f: FilterConfig) -> DroppedReason | None:
    return DroppedReason.MECHANICAL if m.is_mechanical else None


def _category(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    cat = ctx.category.get(m.name)
    return DroppedReason.CATEGORY if _matches_any(cat, cfg.drop_categories) else None


def _mature(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    return DroppedReason.MATURE if (cfg.drop_mature and m.name in ctx.mature) else None


def _japanese_only(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if not cfg.drop_japanese_only_text:
        return None
    langs = ctx.languages.get(m.name)
    if langs == ("Japanese",):
        return DroppedReason.JAPANESE_ONLY
    return None


def _preliminary(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if cfg.drop_preliminary_emulation and m.driver_status is DriverStatus.PRELIMINARY:
        return DroppedReason.PRELIMINARY_DRIVER
    return None


def _chd(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    return DroppedReason.CHD_REQUIRED if (cfg.drop_chd_required and m.name in ctx.chd_required) else None


def _genre(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    genre = _genre_of(ctx.category.get(m.name))
    return DroppedReason.GENRE if _matches_any(genre, cfg.drop_genres) else None


def _publisher(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    return DroppedReason.PUBLISHER if _matches_any(m.publisher, cfg.drop_publishers) else None


def _developer(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    return DroppedReason.DEVELOPER if _matches_any(m.developer, cfg.drop_developers) else None


def _year_before(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if cfg.drop_year_before is not None and m.year is not None and m.year < cfg.drop_year_before:
        return DroppedReason.YEAR_BEFORE
    return None


def _year_after(m: Machine, _c: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    if cfg.drop_year_after is not None and m.year is not None and m.year > cfg.drop_year_after:
        return DroppedReason.YEAR_AFTER
    return None


_PREDICATES: tuple[Callable[[Machine, FilterContext, FilterConfig], DroppedReason | None], ...] = (
    _bios,
    _device,
    _mechanical,
    _category,
    _mature,
    _japanese_only,
    _preliminary,
    _chd,
    _genre,
    _publisher,
    _developer,
    _year_before,
    _year_after,
)


def drop_reason(m: Machine, ctx: FilterContext, cfg: FilterConfig) -> DroppedReason | None:
    """Return the first matching DroppedReason, or None if the machine survives."""
    for predicate in _PREDICATES:
        reason = predicate(m, ctx, cfg)
        if reason is not None:
            return reason
    return None
```

- [ ] **Step 5: Tests pass**

```bash
uv run pytest tests/filter/test_drops.py -v --no-cov
```

Expected: 16 passed.

- [ ] **Step 6: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/filter/drops.py src/mame_curator/filter/types.py \
        tests/filter/test_drops.py
git commit -m "feat(filter): phase A drop predicates with one test per rule"
```

---

## Task 7: Phase B picker — tiebreaker comparators + `pick_winner` + `explain_pick`

**Files:**
- Create: `src/mame_curator/filter/picker.py`
- Create: `tests/filter/test_picker.py`

- [ ] **Step 1: Write `tests/filter/test_picker.py` (failing)**

```python
"""Tests for Phase B tiebreaker comparators and pick_winner."""

from __future__ import annotations

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.picker import explain_pick, pick_winner
from mame_curator.filter.types import FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def m(**kw: object) -> Machine:
    name = str(kw.pop("name", "x"))
    description = str(kw.pop("description", name))
    return Machine(name=name, description=description, **kw)  # type: ignore[arg-type]


def test_tier_tiebreaker_wins() -> None:
    pacman = m(name="pacman", description="Pac-Man (USA)")
    pacmanf = m(name="pacmanf", description="Pac-Man speedup (USA)")
    ctx = FilterContext(bestgames_tier={"pacman": "Best", "pacmanf": "Average"})
    winner = pick_winner([pacman, pacmanf], parent="pacman", ctx=ctx, cfg=FilterConfig())
    assert winner.name == "pacman"


def test_preferred_genre_boost_breaks_tier_tie() -> None:
    a = m(name="a", description="A (World)")
    b = m(name="b", description="B (World)")
    ctx = FilterContext(category={"a": "Maze / Collect", "b": "Shooter / Vertical"})
    cfg = FilterConfig(preferred_genres=("Vertical",))
    assert pick_winner([a, b], parent="a", ctx=ctx, cfg=cfg).name == "b"


def test_parent_over_clone() -> None:
    parent = m(name="sf2", description="SF II (World)")
    clone = m(name="sf2ce", description="SF II CE (World)", cloneof="sf2")
    ctx = FilterContext(cloneof_map={"sf2ce": "sf2"})
    assert pick_winner([clone, parent], parent="sf2", ctx=ctx, cfg=FilterConfig()).name == "sf2"


def test_good_driver_beats_imperfect() -> None:
    a = m(name="a", description="A (World)", driver_status=DriverStatus.GOOD)
    b = m(name="b", description="B (World)", driver_status=DriverStatus.IMPERFECT)
    assert pick_winner([a, b], parent="a", ctx=FilterContext(), cfg=FilterConfig()).name == "a"


def test_region_priority() -> None:
    world = m(name="w", description="Foo (World)")
    usa = m(name="u", description="Foo (USA)")
    assert pick_winner([usa, world], parent="w", ctx=FilterContext(), cfg=FilterConfig()).name == "w"


def test_revision_key_prefers_later() -> None:
    early = m(name="e", description="Foo (Set 1) (World)")
    late = m(name="l", description="Foo (Set 3) (World)")
    assert pick_winner([early, late], parent="e", ctx=FilterContext(), cfg=FilterConfig()).name == "l"


def test_alphabetical_fallback() -> None:
    a = m(name="abc", description="X (World)")
    b = m(name="xyz", description="X (World)")
    assert pick_winner([b, a], parent="abc", ctx=FilterContext(), cfg=FilterConfig()).name == "abc"


def test_explain_records_decisive_steps_only() -> None:
    pacman = m(name="pacman", description="Pac-Man (USA)")
    pacmanf = m(name="pacmanf", description="Pac-Man speedup (USA)")
    ctx = FilterContext(bestgames_tier={"pacman": "Best", "pacmanf": "Average"})
    chain = explain_pick([pacman, pacmanf], parent="pacman", ctx=ctx, cfg=FilterConfig())
    names = [hit.name for hit in chain]
    assert "tier" in names
    # Region is identical for both — must NOT appear.
    assert "region" not in names
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/filter/test_picker.py -v --no-cov
```

- [ ] **Step 3: Implement `src/mame_curator/filter/picker.py`**

```python
"""Phase B picker — tiebreaker chain produces a winner per parent group.

Each tiebreaker is a `score(machine) -> int | tuple` higher-is-better function.
We sort the candidate list by the composite key (score_1, score_2, ..., name)
and pick the maximum. `explain_pick` re-runs the tiebreakers to identify the
ones that actually decided the result (i.e., produced a non-uniform score).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.heuristics import Region, region_of, revision_key_of
from mame_curator.filter.types import FilterContext, TiebreakerHit
from mame_curator.parser.models import DriverStatus, Machine

_TIER_RANK: dict[str, int] = {
    "Best": 6,
    "Great": 5,
    "Good": 4,
    "Average": 3,
    "Bad": 2,
    "Awful": 1,
}
_DRIVER_RANK: dict[DriverStatus | None, int] = {
    DriverStatus.GOOD: 3,
    DriverStatus.IMPERFECT: 2,
    DriverStatus.PRELIMINARY: 1,
    None: 0,
}

ScoreFn = Callable[[Machine, FilterContext, FilterConfig, str], "tuple[int, ...] | int"]


def _score_tier(m: Machine, ctx: FilterContext, _cfg: FilterConfig, _parent: str) -> int:
    return _TIER_RANK.get(ctx.bestgames_tier.get(m.name, ""), 0)


def _score_preferred(m: Machine, ctx: FilterContext, cfg: FilterConfig, _parent: str) -> int:
    score = 0
    cat = ctx.category.get(m.name)
    if cat is not None:
        for pattern in cfg.preferred_genres:
            if pattern in cat:
                score += 1
                break
    if m.publisher and any(p in m.publisher for p in cfg.preferred_publishers):
        score += 1
    if m.developer and any(p in m.developer for p in cfg.preferred_developers):
        score += 1
    return score


def _score_parent_over_clone(m: Machine, ctx: FilterContext, cfg: FilterConfig, parent: str) -> int:
    if not cfg.prefer_parent_over_clone:
        return 0
    return 1 if m.name == parent else 0


def _score_driver(m: Machine, _ctx: FilterContext, cfg: FilterConfig, _parent: str) -> int:
    return _DRIVER_RANK[m.driver_status] if cfg.prefer_good_driver else 0


def _score_region(m: Machine, _ctx: FilterContext, cfg: FilterConfig, _parent: str) -> int:
    region = region_of(m.description)
    if region is Region.UNKNOWN:
        return -1  # ranks below every listed region
    try:
        return -cfg.region_priority.index(region.value)  # earlier = higher score
    except ValueError:
        return -len(cfg.region_priority)  # listed regions absent from priority list


def _score_revision(m: Machine, _ctx: FilterContext, _cfg: FilterConfig, _parent: str) -> tuple[int, ...]:
    return revision_key_of(m.description)


def _score_alpha(m: Machine, _ctx: FilterContext, _cfg: FilterConfig, _parent: str) -> tuple[int, ...]:
    # Negate so higher composite key still wins; alphabetical-first → highest score.
    return tuple(-ord(c) for c in m.name)


_TIEBREAKERS: tuple[tuple[str, ScoreFn], ...] = (
    ("tier", _score_tier),
    ("preferred", _score_preferred),
    ("parent_over_clone", _score_parent_over_clone),
    ("driver", _score_driver),
    ("region", _score_region),
    ("revision", _score_revision),
    ("alpha", _score_alpha),
)


def _composite_key(
    m: Machine, ctx: FilterContext, cfg: FilterConfig, parent: str
) -> tuple[object, ...]:
    return tuple(score(m, ctx, cfg, parent) for _name, score in _TIEBREAKERS)


def pick_winner(
    candidates: Iterable[Machine], parent: str, ctx: FilterContext, cfg: FilterConfig
) -> Machine:
    """Pick the highest-ranked candidate per the spec's tiebreaker chain."""
    return max(candidates, key=lambda c: _composite_key(c, ctx, cfg, parent))


def explain_pick(
    candidates: Iterable[Machine], parent: str, ctx: FilterContext, cfg: FilterConfig
) -> tuple[TiebreakerHit, ...]:
    """List the tiebreakers that actually decided the winner (non-uniform across candidates)."""
    cand_list = list(candidates)
    winner = pick_winner(cand_list, parent, ctx, cfg)
    hits: list[TiebreakerHit] = []
    for name, score in _TIEBREAKERS:
        scores = {c.name: score(c, ctx, cfg, parent) for c in cand_list}
        if len(set(map(repr, scores.values()))) <= 1:
            continue  # no signal from this tiebreaker
        hits.append(TiebreakerHit(name=name, detail=f"{winner.name}={scores[winner.name]!r}"))
    return tuple(hits)
```

- [ ] **Step 4: Tests pass**

```bash
uv run pytest tests/filter/test_picker.py -v --no-cov
```

Expected: 8 passed.

- [ ] **Step 5: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/filter/picker.py tests/filter/test_picker.py
git commit -m "feat(filter): phase B tiebreaker chain with explain_pick"
```

---

## Task 8: `run_filter` orchestrator (Phases A → B → C → D)

**Files:**
- Create: `src/mame_curator/filter/runner.py`
- Create: `tests/filter/test_runner.py`
- Modify: `src/mame_curator/filter/__init__.py` — public re-exports

- [ ] **Step 1: Write `tests/filter/test_runner.py` (failing)**

```python
"""End-to-end tests for run_filter."""

from __future__ import annotations

import pytest

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Session, Sessions
from mame_curator.filter.types import DroppedReason, FilterContext
from mame_curator.parser.models import DriverStatus, Machine


def m(**kw: object) -> Machine:
    name = str(kw.pop("name", "x"))
    description = str(kw.pop("description", name))
    return Machine(name=name, description=description, **kw)  # type: ignore[arg-type]


@pytest.fixture
def sample() -> tuple[dict[str, Machine], FilterContext]:
    machines = {
        "pacman": m(name="pacman", description="Pac-Man (USA)", year=1980, publisher="Namco", developer="Namco"),
        "pacmanf": m(name="pacmanf", description="Pac-Man speedup (USA)", cloneof="pacman", year=1981, publisher="Namco", developer="Namco"),
        "neogeo": m(name="neogeo", description="Neo-Geo", is_bios=True),
        "z80": m(name="z80", description="Z80 device", is_device=True, runnable=False),
        "3bagfull": m(name="3bagfull", description="3 Bags Full", is_mechanical=True),
        "kinst": m(name="kinst", description="Killer Instinct (USA)", year=1994, publisher="Rare", developer="Rare"),
        "brokensim": m(name="brokensim", description="Broken Sim", driver_status=DriverStatus.PRELIMINARY),
    }
    ctx = FilterContext(
        category={"pacman": "Maze / Collect", "pacmanf": "Maze / Collect", "kinst": "Fighter / Versus"},
        chd_required=frozenset({"kinst"}),
        cloneof_map={"pacmanf": "pacman"},
        bestgames_tier={"pacman": "Best", "pacmanf": "Average"},
    )
    return machines, ctx


def test_phase_a_drops(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    result = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    assert result.dropped["neogeo"] is DroppedReason.BIOS
    assert result.dropped["z80"] is DroppedReason.DEVICE
    assert result.dropped["3bagfull"] is DroppedReason.MECHANICAL
    assert result.dropped["kinst"] is DroppedReason.CHD_REQUIRED
    assert result.dropped["brokensim"] is DroppedReason.PRELIMINARY_DRIVER


def test_winners_are_alphabetically_sorted_and_one_per_group(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    result = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    assert result.winners == ("pacman",)


def test_idempotent(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    a = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    b = run_filter(machines, ctx, FilterConfig(), Overrides(), Sessions())
    assert a == b


def test_overrides_replace_pick(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    result = run_filter(
        machines, ctx, FilterConfig(),
        Overrides(entries={"pacman": "pacmanf"}),
        Sessions(),
    )
    assert result.winners == ("pacmanf",)


def test_unknown_override_warns_doesnt_crash(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    result = run_filter(
        machines, ctx, FilterConfig(),
        Overrides(entries={"pacman": "no_such_machine"}),
        Sessions(),
    )
    assert any("no_such_machine" in w for w in result.warnings)
    assert result.winners == ("pacman",)  # falls back to phase B


def test_session_slices_winners(sample: tuple[dict[str, Machine], FilterContext]) -> None:
    machines, ctx = sample
    fighters_session = Session(include_genres=("Fighter*",))
    sessions = Sessions(active="fighters", sessions={"fighters": fighters_session})
    result = run_filter(machines, ctx, FilterConfig(), Overrides(), sessions)
    # pacman is a maze game, not a fighter — sliced out by the session.
    assert result.winners == ()
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/filter/test_runner.py -v --no-cov
```

- [ ] **Step 3: Implement `src/mame_curator/filter/runner.py`**

```python
"""Orchestrator: drop (A) → pick (B) → override (C) → session-slice (D)."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable
from fnmatch import fnmatchcase

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.drops import drop_reason
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.picker import explain_pick, pick_winner
from mame_curator.filter.sessions import Session, Sessions
from mame_curator.filter.types import (
    ContestedGroup,
    DroppedReason,
    FilterContext,
    FilterResult,
)
from mame_curator.parser.models import Machine

logger = logging.getLogger(__name__)


def run_filter(
    machines: dict[str, Machine],
    ctx: FilterContext,
    cfg: FilterConfig,
    overrides: Overrides,
    sessions: Sessions,
) -> FilterResult:
    """Run the four-phase filter and return a FilterResult."""
    # Phase A — drop.
    survivors: dict[str, Machine] = {}
    dropped: dict[str, DroppedReason] = {}
    for name, m in machines.items():
        reason = drop_reason(m, ctx, cfg)
        if reason is None:
            survivors[name] = m
        else:
            dropped[name] = reason

    # Phase B — group by parent and pick a winner per group.
    groups: dict[str, list[Machine]] = defaultdict(list)
    for m in survivors.values():
        parent = ctx.cloneof_map.get(m.name, m.name)
        groups[parent].append(m)

    winners: dict[str, str] = {}
    contested: list[ContestedGroup] = []
    for parent, candidates in groups.items():
        winner = pick_winner(candidates, parent, ctx, cfg)
        winners[parent] = winner.name
        if len(candidates) > 1:
            contested.append(
                ContestedGroup(
                    parent=parent,
                    candidates=tuple(sorted(c.name for c in candidates)),
                    winner=winner.name,
                    chain=explain_pick(candidates, parent, ctx, cfg),
                )
            )

    # Phase C — apply overrides.
    warnings: list[str] = []
    for parent, override_name in overrides.entries.items():
        if parent not in groups:
            warnings.append(f"override key '{parent}' is not a known parent; ignored")
            continue
        if override_name not in machines:
            warnings.append(f"override target '{override_name}' is not in the DAT; ignored")
            continue
        target_parent = ctx.cloneof_map.get(override_name, override_name)
        if target_parent != parent:
            warnings.append(
                f"override '{parent} -> {override_name}': target belongs to a different group; ignored"
            )
            continue
        winners[parent] = override_name
        # If the override target was dropped in Phase A, un-drop it.
        if override_name in dropped:
            del dropped[override_name]

    # Phase D — session slice.
    visible = _apply_session(winners, machines, ctx, sessions)

    return FilterResult(
        winners=tuple(sorted(visible)),
        dropped=dict(dropped),
        contested_groups=tuple(contested),
        warnings=tuple(warnings),
    )


def _apply_session(
    winners: dict[str, str],
    machines: dict[str, Machine],
    ctx: FilterContext,
    sessions: Sessions,
) -> list[str]:
    """Slice winners to those matching the active session, if any."""
    if sessions.active is None:
        return list(winners.values())
    session = sessions.sessions[sessions.active]
    return [name for name in winners.values() if _machine_matches_session(machines[name], session, ctx)]


def _machine_matches_session(m: Machine, session: Session, ctx: FilterContext) -> bool:
    if session.include_genres:
        cat = ctx.category.get(m.name)
        if cat is None or not _any_fnmatch(cat, session.include_genres):
            return False
    if session.include_publishers:
        if m.publisher is None or not _any_fnmatch(m.publisher, session.include_publishers):
            return False
    if session.include_developers:
        if m.developer is None or not _any_fnmatch(m.developer, session.include_developers):
            return False
    if session.include_year_range is not None:
        lo, hi = session.include_year_range
        if m.year is None or m.year < lo or m.year > hi:
            return False
    return True


def _any_fnmatch(value: str, patterns: Iterable[str]) -> bool:
    return any(fnmatchcase(value, p) for p in patterns)
```

- [ ] **Step 4: Update `src/mame_curator/filter/__init__.py` to expose the public API**

Replace its content with:

```python
"""Filter rule chain — drop, pick, override, session-slice.

Public API surface — see spec.md for the full contract.
"""

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.errors import (
    ConfigError,
    FilterError,
    OverridesError,
    SessionsError,
)
from mame_curator.filter.heuristics import Region, region_of, revision_key_of
from mame_curator.filter.overrides import Overrides, load_overrides
from mame_curator.filter.picker import explain_pick, pick_winner
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Session, Sessions, load_sessions
from mame_curator.filter.types import (
    ContestedGroup,
    DroppedReason,
    FilterContext,
    FilterResult,
    TiebreakerHit,
)

__all__ = [
    "ConfigError",
    "ContestedGroup",
    "DroppedReason",
    "FilterConfig",
    "FilterContext",
    "FilterError",
    "FilterResult",
    "Overrides",
    "OverridesError",
    "Region",
    "Session",
    "Sessions",
    "SessionsError",
    "TiebreakerHit",
    "explain_pick",
    "load_overrides",
    "load_sessions",
    "pick_winner",
    "region_of",
    "revision_key_of",
    "run_filter",
]
```

- [ ] **Step 5: Tests pass**

```bash
uv run pytest tests/filter/ -v --no-cov
```

Expected: every filter test passes (config + overrides + sessions + heuristics + listxml_cloneof + drops + picker + runner).

- [ ] **Step 6: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/filter/runner.py src/mame_curator/filter/__init__.py \
        tests/filter/test_runner.py
git commit -m "feat(filter): run_filter orchestrator with overrides and session-slice"
```

---

## Task 9: Property tests — determinism + override-locality

**Files:**
- Create: `tests/filter/test_property.py`

- [ ] **Step 1: Write `tests/filter/test_property.py`**

```python
"""Property-based regression: determinism + override-locality."""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.overrides import Overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import Sessions
from mame_curator.filter.types import FilterContext
from mame_curator.parser.models import Machine


def _machine(name: str, year: int) -> Machine:
    return Machine(
        name=name,
        description=f"{name} (USA)",
        year=year,
        publisher="Acme",
        developer="Acme",
    )


short_names = st.text(
    alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
    min_size=2,
    max_size=8,
)


@settings(max_examples=100, deadline=None)
@given(names=st.lists(short_names, min_size=1, max_size=15, unique=True))
def test_determinism_same_input_same_output(names: list[str]) -> None:
    machines = {n: _machine(n, 1980 + i) for i, n in enumerate(names)}
    a = run_filter(machines, FilterContext(), FilterConfig(), Overrides(), Sessions())
    b = run_filter(machines, FilterContext(), FilterConfig(), Overrides(), Sessions())
    assert a == b


@settings(max_examples=50, deadline=None)
@given(names=st.lists(short_names, min_size=2, max_size=10, unique=True))
def test_idempotent(names: list[str]) -> None:
    """Re-running on the prior result's winners (as new machines) yields the same winners."""
    machines = {n: _machine(n, 1980 + i) for i, n in enumerate(names)}
    first = run_filter(machines, FilterContext(), FilterConfig(), Overrides(), Sessions())
    survivors = {n: machines[n] for n in first.winners}
    second = run_filter(survivors, FilterContext(), FilterConfig(), Overrides(), Sessions())
    assert second.winners == first.winners
```

- [ ] **Step 2: Tests pass**

```bash
uv run pytest tests/filter/test_property.py -v --no-cov
```

Expected: both properties pass (100 + 50 examples).

- [ ] **Step 3: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add tests/filter/test_property.py
git commit -m "test(filter): hypothesis property tests for determinism + idempotency"
```

---

## Task 10: Snapshot test — 30-machine fixture DAT

**Files:**
- Create: `tests/filter/fixtures/snapshot_dat.xml`
- Create: `tests/filter/fixtures/snapshot_listxml.xml`
- Create: `tests/filter/fixtures/snapshot_catver.ini`
- Create: `tests/filter/fixtures/snapshot_languages.ini`
- Create: `tests/filter/fixtures/snapshot_bestgames.ini`
- Create: `tests/filter/fixtures/snapshot_overrides.yaml`
- Create: `tests/filter/fixtures/snapshot_sessions.yaml`
- Create: `tests/snapshots/filter_smoke.json`
- Create: `tests/filter/test_snapshot.py`

Snapshot regression: a hand-picked 30-machine fixture exercising every drop rule, every tiebreaker, plus an override and a session. The expected JSON is committed; the test asserts byte-equality.

- [ ] **Step 1: Write `tests/filter/fixtures/snapshot_dat.xml`**

A 30-machine DAT exercising each rule. Begin with this skeleton and add machines (use the design spec §6.2 worked examples as guidance — the contents below are a complete set):

```xml
<?xml version="1.0" encoding="utf-8"?>
<datafile>
    <header><name>filter snapshot</name><version>0.284-fixture</version></header>

    <!-- Phase A drops -->
    <machine name="neogeo" isbios="yes"><description>Neo-Geo BIOS</description><manufacturer>SNK</manufacturer></machine>
    <machine name="z80dev" isdevice="yes" runnable="no"><description>Z80 device</description><manufacturer>Zilog</manufacturer></machine>
    <machine name="3bagfull" ismechanical="yes"><description>3 Bags Full</description><manufacturer>Aristocrat</manufacturer><year>1996</year></machine>
    <machine name="aristoslot"><description>Slot (Aristocrat)</description><manufacturer>Aristocrat</manufacturer><year>2000</year></machine>
    <machine name="mahjong1"><description>Mahjong Variant</description><manufacturer>Nichibutsu</manufacturer><year>1990</year></machine>
    <machine name="jpgame"><description>Japan Only Game</description><manufacturer>Hudson</manufacturer><year>1988</year></machine>
    <machine name="brokensim"><description>Broken (preliminary)</description><manufacturer>?</manufacturer><year>1992</year><driver status="preliminary"/></machine>
    <machine name="kinst"><description>Killer Instinct (USA)</description><manufacturer>Rare</manufacturer><year>1994</year></machine>
    <machine name="oldgame"><description>Old Game (1975)</description><manufacturer>Atari</manufacturer><year>1975</year></machine>
    <machine name="newgame"><description>New Game (2020)</description><manufacturer>Modern</manufacturer><year>2020</year></machine>

    <!-- Phase B groups -->
    <machine name="pacman"><description>Pac-Man (USA)</description><manufacturer>Namco (Midway license)</manufacturer><year>1980</year></machine>
    <machine name="pacmanf" cloneof="pacman" romof="pacman"><description>Pac-Man speedup (USA)</description><manufacturer>hack</manufacturer><year>1981</year><driver status="imperfect"/></machine>

    <machine name="sf2"><description>Street Fighter II: World Warrior (World 910411)</description><manufacturer>Capcom</manufacturer><year>1991</year></machine>
    <machine name="sf2ce" cloneof="sf2" romof="sf2"><description>SF II: Champion Edition (World 920313)</description><manufacturer>Capcom</manufacturer><year>1992</year></machine>
    <machine name="sf2t" cloneof="sf2" romof="sf2"><description>SF II: Hyper Fighting (World 921209)</description><manufacturer>Capcom</manufacturer><year>1992</year></machine>

    <machine name="galaxian"><description>Galaxian (Namco set 1) (World)</description><manufacturer>Namco</manufacturer><year>1979</year></machine>
    <machine name="galaxianm" cloneof="galaxian"><description>Galaxian (Midway set 2) (USA)</description><manufacturer>Midway</manufacturer><year>1979</year></machine>

    <machine name="dkong"><description>Donkey Kong (US set 1)</description><manufacturer>Nintendo</manufacturer><year>1981</year></machine>
    <machine name="dkongj" cloneof="dkong"><description>Donkey Kong (Japan)</description><manufacturer>Nintendo</manufacturer><year>1981</year></machine>

    <machine name="mslug"><description>Metal Slug (World)</description><manufacturer>Nazca</manufacturer><year>1996</year></machine>
    <machine name="mslugu" cloneof="mslug"><description>Metal Slug (USA, set 2) v1.5</description><manufacturer>Nazca</manufacturer><year>1996</year></machine>

    <machine name="ddragon"><description>Double Dragon (World rev A)</description><manufacturer>Technos Japan</manufacturer><year>1987</year></machine>
    <machine name="ddragonb" cloneof="ddragon"><description>Double Dragon (World rev B)</description><manufacturer>Technos Japan</manufacturer><year>1987</year></machine>

    <machine name="rtype"><description>R-Type (World)</description><manufacturer>Irem</manufacturer><year>1987</year></machine>
    <machine name="rtypeu" cloneof="rtype"><description>R-Type (USA)</description><manufacturer>Irem</manufacturer><year>1987</year></machine>

    <machine name="qbert"><description>Q*bert's Qubes (USA)</description><manufacturer>Mylstar</manufacturer><year>1983</year></machine>

    <machine name="bublbobl"><description>Bubble Bobble (World)</description><manufacturer>Taito</manufacturer><year>1986</year></machine>
    <machine name="bublboblj" cloneof="bublbobl"><description>Bubble Bobble (Japan)</description><manufacturer>Taito</manufacturer><year>1986</year></machine>

    <machine name="contra"><description>Contra (World)</description><manufacturer>Konami</manufacturer><year>1987</year></machine>
    <machine name="contrau" cloneof="contra"><description>Contra (USA)</description><manufacturer>Konami</manufacturer><year>1987</year></machine>
</datafile>
```

- [ ] **Step 2: Write `tests/filter/fixtures/snapshot_listxml.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<mame build="0.284-fixture">
    <machine name="pacman"><description>Pac-Man</description></machine>
    <machine name="pacmanf" cloneof="pacman"><description>Pac-Man speedup</description></machine>
    <machine name="sf2"><description>SF II</description></machine>
    <machine name="sf2ce" cloneof="sf2"><description>SF II CE</description></machine>
    <machine name="sf2t" cloneof="sf2"><description>SF II HF</description></machine>
    <machine name="galaxian"><description>Galaxian</description></machine>
    <machine name="galaxianm" cloneof="galaxian"><description>Galaxian Midway</description></machine>
    <machine name="dkong"><description>Donkey Kong</description></machine>
    <machine name="dkongj" cloneof="dkong"><description>Donkey Kong J</description></machine>
    <machine name="mslug"><description>Metal Slug</description></machine>
    <machine name="mslugu" cloneof="mslug"><description>Metal Slug US</description></machine>
    <machine name="ddragon"><description>Double Dragon</description></machine>
    <machine name="ddragonb" cloneof="ddragon"><description>Double Dragon revB</description></machine>
    <machine name="rtype"><description>R-Type</description></machine>
    <machine name="rtypeu" cloneof="rtype"><description>R-Type US</description></machine>
    <machine name="bublbobl"><description>Bubble Bobble</description></machine>
    <machine name="bublboblj" cloneof="bublbobl"><description>Bubble Bobble J</description></machine>
    <machine name="contra"><description>Contra</description></machine>
    <machine name="contrau" cloneof="contra"><description>Contra US</description></machine>
    <machine name="kinst">
        <description>Killer Instinct</description>
        <disk name="kinst" sha1="00000000000000000000000000000000000000aa"/>
    </machine>
</mame>
```

- [ ] **Step 3: Write the three INI fixtures**

`tests/filter/fixtures/snapshot_catver.ini`:

```ini
[Category]
3bagfull=Casino / Slot Machine
aristoslot=Casino / Slot Machine
mahjong1=Mahjong / Reels
pacman=Maze / Collect
pacmanf=Maze / Collect
sf2=Fighter / Versus
sf2ce=Fighter / Versus
sf2t=Fighter / Versus
galaxian=Shooter / Vertical
galaxianm=Shooter / Vertical
dkong=Platformer
dkongj=Platformer
mslug=Shooter / Run-and-Gun
mslugu=Shooter / Run-and-Gun
ddragon=Beat'em up
ddragonb=Beat'em up
rtype=Shooter / Horizontal
rtypeu=Shooter / Horizontal
bublbobl=Platformer
bublboblj=Platformer
contra=Shooter / Run-and-Gun
contrau=Shooter / Run-and-Gun
kinst=Fighter / Versus
qbert=Maze / Collect
oldgame=Misc.
newgame=Misc.
brokensim=Misc.
jpgame=Adventure
```

`tests/filter/fixtures/snapshot_languages.ini`:

```ini
[Languages]
jpgame=Japanese
pacman=English
sf2=English
```

`tests/filter/fixtures/snapshot_bestgames.ini`:

```ini
[Best]
pacman=
sf2=
mslug=
contra=

[Great]
sf2ce=
ddragon=

[Good]
sf2t=
ddragonb=
rtype=

[Average]
pacmanf=
galaxian=
galaxianm=
dkong=
dkongj=
bublbobl=
bublboblj=

[Bad]
qbert=
```

- [ ] **Step 4: Write override + session fixtures**

`tests/filter/fixtures/snapshot_overrides.yaml`:

```yaml
overrides:
  pacman: pacmanf       # explicit user pin against best-tier auto-pick
  sf2: sf2ce            # CE preferred over vanilla
```

`tests/filter/fixtures/snapshot_sessions.yaml`:

```yaml
active: shooters
sessions:
  shooters:
    include_genres: ["Shooter*"]
```

- [ ] **Step 5: Write `tests/filter/test_snapshot.py` with a regenerate flag**

```python
"""Snapshot regression: full pipeline against a 30-machine fixture."""

from __future__ import annotations

import json
import os
from pathlib import Path

from mame_curator.filter.config import FilterConfig
from mame_curator.filter.overrides import load_overrides
from mame_curator.filter.runner import run_filter
from mame_curator.filter.sessions import load_sessions
from mame_curator.filter.types import FilterContext
from mame_curator.parser import parse_bestgames, parse_catver, parse_dat, parse_languages
from mame_curator.parser.listxml import parse_listxml_cloneof, parse_listxml_disks

SNAPSHOT_PATH = Path(__file__).parents[1] / "snapshots" / "filter_smoke.json"


def _build_input(fixtures_dir: Path) -> tuple[dict, FilterContext, FilterConfig]:
    machines = parse_dat(fixtures_dir / "snapshot_dat.xml")
    cloneof = parse_listxml_cloneof(fixtures_dir / "snapshot_listxml.xml")
    chd = parse_listxml_disks(fixtures_dir / "snapshot_listxml.xml")
    catver = parse_catver(fixtures_dir / "snapshot_catver.ini")
    langs_lists = parse_languages(fixtures_dir / "snapshot_languages.ini")
    bestgames = parse_bestgames(fixtures_dir / "snapshot_bestgames.ini")
    ctx = FilterContext(
        category=catver,
        languages={k: tuple(v) for k, v in langs_lists.items()},
        cloneof_map=cloneof,
        chd_required=frozenset(chd),
        bestgames_tier=bestgames,
    )
    cfg = FilterConfig(
        drop_categories=("Casino*", "Mahjong*"),
        drop_year_before=1978,
        drop_year_after=2015,
    )
    return machines, ctx, cfg


def test_snapshot_matches(fixtures_dir: Path) -> None:
    """Re-run the full filter against the fixture; assert byte-identical to snapshot."""
    machines, ctx, cfg = _build_input(fixtures_dir)
    overrides = load_overrides(fixtures_dir / "snapshot_overrides.yaml")
    sessions = load_sessions(fixtures_dir / "snapshot_sessions.yaml")
    result = run_filter(machines, ctx, cfg, overrides, sessions)

    actual = json.loads(result.model_dump_json())
    if os.environ.get("UPDATE_SNAPSHOTS") == "1":
        SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT_PATH.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n")
    expected = json.loads(SNAPSHOT_PATH.read_text())
    assert actual == expected, "Snapshot drift — re-run with UPDATE_SNAPSHOTS=1 if intentional."
```

- [ ] **Step 6: Generate the snapshot once**

```bash
mkdir -p tests/snapshots
UPDATE_SNAPSHOTS=1 uv run pytest tests/filter/test_snapshot.py -v --no-cov
```

Expected: snapshot file is written; test passes.

- [ ] **Step 7: Inspect the snapshot for sanity**

```bash
cat tests/snapshots/filter_smoke.json | head -40
```

Expected (illustrative — actual content will differ):
- `winners`: a sorted tuple containing shooters that survived all four phases. Should include `mslug`, `contra`, `galaxian`, `rtype` (or their winners-per-group). Should NOT include `pacman` (Maze) or `sf2ce` (Fighter) — sliced out by the `shooters` session.
- `dropped`: includes `neogeo` (BIOS), `z80dev` (DEVICE), `3bagfull`/`aristoslot` (MECHANICAL/CATEGORY), `mahjong1` (CATEGORY), `jpgame` (JAPANESE_ONLY), `brokensim` (PRELIMINARY_DRIVER), `kinst` (CHD_REQUIRED), `oldgame` (YEAR_BEFORE), `newgame` (YEAR_AFTER).

If anything looks wrong, fix the implementation, regenerate the snapshot, and inspect again before committing.

- [ ] **Step 8: Re-run without the env var to confirm the test is now binding**

```bash
uv run pytest tests/filter/test_snapshot.py -v --no-cov
```

Expected: passes against the committed snapshot.

- [ ] **Step 9: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add tests/filter/fixtures/snapshot_*.* tests/snapshots/filter_smoke.json \
        tests/filter/test_snapshot.py
git commit -m "test(filter): 30-machine snapshot regression covering all 4 phases"
```

---

## Task 11: CLI subcommand `mame-curator filter`

**Files:**
- Modify: `src/mame_curator/cli.py`
- Create: `tests/filter/test_cli_filter.py`

The CLI consumes a `config.yaml`, `overrides.yaml`, `sessions.yaml`, the DAT, the listxml, and the five INI files; runs `run_filter`; writes a `report.json` and prints a summary.

- [ ] **Step 1: Write `tests/filter/test_cli_filter.py` (failing)**

```python
"""End-to-end test for `mame-curator filter`."""

from __future__ import annotations

import json
from pathlib import Path

from mame_curator.cli import build_parser, run


def test_filter_subcommand_writes_report(fixtures_dir: Path, tmp_path: Path, capsys: object) -> None:
    report = tmp_path / "report.json"
    parser = build_parser()
    args = parser.parse_args(
        [
            "filter",
            "--dat", str(fixtures_dir / "snapshot_dat.xml"),
            "--listxml", str(fixtures_dir / "snapshot_listxml.xml"),
            "--catver", str(fixtures_dir / "snapshot_catver.ini"),
            "--languages", str(fixtures_dir / "snapshot_languages.ini"),
            "--bestgames", str(fixtures_dir / "snapshot_bestgames.ini"),
            "--overrides", str(fixtures_dir / "snapshot_overrides.yaml"),
            "--sessions", str(fixtures_dir / "snapshot_sessions.yaml"),
            "--out", str(report),
        ]
    )
    assert run(args) == 0
    payload = json.loads(report.read_text())
    assert "winners" in payload
    assert "dropped" in payload
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "winners:" in captured.out
```

- [ ] **Step 2: Run, expect failure**

```bash
uv run pytest tests/filter/test_cli_filter.py -v --no-cov
```

- [ ] **Step 3: Extend `src/mame_curator/cli.py` to add the subcommand**

Replace the file with:

```python
"""mame-curator command-line interface.

Subcommands (added incrementally as phases land):
    parse <dat-path>       — parse the DAT and print summary stats (Phase 1)
    filter <args>          — run the filter pipeline and write a report (Phase 2)
    copy ...               — Phase 3
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from rich.console import Console

from mame_curator.filter import (
    FilterConfig,
    FilterContext,
    FilterError,
    load_overrides,
    load_sessions,
    run_filter,
)
from mame_curator.parser import (
    ParserError,
    parse_bestgames,
    parse_catver,
    parse_dat,
    parse_languages,
    parse_mature,
)
from mame_curator.parser.listxml import parse_listxml_cloneof, parse_listxml_disks

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser with all subcommands."""
    parser = argparse.ArgumentParser(prog="mame-curator", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse", help="Parse a DAT and print summary stats")
    parse_cmd.add_argument("dat", type=Path, help="Path to DAT XML or .zip")

    filt = sub.add_parser("filter", help="Run the filter pipeline and write a JSON report")
    filt.add_argument("--dat", type=Path, required=True)
    filt.add_argument("--listxml", type=Path, required=True, help="Official MAME -listxml output")
    filt.add_argument("--catver", type=Path, required=True)
    filt.add_argument("--languages", type=Path, required=True)
    filt.add_argument("--bestgames", type=Path, required=True)
    filt.add_argument("--mature", type=Path, default=None, help="progettoSnaps mature.ini")
    filt.add_argument("--overrides", type=Path, default=None)
    filt.add_argument("--sessions", type=Path, default=None)
    filt.add_argument("--out", type=Path, required=True, help="Path to write report JSON")

    return parser


def run(args: argparse.Namespace) -> int:
    """Dispatch to the chosen subcommand. Returns process exit code."""
    if args.command == "parse":
        return _cmd_parse(args)
    if args.command == "filter":
        return _cmd_filter(args)
    return 1  # unreachable: argparse `required=True` enforces a subcommand


def _cmd_parse(args: argparse.Namespace) -> int:
    console = Console()
    try:
        machines = parse_dat(args.dat)
    except ParserError as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 2

    parents = sum(1 for m in machines.values() if m.cloneof is None)
    clones = sum(1 for m in machines.values() if m.cloneof is not None)
    bios = sum(1 for m in machines.values() if m.is_bios)
    devices = sum(1 for m in machines.values() if m.is_device)
    mechanical = sum(1 for m in machines.values() if m.is_mechanical)

    console.print(f"DAT: {args.dat}")
    console.print(f"  machines: {len(machines)}")
    console.print(f"  parents: {parents}")
    console.print(f"  clones: {clones}")
    console.print(f"  bios: {bios}")
    console.print(f"  devices: {devices}")
    console.print(f"  mechanical: {mechanical}")
    return 0


def _cmd_filter(args: argparse.Namespace) -> int:
    console = Console()
    try:
        machines = parse_dat(args.dat)
        mature = frozenset(parse_mature(args.mature)) if args.mature else frozenset()
        ctx = FilterContext(
            category=parse_catver(args.catver),
            languages={k: tuple(v) for k, v in parse_languages(args.languages).items()},
            bestgames_tier=parse_bestgames(args.bestgames),
            cloneof_map=parse_listxml_cloneof(args.listxml),
            chd_required=frozenset(parse_listxml_disks(args.listxml)),
            mature=mature,
        )
        overrides = load_overrides(args.overrides) if args.overrides else load_overrides(Path("/nonexistent"))
        sessions = load_sessions(args.sessions) if args.sessions else load_sessions(Path("/nonexistent"))
    except (ParserError, FilterError) as exc:
        console.print(f"[red]error:[/red] {exc}")
        return 2

    result = run_filter(machines, ctx, FilterConfig(), overrides, sessions)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result.model_dump_json(indent=2) + "\n")

    console.print(f"  winners: {len(result.winners)}")
    console.print(f"  dropped: {len(result.dropped)}")
    console.print(f"  contested groups: {len(result.contested_groups)}")
    console.print(f"  warnings: {len(result.warnings)}")
    console.print(f"  report: {args.out}")
    return 0
```

- [ ] **Step 4: Tests pass**

```bash
uv run pytest tests/filter/test_cli_filter.py -v --no-cov
```

Expected: 1 passed.

- [ ] **Step 5: Lint + types + commit**

```bash
uv run ruff check
uv run ruff format
uv run mypy
git add src/mame_curator/cli.py tests/filter/test_cli_filter.py
git commit -m "feat(cli): mame-curator filter subcommand with JSON report"
```

---

## Task 12: Coverage check + final phase commit

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Run the full suite with coverage and confirm `filter/` ≥ 95%**

```bash
uv run pytest --cov=mame_curator.filter --cov-report=term-missing tests/filter/ -v
```

Expected: every test passes; the `Cover` column for files under `src/mame_curator/filter/` is ≥ 95%. If any file falls short, write the missing test before continuing.

- [ ] **Step 2: Run the full project suite (regression check)**

```bash
uv run pytest -v
```

Expected: every test passes (parser + filter + smoke).

- [ ] **Step 3: Run all gates**

```bash
uv run ruff check
uv run ruff format --check
uv run mypy
uv run bandit -c pyproject.toml -r src
uv run pre-commit run --all-files
```

Expected: every gate green.

- [ ] **Step 4: Verify no public function exceeds 50 lines**

```bash
awk '/^def / {name=$2; start=NR} /^[a-zA-Z_]/ && name && NR>start+50 {print FILENAME":"start" "name" exceeds 50 lines"; name=""}' src/mame_curator/filter/*.py
```

Expected: no output.

- [ ] **Step 5: Update `CHANGELOG.md`**

In the `[Unreleased] / Added` section, add:

```markdown
- **Phase 2 complete** — filter rule chain (`filter/`):
  - Phase A drop predicates (13 rules) with one regression test per rule.
  - Phase B picker chain (tier → preferred-genre/publisher/developer →
    parent-over-clone → driver → region → revision → alphabetical) with
    `pick_winner` and `explain_pick` per parent/clone group.
  - Phase C overrides (`overrides.yaml` schema pinned via Pydantic) — overrides
    bypass the picker; unknown targets warn but never crash.
  - Phase D session focus (`sessions.yaml` schema pinned via Pydantic) — slices
    visible winners by genre / publisher / developer / year-range patterns.
  - `parse_listxml_cloneof` extension to `parser/listxml.py` (Pleasuredome DATs
    strip `cloneof`, so parent/clone relationships come from MAME `-listxml`).
  - Region + revision heuristics (`region_of`, `revision_key_of`) used by the
    picker.
  - `mame-curator filter` CLI writes a JSON `FilterResult` report.
  - Property tests (hypothesis): determinism + idempotency.
  - 30-machine snapshot regression test (`tests/snapshots/filter_smoke.json`).
  - Coverage on `filter/` ≥ 95%; every public function ≤ 50 lines.
```

- [ ] **Step 6: Final phase commit**

```bash
git add CHANGELOG.md
git commit -m "chore(filter): phase-2 filter rule chain complete"
```

- [ ] **Step 7: Verify the commit landed**

```bash
git log --oneline -15
```

Expected: top of log shows the phase-2 complete commit plus all per-task commits.

---

## Phase 2 Acceptance — final checklist

Re-confirm each item from the roadmap:

- [ ] Every test in this plan passes (`uv run pytest tests/filter/`).
- [ ] `src/mame_curator/filter/spec.md` matches the implementation (no public symbol in code that's not in spec; no spec contract that's not in code).
- [ ] Coverage on `filter/` ≥ 95%.
- [ ] Snapshot test passes; `tests/snapshots/filter_smoke.json` is committed.
- [ ] No public function exceeds 50 lines.
- [ ] All Phase 0 / Phase 1 gates still pass.

If every box is ticked, **stop here.** Per roadmap anti-jump rule #1, do not start Phase 3 until the user confirms Phase 2 is complete.

## Per-phase review questions to ask the user

1. Spot-check a contested group from `report.json` — does the chain in `contested_groups[*].chain` describe a reasonable picker decision?
2. Try the `mame-curator filter` CLI on the user's real DAT (with their own `-listxml` and INI files). Are the winner counts in a sane range (~2,000–3,000)? Spot-check 10–20 contested picks and report any that surprise the user.
3. Anything to refine before Phase 3 (copy)? E.g., a tiebreaker that keeps choosing the wrong version for a particular publisher.
