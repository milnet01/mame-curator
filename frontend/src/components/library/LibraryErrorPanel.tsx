import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

interface LibraryErrorPanelProps {
  onRetry: () => void
}

/**
 * FP20-I: inline error panel that replaces the LibraryGrid when the games
 * query fails. The global toast (FP20-G) flashes once and dismisses; this
 * panel keeps the failure state visible in the page surface so the user
 * has a clear retry affordance.
 *
 * ``role="alert"`` (not ``status``) — assertive live-region etiquette
 * because the failure interrupts the user's work flow. Retry calls
 * react-query's ``refetch`` which re-runs the failed query.
 */
export function LibraryErrorPanel({ onRetry }: LibraryErrorPanelProps) {
  return (
    <div
      role="alert"
      className="mx-4 my-4 flex flex-col gap-2 rounded border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm"
    >
      <p className="font-medium">{strings.library.loadFailedTitle}</p>
      <p className="text-muted-foreground">{strings.library.loadFailedHint}</p>
      <div>
        <Button variant="outline" size="sm" onClick={onRetry}>
          {strings.common.retry}
        </Button>
      </div>
    </div>
  )
}
