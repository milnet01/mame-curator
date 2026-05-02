import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { strings } from '@/strings'
import type { DryRunReport } from '@/api/types'

interface DryRunModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  report: DryRunReport
  onConfirm: () => void
}

const SECTIONS: Array<{ key: string; label: string }> = [
  { key: 'new', label: 'new' },
  { key: 'replace', label: 'replace' },
  { key: 'skip', label: 'skip' },
  { key: 'bios_included', label: 'BIOS included' },
]

export function DryRunModal({
  open,
  onOpenChange,
  report,
  onConfirm,
}: DryRunModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{strings.copy.dryRunTitle}</DialogTitle>
          <DialogDescription>{strings.copy.dryRunHint}</DialogDescription>
        </DialogHeader>

        <ul className="flex flex-col gap-2 text-sm">
          {SECTIONS.map(({ key, label }) => (
            <li
              key={key}
              className="flex items-center justify-between rounded bg-muted/50 px-3 py-2"
            >
              <span className="capitalize">{label}</span>
              <span className="font-mono tabular-nums">
                {(report.counts[key] ?? 0).toLocaleString()} {label}
              </span>
            </li>
          ))}
        </ul>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={onConfirm}>{strings.library.actions.copy}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
