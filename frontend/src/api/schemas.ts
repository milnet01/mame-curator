/**
 * Zod runtime validators for the API contract surface.
 *
 * Split out from `types.ts` in DS02 A3 (Tier 3 structural debt sweep) so the
 * combined schema bridge fits under the project's 500-line per-file cap. The
 * TypeScript `interface` declarations remain in `types.ts` because the CI
 * gate (`tools/check_api_types_sync.py`) parses that file for `^export
 * interface Foo {` blocks — the validators are free to live alongside.
 *
 * `client.ts` validates every response at runtime via these schemas,
 * mirroring Pydantic's `extra="forbid"` (we use `.strict()`).
 *
 * Call sites should keep importing from `@/api/types` — `types.ts`
 * re-exports everything from this module at the bottom of the file.
 */

import { z } from 'zod'

// === Common ================================================================
/**
 * Shared zod helper: an ISO-8601 datetime string parsed to a Date.
 *
 * `offset: true` accepts `+HH:MM` / `-HH:MM` suffixes (Pydantic emits
 * these for tz-aware datetimes when the deployer configures a non-UTC
 * timezone); `local: true` accepts naive datetimes (no offset, no Z)
 * so a single missed `tz=UTC` on the backend doesn't blow up the
 * whole frontend. The default `z.iso.datetime()` rejects both forms
 * — too strict for a contract that aims to be drift-tolerant
 * (FP11 § G2).
 */
const zDateTime = z.iso
  .datetime({ offset: true, local: true })
  .pipe(z.coerce.date())

// === Error envelope (api/errors.py) ========================================
export const FieldErrorSchema = z
  .object({
    loc: z.string(),
    msg: z.string(),
    type: z.string(),
  })
  .strict()

export const ApiErrorBodySchema = z
  .object({
    detail: z.string(),
    code: z.string(),
    fields: z.array(FieldErrorSchema),
  })
  .strict()

// === Parser models (re-exported from schemas via Machine) ==================
export const DriverStatusSchema = z.enum(['good', 'imperfect', 'preliminary'])

export const RomSchema = z
  .object({
    name: z.string().min(1),
    // FP11 § G1: mirror Pydantic `Field(ge=0)` constraint.
    size: z.number().int().nonnegative().nullable(),
    crc: z.string().nullable(),
    sha1: z.string().nullable(),
  })
  .strict()

export const BiosSetSchema = z
  .object({
    name: z.string().min(1),
    description: z.string().nullable(),
    default: z.boolean(),
  })
  .strict()

export const MachineSchema = z
  .object({
    name: z.string(),
    description: z.string(),
    year: z.number().int().nullable(),
    manufacturer_raw: z.string().nullable(),
    publisher: z.string().nullable(),
    developer: z.string().nullable(),
    cloneof: z.string().nullable(),
    romof: z.string().nullable(),
    is_bios: z.boolean(),
    is_device: z.boolean(),
    is_mechanical: z.boolean(),
    runnable: z.boolean(),
    roms: z.array(RomSchema),
    biossets: z.array(BiosSetSchema),
    driver_status: DriverStatusSchema.nullable(),
    sample_of: z.string().nullable(),
  })
  .strict()

// === Filter types (TiebreakerHit, Session) =================================
export const TiebreakerHitSchema = z
  .object({ name: z.string(), detail: z.string() })
  .strict()

export const SessionSchema = z
  .object({
    include_genres: z.array(z.string()),
    include_publishers: z.array(z.string()),
    include_developers: z.array(z.string()),
    include_year_range: z.tuple([z.number().int(), z.number().int()]).nullable(),
  })
  .strict()

// === Copy types (re-exported) ==============================================
export const ConflictStrategySchema = z.enum(['APPEND', 'OVERWRITE', 'CANCEL'])

export const AppendDecisionKindSchema = z.enum([
  'KEEP_EXISTING',
  'REPLACE',
  'REPLACE_AND_RECYCLE',
])

export const AppendDecisionSchema = z
  .object({
    kind: AppendDecisionKindSchema,
    replaces: z.string().nullable(),
  })
  .strict()

