# filter/review_state spec

Per-game review state (P14). Co-located contract for the
`filter/review_state.py` model + loader and the cross-module surface it
anchors (the `/api/state` routes, the `?review_state=` request filter,
and the `review_state` activity event). Promoted here from
`docs/specs/P14.md` per the `CLAUDE.md` rule that a shipped feature gets
a co-located `spec.md` next to its code; the P14 doc remains the
historical design record, this file is the live audit surface.

## Contract

Each MAME machine carries one of four review states: `pending` (the
default), `reviewed`, `skipped`, `needs-decision`. The state is a
**global per-game annotation** — it is *not* scoped to the active
session, so a game marked Reviewed from the full catalogue is still
Reviewed when seen through an "80s shooters" session. It persists on
disk in `data/state.yaml` and every change appends one line to
`data/activity.jsonl`.

Review state does **not** gate machine eligibility. Every machine in the
DAT is eligible regardless of whether it has been reviewed; review state
only changes what the library *shows*, never what the filter pipeline
*keeps*. This split is the load-bearing fact of the whole feature — it
is why the state lives outside `run_filter()` (see "Per-request filter"
and INV-4).

Layering: `review_state.py` sits inside `filter/` and depends only on
`filter/_io` + `filter/errors` (no `api/` or `copy/` imports). The
API-layer and activity-layer pieces below live in `api/` and `copy/`
respectively and are documented here because they form one contract;
their module specs (`api/spec.md`, `copy/spec.md`) own the wider route
inventory and activity-union shape.

## Public surface

Re-exported from `mame_curator.filter.__init__`:

| Name | Kind | Source |
|---|---|---|
| `ReviewState` | frozen Pydantic model | `filter/review_state.py` |
| `ReviewStateValue` | `StrEnum` (storage) | `filter/review_state.py` |
| `ReviewStateFilter` | `StrEnum` (query) | `filter/review_state.py` |
| `load_review_state` | function | `filter/review_state.py` |
| `ReviewStateError` | exception | `filter/errors.py` |

## Public types

### `ReviewStateValue` (`StrEnum`)

The values `state.yaml` ever holds: `reviewed`, `skipped`,
`needs-decision`. **`pending` is intentionally absent** — a pending game
has no entry on disk (the sparse-store invariant, INV-1). Typing the
write-path body field as `ReviewStateValue` (not `ReviewStateFilter`) is
what makes a `POST` of `pending` a 422 *before* the handler runs
(INV-8).

### `ReviewStateFilter` (`StrEnum`)

The values the `?review_state=` query parameter accepts: the three
storage values plus two sentinels — `all` (no narrowing, the default)
and `pending` (the complement of the stored set). Distinct from
`ReviewStateValue` precisely because `all` and `pending` never appear on
disk.

### `ReviewState` (frozen Pydantic model)

`model_config = frozen, extra="forbid", populate_by_name=True`. One
field:

| Field | Type | Notes |
|---|---|---|
| `entries` | `dict[str, ReviewStateValue]` | `alias="state"` |

The code-side name is `entries`; it serialises under the top-level YAML
key `state` via the alias, mirroring `Overrides` (`entries` ↔
`overrides`). Frozen — a mutation builds a new instance, never edits in
place.

## Public functions

### `load_review_state(path) -> ReviewState`

Reads and validates `state.yaml`. Mirrors `load_overrides` exactly:

- Missing file → empty `ReviewState()` (no error).
- Read is size-capped via `filter/_io.read_capped_text(path,
  exc_cls=ReviewStateError)` (the shared DoS-guard read).
- `yaml.YAMLError` while parsing → `ReviewStateError` (the path is
  `repr()`-quoted per FP06 B3).
- Top-level `null` / empty file → empty `ReviewState()` (same as
  missing).
- Top-level value that is not a mapping → `ReviewStateError`.
- Pydantic `ValidationError` (unknown state value, wrong shape) →
  re-raised as `ReviewStateError`.

## Persistence — `data/state.yaml`

Sparse store; pending = absence. Two-space indent, matching
`overrides.yaml`:

```yaml
state:
  sf2: reviewed
  pacman: skipped
  galaga: needs-decision
```

Writes go through the existing `write_yaml_atomic` (`api/persist.py`),
whose `safe_dump(sort_keys=True, default_flow_style=False)` contract
gives byte-identical output for a given logical map (INV-9).

**State is deliberately not snapshotted.** `write_yaml_atomic` is called
directly, bypassing `snapshot_files()`. Rationale: state mutates at
keypress frequency (a walkthrough can mark 100+ games in minutes), and
`data/snapshots/` is a shared LRU pool (cap 200, evicted across
overrides + sessions + config). Snapshotting state would churn the pool
and evict every editorial snapshot within minutes. Recovery for state is
`activity.jsonl` replay instead — every transition is one append-only
line. (`overrides.yaml` / `sessions.yaml` keep their per-write snapshot
policy; they are low-frequency editorial mutations.)

