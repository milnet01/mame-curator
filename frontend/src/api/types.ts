/**
 * Hand-mirrored API types from `mame_curator.api.schemas`.
 *
 * The `interface` declarations stay here because `tools/check_api_types_sync.py`
 * (the CI gate) parses this file for field parity against the Pydantic side.
 * The zod runtime validators were lifted to `./schemas.ts` in DS02 A3 to keep
 * both files under the 500-line cap; this file re-exports them at the bottom
 * so call-sites can keep importing `{ FooType, FooSchema }` from `@/api/types`
 * unchanged. See `docs/specs/P06.md` § "API contract surface".
 */

// === Error envelope (api/errors.py) ========================================
export interface FieldError {
  loc: string
  msg: string
  type: string
}

export interface ApiErrorBody {
  detail: string
  code: string
  fields: FieldError[]
}

// === Parser models (re-exported from schemas via Machine) ==================
export type DriverStatus = 'good' | 'imperfect' | 'preliminary'

export interface Rom {
  name: string
  size: number | null
  crc: string | null
  sha1: string | null
}

export interface BiosSet {
  name: string
  description: string | null
  default: boolean
}

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

// === Filter types (TiebreakerHit, Session) =================================
export interface TiebreakerHit {
  name: string
  detail: string
}

export interface Session {
  include_genres: string[]
  include_publishers: string[]
  include_developers: string[]
  include_year_range: [number, number] | null
}

// === Copy types (re-exported) ==============================================
export type ConflictStrategy = 'APPEND' | 'OVERWRITE' | 'CANCEL'

export type AppendDecisionKind =
  | 'KEEP_EXISTING'
  | 'REPLACE'
  | 'REPLACE_AND_RECYCLE'

export interface AppendDecision {
  kind: AppendDecisionKind
  replaces: string | null
}

export type CopyReportStatus =
  | 'OK'
  | 'CANCELLED'
  | 'CANCELLED_PLAYLIST_CONFLICT'
  | 'PARTIAL_FAILURE'

// === Config (api/schemas.py) ===============================================
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
  retroarch: string | null
  retroarch_core: string | null
}

export interface ServerConfig {
  host: string
  port: number
  open_browser_on_start: boolean
}

export interface FsConfig {
  granted_roots: string[]
}

export interface MediaConfig {
  fetch_videos: boolean
  cache_dir: string
}

export type ThemeName =
  | 'dark'
  | 'light'
  | 'double_dragon'
  | 'pacman'
  | 'sf2'
  | 'neogeo'

export type LayoutName = 'masonry' | 'list' | 'covers' | 'grouped'

export type SortKey = 'name' | 'year' | 'manufacturer' | 'rating'

export type CardsPerRowHint = 'auto' | 4 | 5 | 6 | 8

export interface UiConfig {
  theme: ThemeName
  layout: LayoutName
  default_sort: SortKey
  show_alternatives_indicator: boolean
  cards_per_row_hint: CardsPerRowHint
  cart_clear_on_copy: 'always' | 'on_success' | 'never'
}

export interface UpdatesConfig {
  channel: 'stable' | 'dev'
  check_on_startup: boolean
  ini_check_on_startup: boolean
}

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

// === Games + metadata ======================================================
export type Badge =
  | 'contested'
  | 'overridden'
  | 'chd_missing'
  | 'bios_missing'
  | 'has_notes'

export interface GameCard {
  short_name: string
  description: string
  year: number | null
  manufacturer: string | null
  publisher: string | null
  developer: string | null
  badges: Badge[]
}

export interface GamesPage {
  items: GameCard[]
  page: number
  page_size: number
  total: number
  total_bytes: number
}

export interface ValidateRequest {
  short_names: string[]
}

export interface ValidateResponse {
  existing: string[]
  missing: string[]
}

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

export interface Alternatives {
  items: GameCard[]
}

/** FP17: facets for FiltersSidebar dropdowns. ``letters`` uses ``'#'`` for digit-prefixed games. */
export interface LibraryFacets {
  genres: string[]
  publishers: string[]
  developers: string[]
  letters: string[]
}

/** FP19: outcome of POST /api/games/{name}/launch. */
export interface LaunchResponse {
  pid: number
  rom_path: string
  argv: string[]
}

