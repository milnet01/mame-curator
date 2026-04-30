# copy/ spec

## Contract

Given a Phase-2 `FilterResult` (winner short names), a source ROM directory, and a destination directory, this module:

1. Resolves the **transitive BIOS chain** for every winner via the official MAME `-listxml`'s `romof` and `<biosset>` references.
2. **Pre-flights** the plan (source-side existence, destination writability, free-space estimate, existing-playlist detection).
3. **Atomically copies** every winner's `.zip` plus the deduplicated BIOS-set `.zip`s from source to destination. Already-copied files (size + mtime match) are skipped (idempotency).
4. Writes a **RetroArch v6+ JSON `mame.lpl` playlist** with one entry per winner.
5. Resolves **playlist conflicts** (append vs overwrite vs cancel; per-game version replace; project-internal recycle-bin retention).
6. Emits a **frozen `CopyReport`** Pydantic model (also persisted to `data/copy-history/<id>/report.json`) and **appends one or more `ActivityEvent` lines** to `data/activity.jsonl`.
7. Streams progress via callback at file boundaries; supports **pause / resume / cancel** between files.

The CLI surface is `mame-curator copy --dry-run` (preview, no writes) and `mame-curator copy --apply` (execute).

This module depends on `parser/` (DAT + listxml) and `filter/` (FilterResult). It must NOT import from `api/`, `media/`, or any later-phase module per the project's anti-jump rule.

## Source of BIOS-chain relationships

The Pleasuredome ROM-set DAT strips both `romof` and `cloneof` (verified empirically — see `parser/spec.md` "Edge cases handled"). Phase 3 sources BIOS-chain relationships from the **official MAME `-listxml`**, the same artefact P02 already consumes for `cloneof_map` and `chd_required` (ADR-0002, ADR-0003).

A new helper `parse_listxml_bios_chain(path) -> dict[str, BIOSChainEntry]` in `parser/listxml.py` returns, per machine:

```python
class BIOSChainEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    romof: str | None = None                      # parent ROM-of relation (often == cloneof but not always)
    biossets: tuple[str, ...] = ()                # <biosset name="..."> children
```

Same `lxml.iterparse` + fast-iter + `# nosec B410` pattern as `parse_listxml_disks` and `parse_listxml_cloneof`.

## BIOS chain resolution

```python
def resolve_bios_dependencies(
    winners: Iterable[str],
    bios_chain: dict[str, BIOSChainEntry],
) -> tuple[frozenset[str], tuple[BIOSResolutionWarning, ...]]:
    """Return (set of BIOS short-names to copy, warnings)."""
```

Algorithm:

1. Initialize `to_visit = deque(winners)`, `bios: set[str] = set()`, `seen: set[str] = set()`.
2. While `to_visit`:
   1. Pop `name`. If `name in seen`: continue. Add to `seen`.
   2. Look up `entry = bios_chain.get(name)`. If absent: emit `BIOSResolutionWarning(name=name, kind="missing_from_listxml")` and continue (a winner not in listxml is a configuration mismatch, not fatal — we still copy the winner zip; design decision: warn loudly, do not crash).
   3. For each `b in entry.biossets`: add `b` to `bios` and push to `to_visit`.
   4. If `entry.romof and entry.romof != name`: add `entry.romof` to `bios` and push to `to_visit`.
3. Return `frozenset(bios)`, sorted-tuple of warnings (canonical order: by name).

**Cycle safety** is provided by `seen`. Self-references (`romof = self.name`, which appears in some MAME entries for slot-machine bios markers) are filtered by the `entry.romof != name` guard in step 2.4.

**The winner set itself is NOT included in the BIOS set** — this function returns only the *additional* dependencies. `run_copy` constructs the full copy plan as `winners | bios`.

## Atomic copy primitive

