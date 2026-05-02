/**
 * Hand-mirrored API types from `mame_curator.api.schemas`.
 *
 * Both the TypeScript interface and the zod schema for each model live here
 * side-by-side so:
 *   1. `tools/check_api_types_sync.py` (the CI gate) verifies field parity
 *      against the Pydantic side by parsing the `interface` declarations.
 *   2. `client.ts` validates every response at runtime via the zod schema,
 *      mirroring Pydantic's `extra="forbid"` (we use `.strict()`).
 *
 * Size note: this file is intentionally a flat type-mirror dump. The
 * frontend's component-size caps (~200 lines, hard 350) target UI files;
 * a schema bridge has no logic and stays in one place so the CI gate has
 * a single parsing target — see `docs/specs/P06.md` § "API contract surface".
 */

import { z } from 'zod'

// ---------------------------------------------------------------------------
// Common
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Error envelope (api/errors.py)
// ---------------------------------------------------------------------------

export interface FieldError {
  loc: string
  msg: string
  type: string
}

export const FieldErrorSchema = z
  .object({
    loc: z.string(),
    msg: z.string(),
    type: z.string(),
  })
  .strict()

export interface ApiErrorBody {
  detail: string
  code: string
  fields: FieldError[]
}

export const ApiErrorBodySchema = z
  .object({
    detail: z.string(),
    code: z.string(),
    fields: z.array(FieldErrorSchema),
  })
  .strict()

// ---------------------------------------------------------------------------
// Parser models (re-exported from schemas via Machine)
// ---------------------------------------------------------------------------

export type DriverStatus = 'good' | 'imperfect' | 'preliminary'
export const DriverStatusSchema = z.enum(['good', 'imperfect', 'preliminary'])

export interface Rom {
  name: string
  size: number | null
  crc: string | null
  sha1: string | null
}
export const RomSchema = z
  .object({
    name: z.string().min(1),
    // FP11 § G1: mirror Pydantic `Field(ge=0)` constraint.
    size: z.number().int().nonnegative().nullable(),
    crc: z.string().nullable(),
    sha1: z.string().nullable(),
  })
  .strict()

export interface BiosSet {
  name: string
  description: string | null
  default: boolean
}
export const BiosSetSchema = z
  .object({
    name: z.string().min(1),
    description: z.string().nullable(),
    default: z.boolean(),
  })
  .strict()

export interface Machine {
  name: string
  description: string
  year: number | null
  manufacturer_raw: string | null
  publisher: string | null
  developer: string | null
  cloneof: string | null
  romof: string | null
  is_bios: boolean
  is_device: boolean
  is_mechanical: boolean
  runnable: boolean
  roms: Rom[]
  biossets: BiosSet[]
  driver_status: DriverStatus | null
  sample_of: string | null
}
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

// ---------------------------------------------------------------------------
// Filter types (TiebreakerHit, Session)
// ---------------------------------------------------------------------------

export interface TiebreakerHit {
  name: string
  detail: string
}
export const TiebreakerHitSchema = z
  .object({ name: z.string(), detail: z.string() })
  .strict()

export interface Session {
  include_genres: string[]
  include_publishers: string[]
  include_developers: string[]
  include_year_range: [number, number] | null
}
export const SessionSchema = z
  .object({
    include_genres: z.array(z.string()),
    include_publishers: z.array(z.string()),
    include_developers: z.array(z.string()),
    include_year_range: z.tuple([z.number().int(), z.number().int()]).nullable(),
  })
  .strict()

// ---------------------------------------------------------------------------
// Copy types (re-exported)
// ---------------------------------------------------------------------------

export type ConflictStrategy = 'APPEND' | 'OVERWRITE' | 'CANCEL'
export const ConflictStrategySchema = z.enum(['APPEND', 'OVERWRITE', 'CANCEL'])

export type AppendDecisionKind =
  | 'KEEP_EXISTING'
  | 'REPLACE'
  | 'REPLACE_AND_RECYCLE'
