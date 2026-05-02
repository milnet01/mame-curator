import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

interface ActionBarProps {
  gameCount: number
  totalSizeBytes: number
  biosDepCount: number
  onDryRun: () => void
  onCopy: () => void
}

function formatGB(bytes: number): string {
  const gb = bytes / (1024 ** 3)
  return `${gb.toFixed(1)} GB`
}

export function ActionBar({
  gameCount,
  totalSizeBytes,
  biosDepCount,
  onDryRun,
  onCopy,
}: ActionBarProps) {
  const empty = gameCount === 0
  return (
    <footer className="sticky bottom-0 z-10 flex items-center justify-between gap-3 border-t bg-background/95 px-4 py-2 backdrop-blur">
      <p className="text-sm tabular-nums text-muted-foreground">
        {strings.library.countSummary(gameCount, formatGB(totalSizeBytes), biosDepCount)}
      </p>
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={onDryRun} disabled={empty}>
          {strings.library.actions.dryRun}
        </Button>
        <Button onClick={onCopy} disabled={empty}>
          {strings.library.actions.copy}
        </Button>
      </div>
    </footer>
  )
}
