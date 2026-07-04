import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type { SourceReadinessRow } from '@/api/types'

interface MediaSourceRowProps {
  row: SourceReadinessRow
  onConfigure: (name: string) => void
  onDownloadPack: (name: string) => void
  onToggle: (name: string, next: boolean) => void
  /**
   * mame-curator-1084 — libretro is the baseline the backend registry always
   * re-appends (`MediaSourceRegistry.chain_for`), so its toggle is locked on:
   * removing it from `media.sources` wouldn't take effect.
   */
  locked?: boolean
}

/**
 * P10 chunk 10 / mame-curator-1084 — one row of the Settings → Media source
 * list. Rendered inside DragReorderList's `renderItem` slot for in-chain
 * sources (the arrow reorder buttons sit to the right, provided by the list),
 * and directly below the list for unconfigured (off) sources. Shows a status
 * dot (`data-state`), the source name + covered kinds, an inline
 * disabled-reason line, a chain-membership toggle, and — when disabled and
 * fixable — a Configure (value-paste) or Download-pack (progettoSnaps) button.
 */
export function MediaSourceRow({
  row,
  onConfigure,
  onDownloadPack,
  onToggle,
  locked = false,
}: MediaSourceRowProps) {
  const active = row.enabled
  const showConfigure = row.needs_config && !row.enabled
  const showDownload = row.name === 'progettoSnaps' && !row.enabled
  const inChain = locked || row.in_chain
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-0.5">
      <div className="flex items-center gap-2">
        <span
          data-state={active ? 'active' : 'disabled'}
          aria-hidden="true"
          className={cn(
            'inline-block h-2 w-2 shrink-0 rounded-full',
            active ? 'bg-green-500' : 'bg-muted-foreground/40',
          )}
        />
        <span className="font-medium">{row.name}</span>
        <span className="text-xs text-muted-foreground">
          {active ? strings.settings.mediaSources.statusActive : strings.settings.mediaSources.statusDisabled}
        </span>
        <span className="ml-2 truncate text-xs text-muted-foreground">
          {row.kinds.join(', ')}
        </span>
        {/* Inner controls must not let ArrowUp/Down bubble to the row-level
            reorder handler (DragReorderList <li> onKeyDown). */}
        <div
          className="ml-auto flex shrink-0 items-center gap-2"
          onKeyDown={(e) => e.stopPropagation()}
        >
          {showConfigure && (
            <Button variant="outline" size="sm" onClick={() => onConfigure(row.name)}>
              {strings.settings.mediaSources.configureButton}
            </Button>
          )}
          {showDownload && (
            <Button variant="outline" size="sm" onClick={() => onDownloadPack(row.name)}>
              {strings.settings.mediaSources.downloadPackButton}
            </Button>
          )}
          {locked && (
            <span className="text-xs text-muted-foreground">
              {strings.settings.mediaSources.lockedHint}
            </span>
          )}
          <Switch
            aria-label={strings.settings.mediaSources.toggleAriaLabel(row.name)}
            checked={inChain}
            disabled={locked}
            onCheckedChange={(next) => onToggle(row.name, next)}
          />
        </div>
      </div>
      {row.disabled_reason && (
        <p className="pl-4 text-xs text-muted-foreground">{row.disabled_reason}</p>
      )}
    </div>
  )
}