export const AppendDecisionKindSchema = z.enum([
  'KEEP_EXISTING',
  'REPLACE',
  'REPLACE_AND_RECYCLE',
])

export interface AppendDecision {
  kind: AppendDecisionKind
  replaces: string | null
}
export const AppendDecisionSchema = z
  .object({
    kind: AppendDecisionKindSchema,
    replaces: z.string().nullable(),
  })
  .strict()

export type CopyReportStatus =
  | 'OK'
  | 'CANCELLED'
  | 'CANCELLED_PLAYLIST_CONFLICT'
  | 'PARTIAL_FAILURE'
export const CopyReportStatusSchema = z.enum([
  'OK',
  'CANCELLED',
  'CANCELLED_PLAYLIST_CONFLICT',
  'PARTIAL_FAILURE',
])

// ---------------------------------------------------------------------------
// Config (api/schemas.py)
// ---------------------------------------------------------------------------

export interface PathsConfig {
  source_roms: string
  source_dat: string
  dest_roms: string
  retroarch_playlist: string
  catver: string | null
  languages: string | null
  bestgames: string | null
  mature: string | null
  series: string | null
  listxml: string | null
}
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
  })
  .strict()

export interface ServerConfig {
  host: string
  port: number
  open_browser_on_start: boolean
}
export const ServerConfigSchema = z
  .object({
    host: z.string(),
    port: z.number().int(),
    open_browser_on_start: z.boolean(),
  })
  .strict()

export interface FsConfig {
  granted_roots: string[]
}
export const FsConfigSchema = z
  .object({ granted_roots: z.array(z.string()) })
  .strict()

export interface MediaConfig {
  fetch_videos: boolean
  cache_dir: string
}
export const MediaConfigSchema = z
  .object({ fetch_videos: z.boolean(), cache_dir: z.string() })
  .strict()

export type ThemeName =
  | 'dark'
  | 'light'
  | 'double_dragon'
  | 'pacman'
  | 'sf2'
  | 'neogeo'
export const ThemeNameSchema = z.enum([
  'dark',
  'light',
  'double_dragon',
  'pacman',
  'sf2',
  'neogeo',
])

export type LayoutName = 'masonry' | 'list' | 'covers' | 'grouped'
export const LayoutNameSchema = z.enum(['masonry', 'list', 'covers', 'grouped'])

export type SortKey = 'name' | 'year' | 'manufacturer' | 'rating'
export const SortKeySchema = z.enum(['name', 'year', 'manufacturer', 'rating'])

export type CardsPerRowHint = 'auto' | 4 | 5 | 6 | 8
export const CardsPerRowHintSchema = z.union([
  z.literal('auto'),
  z.literal(4),
  z.literal(5),
  z.literal(6),
  z.literal(8),
])

export interface UiConfig {
  theme: ThemeName
  layout: LayoutName
  default_sort: SortKey
  show_alternatives_indicator: boolean
  cards_per_row_hint: CardsPerRowHint
}
export const UiConfigSchema = z
  .object({
    theme: ThemeNameSchema,
    layout: LayoutNameSchema,
    default_sort: SortKeySchema,
    show_alternatives_indicator: z.boolean(),
    cards_per_row_hint: CardsPerRowHintSchema,
  })
  .strict()

export interface UpdatesConfig {
  channel: 'stable' | 'dev'
  check_on_startup: boolean
  ini_check_on_startup: boolean
}
export const UpdatesConfigSchema = z
  .object({
    channel: z.enum(['stable', 'dev']),
    check_on_startup: z.boolean(),
    ini_check_on_startup: z.boolean(),
  })
  .strict()

export interface FilterConfig {
  drop_bios_devices_mechanical: boolean
  drop_categories: string[]
  drop_genres: string[]
  drop_publishers: string[]
  drop_developers: string[]
  drop_year_before: number | null
  drop_year_after: number | null
  drop_japanese_only_text: boolean
  drop_preliminary_emulation: boolean
  drop_chd_required: boolean
  drop_mature: boolean
  region_priority: string[]
  preferred_genres: string[]
  preferred_publishers: string[]
  preferred_developers: string[]
  prefer_parent_over_clone: boolean
  prefer_good_driver: boolean
}
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