export const CopyReportStatusSchema = z.enum([
  'OK',
  'CANCELLED',
  'CANCELLED_PLAYLIST_CONFLICT',
  'PARTIAL_FAILURE',
])

// === Config (api/schemas.py) ===============================================
export const PathsConfigSchema = z
  .object({
    source_roms: z.string(),
    source_dat: z.string(),
    dest_roms: z.string(),
    retroarch_playlist: z.string(),
    catver: z.string().nullable(),
    languages: z.string().nullable(),
    bestgames: z.string().nullable(),
    mature: z.string().nullable(),
    series: z.string().nullable(),
    listxml: z.string().nullable(),
    retroarch: z.string().nullable(),
    retroarch_core: z.string().nullable(),
  })
  .strict()

export const ServerConfigSchema = z
  .object({
    host: z.string(),
    port: z.number().int(),
    open_browser_on_start: z.boolean(),
  })
  .strict()

export const FsConfigSchema = z
  .object({ granted_roots: z.array(z.string()) })
  .strict()

export const MediaConfigSchema = z
  .object({ fetch_videos: z.boolean(), cache_dir: z.string() })
  .strict()

export const ThemeNameSchema = z.enum([
  'dark',
  'light',
  'double_dragon',
  'pacman',
  'sf2',
  'neogeo',
])

export const LayoutNameSchema = z.enum(['masonry', 'list', 'covers', 'grouped'])

export const SortKeySchema = z.enum(['name', 'year', 'manufacturer', 'rating'])

export const CardsPerRowHintSchema = z.union([
  z.literal('auto'),
  z.literal(4),
  z.literal(5),
  z.literal(6),
  z.literal(8),
])

export const UiConfigSchema = z
  .object({
    theme: ThemeNameSchema,
    layout: LayoutNameSchema,
    default_sort: SortKeySchema,
    show_alternatives_indicator: z.boolean(),
    cards_per_row_hint: CardsPerRowHintSchema,
    cart_clear_on_copy: z.enum(['always', 'on_success', 'never']).default('on_success'),
  })
  .strict()

export const UpdatesConfigSchema = z
  .object({
    channel: z.enum(['stable', 'dev']),
    check_on_startup: z.boolean(),
    ini_check_on_startup: z.boolean(),
  })
  .strict()

export const FilterConfigSchema = z
  .object({
    drop_bios_devices_mechanical: z.boolean(),
    drop_categories: z.array(z.string()),
    drop_genres: z.array(z.string()),
    drop_publishers: z.array(z.string()),
    drop_developers: z.array(z.string()),
    drop_year_before: z.number().int().nullable(),
    drop_year_after: z.number().int().nullable(),
    drop_japanese_only_text: z.boolean(),
    drop_preliminary_emulation: z.boolean(),
    drop_chd_required: z.boolean(),
    drop_mature: z.boolean(),
    region_priority: z.array(z.string()),
    preferred_genres: z.array(z.string()),
    preferred_publishers: z.array(z.string()),
    preferred_developers: z.array(z.string()),
    prefer_parent_over_clone: z.boolean(),
    prefer_good_driver: z.boolean(),
  })
  .strict()

export const AppConfigResponseSchema = z
  .object({
    paths: PathsConfigSchema,
    server: ServerConfigSchema,
    filters: FilterConfigSchema,
    media: MediaConfigSchema,
    ui: UiConfigSchema,
    updates: UpdatesConfigSchema,
    fs: FsConfigSchema,
    restart_required: z.boolean(),
  })
  .strict()

// === Games + metadata ======================================================
export const BadgeSchema = z.enum([
  'contested',
  'overridden',
  'chd_missing',
  'bios_missing',
  'has_notes',
])

export const GameCardSchema = z
  .object({
    short_name: z.string(),
    description: z.string(),
    year: z.number().int().nullable(),
    manufacturer: z.string().nullable(),
    publisher: z.string().nullable(),
    developer: z.string().nullable(),
    badges: z.array(BadgeSchema),
  })
  .strict()

export const GamesPageSchema = z
  .object({
    items: z.array(GameCardSchema),
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
    total_bytes: z.number().int().nonnegative(),
  })
  .strict()

export const ValidateRequestSchema = z
  .object({
    short_names: z.array(z.string()),
  })
  .strict()