```python
def copy_one(
    src: Path,
    dst: Path,
    *,
    short_name: str,
    role: Literal["winner", "bios"],
    progress: Callable[[int, int], None] | None = None,
) -> CopyOutcome:
    """Atomically copy `src` to `dst`, preserving mtime and reporting per-chunk progress."""
```

`short_name` and `role` are required keyword arguments; they're carried into the returned `CopyOutcome` so the runner can build the `CopyReport` without re-deriving them. Both arguments are part of the public API surface — changing them is a breaking change.

Algorithm:

1. If `dst.exists()` and `dst.stat().st_size == src.stat().st_size` and `abs(dst.stat().st_mtime - src.stat().st_mtime) < 1.0`: return `CopyOutcome(status=SKIPPED_IDEMPOTENT, src=src, dst=dst, bytes=0)`. (Idempotency contract — design § 6.4 "re-running with no changes is a no-op".)
2. Compute `tmp = dst.with_suffix(dst.suffix + ".tmp")`. Tmp file lives **in the same directory** as the destination so `os.replace` is atomic on the same filesystem (per the Python atomic-write idiom; cross-FS replaces are not atomic).
3. `shutil.copy2(src, tmp)` — preserves mtime + permissions.
4. `os.replace(tmp, dst)` — atomic rename. The destination is either the old file or the new file; never a half-written file.
5. On any exception during steps 3–4: `tmp.unlink(missing_ok=True)`; re-raise as `CopyError(message, src=src, dst=dst)` with the underlying OSError chained (`raise CopyError(...) from exc`).
6. On `KeyboardInterrupt` mid-copy: same cleanup, re-raise the `KeyboardInterrupt` (do not swallow signals).
7. Return `CopyOutcome(status=SUCCEEDED, src=src, dst=dst, bytes=src.stat().st_size)`.