export interface AppConfigResponse {
  paths: PathsConfig
  server: ServerConfig
  filters: FilterConfig
  media: MediaConfig
  ui: UiConfig
  updates: UpdatesConfig
  fs: FsConfig
  restart_required: boolean
}
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

// ---------------------------------------------------------------------------
// Games + metadata
// ---------------------------------------------------------------------------

export type Badge =
  | 'contested'
  | 'overridden'
  | 'chd_missing'
  | 'bios_missing'
  | 'has_notes'
export const BadgeSchema = z.enum([
  'contested',
  'overridden',
  'chd_missing',
  'bios_missing',
  'has_notes',
])

export interface GameCard {
  short_name: string
  description: string
  year: number | null
  manufacturer: string | null
  publisher: string | null
  developer: string | null
  badges: Badge[]
}
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

export interface GamesPage {
  items: GameCard[]
  page: number
  page_size: number
  total: number
}
export const GamesPageSchema = z
  .object({
    items: z.array(GameCardSchema),
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
  })
  .strict()

export interface GameDetail {
  short_name: string
  machine: Machine
  category: string | null
  languages: string[]
  bestgames_tier: string | null
  mature: boolean
  chd_required: boolean
  badges: Badge[]
  override: string | null
  parent: string
}
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

export interface Alternatives {
  items: GameCard[]
}
export const AlternativesSchema = z
  .object({ items: z.array(GameCardSchema) })
  .strict()

export interface Explanation {
  short_name: string
  parent: string
  candidates: string[]
  hits: TiebreakerHit[]
}
export const ExplanationSchema = z
  .object({
    short_name: z.string(),
    parent: z.string(),
    candidates: z.array(z.string()),
    hits: z.array(TiebreakerHitSchema),
  })
  .strict()

export interface Notes {
  notes: string
}
export const NotesSchema = z.object({ notes: z.string().max(4096) }).strict()

export interface NotesPutRequest {
  notes: string
}
export const NotesPutRequestSchema = z
  .object({ notes: z.string().max(4096) })
  .strict()

export interface Stats {
  by_genre: Record<string, number>
  by_decade: Record<string, number>
  by_publisher: Record<string, number>
  by_driver_status: Record<string, number>
  total_bytes: number
}
export const StatsSchema = z
  .object({
    by_genre: z.record(z.string(), z.number().int()),
    by_decade: z.record(z.string(), z.number().int()),
    by_publisher: z.record(z.string(), z.number().int()),
    by_driver_status: z.record(z.string(), z.number().int()),
    total_bytes: z.number().int(),
  })
  .strict()

// ---------------------------------------------------------------------------
// Overrides + sessions
// ---------------------------------------------------------------------------

export interface OverridesView {
  entries: Record<string, string>
  warnings: string[]
}
export const OverridesViewSchema = z
  .object({
    entries: z.record(z.string(), z.string()),
    warnings: z.array(z.string()),
  })
  .strict()

export interface OverridePostRequest {
  parent: string
  winner: string
}
export const OverridePostRequestSchema = z
  .object({ parent: z.string(), winner: z.string() })
  .strict()

export interface SessionsListing {
  active: string | null
  sessions: Record<string, Session>
}
export const SessionsListingSchema = z
  .object({
    active: z.string().nullable(),
    sessions: z.record(z.string(), SessionSchema),
  })
  .strict()

export interface SessionUpsertRequest {
  name: string
  session: Session
}
export const SessionUpsertRequestSchema = z
  .object({ name: z.string(), session: SessionSchema })
  .strict()

// ---------------------------------------------------------------------------
// Snapshots / export-import
// ---------------------------------------------------------------------------

export interface Snapshot {
  id: string
  ts: Date
  files: string[]
}
export const SnapshotSchema = z
  .object({
    id: z.string(),
    ts: zDateTime,
    files: z.array(z.string()),
  })
  .strict()

