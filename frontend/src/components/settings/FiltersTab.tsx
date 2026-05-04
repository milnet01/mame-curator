import { Label } from '@/components/ui/label'
import { ChipListEditor } from '@/components/settings/ChipListEditor'
import { YearRangeEditor } from '@/components/settings/YearRangeEditor'
import { PrefSwitch } from '@/components/settings/PrefSwitch'
import { strings } from '@/strings'
import type { AppConfigResponse } from '@/api/types'

type FilterCfg = AppConfigResponse['filters']

const FILTER_CHIP_KEYS = [
  'drop_categories',
  'drop_genres',
  'drop_publishers',
  'drop_developers',
] as const

interface FiltersTabProps {
  filters: FilterCfg
  onChange: <K extends keyof FilterCfg>(key: K, value: FilterCfg[K]) => void
  minYear: number
  maxYear: number
}

export function FiltersTab({
  filters,
  onChange,
  minYear,
  maxYear,
}: FiltersTabProps) {
  return (
    <>
      <PrefSwitch
        id="filters-drop-bios"
        label={strings.settings.filterLabels.drop_bios_devices_mechanical}
        checked={filters.drop_bios_devices_mechanical}
        onChange={(v) => onChange('drop_bios_devices_mechanical', v)}
      />
      <PrefSwitch
        id="filters-drop-japanese"
        label={strings.settings.filterLabels.drop_japanese_only_text}
        checked={filters.drop_japanese_only_text}
        onChange={(v) => onChange('drop_japanese_only_text', v)}
      />
      <PrefSwitch
        id="filters-drop-preliminary"
        label={strings.settings.filterLabels.drop_preliminary_emulation}
        checked={filters.drop_preliminary_emulation}
        onChange={(v) => onChange('drop_preliminary_emulation', v)}
      />
      <PrefSwitch
        id="filters-drop-chd"
        label={strings.settings.filterLabels.drop_chd_required}
        checked={filters.drop_chd_required}
        onChange={(v) => onChange('drop_chd_required', v)}
      />
      <PrefSwitch
        id="filters-drop-mature"
        label={strings.settings.filterLabels.drop_mature}
        checked={filters.drop_mature}
        onChange={(v) => onChange('drop_mature', v)}
      />
      <YearRangeEditor
        before={filters.drop_year_before}
        after={filters.drop_year_after}
        onBeforeChange={(v) => onChange('drop_year_before', v)}
        onAfterChange={(v) => onChange('drop_year_after', v)}
        minYear={minYear}
        maxYear={maxYear}
      />
      {FILTER_CHIP_KEYS.map((key) => {
        const id = `filters-${key.replace(/_/g, '-')}`
        return (
          <div key={key} className="flex flex-col gap-1">
            <Label htmlFor={id}>{strings.settings.filterChipLists[key]}</Label>
            <ChipListEditor
              ariaLabel={strings.settings.filterChipLists[key]}
              inputId={id}
              value={filters[key]}
              onChange={(next) => onChange(key, next)}
              addPlaceholder={strings.settings.filterChipPlaceholders[key]}
            />
          </div>
        )
      })}
    </>
  )
}