export const ValidateResponseSchema = z
  .object({
    existing: z.array(z.string()),
    missing: z.array(z.string()),
  })
  .strict()

export const GameDetailSchema = z
  .object({
    short_name: z.string(),
    machine: MachineSchema,
    category: z.string().nullable(),
    languages: z.array(z.string()),
    bestgames_tier: z.string().nullable(),
    mature: z.boolean(),
    chd_required: z.boolean(),
    badges: z.array(BadgeSchema),
    override: z.string().nullable(),
    parent: z.string(),
  })
  .strict()

export const AlternativesSchema = z
  .object({ items: z.array(GameCardSchema) })
  .strict()

export const LibraryFacetsSchema = z
  .object({
    genres: z.array(z.string()),
    publishers: z.array(z.string()),
    developers: z.array(z.string()),
    letters: z.array(z.string()),
  })
  .strict()

export const LaunchResponseSchema = z
  .object({
    pid: z.number().int(),
    rom_path: z.string(),
    argv: z.array(z.string()),
  })
  .strict()

export const ExplanationSchema = z
  .object({
    short_name: z.string(),
    parent: z.string(),
    candidates: z.array(z.string()),
    hits: z.array(TiebreakerHitSchema),
  })
  .strict()

export const NotesSchema = z.object({ notes: z.string().max(4096) }).strict()

export const NotesPutRequestSchema = z
  .object({ notes: z.string().max(4096) })
  .strict()

export const StatsSchema = z
  .object({
    by_genre: z.record(z.string(), z.number().int()),
    by_decade: z.record(z.string(), z.number().int()),
    by_publisher: z.record(z.string(), z.number().int()),
    by_driver_status: z.record(z.string(), z.number().int()),
    total_bytes: z.number().int(),
  })
  .strict()

// === Overrides + sessions ==================================================
export const OverridesViewSchema = z
  .object({
    entries: z.record(z.string(), z.string()),
    warnings: z.array(z.string()),
  })
  .strict()

export const OverridePostRequestSchema = z
  .object({ parent: z.string(), winner: z.string() })
  .strict()

export const SessionsListingSchema = z
  .object({
    active: z.string().nullable(),
    sessions: z.record(z.string(), SessionSchema),
  })
  .strict()

export const SessionUpsertRequestSchema = z
  .object({ name: z.string(), session: SessionSchema })
  .strict()

// === P14 — per-game review state ===========================================
export const ReviewStateValueSchema = z.enum(['reviewed', 'skipped', 'needs-decision'])

export const StateViewSchema = z
  .object({ entries: z.record(z.string(), ReviewStateValueSchema) })
  .strict()

export const StatePostRequestSchema = z
  .object({ short_name: z.string(), state: ReviewStateValueSchema })
  .strict()

// === Snapshots / export-import =============================================
export const SnapshotSchema = z
  .object({
    id: z.string(),
    ts: zDateTime,
    files: z.array(z.string()),
  })
  .strict()

export const SnapshotsListingSchema = z
  .object({ items: z.array(SnapshotSchema) })
  .strict()

export const ConfigExportBundleSchema = z
  .object({
    config: z.record(z.string(), z.unknown()),
    overrides: z.record(z.string(), z.unknown()),
    sessions: z.record(z.string(), z.unknown()),
    notes: z.record(z.string(), z.string()),
  })
  .strict()

// === Copy job ==============================================================
export const CopyJobRequestSchema = z
  .object({
    selected_names: z.array(z.string()),
    conflict_strategy: ConflictStrategySchema,
    append_decisions: z.record(z.string(), AppendDecisionSchema),
  })
  .strict()

export const DryRunReportSchema = z
  .object({
    counts: z.record(z.string(), z.number().int()),
    summary: z.record(z.string(), z.unknown()),
  })
  .strict()

export const JobAcceptedSchema = z.object({ job_id: z.string() }).strict()

export const JobStateSchema = z.enum([
  'running',
  'paused',
  'terminating',
  'finished',
  'aborted',
])

export const JobStatusSchema = z
  .object({
    job_id: z.string(),
    state: JobStateSchema,
    started_at: zDateTime,
    files_done: z.number().int(),
    files_total: z.number().int(),
    bytes_done: z.number().int(),
    bytes_total: z.number().int(),
  })
  .strict()