export interface SnapshotsListing {
  items: Snapshot[]
}
export const SnapshotsListingSchema = z
  .object({ items: z.array(SnapshotSchema) })
  .strict()

export interface ConfigExportBundle {
  config: Record<string, unknown>
  overrides: Record<string, unknown>
  sessions: Record<string, unknown>
  notes: Record<string, string>
}
export const ConfigExportBundleSchema = z
  .object({
    config: z.record(z.string(), z.unknown()),
    overrides: z.record(z.string(), z.unknown()),
    sessions: z.record(z.string(), z.unknown()),
    notes: z.record(z.string(), z.string()),
  })
  .strict()

// ---------------------------------------------------------------------------
// Copy job
// ---------------------------------------------------------------------------

export interface CopyJobRequest {
  selected_names: string[]
  conflict_strategy: ConflictStrategy
  append_decisions: Record<string, AppendDecision>
}
export const CopyJobRequestSchema = z
  .object({
    selected_names: z.array(z.string()),
    conflict_strategy: ConflictStrategySchema,
    append_decisions: z.record(z.string(), AppendDecisionSchema),
  })
  .strict()

export interface DryRunReport {
  counts: Record<string, number>
  summary: Record<string, unknown>
}
export const DryRunReportSchema = z
  .object({
    counts: z.record(z.string(), z.number().int()),
    summary: z.record(z.string(), z.unknown()),
  })
  .strict()

export interface JobAccepted {
  job_id: string
}
export const JobAcceptedSchema = z.object({ job_id: z.string() }).strict()

export type JobState =
  | 'running'
  | 'paused'
  | 'terminating'
  | 'finished'
  | 'aborted'
export const JobStateSchema = z.enum([
  'running',
  'paused',
  'terminating',
  'finished',
  'aborted',
])

export interface JobStatus {
  job_id: string
  state: JobState
  started_at: Date
  files_done: number
  files_total: number
  bytes_done: number
  bytes_total: number
}
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

export type JobEventName =
  | 'job_started'
  | 'file_started'
  | 'file_progress'
  | 'file_finished'
  | 'paused'
  | 'resumed'
  | 'bios_warning'
  | 'job_finished'
  | 'job_aborted'
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

export interface JobEvent {
  event: JobEventName
  payload: Record<string, unknown>
  ts: Date
}
export const JobEventSchema = z
  .object({
    event: JobEventNameSchema,
    payload: z.record(z.string(), z.unknown()),
    ts: zDateTime,
  })
  .strict()

export interface CopyAbortRequest {
  recycle_partial: boolean
}
export const CopyAbortRequestSchema = z
  .object({ recycle_partial: z.boolean() })
  .strict()

export interface HistoryItem {
  job_id: string
  started_at: Date
  finished_at: Date
  status: CopyReportStatus
  succeeded: number
  failed: number
  bytes_copied: number
}
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

export interface HistoryListing {
  items: HistoryItem[]
  page: number
  page_size: number
  total: number
}
export const HistoryListingSchema = z
  .object({
    items: z.array(HistoryItemSchema),
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
  })
  .strict()

// ---------------------------------------------------------------------------
// Activity
// ---------------------------------------------------------------------------

export interface ActivityPage {
  items: Record<string, unknown>[]
  page: number
  page_size: number
  total: number
}
export const ActivityPageSchema = z
  .object({
    items: z.array(z.record(z.string(), z.unknown())),
    page: z.number().int(),
    page_size: z.number().int(),
    total: z.number().int(),
  })
  .strict()

// ---------------------------------------------------------------------------
// Filesystem
// ---------------------------------------------------------------------------

export interface FsEntry {
  name: string
  path: string
  is_dir: boolean
  size: number | null
  mtime: Date
}
export const FsEntrySchema = z
  .object({
    name: z.string(),
    path: z.string(),
    is_dir: z.boolean(),
    size: z.number().int().nullable(),
    mtime: zDateTime,
  })
  .strict()

