import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PrefSwitch } from '@/components/settings/PrefSwitch'
import { strings } from '@/strings'
import type { AppConfigResponse, AppUpdateInfo } from '@/api/types'

type UpdatesCfg = AppConfigResponse['updates']
type UpdateChannel = UpdatesCfg['channel']

const UPDATE_CHANNEL_VALUES: readonly UpdateChannel[] = ['stable', 'dev']

interface UpdatesTabProps {
  updates: UpdatesCfg
  onChange: <K extends keyof UpdatesCfg>(key: K, value: UpdatesCfg[K]) => void
  /** R36 update-check payload — when present, drives the Updates banner. */
  updateInfo?: AppUpdateInfo
}

export function UpdatesTab({ updates, onChange, updateInfo }: UpdatesTabProps) {
  return (
    <>
      {/* FP11 § B3: R36 read-only banner — design §8 + spec § 147-150 demand
          it. Phase 7 will swap this for the apply-update flow. */}
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
            : strings.settings.banners.updateCurrent(updateInfo.current_version)}
        </p>
      )}
      <div className="flex items-center justify-between">
        <Label htmlFor="updates-channel">
          {strings.settings.updatesLabels.channel}
        </Label>
        <Select
          value={updates.channel}
          onValueChange={(v) => onChange('channel', v as UpdateChannel)}
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
        checked={updates.check_on_startup}
        onChange={(v) => onChange('check_on_startup', v)}
      />
      <PrefSwitch
        id="updates-ini-check-on-startup"
        label={strings.settings.updatesLabels.ini_check_on_startup}
        checked={updates.ini_check_on_startup}
        onChange={(v) => onChange('ini_check_on_startup', v)}
      />
    </>
  )
}