`progress` callback is invoked once per ~1 MiB chunk via a chunked copy (not `shutil.copyfileobj`'s default block; tune for large `.zip` files). If `None`, no callback. Callback signature: `(bytes_done: int, bytes_total: int) -> None`.

**No CRC verification** — design § 6.4's "matching CRC" wording is shorthand for "matching size + mtime"; CRCing 50 GB on every re-run is unaffordable. Users can opt into CRC verification post-v1 (out of scope here).

## Preflight

```python
def preflight(plan: CopyPlan) -> PreflightResult:
    """Validate the plan against the source and destination filesystems."""
```

Checks (all non-fatal — accumulate into `PreflightResult`; the caller decides whether to proceed):

| Check | Lands in `PreflightResult.` |
|---|---|
| Each `<short>.zip` exists in `plan.source_dir` | `missing_source: tuple[str, ...]` |
| `plan.dest_dir` exists or can be created | `dest_writable: bool` |
| Sum of source-zip sizes ≤ free space at dest | `free_space_gap_bytes: int` (positive = sufficient; negative = shortfall) |
| `plan.dest_dir / "mame.lpl"` exists | `existing_playlist: bool` |
| Each existing dest zip's size+mtime matches source (idempotency hit count) | `already_copied: tuple[str, ...]` |

A preflight finding is **not** an error — the CLI may proceed with `--dry-run` regardless and `--apply` proceeds unless `missing_source` is non-empty AND `--strict` is set.

## RetroArch `.lpl` writer

```python
def write_lpl(playlist_path: Path, entries: Iterable[PlaylistEntry]) -> None:
    """Write a RetroArch v6+ JSON playlist atomically."""
```

Format (per [Libretro docs — "Playlists and Thumbnails"](https://docs.libretro.com/guides/roms-playlists-thumbnails/) and the JSON schema introduced in RetroArch 1.7.5 / pull #7959):

```json
{
  "version": "1.5",
  "default_core_path": "",
  "default_core_name": "",
  "label_display_mode": 0,
  "right_thumbnail_mode": 0,
  "left_thumbnail_mode": 0,
  "sort_mode": 0,
  "items": [
    {
      "path": "/abs/path/to/dest/sf2ce.zip",
      "label": "Street Fighter II' - Champion Edition (World 920313)",
      "core_path": "DETECT",
      "core_name": "DETECT",
      "crc32": "00000000|crc",
      "db_name": "MAME.lpl"
    }
  ]
}
```

Constraints (these are testable assertions; `test_lpl_format_matches_retroarch_spec` enforces them):

- File MUST be UTF-8 with no BOM.
- Top-level keys MUST appear in the exact order listed above (RetroArch parsers since 1.7.5 are tolerant, but earlier releases — and some derivative tools — are key-order-sensitive; see [libretro/RetroArch#8439](https://github.com/libretro/RetroArch/issues/8439)).
- Indented with 2 spaces. JSON-stdlib's `json.dump(..., indent=2)` is sufficient.
- `path` is an absolute path on the host filesystem (`plan.dest_dir.resolve() / f"{short}.zip"`). RetroArch resolves these literally; a relative path breaks "Add Content".
- `label` is `Machine.description` verbatim — no escaping beyond JSON's own (`json.dump` handles `&`, `'`, `:`, `"`, control chars). UTF-8 multi-byte sequences (e.g. Japanese descriptions) are passed through; `ensure_ascii=False`.
- `crc32`: `"00000000|crc"` placeholder. Computing real CRCs is out of scope (cost > benefit; RetroArch can run with `00000000|crc` and resolves matches by filename anyway). When a real CRC is desired, set `crc32` to `"<hex8>|crc"` (lower-case hex). Future enhancement.
- `core_path` / `core_name` are `"DETECT"` placeholders so RetroArch falls back to its core scan. Hard-coding a path traps users on a specific RetroArch install.
- `db_name` is `"MAME.lpl"` — the canonical MAME database name shipped with libretro-database. Tells RetroArch which thumbnail subdirectory to consult.

The writer itself uses the **`copy_one` atomic pattern** — write to `mame.lpl.tmp`, `os.replace` to `mame.lpl`. A half-written playlist breaks RetroArch on next launch.

### Which winners become entries

`run_copy` includes a winner in `mame.lpl` only when the `.zip` is **definitely present at the destination** after the run:

| `CopyOutcome.status` | In `mame.lpl`? | Why |
|---|---|---|
| `SUCCEEDED` | Yes | Just-written; dst exists. |
| `SKIPPED_IDEMPOTENT` | Yes | Already at dst with matching size+mtime. |
| `SKIPPED_EXISTING_VERSION` | No | KEEP_EXISTING was chosen; the **existing** entry stays in the playlist (carried over from `existing_items`); the new winner's `dst` was never written. |
| `SKIPPED_MISSING_SOURCE` | No | Source `.zip` was missing; nothing copied; `dst` does not exist. |
| `FAILED` | No | Copy raised; `dst` does not exist. |

(Pre-FP02, `SKIPPED_MISSING_SOURCE` outcomes were included by accident — their `dst` was the would-be path, never created. Filtering to the two "present at dst" statuses is the v1 contract.)

### `read_lpl` input scope

`read_lpl(playlist_path) -> list[dict[str, str]]` reads existing playlists during `APPEND` conflict resolution. **Only RetroArch v1.5+ JSON-format playlists are supported.** The legacy 6-line format (deprecated since RetroArch 1.7.5; see libretro/RetroArch#7959 / #8439) is **out of scope for v1** — a pre-1.7.5 playlist at the destination raises `PlaylistError("failed to parse playlist")`. Users on legacy installs should run RetroArch's built-in conversion (Settings → Playlists → Refresh Playlist) before using this tool. (Post-v1: a legacy-format reader could ship as a feature flag.)

## Playlist conflict resolution

When `plan.dest_dir / "mame.lpl"` exists at preflight time, the caller (CLI or API) chooses one of three modes via `plan.conflict_strategy: ConflictStrategy`:

| Strategy | Behaviour |
|---|---|
| `APPEND` | Merge new entries into existing playlist; per-entry conflicts (below) resolved per `plan.append_decisions: dict[str, AppendDecision]` |
| `OVERWRITE` | Discard existing playlist entirely; if `plan.delete_existing_zips=True`, **all** existing dest `.zip` files are moved to the recycle bin; new entries written |
| `CANCEL` | `run_copy` returns `CopyReport.status = CANCELLED_PLAYLIST_CONFLICT`; no writes; no recycling |

For `APPEND`, each new winner is checked against the existing entries (matched by `path` basename, i.e. short-name + `.zip`):

| Existing? | Same short-name? | Default action |
|---|---|---|
| No | n/a | Add new entry |
| Yes | Yes (e.g. `sf2.zip` already present, winner is `sf2.zip`) | Skip (idempotent — `copy_one` returns `SKIPPED_IDEMPOTENT`); count in report `already_present` |
| Yes | No (existing is `sf2.zip`, winner is `sf2ce.zip` — different short-name within same parent group) | Look up `plan.append_decisions[winner_short]`. The decision carries a `kind` (`KEEP_EXISTING` / `REPLACE` / `REPLACE_AND_RECYCLE`) and, for the two replace kinds, the short-name being replaced. |

`AppendDecision` shape (FP02 widened from a `StrEnum` to a Pydantic model so the caller specifies *which* existing entry is replaced — the prior heuristic broke on multi-conflict sessions):

```python
class AppendDecisionKind(StrEnum):
    KEEP_EXISTING = "KEEP_EXISTING"
    REPLACE = "REPLACE"
    REPLACE_AND_RECYCLE = "REPLACE_AND_RECYCLE"

class AppendDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: AppendDecisionKind
    replaces: str | None = None        # short-name of replaced entry; required for REPLACE / REPLACE_AND_RECYCLE
```

Semantics:

- `KEEP_EXISTING` — winner is recorded in `CopyReport.skipped_existing_version`; not copied; existing playlist entry untouched. `replaces` is ignored.
- `REPLACE` — winner is copied (atomic); old playlist entry (matched by `replaces`) is replaced with new; **old `.zip` stays on disk untouched** (per design § 6.4 — explicit confirmation is required to delete). `replaces` is required.
- `REPLACE_AND_RECYCLE` — winner is copied (atomic); old playlist entry (matched by `replaces`) replaced; old `.zip` (`<replaces>.zip`) is moved to `data/recycle/<session_id>/<old-short>.zip`; recycled file recorded in `CopyReport.recycled` and one `file_recycled` activity event is emitted. `replaces` is required.

**Caller responsibility for conflict detection.** Same-parent-group cross-version conflict detection requires the cloneof map (P02 produces it; the runner does not carry it). The CLI / API caller is responsible for:

1. Reading the existing playlist and the cloneof map.
2. For each new winner, looking up whether any existing entry is a same-parent-group sibling.
3. Adding one entry to `plan.append_decisions` per conflict — `AppendDecision(kind=..., replaces=<existing_short>)` — typically via user prompt or via a CLI flag like `--auto-keep`.

The runner trusts presence-in-`append_decisions` as the conflict signal: when `short` is a key in the map, the runner applies the chosen decision (using `replaces` to identify the old entry; no heuristic search). When `short` is absent, the runner treats the winner as non-conflicting and adds it alongside existing entries. (Pre-FP01 wording mandated `PlaylistError` on a missing decision; that imposed an invariant the runner can't verify without cloneof_map. See `docs/journal/FP01.md` for the design fix.)

## Recycle bin

Project-internal recycle bin at `data/recycle/`. **Not** the OS recycle bin (no `send2trash` dependency — keeps the cross-platform footprint zero, and the design's 30-day retention contract is project-owned, not OS-owned).

Layout — one subdirectory per **copy session**, keyed by the session_id (which embeds the timestamp + a random suffix). Different sessions never collide; multiple files recycled in the same session share the directory:

```
data/recycle/
├── 20260430T142305Z-deadbeef/
│   ├── sf2.zip
│   ├── kof94.zip
│   └── manifest.json    # {"recycled_at": "...", "reason": "REPLACE_AND_RECYCLE", "session_id": "..."}
└── 20260501T091244Z-cafef00d/
    └── ...
```

(Pre-FP02, dirnames were the timestamp alone. Two sessions recycling within the same second collided on the directory and the second session's `manifest.json` overwrote the first's. Session-keyed dirnames make cross-session collisions impossible — see ROADMAP § FP02.)

Public functions:

```python
def recycle_file(
    path: Path,
    *,
    reason: str,
    session_id: str,
    recycle_root: Path = Path("data/recycle"),
) -> Path:
    """Move `path` into data/recycle/<session_id>/, return the new location."""

def purge_recycle(
    *,
    older_than: timedelta = timedelta(days=30),
    recycle_root: Path = Path("data/recycle"),
) -> tuple[int, int]:
    """Delete recycle subdirectories older than the threshold. Return (dirs_purged, bytes_freed)."""
```

`recycle_file` MUST be atomic on the same filesystem (same `os.replace` discipline as `copy_one`). On a cross-filesystem move (e.g. dest is on USB, project is on internal), it falls back to `shutil.move` which is `copy + unlink`; a crash mid-move on cross-FS leaves the source file intact — that's the right failure mode (no data loss).

`purge_recycle` runs only on explicit user opt-in (CLI `mame-curator copy --purge-recycle` or API `POST /api/copy/recycle/purge`). It is NOT automatic — the design's 30-day retention is a *minimum*; users can keep recycle indefinitely.

Each `recycle_file` call appends one `file_recycled` event to `data/activity.jsonl`; each `purge_recycle` call appends one `recycle_purged` event.

## Pause / resume / cancel

The pause/resume/cancel state machine is exposed via a `CopyController` object (one per copy session) so the CLI's `--apply` mode can drive it from a signal handler and the API's SSE endpoint can drive it from request handlers.

```python
class CopyControlState(StrEnum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    CANCELLING = "CANCELLING"
    DONE = "DONE"

class CopyController:
    def __init__(self) -> None:
        self._state = CopyControlState.RUNNING
        self._resume_event = threading.Event()
        self._resume_event.set()                  # not paused

    def pause(self) -> None: ...                  # transition RUNNING -> PAUSED
    def resume(self) -> None: ...                 # transition PAUSED -> RUNNING; sets _resume_event
    def cancel(self, *, recycle_partial: bool) -> None: ...
    def wait_if_paused(self) -> None: ...         # called by run_copy between files
    def should_cancel(self) -> bool: ...
```

Contract (testable per `test_pause_holds_at_file_boundary`, `test_cancel_with_keep_partial`):

- **Pause holds at file boundary.** `run_copy` calls `controller.wait_if_paused()` *before* starting each `copy_one` call — never mid-file. A pause issued during a file-in-flight waits for the current file to finish, then halts. This matches design § 6.4 and the long-form roadmap test name.
- **Resume continues from the next file.** No state is rebuilt; `run_copy` simply un-blocks on the threading.Event and proceeds to the next entry in its iteration order.
- **Cancel transitions to `CANCELLING`** which `run_copy` checks via `controller.should_cancel()` after each `copy_one` (and inside `wait_if_paused`). On cancel:
  - `recycle_partial=False` (default): copies completed so far stay; `run_copy` returns `CopyReport.status = CANCELLED`; no recycling.
  - `recycle_partial=True`: every successfully-copied file from the current session is moved to recycle (via `recycle_file(reason="CANCELLED_RECYCLE_PARTIAL")`); report records the recycled set; one `copy_aborted` activity event with `details.recycled_count = N`.
- **No mid-file cancellation** — design constraint. A `KeyboardInterrupt` mid-`copy_one` is the only way to stop in-flight; the `.tmp` is cleaned up but the rest of the session is left in whatever state it reached.
- **Threading discipline** — `CopyController` is thread-safe via the `threading.Event`. Concurrent `pause()` and `resume()` calls collapse to "last call wins" by design. `cancel()` is sticky — it cannot be undone (a sticky `_cancel_flag: bool` set once and never cleared).

## Activity log

Append-only newline-delimited JSON at `data/activity.jsonl`. Every line is one `ActivityEvent`:

```python
class ActivityEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    timestamp: datetime                            # ISO-8601 UTC, microsecond precision; serialized with `.isoformat()`
    event_type: ActivityEventType                  # see enum below
    summary: str                                   # one-line human-readable
    session_id: str                                # ULID (sortable, monotonic); shared across events from one copy run
    details: ActivityDetails                       # tagged-union by event_type
```

`ActivityEventType` enum (closed; adding new variants is a major version bump per the no-backwards-compat-shims-pre-v1 rule):

| Variant | When emitted | `details` shape |
|---|---|---|
| `copy_started` | `run_copy` enters | `CopyStartedDetails(plan_summary: PlanSummary, conflict_strategy: ConflictStrategy)` |
| `copy_finished` | `run_copy` returns successfully | `CopyFinishedDetails(report_summary: ReportSummary)` |
| `copy_aborted` | `run_copy` cancelled or failed | `CopyAbortedDetails(reason: str, recycled_count: int)` |
| `override_set` | `filter/` Phase C applies an override (emitted by Phase 2; included here so the schema is unified) | `OverrideSetDetails(parent: str, winner: str)` |
| `session_activated` | `filter/` Phase D activates a session | `SessionActivatedDetails(session_name: str)` |
| `ini_refreshed` | `updates/` re-fetches an INI (Phase 7) | `IniRefreshedDetails(ini_name: str, sha256_old: str, sha256_new: str)` |
| `app_updated` | `updates/` self-update completes (Phase 7) | `AppUpdatedDetails(version_old: str, version_new: str)` |
| `file_recycled` | `recycle_file` completes | `FileRecycledDetails(path: str, reason: str)` |
| `recycle_purged` | `purge_recycle` completes | `RecyclePurgedDetails(dirs_purged: int, bytes_freed: int)` |

Each `details` shape is itself a frozen Pydantic model with `extra="forbid"`. The `ActivityEvent` Pydantic discriminator is `event_type`; `details` is a `Annotated[Union[...], Discriminator("event_type")]`.

Writer:

```python
def append_activity(event: ActivityEvent, log_path: Path = Path("data/activity.jsonl")) -> None:
    """Append one event line. Atomic at the per-line level via O_APPEND."""
```

Implementation: open `log_path` with `mode="a"`, write `event.model_dump_json() + "\n"`, close. POSIX `O_APPEND` guarantees atomicity for writes ≤ `PIPE_BUF` (4096 bytes on Linux). Each `ActivityEvent` line is well under 4 KiB; concurrent writers from different processes won't interleave bytes.

Reader (for the future Activity API in Phase 4):

```python
def read_activity(log_path: Path = Path("data/activity.jsonl")) -> Iterator[ActivityEvent]:
    """Stream events newest-first via reverse-line iteration. Tolerates corrupt lines (logs warning, skips)."""
```

## CopyReport

Returned from `run_copy(plan, controller=None) -> CopyReport`. Persisted to `data/copy-history/<session_id>/report.json` for later replay via Phase 4's `/api/copy/history/{id}/report`.

```python
class CopyOutcomeStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    SKIPPED_IDEMPOTENT = "SKIPPED_IDEMPOTENT"        # already at dest with matching size+mtime
    SKIPPED_MISSING_SOURCE = "SKIPPED_MISSING_SOURCE"
    SKIPPED_EXISTING_VERSION = "SKIPPED_EXISTING_VERSION"  # APPEND + KEEP_EXISTING
    FAILED = "FAILED"

class CopyOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    short_name: str
    role: Literal["winner", "bios"]
    status: CopyOutcomeStatus
    src: Path
    dst: Path
    bytes: int = 0
    error: str | None = None                          # set when status == FAILED

class CopyReportStatus(StrEnum):
    OK = "OK"
    CANCELLED = "CANCELLED"
    CANCELLED_PLAYLIST_CONFLICT = "CANCELLED_PLAYLIST_CONFLICT"
    PARTIAL_FAILURE = "PARTIAL_FAILURE"

class CopyReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    session_id: str                                   # ULID; matches the activity log's session_id
    started_at: datetime
    finished_at: datetime
    status: CopyReportStatus
    plan_summary: PlanSummary                         # winners count, BIOS count, conflict strategy, dirs
    succeeded: tuple[CopyOutcome, ...]
    skipped: tuple[CopyOutcome, ...]
    failed: tuple[CopyOutcome, ...]
    overwritten: tuple[OverwriteRecord, ...]          # APPEND + REPLACE; existing entry replaced
    recycled: tuple[RecycleRecord, ...]               # files moved to data/recycle/
    bios_included: tuple[str, ...]                    # transitive BIOS set (sorted)
    chd_missing: tuple[str, ...]                      # winners flagged CHD-required by parser; copied but unplayable
    bytes_copied: int
    warnings: tuple[str, ...]                         # BIOSResolutionWarnings + preflight non-fatals + override warnings
```

**Completeness invariant** (testable per `test_copy_report_completeness`): every entry of `plan.winners | bios_set` appears in exactly one of `succeeded`, `skipped`, or `failed`. The lists are disjoint and their union covers the plan.

**Sorting**: every tuple is sorted in canonical order (`short_name` for outcomes, `path` for recycle records) for byte-identical determinism.

## CopyPlan

The input to `run_copy`:

`ConflictStrategy` and `AppendDecision` are defined under § "Playlist conflict resolution" above. `CopyPlan` references both:

```python
class CopyPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    winners: tuple[str, ...]                          # from FilterResult.winners (post-session-slice)
    machines: dict[str, Machine]                      # for description -> .lpl label
    bios_chain: dict[str, BIOSChainEntry]             # from parse_listxml_bios_chain
    chd_required: frozenset[str]                      # from parse_listxml_disks
    source_dir: Path
    dest_dir: Path
    conflict_strategy: ConflictStrategy
    append_decisions: dict[str, AppendDecision]       # one entry per cross-version conflict; key = winner short, value = (kind, replaces)
    delete_existing_zips: bool = False                # only meaningful with OVERWRITE
    dry_run: bool = False
```

**Multiple winners targeting the same `replaces` is undefined.** The runner records one `OverwriteRecord` per decision (so duplicates surface in the report), but only the first `recycle_file` call moves the file; subsequent calls find the source missing. The caller-responsibility contract (§ "Playlist conflict resolution") requires each `replaces` short to be unique within `append_decisions`.

A `CopyPlan` is constructed by the CLI from parsed config + a `FilterResult`, or by the API from a request body. `run_copy` validates the plan via `preflight()` before doing any work.

## Errors

`CopyError(Exception)` base. Subclasses:

- `BIOSResolutionError` — fatal failure during chain walk (rare; only on malformed `bios_chain` map structure).
- `PreflightError` — destination not writable, free-space shortfall, source dir missing entirely.
- `PlaylistError` — `append_decisions` missing for a conflicting winner; existing playlist file is corrupt JSON; write failure.
- `RecycleError` — recycle move failed (filesystem readonly, permission denied).
- `CopyExecutionError` — wrapped `OSError` from `copy_one` that escaped retry (currently no retry; surfaces directly).

Per `coding-standards.md` § 9 and `cli/spec.md` "Errors the CLI catches but never raises", every `CopyError` carries:

- The originating short-name and/or path.
- The cause sentence.
- A user-actionable next-step pointer when one exists (e.g. `PreflightError` includes free-space shortfall).

The CLI catches `CopyError` at the boundary and exits 1 with `error: ...` to stderr. It NEVER lets a Python traceback reach the user.

## CLI

`mame-curator copy` subcommand. Two mutually-exclusive modes:

| Flag | Semantics |
|---|---|
| `--dry-run` | Run preflight + BIOS resolution + conflict detection. Print a copy plan summary. **No writes.** Exits 0. |
| `--apply` | Run the full copy. Prompt for `append_decisions` if APPEND mode hits cross-version conflicts (or read from `--decisions <file>`). Exit 0 on `OK`, 1 on `PARTIAL_FAILURE` / `CANCELLED`. |

Required flags (both modes):

- `--config <path>` — `config.yaml` carrying `paths.source_roms`, `paths.dest_roms`, `paths.retroarch_playlist`.
- `--listxml <path>` — official MAME `-listxml` for BIOS chain + CHD detection.
- `--filter-report <path>` — JSON output of `mame-curator filter` (the `FilterResult` serialized).

Optional flags:

| Flag | Default | Effect |
|---|---|---|
| `--conflict {append,overwrite,cancel}` | `cancel` | Strategy when `mame.lpl` already exists |
| `--decisions <path>` | none | YAML/JSON file mapping `<short> -> AppendDecision` |
| `--auto-keep` | false | Apply `KEEP_EXISTING` to every cross-version conflict (CI-friendly) |
| `--delete-existing-zips` | false | With `--conflict overwrite`, recycle existing dest zips |
| `--purge-recycle` | none | One-shot: delete recycle entries older than 30 days; exits without copying |
| `-v` / `--verbose` | INFO | Logging level |

Output routing per `coding-standards.md` § 9 and `cli/spec.md`:

- Plan summary, per-file progress, final report → stdout.
- Errors, warnings → stderr.
- Two `rich.Console()` instances (one default, one `stderr=True`).

Dispatch via `set_defaults(func=_cmd_copy)` per `cli/spec.md`.

## Out of scope

- HTTP API exposure (Phase 4).
- Media URL fetching (Phase 5).
- CRC verification of source vs dest (post-v1 enhancement; size+mtime is sufficient for v1's idempotency contract).
- Cross-filesystem optimisations (e.g. reflink/CoW). Stays as `shutil.copy2` everywhere; users on btrfs / APFS already benefit from copy-on-write at the syscall level.
- Software-list routing (per-system folder splitting). Post-v1 — see design § 13.
- Multi-user concurrency. Single-user local tool (design § 3 non-goal).
- OS recycle bin integration (`send2trash`). Project-internal `data/recycle/` is the v1 surface; `send2trash` adds a cross-platform wheel without buying anything the design § 6.4 retention rule needs.

## References

- [Libretro docs — Playlists and Thumbnails](https://docs.libretro.com/guides/roms-playlists-thumbnails/) — `.lpl` JSON schema.
- [libretro/RetroArch#7959](https://github.com/libretro/RetroArch/pull/7959) — JSON playlist format introduction (RetroArch 1.7.5).
- [libretro/RetroArch#8439](https://github.com/libretro/RetroArch/issues/8439) — playlist-format whitespace sensitivity in older parsers.
- [Python `os.replace` atomic-write pattern](https://python-atomicwrites.readthedocs.io/) — same-directory tmp + replace idiom.
- [MAME documentation — About ROMs and Sets](https://docs.mamedev.org/usingmame/aboutromsets.html) — non-merged set definition.
- [send2trash](https://pypi.org/project/Send2Trash/) — considered and rejected for v1 (project-internal recycle suffices; see "Recycle bin" section).
- [sse-starlette](https://pypi.org/project/sse-starlette/) — SSE plumbing for the Phase 4 API; out of scope here, mentioned for forward reference.
- ADR-0002 — cloneof from listxml; same source for `bios_chain`.
- ADR-0003 — listxml tiered acquisition; this module consumes whatever the wizard delivers.