export interface FsListing {
  path: string
  entries: FsEntry[]
  parent: string | null
}
export const FsListingSchema = z
  .object({
    path: z.string(),
    entries: z.array(FsEntrySchema),
    parent: z.string().nullable(),
  })
  .strict()

export interface FsPath {
  path: string
}
export const FsPathSchema = z.object({ path: z.string() }).strict()

export interface FsAllowedRoot {
  id: string
  path: string
  source: 'config' | 'granted'
}
export const FsAllowedRootSchema = z
  .object({
    id: z.string(),
    path: z.string(),
    source: z.enum(['config', 'granted']),
  })
  .strict()

export interface FsAllowedRoots {
  roots: FsAllowedRoot[]
}
export const FsAllowedRootsSchema = z
  .object({ roots: z.array(FsAllowedRootSchema) })
  .strict()

export interface FsDriveRoots {
  roots: string[]
}
export const FsDriveRootsSchema = z
  .object({ roots: z.array(z.string()) })
  .strict()

export interface FsGrantRootRequest {
  path: string
}
export const FsGrantRootRequestSchema = z
  .object({ path: z.string() })
  .strict()

// ---------------------------------------------------------------------------
// Setup / updates stubs
// ---------------------------------------------------------------------------

export interface SetupPathStatus {
  path: string
  exists: boolean
  readable: boolean
  writable: boolean
  dat_parses: boolean | null
}
export const SetupPathStatusSchema = z
  .object({
    path: z.string(),
    exists: z.boolean(),
    readable: z.boolean(),
    writable: z.boolean(),
    dat_parses: z.boolean().nullable(),
  })
  .strict()

export interface SetupPaths {
  source_roms: SetupPathStatus
  source_dat: SetupPathStatus
  dest_roms: SetupPathStatus
}
export const SetupPathsSchema = z
  .object({
    source_roms: SetupPathStatusSchema,
    source_dat: SetupPathStatusSchema,
    dest_roms: SetupPathStatusSchema,
  })
  .strict()

export interface SetupReferenceStatus {
  path: string
  exists: boolean
}
export const SetupReferenceStatusSchema = z
  .object({ path: z.string(), exists: z.boolean() })
  .strict()

export interface SetupReferenceFiles {
  catver: SetupReferenceStatus
  languages: SetupReferenceStatus
  bestgames: SetupReferenceStatus
  mature: SetupReferenceStatus
  series: SetupReferenceStatus
  listxml: SetupReferenceStatus
}
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

export interface SetupCheck {
  config_present: boolean
  paths: SetupPaths
  reference_files: SetupReferenceFiles
}
export const SetupCheckSchema = z
  .object({
    config_present: z.boolean(),
    paths: SetupPathsSchema,
    reference_files: SetupReferenceFilesSchema,
  })
  .strict()

export interface AppUpdateInfo {
  current_version: string
  latest_version: string | null
  update_available: boolean
}
export const AppUpdateInfoSchema = z
  .object({
    current_version: z.string(),
    latest_version: z.string().nullable(),
    update_available: z.boolean(),
  })
  .strict()

export interface UpdatesCheck {
  app: AppUpdateInfo
  ini: unknown[]
}
export const UpdatesCheckSchema = z
  .object({ app: AppUpdateInfoSchema, ini: z.array(z.unknown()) })
  .strict()

// ---------------------------------------------------------------------------
// Help
// ---------------------------------------------------------------------------

export interface HelpTopic {
  slug: string
  title: string
}
export const HelpTopicSchema = z
  .object({ slug: z.string(), title: z.string() })
  .strict()

export interface HelpIndex {
  topics: HelpTopic[]
}
export const HelpIndexSchema = z
  .object({ topics: z.array(HelpTopicSchema) })
  .strict()

export interface HelpContent {
  slug: string
  title: string
  html: string
}
export const HelpContentSchema = z
  .object({ slug: z.string(), title: z.string(), html: z.string() })
  .strict()