export const JobEventNameSchema = z.enum([
  'job_started',
  'file_started',
  'file_progress',
  'file_finished',
  'paused',
  'resumed',
  'bios_warning',
  'job_finished',
  'job_aborted',
])

export const JobEventSchema = z
  .object({
    event: JobEventNameSchema,
    payload: z.record(z.string(), z.unknown()),
    ts: zDateTime,
  })
  .strict()

export const CopyAbortRequestSchema = z
  .object({ recycle_partial: z.boolean() })
  .strict()

export const HistoryItemSchema = z
  .object({
    job_id: z.string(),
    started_at: zDateTime,
    finished_at: zDateTime,
    status: CopyReportStatusSchema,
    succeeded: z.number().int(),
    failed: z.number().int(),
    bytes_copied: z.number().int(),
  })
  .strict()

export const HistoryListingSchema = z
  .object({
    items: z.array(HistoryItemSchema),
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
  })
  .strict()

// === Activity ==============================================================
export const ActivityPageSchema = z
  .object({
    items: z.array(z.record(z.string(), z.unknown())),
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
  })
  .strict()

// === Filesystem ============================================================
export const FsEntrySchema = z
  .object({
    name: z.string(),
    path: z.string(),
    is_dir: z.boolean(),
    size: z.number().int().nullable(),
    mtime: zDateTime,
  })
  .strict()

export const FsListingSchema = z
  .object({
    path: z.string(),
    entries: z.array(FsEntrySchema),
    parent: z.string().nullable(),
  })
  .strict()

export const FsPathSchema = z.object({ path: z.string() }).strict()

export const FsAllowedRootSchema = z
  .object({
    id: z.string(),
    path: z.string(),
    source: z.enum(['config', 'granted']),
  })
  .strict()

export const FsAllowedRootsSchema = z
  .object({ roots: z.array(FsAllowedRootSchema) })
  .strict()

export const FsDriveRootsSchema = z
  .object({ roots: z.array(z.string()) })
  .strict()

export const FsGrantRootRequestSchema = z
  .object({ path: z.string() })
  .strict()

// === Setup / updates stubs =================================================
export const SetupPathStatusSchema = z
  .object({
    path: z.string(),
    exists: z.boolean(),
    readable: z.boolean(),
    writable: z.boolean(),
    dat_parses: z.boolean().nullable(),
  })
  .strict()

export const SetupPathsSchema = z
  .object({
    source_roms: SetupPathStatusSchema,
    source_dat: SetupPathStatusSchema,
    dest_roms: SetupPathStatusSchema,
  })
  .strict()

export const SetupReferenceStatusSchema = z
  .object({ path: z.string(), exists: z.boolean() })
  .strict()

export const SetupReferenceFilesSchema = z
  .object({
    catver: SetupReferenceStatusSchema,
    languages: SetupReferenceStatusSchema,
    bestgames: SetupReferenceStatusSchema,
    mature: SetupReferenceStatusSchema,
    series: SetupReferenceStatusSchema,
    listxml: SetupReferenceStatusSchema,
  })
  .strict()

export const SetupCheckSchema = z
  .object({
    config_present: z.boolean(),
    paths: SetupPathsSchema,
    reference_files: SetupReferenceFilesSchema,
    cloneof_map_size: z.number().int().nonnegative(),
    retroarch_configured: z.boolean(),
  })
  .strict()

export const AppUpdateInfoSchema = z
  .object({
    current_version: z.string(),
    latest_version: z.string().nullable(),
    update_available: z.boolean(),
  })
  .strict()

export const UpdatesCheckSchema = z
  .object({ app: AppUpdateInfoSchema, ini: z.array(z.unknown()) })
  .strict()

// === Help ==================================================================
export const HelpTopicSchema = z
  .object({ slug: z.string(), title: z.string() })
  .strict()

export const HelpIndexSchema = z
  .object({ topics: z.array(HelpTopicSchema) })
  .strict()

export const HelpContentSchema = z
  .object({ slug: z.string(), title: z.string(), html: z.string() })
  .strict()
