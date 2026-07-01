import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { strings } from '@/strings'
import type { SourceReadinessRow } from '@/api/types'

interface MediaSourceRowProps {
  row: SourceReadinessRow
  onConfigure: (name: string) => void
  onDownloadPack: (name: string) => void
}

/**
 * P10 chunk 10 — one row of the Settings → Media source list. Rendered inside
 * DragReorderList's `renderItem` slot (the arrow reorder buttons sit to the
 * right, provided by the list). Shows a status dot (`data-state`), the source
 * name + covered kinds, an inline disabled-reason line, and — when disabled and
 * fixable — a Configure (value-paste) or Download-pack (progettoSnaps) button.
 */
export function MediaSourceRow({ row, onConfigure, onDownloadPack }: MediaSourceRowProps) {
  const active = row.enabled
  const showConfigure = row.needs_config && !row.enabled
  const showDownload = row.name === 'progettoSnaps' && !row.enabled
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
        {(showConfigure || showDownload) && (
          // Inner controls must not let ArrowUp/Down bubble to the row-level
          // reorder handler (DragReorderList <li> onKeyDown).
          <div className="ml-auto flex shrink-0 gap-1" onKeyDown={(e) => e.stopPropagation()}>
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
          </div>
        )}
      </div>
      {row.disabled_reason && (
        <p className="pl-4 text-xs text-muted-foreground">{row.disabled_reason}</p>
      )}
    </div>
  )
}
