import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import { strings } from '@/strings'

interface BackupTabProps {
  onExport: () => void
  onImport: (file: File) => void
  /** Surfaces export- or import-side errors above the controls. */
  error?: string | null
}

export function BackupTab({ onExport, onImport, error = null }: BackupTabProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [pending, setPending] = useState<File | null>(null)

  const handleFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    if (file) setPending(file)
    // Clear the input so picking the same file twice still fires onChange.
    event.target.value = ''
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        {strings.settings.backupTabBlurb}
      </p>

      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={onExport} variant="outline">
          {strings.settings.backupExportLabel}
        </Button>
        <Button
          onClick={() => inputRef.current?.click()}
          variant="outline"
        >
          {strings.settings.backupImportLabel}
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept="application/json,.json"
          className="sr-only"
          aria-label={strings.settings.backupImportLabel}
          onChange={handleFile}
        />
      </div>

      <p className="text-xs text-muted-foreground">
        {strings.settings.backupWizardForwardLink}
      </p>

      {pending && (
        <ConfirmationDialog
          open
          onOpenChange={(open) => {
            if (!open) setPending(null)
          }}
          title={strings.settings.backupImportConfirmTitle}
          description={strings.settings.backupImportConfirm(pending.name)}
          actionLabel={strings.settings.backupImportActionLabel(pending.name)}
          onConfirm={() => onImport(pending)}
          destructive
        />
      )}
    </div>
  )
}
