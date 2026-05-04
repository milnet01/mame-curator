import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import { strings } from '@/strings'
import type { Snapshot } from '@/api/types'

interface SnapshotsTabProps {
  snapshots: readonly Snapshot[]
  loading?: boolean
  error?: string | null
  onRestore: (id: string) => void
}

const FORMAT = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

export function SnapshotsTab({
  snapshots,
  loading = false,
  error = null,
  onRestore,
}: SnapshotsTabProps) {
  const [pending, setPending] = useState<Snapshot | null>(null)

  if (loading) {
    return (
      <p className="text-sm text-muted-foreground">
        {strings.settings.snapshotsLoading}
      </p>
    )
  }
  if (error) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {error}
      </p>
    )
  }
  if (snapshots.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        {strings.settings.snapshotsEmpty}
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-sm font-medium">{strings.settings.snapshotsTitle}</h2>
      <ul className="flex flex-col gap-1">
        {snapshots.map((s) => (
          <li
            key={s.id}
            className="flex items-center justify-between rounded border border-muted px-3 py-2"
          >
            <span className="text-sm">
              <time dateTime={s.ts.toISOString()}>{FORMAT.format(s.ts)}</time>
              {' · '}
              <span className="text-muted-foreground">
                {strings.settings.snapshotItemFiles(s.files.length)}
              </span>
            </span>
            <Button size="sm" variant="outline" onClick={() => setPending(s)}>
              {strings.settings.snapshotRestoreLabel}
            </Button>
          </li>
        ))}
      </ul>

      {pending && (
        <ConfirmationDialog
          open
          onOpenChange={(open) => {
            if (!open) setPending(null)
          }}
          title={strings.settings.snapshotRestoreConfirmTitle}
          description={strings.settings.snapshotRestoreConfirm(
            pending.files.length,
          )}
          actionLabel={strings.settings.snapshotRestoreActionLabel(
            pending.files.length,
          )}
          onConfirm={() => onRestore(pending.id)}
          destructive
        />
      )}
    </div>
  )
}
