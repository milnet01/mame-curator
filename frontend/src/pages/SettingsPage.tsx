import { useState } from 'react'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import { BackupTab } from '@/components/settings/BackupTab'
import { FiltersTab } from '@/components/settings/FiltersTab'
import { MediaTab } from '@/components/settings/MediaTab'
import { PathRow } from '@/components/settings/PathRow'
import { PickerTab } from '@/components/settings/PickerTab'
import { PrefSwitch } from '@/components/settings/PrefSwitch'
import { SnapshotsTab } from '@/components/settings/SnapshotsTab'
import { UpdatesTab } from '@/components/settings/UpdatesTab'
import { strings } from '@/strings'
import type {
  AppConfigResponse,
  AppUpdateInfo,
  ConfigExportBundle,
  SetupCheck,
  Snapshot,
} from '@/api/types'

type FilterCfg = AppConfigResponse['filters']
type UiCfg = AppConfigResponse['ui']
type UpdatesCfg = AppConfigResponse['updates']
type DefaultSort = UiCfg['default_sort']

const DEFAULT_SORT_VALUES: readonly DefaultSort[] = [
  'name',
  'year',
  'manufacturer',
  'rating',
]

const ARCADE_FLOOR_YEAR = 1971
const CURRENT_YEAR = new Date().getFullYear()

const SECTION_KEYS = [
  'paths',
  'filters',
  'picker',
  'ui',
  'updates',
  'media',
  'snapshots',
  'backup',
  'about',
] as const

interface SettingsPageProps {
  config: AppConfigResponse
  onPatch: (patch: Partial<AppConfigResponse>) => void
  onSnapshotRestore: (id: string) => void
  /** R36 update-check payload — when present, drives the Updates banner. */
  updateInfo?: AppUpdateInfo
  /** R35 setup-check payload — when present, drives the Setup banner. */
  setupInfo?: SetupCheck
  /** FP12 § I — R16 snapshot listing. Defaults to empty for callers that
      haven't wired the hook yet (e.g. pre-cluster-I tests). */
  snapshots?: readonly Snapshot[]
  snapshotsLoading?: boolean
  snapshotsError?: string | null
  /** FP12 § J — Backup tab callbacks. No-op defaults so callers without
      export/import wiring still compile. */
  onBackupExport?: () => void
  onBackupImport?: (bundle: ConfigExportBundle) => void
  backupError?: string | null
}

