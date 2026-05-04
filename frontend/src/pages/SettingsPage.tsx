import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ChipListEditor } from '@/components/settings/ChipListEditor'
import { DragReorderList } from '@/components/settings/DragReorderList'
import { YearRangeEditor } from '@/components/settings/YearRangeEditor'
import { SnapshotsTab } from '@/components/settings/SnapshotsTab'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { strings } from '@/strings'
import type {
  AppConfigResponse,
  AppUpdateInfo,
  SetupCheck,
  Snapshot,
} from '@/api/types'

type FilterCfg = AppConfigResponse['filters']
type UiCfg = AppConfigResponse['ui']
type UpdatesCfg = AppConfigResponse['updates']
type DefaultSort = UiCfg['default_sort']
type UpdateChannel = UpdatesCfg['channel']

const UPDATE_CHANNEL_VALUES: readonly UpdateChannel[] = ['stable', 'dev']

const DEFAULT_SORT_VALUES: readonly DefaultSort[] = [
  'name',
  'year',
  'manufacturer',
  'rating',
]

const FILTER_CHIP_KEYS = [
  'drop_categories',
  'drop_genres',
  'drop_publishers',
  'drop_developers',
] as const

const PICKER_CHIP_KEYS = [
  'preferred_genres',
  'preferred_publishers',
  'preferred_developers',
] as const

const ARCADE_FLOOR_YEAR = 1971
const CURRENT_YEAR = new Date().getFullYear()

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
}

interface PrefSwitchProps {
  id: string
  label: string
  checked: boolean
  onChange: (next: boolean) => void
}

function PrefSwitch({ id, label, checked, onChange }: PrefSwitchProps) {
  return (
    <div className="flex items-center justify-between">
      <Label htmlFor={id}>{label}</Label>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </div>
  )
}

const SECTION_KEYS = [
  'paths',
  'filters',
  'picker',
  'ui',
  'updates',
  'media',
  'snapshots',
  'about',
] as const