Consequence: the Settings → Snapshots view cannot roll back review state
(it lists `data/snapshots/` only). `docs/specs/P14.md` § "Snapshot
policy" intended a one-line caption surfacing this to the user, but it
was never shipped — no UI caveat is currently shown (tracked as
`mame-curator-1078`).

## API surface

Three routes on the `curate.py` router (`api/spec.md` owns the full
route inventory + the world-lock list; documented here for the
review-state-specific semantics). All three return `StateView { entries:
{[short_name]: ReviewStateValue} }` (`api/schemas_overrides.py`). The two
**mutating** routes (`POST` / `DELETE`) acquire
`request.app.state.world_lock` (INV-3); `GET /api/state` is a lock-free
read (`get_state` is a plain `Depends(get_world)` handler).

| Method | Path | Handler | Semantics |
|---|---|---|---|
| `GET` | `/api/state` | `get_state` | full map, for frontend cache hydration |
| `POST` | `/api/state` | `post_state` | set a non-pending state |
| `DELETE` | `/api/state/{short_name}` | `delete_state` | clear to pending |

`POST` body is `StatePostRequest { short_name, state }` with `state ∈
{reviewed, skipped, needs-decision}`. `DELETE` removes the sparse-store
entry. Both are **idempotent and no-op-skipping** (INV-13): a write that
would leave the in-memory `entries` map byte-identical (re-POST of the
current value, or DELETE of an already-pending game) skips *both* the
YAML write and the activity append, so a keypress that changes nothing
never touches the file mtime or the log.

**Write ordering under partial failure** (`post_state`): persist YAML →
append activity → swap world. A YAML-write failure leaves state, log,
and world all unchanged (caller sees 500). An activity-append failure
*after* a successful persist leaves the on-disk YAML ahead of the log;
the YAML is the source of truth and is what a restart reloads.

## Per-request filter — `?review_state=` on `GET /api/games`

The narrowing filter is applied in the `list_games` handler
(`api/routes/games.py`) **after** the cached `world.filter_result`
slice — never inside `run_filter()`. The handler reads
`world.review_state.entries` on demand and removes games whose stored
state doesn't match the requested `ReviewStateFilter`:

- `all` → no narrowing (default).
- `pending` → keep games with *no* entry.
- `reviewed` / `skipped` / `needs-decision` → keep games whose entry
  equals that value.

This composes with the eligibility set as: eligibility (from
`run_filter`) **then** visibility (this filter). The per-request stage
can only ever *remove* games already in `filter_result`; it can never
reintroduce a game a session or drop rule excluded.

**Why per-request, not a pipeline stage.** `filter_result` is the
materialised eligible set, cached at world-build cost and reused for
every page load until `replace_world` runs. Review state is a
fast-mutating per-request slice — the same world serves
`?review_state=pending` to one request and `?review_state=reviewed` to
the next with no rebuild. Folding it into `run_filter()` would force a
full re-filter per keypress.

### `WorldState` integration — the passive swap

`WorldState` (`api/state.py`) carries a `review_state: ReviewState`
field beside `overrides` / `sessions`. `replace_world(...,
review_state=ReviewState | None = None, ...)` swaps it as a **passive
field replacement**: the filter-recompute trigger is *not* broadened to
cover `review_state`, so a `review_state`-only swap returns a new
`WorldState` whose `filter_result` is `is`-identical to the base's. The
`compose_allowlist` short-circuit (load-bearing per FP09 Cluster R H2)
is likewise untouched. INV-4 pins this identity with a test.

## Activity log — `review_state` event

Every mutation that changes the in-memory map emits one
`ActivityEventType.REVIEW_STATE` event (`copy/spec.md` owns the
discriminated-union shape). Payload `ReviewStateDetails`
(`copy/types.py`):

| Field | Type | Notes |
|---|---|---|
| `event_type` | `Literal[REVIEW_STATE]` | union discriminant |
| `short_name` | `str` | |
| `state` | `str` | post-change value; **includes `"pending"`** |
| `previous` | `str` | pre-change value, same domain |

`state` / `previous` are plain `str`, *not* `ReviewStateValue`: the log
records the literal transition including the sentinel `"pending"`,
keeping the log's domain decoupled from the storage enum (which excludes
pending). `session_id` is `""` — per-game state has no enclosing session
or copy-job scope; P14 set the precedent that non-job-scoped events use
the empty string rather than a placeholder. `summary` is composed at
emit time (`"marked {short_name} as {state}"` / `"cleared
{short_name}"`).