export function SettingsPage({
  config,
  onPatch,
  onSnapshotRestore,
  updateInfo,
  setupInfo,
  snapshots = [],
  snapshotsLoading = false,
  snapshotsError = null,
  onBackupExport = () => {},
  onBackupImport = () => {},
  backupError = null,
}: SettingsPageProps) {
  const updateUi = <K extends keyof UiCfg>(key: K, value: UiCfg[K]) => {
    onPatch({ ui: { ...config.ui, [key]: value } })
  }
  // FP12 § A: generic so chip-list (string[]) and toggle (boolean) fields
  // share one helper. P06's original boolean-only signature blocked the
  // list editors; per-key inference keeps callers type-safe.
  const updateFilters = <K extends keyof FilterCfg>(
    key: K,
    value: FilterCfg[K],
  ) => {
    onPatch({ filters: { ...config.filters, [key]: value } })
  }
  const updateMedia = <K extends keyof AppConfigResponse['media']>(
    key: K,
    value: AppConfigResponse['media'][K],
  ) => {
    onPatch({ media: { ...config.media, [key]: value } })
  }
  const updatePaths = <K extends keyof AppConfigResponse['paths']>(
    key: K,
    value: AppConfigResponse['paths'][K],
  ) => {
    onPatch({ paths: { ...config.paths, [key]: value } })
  }
  const updateUpdates = <K extends keyof UpdatesCfg>(
    key: K,
    value: UpdatesCfg[K],
  ) => {
    onPatch({ updates: { ...config.updates, [key]: value } })
  }

  // FP12 § H — DAT swap is destructive (replaces the whole library);
  // hold the pending value here until the user confirms.
  const [pendingDat, setPendingDat] = useState<string | null>(null)
  // FP13 § B2: bumped after each pendingDat resolution (cancel or confirm)
  // so the source_dat PathRow re-mounts and `draft` re-seeds from `value`.
  // Without this, a typed-then-cancelled DAT path stays stale in the input.
  const [datResetTick, setDatResetTick] = useState(0)

  return (
    <section className="flex flex-col gap-4 p-4">
      <h1 className="text-2xl font-semibold">{strings.settings.pageTitle}</h1>

      {/* FP11 § B3: read-only Setup banner driven by R35 — design §8
          calls for a banner ahead of the tab list when paths or
          reference files are missing. Banner copy lives in strings.ts
          so the Phase 7 wizard wiring is a single-file change. */}
      {setupInfo && (
        <p
          role="status"
          className="rounded border border-muted bg-muted/30 px-3 py-2 text-sm"
        >
          {setupInfo.config_present
            ? strings.settings.banners.setupReady
            : strings.settings.banners.setupIncomplete}
        </p>
      )}

      {/* FP13 § A4: surface PATCH-response `restart_required` so server-bind
          changes (host/port) don't silently take effect only after restart. */}
      {config.restart_required && (
        <p
          role="status"
          className="rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm"
        >
          {strings.settings.banners.restartRequired}
        </p>
      )}

      <Tabs defaultValue="paths">
        <TabsList>
          {SECTION_KEYS.map((key) => (
            <TabsTrigger key={key} value={key}>
              {strings.settings.sections[key]}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="paths" className="flex flex-col gap-3">
          <PathRow
            id="paths-source-roms"
            label={strings.settings.pathRowLabels.sourceRoms}
            value={config.paths.source_roms}
            onChange={(next) => updatePaths('source_roms', next)}
          />
          <PathRow
            id="paths-dest-roms"
            label={strings.settings.pathRowLabels.destination}
            value={config.paths.dest_roms}
            onChange={(next) => updatePaths('dest_roms', next)}
          />
          <PathRow
            key={`paths-source-dat-${datResetTick}`}
            id="paths-source-dat"
            label={strings.settings.pathRowLabels.dat}
            value={config.paths.source_dat}
            mode="file"
            onChange={(next) => {
              if (next !== config.paths.source_dat) setPendingDat(next)
            }}
          />
          <PathRow
            id="paths-retroarch-playlist"
            label={strings.settings.pathRowLabels.retroarchPlaylist}
            value={config.paths.retroarch_playlist}
            mode="file"
            onChange={(next) => updatePaths('retroarch_playlist', next)}
          />
          {pendingDat !== null && (
            <ConfirmationDialog
              open
              onOpenChange={(o) => {
                if (!o) {
                  setPendingDat(null)
                  setDatResetTick((n) => n + 1)
                }
              }}
              title={strings.settings.datSwapConfirmTitle}
              description={strings.settings.datSwapConfirm}
              actionLabel={strings.settings.datSwapActionLabel(pendingDat)}
              destructive
              onConfirm={() => {
                updatePaths('source_dat', pendingDat)
                setDatResetTick((n) => n + 1)
              }}
            />
          )}
        </TabsContent>

        <TabsContent value="filters" className="flex flex-col gap-2">
          <FiltersTab
            filters={config.filters}
            onChange={updateFilters}
            minYear={ARCADE_FLOOR_YEAR}
            maxYear={CURRENT_YEAR}
          />
        </TabsContent>

        <TabsContent value="picker" className="flex flex-col gap-2">
          <PickerTab filters={config.filters} onChange={updateFilters} />
        </TabsContent>

        <TabsContent value="ui" className="flex flex-col gap-2">
          <PrefSwitch
            id="ui-show-alternatives"
            label={strings.settings.uiLabels.show_alternatives_indicator}
            checked={config.ui.show_alternatives_indicator}
            onChange={(v) => updateUi('show_alternatives_indicator', v)}
          />
          <div className="flex items-center justify-between">
            <Label htmlFor="ui-default-sort">
              {strings.settings.uiLabels.default_sort}
            </Label>
            <Select
              value={config.ui.default_sort}
              onValueChange={(v) => updateUi('default_sort', v as DefaultSort)}
            >
              <SelectTrigger
                id="ui-default-sort"
                aria-label={strings.settings.uiLabels.default_sort}
                className="w-48"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DEFAULT_SORT_VALUES.map((v) => (
                  <SelectItem key={v} value={v}>
                    {strings.settings.defaultSortOptions[v]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </TabsContent>

        <TabsContent value="updates" className="flex flex-col gap-2">
          <UpdatesTab
            updates={config.updates}
            onChange={updateUpdates}
            updateInfo={updateInfo}
          />
        </TabsContent>

        <TabsContent value="media" className="flex flex-col gap-2">
          <MediaTab media={config.media} onChange={updateMedia} />
        </TabsContent>

        <TabsContent value="snapshots" className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            {strings.settings.backupBlurb}
          </p>
          <SnapshotsTab
            snapshots={snapshots}
            loading={snapshotsLoading}
            error={snapshotsError}
            onRestore={onSnapshotRestore}
          />
        </TabsContent>

        <TabsContent value="backup" className="flex flex-col gap-2">
          <BackupTab
            onExport={onBackupExport}
            onImport={onBackupImport}
            error={backupError}
          />
        </TabsContent>

        <TabsContent value="about" className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            {strings.app.name} · {strings.app.tagline}
          </p>
        </TabsContent>
      </Tabs>
    </section>
  )
}