export function SettingsPage({
  config,
  onPatch,
  onSnapshotRestore,
  updateInfo,
  setupInfo,
  snapshots = [],
  snapshotsLoading = false,
  snapshotsError = null,
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
  const updateMedia = (
    key: keyof AppConfigResponse['media'],
    value: boolean,
  ) => {
    onPatch({ media: { ...config.media, [key]: value } })
  }
  const updateUpdates = <K extends keyof UpdatesCfg>(
    key: K,
    value: UpdatesCfg[K],
  ) => {
    onPatch({ updates: { ...config.updates, [key]: value } })
  }

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

      <Tabs defaultValue="paths">
        <TabsList>
          {SECTION_KEYS.map((key) => (
            <TabsTrigger key={key} value={key}>
              {strings.settings.sections[key]}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="paths" className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            {strings.settings.pathRowLabels.sourceRoms}{' '}
            <code>{config.paths.source_roms}</code>
          </p>
          <p className="text-sm text-muted-foreground">
            {strings.settings.pathRowLabels.destination}{' '}
            <code>{config.paths.dest_roms}</code>
          </p>
          <p className="text-sm text-muted-foreground">
            {strings.settings.pathRowLabels.dat}{' '}
            <code>{config.paths.source_dat}</code>
          </p>
        </TabsContent>

        <TabsContent value="filters" className="flex flex-col gap-2">
          <PrefSwitch
            id="filters-drop-bios"
            label={strings.settings.filterLabels.drop_bios_devices_mechanical}
            checked={config.filters.drop_bios_devices_mechanical}
            onChange={(v) => updateFilters('drop_bios_devices_mechanical', v)}
          />
          <PrefSwitch
            id="filters-drop-japanese"
            label={strings.settings.filterLabels.drop_japanese_only_text}
            checked={config.filters.drop_japanese_only_text}
            onChange={(v) => updateFilters('drop_japanese_only_text', v)}
          />
          <PrefSwitch
            id="filters-drop-preliminary"
            label={strings.settings.filterLabels.drop_preliminary_emulation}
            checked={config.filters.drop_preliminary_emulation}
            onChange={(v) => updateFilters('drop_preliminary_emulation', v)}
          />
          <PrefSwitch
            id="filters-drop-chd"
            label={strings.settings.filterLabels.drop_chd_required}
            checked={config.filters.drop_chd_required}
            onChange={(v) => updateFilters('drop_chd_required', v)}
          />
          <PrefSwitch
            id="filters-drop-mature"
            label={strings.settings.filterLabels.drop_mature}
            checked={config.filters.drop_mature}
            onChange={(v) => updateFilters('drop_mature', v)}
          />
          <YearRangeEditor
            before={config.filters.drop_year_before}
            after={config.filters.drop_year_after}
            onBeforeChange={(v) => updateFilters('drop_year_before', v)}
            onAfterChange={(v) => updateFilters('drop_year_after', v)}
            minYear={ARCADE_FLOOR_YEAR}
            maxYear={CURRENT_YEAR}
          />
          {FILTER_CHIP_KEYS.map((key) => {
            const id = `filters-${key.replace(/_/g, '-')}`
            return (
              <div key={key} className="flex flex-col gap-1">
                <Label htmlFor={id}>
                  {strings.settings.filterChipLists[key]}
                </Label>
                <ChipListEditor
                  ariaLabel={strings.settings.filterChipLists[key]}
                  inputId={id}
                  value={config.filters[key]}
                  onChange={(next) => updateFilters(key, next)}
                  addPlaceholder={strings.settings.filterChipPlaceholders[key]}
                />
              </div>
            )
          })}
        </TabsContent>

        <TabsContent value="picker" className="flex flex-col gap-2">
          {/* Picker prefs are stored on the same FilterConfig server-side
              (design §6.2) so the dispatch goes through `updateFilters`. */}
          <PrefSwitch
            id="picker-parent-over-clone"
            label={strings.settings.pickerLabels.prefer_parent_over_clone}
            checked={config.filters.prefer_parent_over_clone}
            onChange={(v) => updateFilters('prefer_parent_over_clone', v)}
          />
          <PrefSwitch
            id="picker-good-driver"
            label={strings.settings.pickerLabels.prefer_good_driver}
            checked={config.filters.prefer_good_driver}
            onChange={(v) => updateFilters('prefer_good_driver', v)}
          />
          {PICKER_CHIP_KEYS.map((key) => {
            const id = `picker-${key.replace(/_/g, '-')}`
            return (
              <div key={key} className="flex flex-col gap-1">
                <Label htmlFor={id}>
                  {strings.settings.pickerChipLists[key]}
                </Label>
                <ChipListEditor
                  ariaLabel={strings.settings.pickerChipLists[key]}
                  inputId={id}
                  value={config.filters[key]}
                  onChange={(next) => updateFilters(key, next)}
                  addPlaceholder={strings.settings.pickerChipPlaceholders[key]}
                />
              </div>
            )
          })}
          <div className="flex flex-col gap-1">
            <span className="text-sm font-medium">
              {strings.settings.pickerLabels.region_priority}
            </span>
            <p className="text-xs text-muted-foreground">
              {strings.settings.regionPriorityHelp}
            </p>
            <DragReorderList
              ariaLabel={strings.settings.pickerLabels.region_priority}
              items={config.filters.region_priority}
              onChange={(next) => updateFilters('region_priority', next)}
            />
          </div>
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
          {/* FP11 § B3: R36 read-only banner — design §8 + spec § 147-150
              demand it. Phase 7 will swap this for the apply-update flow. */}
          {updateInfo && (
            <p
              role="status"
              className="rounded border border-muted bg-muted/30 px-3 py-2 text-sm"
            >
              {updateInfo.update_available && updateInfo.latest_version
                ? strings.settings.banners.updateAvailable(
                    updateInfo.current_version,
                    updateInfo.latest_version,
                  )
                : strings.settings.banners.updateCurrent(
                    updateInfo.current_version,
                  )}
            </p>
          )}
          <div className="flex items-center justify-between">
            <Label htmlFor="updates-channel">
              {strings.settings.updatesLabels.channel}
            </Label>
            <Select
              value={config.updates.channel}
              onValueChange={(v) =>
                updateUpdates('channel', v as UpdateChannel)
              }
            >
              <SelectTrigger
                id="updates-channel"
                aria-label={strings.settings.updatesLabels.channel}
                className="w-32"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {UPDATE_CHANNEL_VALUES.map((v) => (
                  <SelectItem key={v} value={v}>
                    {strings.settings.updateChannelOptions[v]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <PrefSwitch
            id="updates-check-on-startup"
            label={strings.settings.updatesLabels.check_on_startup}
            checked={config.updates.check_on_startup}
            onChange={(v) => updateUpdates('check_on_startup', v)}
          />
          <PrefSwitch
            id="updates-ini-check-on-startup"
            label={strings.settings.updatesLabels.ini_check_on_startup}
            checked={config.updates.ini_check_on_startup}
            onChange={(v) => updateUpdates('ini_check_on_startup', v)}
          />
        </TabsContent>

        <TabsContent value="media" className="flex flex-col gap-2">
          <PrefSwitch
            id="media-fetch-videos"
            label={strings.settings.mediaLabels.fetch_videos}
            checked={config.media.fetch_videos}
            onChange={(v) => updateMedia('fetch_videos', v)}
          />
          <p className="text-xs text-muted-foreground">
            {strings.settings.mediaCacheLabel}{' '}
            <code>{config.media.cache_dir}</code>
          </p>
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

        <TabsContent value="about" className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            {strings.app.name} · {strings.app.tagline}
          </p>
        </TabsContent>
      </Tabs>
    </section>
  )
}
