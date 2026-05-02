import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { strings } from '@/strings'
import type { AppConfigResponse } from '@/api/types'

interface SettingsPageProps {
  config: AppConfigResponse
  onPatch: (patch: Partial<AppConfigResponse>) => void
  onSnapshotRestore: (id: string) => void
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
  'backup',
] as const

export function SettingsPage({ config, onPatch }: SettingsPageProps) {
  const updateUi = (key: keyof AppConfigResponse['ui'], value: boolean) => {
    onPatch({ ui: { ...config.ui, [key]: value } })
  }
  const updateFilters = (
    key: keyof AppConfigResponse['filters'],
    value: boolean,
  ) => {
    onPatch({ filters: { ...config.filters, [key]: value } })
  }
  const updateMedia = (
    key: keyof AppConfigResponse['media'],
    value: boolean,
  ) => {
    onPatch({ media: { ...config.media, [key]: value } })
  }
  const updateUpdates = (
    key: keyof AppConfigResponse['updates'],
    value: boolean,
  ) => {
    onPatch({ updates: { ...config.updates, [key]: value } })
  }

  return (
    <section className="flex flex-col gap-4 p-4">
      <h1 className="text-2xl font-semibold">{strings.settings.pageTitle}</h1>

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
            Source ROMs: <code>{config.paths.source_roms}</code>
          </p>
          <p className="text-sm text-muted-foreground">
            Destination: <code>{config.paths.dest_roms}</code>
          </p>
          <p className="text-sm text-muted-foreground">
            DAT: <code>{config.paths.source_dat}</code>
          </p>
        </TabsContent>

        <TabsContent value="filters" className="flex flex-col gap-2">
          <PrefSwitch
            id="filters-drop-bios"
            label="Drop BIOS / device / mechanical"
            checked={config.filters.drop_bios_devices_mechanical}
            onChange={(v) => updateFilters('drop_bios_devices_mechanical', v)}
          />
          <PrefSwitch
            id="filters-drop-japanese"
            label="Drop Japanese-only text games"
            checked={config.filters.drop_japanese_only_text}
            onChange={(v) => updateFilters('drop_japanese_only_text', v)}
          />
          <PrefSwitch
            id="filters-drop-preliminary"
            label="Drop preliminary emulation"
            checked={config.filters.drop_preliminary_emulation}
            onChange={(v) => updateFilters('drop_preliminary_emulation', v)}
          />
          <PrefSwitch
            id="filters-drop-chd"
            label="Drop CHD-required games"
            checked={config.filters.drop_chd_required}
            onChange={(v) => updateFilters('drop_chd_required', v)}
          />
          <PrefSwitch
            id="filters-drop-mature"
            label="Drop mature content"
            checked={config.filters.drop_mature}
            onChange={(v) => updateFilters('drop_mature', v)}
          />
        </TabsContent>

        <TabsContent value="picker" className="flex flex-col gap-2">
          <PrefSwitch
            id="picker-parent-over-clone"
            label="Prefer parent over clone"
            checked={config.filters.prefer_parent_over_clone}
            onChange={(v) => updateFilters('prefer_parent_over_clone', v)}
          />
          <PrefSwitch
            id="picker-good-driver"
            label="Prefer good driver"
            checked={config.filters.prefer_good_driver}
            onChange={(v) => updateFilters('prefer_good_driver', v)}
          />
        </TabsContent>

        <TabsContent value="ui" className="flex flex-col gap-2">
          <PrefSwitch
            id="ui-show-alternatives"
            label="Show alternatives indicator"
            checked={config.ui.show_alternatives_indicator}
            onChange={(v) => updateUi('show_alternatives_indicator', v)}
          />
        </TabsContent>

        <TabsContent value="updates" className="flex flex-col gap-2">
          <PrefSwitch
            id="updates-check-on-startup"
            label="Check for app updates on startup"
            checked={config.updates.check_on_startup}
            onChange={(v) => updateUpdates('check_on_startup', v)}
          />
          <PrefSwitch
            id="updates-ini-check-on-startup"
            label="Check for INI updates on startup"
            checked={config.updates.ini_check_on_startup}
            onChange={(v) => updateUpdates('ini_check_on_startup', v)}
          />
        </TabsContent>

        <TabsContent value="media" className="flex flex-col gap-2">
          <PrefSwitch
            id="media-fetch-videos"
            label="Fetch video previews (post-P06)"
            checked={config.media.fetch_videos}
            onChange={(v) => updateMedia('fetch_videos', v)}
          />
          <p className="text-xs text-muted-foreground">
            Cache: <code>{config.media.cache_dir}</code>
          </p>
        </TabsContent>

        <TabsContent value="backup" className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">
            Configuration snapshots can be restored from disk. Restore
            confirmation surfaces a destructive-action dialog.
          </p>
        </TabsContent>
      </Tabs>
    </section>
  )
}
