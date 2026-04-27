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
