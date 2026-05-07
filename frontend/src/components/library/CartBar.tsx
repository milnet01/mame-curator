import { ChevronDown, ChevronUp, ShoppingCart } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'

interface CartBarProps {
  itemCount: number
  totalSizeBytes: number
  bulkAddTotal: number | null
  expanded: boolean
  onBulkAdd: () => void
  onToggleExpand: () => void
  onDryRun: () => void
  onCopy: () => void
}

function formatGB(bytes: number): string {
  const gb = bytes / 1024 ** 3
  return `${gb.toFixed(1)} GB`
}

export function CartBar({
  itemCount,
  totalSizeBytes,
  bulkAddTotal,
  expanded,
  onBulkAdd,
  onToggleExpand,
  onDryRun,
  onCopy,
}: CartBarProps) {
  const empty = itemCount === 0
  const ChevronIcon = expanded ? ChevronDown : ChevronUp

  return (
    <footer className="sticky bottom-0 z-10 flex items-center justify-between gap-3 border-t bg-background/95 px-4 py-2 backdrop-blur">
      <div className="flex items-center gap-2 text-sm tabular-nums">
        <ShoppingCart className="h-4 w-4" aria-hidden="true" />
        <span className={empty ? 'text-muted-foreground' : 'font-medium'}>
          {empty
            ? strings.library.cart.summaryEmpty
            : strings.library.cart.summary(itemCount, formatGB(totalSizeBytes))}
        </span>
      </div>
      <div className="flex items-center gap-2">
        {bulkAddTotal !== null && (
          <Button variant="outline" onClick={onBulkAdd}>
            {strings.library.cart.bulkAdd(bulkAddTotal)}
          </Button>
        )}
        <Button variant="outline" onClick={onDryRun} disabled={empty}>
          {strings.library.actions.dryRun}
        </Button>
        <Button onClick={onCopy} disabled={empty}>
          {strings.library.actions.copy}
        </Button>
        <Button
          size="icon"
          variant="ghost"
          onClick={onToggleExpand}
          aria-label={
            expanded ? strings.library.cart.collapse : strings.library.cart.expand
          }
        >
          <ChevronIcon className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </footer>
  )
}