The emitter passes `log_path=world.data_dir / "activity.jsonl"`
explicitly (it does not rely on `append_activity`'s CWD-relative
default). **Invariant going forward:** all emitters should funnel
through `world.data_dir`; the existing `copy/runner.py` default-path
emitters resolve to the same file only because the API process's CWD ==
config-parent, and should migrate in a later phase.

## Errors

- `ReviewStateError` (subclass of `filter.FilterError`) — malformed
  `state.yaml` (parse error, non-mapping top level, schema violation).
  Raised only by `load_review_state`.
- `POST` / `DELETE /api/state/{short_name}` reuse the existing
  `GameNotFoundError` (`code: "game_not_found"`, 404) for an unknown
  `short_name` — **no new error code** is introduced by this feature.
  (`GET /api/state` takes no `short_name` and cannot 404.)
- Invalid `state` enum, `state = pending`, or an unknown
  `?review_state=` value → 422 (FastAPI's standard Pydantic-validation
  envelope; no hand-rolled rejection).
- Disk-write failures → 500: the YAML write raises bare `OSError`;
  `append_activity` raises typed `ActivityLogError` (a `CopyError`
  subclass). Both reach FastAPI's default 500 handler.

## Invariants (audit surface)

Each has at least one enforcing test.

- **INV-1** `state.yaml` is sparse — only `{reviewed, skipped,
  needs-decision}` entries are written; pending is never stored.
- **INV-2** Missing `state.yaml` → empty `ReviewState`, no error.
- **INV-3** All state mutations serialise via `app.state.world_lock`.
- **INV-4** `WorldState` is frozen; a `replace_world(review_state=...)`
  swap is a passive field replacement that does NOT re-run
  `run_filter()` — `world.filter_result` is `is`-identical to the base
  across review-state-only swaps.
- **INV-5** Every mutation that changes the in-memory `entries` map
  appends exactly one `review_state` line to `activity.jsonl`, with
  `previous` reflecting the prior in-memory value. A no-op writes
  nothing.
- **INV-6** R / S / ? on a focused card mutates that card's state; when
  walkthrough is on and the result is non-pending, focus advances to the
  next pending card in current filter scope. Mutation and advance are
  independent observable events.
- **INV-7** With the alternatives drawer open, R / S / ? mutates the
  highlighted drawer row, not the launching card; drawer mutations do
  **not** auto-advance regardless of the walkthrough setting.
- **INV-8** `POST /api/state`: unknown `short_name` → 404
  `game_not_found`; invalid `state` → 422; `state = pending` → 422 at
  the Pydantic-validation layer, before the handler runs.
- **INV-9** On-disk format is `{state: {short_name: enum_value}}`,
  two-space indent; byte-identical re-writes rest on `write_yaml_atomic`
  (`sort_keys=True, default_flow_style=False`). The feature never relies
  on insertion order and never compares the file's byte form.
- **INV-10** `?review_state=` accepts `{all, pending, reviewed, skipped,
  needs-decision}`; any other value → 422.
- **INV-11** Entries for unknown short names (game dropped from the DAT
  between sessions) are tolerated on load — they sit in `entries`
  without raising and are filtered out wherever state is consulted,
  since the game is no longer in `world.machines`.
- **INV-12 (pending parity)** The pending set the frontend walkthrough
  cycles through equals `GET /api/games?review_state=pending&<other
  filters>`. The frontend walks the locally cached `games[]` (already
  shaped by active filters) and skips any `short_name` present in the
  cached state map — the identical predicate to the backend stage.
- **INV-13 (no-op write skip)** A mutation that leaves the in-memory map
  byte-identical skips both `write_yaml_atomic` and `append_activity`.
  Covers a DELETE of an already-pending game and a re-POST of the
  current value (`post_state` short-circuits when `previous ==
  body.state`).

## Out of scope (YAGNI guardrails)

- Cross-device sync / cloud backup of state.
- Per-session state (state is global by design).
- Bulk operations ("mark all visible as reviewed").
- Multi-step undo (the toggle gives single-step revert).
- Pruning state entries for games no longer in the DAT (tolerated on
  load, filtered at use — INV-11).
- A help-overlay shortcut: `?` is claimed here; a future help overlay
  must pick a different key.
- The wider `/api/games` route, the activity discriminated union, and
  the frontend grid/drawer/badge components — owned by `api/spec.md`,
  `copy/spec.md`, and the frontend tree respectively. This spec owns the
  review-state *contract* that crosses them.

## Companion docs

- Design record: `docs/specs/P14.md` · journal: `docs/journal/P14.md`.
- Cross-module specs: `api/spec.md` (routes + world lock), `copy/spec.md`
  (activity union), `filter/spec.md` (the rest of the filter surface).
- ROADMAP: `mame-curator-1014` (P14), `mame-curator-1061` (this
  promotion).