export interface Explanation {
  short_name: string
  parent: string
  candidates: string[]
  hits: TiebreakerHit[]
}

export interface Notes {
  notes: string
}

export interface NotesPutRequest {
  notes: string
}

export interface Stats {
  by_genre: Record<string, number>
  by_decade: Record<string, number>
  by_publisher: Record<string, number>
  by_driver_status: Record<string, number>
  total_bytes: number
}

// === Overrides + sessions ==================================================
export interface OverridesView {
  entries: Record<string, string>
  warnings: string[]
}

export interface OverridePostRequest {
  parent: string
  winner: string
}

export interface SessionsListing {
  active: string | null
  sessions: Record<string, Session>
}

export interface SessionUpsertRequest {
  name: string
  session: Session
}

// === Snapshots / export-import =============================================
export interface Snapshot {
  id: string
  ts: Date
  files: string[]
}

export interface SnapshotsListing {
  items: Snapshot[]
}

export interface ConfigExportBundle {
  config: Record<string, unknown>
  overrides: Record<string, unknown>
  sessions: Record<string, unknown>
  notes: Record<string, string>
}

// === Copy job ==============================================================
export interface CopyJobRequest {
  selected_names: string[]
  conflict_strategy: ConflictStrategy
  append_decisions: Record<string, AppendDecision>
}

export interface DryRunReport {
  counts: Record<string, number>
  summary: Record<string, unknown>
}

export interface JobAccepted {
  job_id: string
}

export type JobState =
  | 'running'
  | 'paused'
  | 'terminating'
  | 'finished'
  | 'aborted'

export interface JobStatus {
  job_id: string
  state: JobState
  started_at: Date
  files_done: number
  files_total: number
  bytes_done: number
  bytes_total: number
}

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

export interface JobEvent {
  event: JobEventName
  payload: Record<string, unknown>
  ts: Date
}

export interface CopyAbortRequest {
  recycle_partial: boolean
}

export interface HistoryItem {
  job_id: string
  started_at: Date
  finished_at: Date
  status: CopyReportStatus
  succeeded: number
  failed: number
  bytes_copied: number
}

export interface HistoryListing {
  items: HistoryItem[]
  page: number
  page_size: number
  total: number
}

// === Activity ==============================================================
export interface ActivityPage {
  items: Record<string, unknown>[]
  page: number
  page_size: number
  total: number
}

// === Filesystem ============================================================
export interface FsEntry {
  name: string
  path: string
  is_dir: boolean
  size: number | null
  mtime: Date
}

export interface FsListing {
  path: string
  entries: FsEntry[]
  parent: string | null
}

export interface FsPath {
  path: string
}

export interface FsAllowedRoot {
  id: string
  path: string
  source: 'config' | 'granted'
}

export interface FsAllowedRoots {
  roots: FsAllowedRoot[]
}

export interface FsDriveRoots {
  roots: string[]
}

export interface FsGrantRootRequest {
  path: string
}

// === Setup / updates stubs =================================================
export interface SetupPathStatus {
  path: string
  exists: boolean
  readable: boolean
  writable: boolean
  dat_parses: boolean | null
}

export interface SetupPaths {
  source_roms: SetupPathStatus
  source_dat: SetupPathStatus
  dest_roms: SetupPathStatus
}

export interface SetupReferenceStatus {
  path: string
  exists: boolean
}

export interface SetupReferenceFiles {
  catver: SetupReferenceStatus
  languages: SetupReferenceStatus
  bestgames: SetupReferenceStatus
  mature: SetupReferenceStatus
  series: SetupReferenceStatus
  listxml: SetupReferenceStatus
}

export interface SetupCheck {
  config_present: boolean
  paths: SetupPaths
  reference_files: SetupReferenceFiles
  cloneof_map_size: number
  retroarch_configured: boolean
}

export interface AppUpdateInfo {
  current_version: string
  latest_version: string | null
  update_available: boolean
}

export interface UpdatesCheck {
  app: AppUpdateInfo
  ini: unknown[]
}

// === Help ==================================================================
export interface HelpTopic {
  slug: string
  title: string
}

export interface HelpIndex {
  topics: HelpTopic[]
}

export interface HelpContent {
  slug: string
  title: string
  html: string
}

// === Re-export zod schemas (DS02 A3: split to keep both files ≤ caps) ======
export * from './schemas'
