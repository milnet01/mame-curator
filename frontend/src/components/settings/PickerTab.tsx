import { Label } from '@/components/ui/label'
import { ChipListEditor } from '@/components/settings/ChipListEditor'
import { DragReorderList } from '@/components/settings/DragReorderList'
import { PrefSwitch } from '@/components/settings/PrefSwitch'
import { strings } from '@/strings'
import type { AppConfigResponse } from '@/api/types'

type FilterCfg = AppConfigResponse['filters']

const PICKER_CHIP_KEYS = [
  'preferred_genres',
  'preferred_publishers',
  'preferred_developers',
] as const

interface PickerTabProps {
  filters: FilterCfg
  /** Picker prefs are stored on the same FilterConfig server-side
      (design §6.2) so the dispatch goes through the parent's
      filters-onChange. */
  onChange: <K extends keyof FilterCfg>(key: K, value: FilterCfg[K]) => void
}

export function PickerTab({ filters, onChange }: PickerTabProps) {
  return (
    <>
      <PrefSwitch
        id="picker-parent-over-clone"
        label={strings.settings.pickerLabels.prefer_parent_over_clone}
        checked={filters.prefer_parent_over_clone}
        onChange={(v) => onChange('prefer_parent_over_clone', v)}
      />
      <PrefSwitch
        id="picker-good-driver"
        label={strings.settings.pickerLabels.prefer_good_driver}
        checked={filters.prefer_good_driver}
        onChange={(v) => onChange('prefer_good_driver', v)}
      />
      {PICKER_CHIP_KEYS.map((key) => {
        const id = `picker-${key.replace(/_/g, '-')}`
        return (
          <div key={key} className="flex flex-col gap-1">
            <Label htmlFor={id}>{strings.settings.pickerChipLists[key]}</Label>
            <ChipListEditor
              ariaLabel={strings.settings.pickerChipLists[key]}
              inputId={id}
              value={filters[key]}
              onChange={(next) => onChange(key, next)}
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
          items={filters.region_priority}
          onChange={(next) => onChange('region_priority', next)}
        />
      </div>
    </>
  )
}
