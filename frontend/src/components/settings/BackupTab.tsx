import { useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmationDialog } from '@/components/ConfirmationDialog'
import {
  ConfigExportBundleSchema,
  type ConfigExportBundle,
} from '@/api/types'
import { strings } from '@/strings'

// FP13 § B3 — file-size pre-check before `await file.text()`. Real bundles
// are ~10 KB; 5 MB is generous. Stops a multi-hundred-MB JSON paste from
// freezing the main thread on `file.text()` + `JSON.parse`.
const MAX_IMPORT_BYTES = 5 * 1024 * 1024

interface BackupTabProps {
  onExport: () => void
  /** FP13 § B1: parent receives an already-validated bundle, not a raw File.
      Schema + size + JSON-parse gating happens before the destructive
      "Replace settings from <file>" confirmation opens. */
  onImport: (bundle: ConfigExportBundle) => void
  /** Surfaces export- or mutate-side errors from the parent above the
      controls. BackupTab also owns its own validation-error state and
      displays whichever is set (validation wins when both are non-null). */
  error?: string | null
}

export function BackupTab({ onExport, onImport, error = null }: BackupTabProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [pending, setPending] = useState<{
    file: File
    bundle: ConfigExportBundle
  } | null>(null)
  const [validationError, setValidationError] = useState<string | null>(null)

  const handleFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    // Clear the input so picking the same file twice still fires onChange.
    event.target.value = ''
    setValidationError(null)
    if (!file) return
    if (file.size > MAX_IMPORT_BYTES) {
      setValidationError(strings.settings.backupImportTooLarge)
      return
    }
    let parsed: unknown
    try {
      parsed = JSON.parse(await file.text())
    } catch {
      setValidationError(strings.settings.backupImportInvalidJson)
      return
    }
    const result = ConfigExportBundleSchema.safeParse(parsed)
    if (!result.success) {
      setValidationError(strings.settings.backupImportInvalidShape)
      return
    }
    setPending({ file, bundle: result.data })
  }

  const displayError = validationError ?? error

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        {strings.settings.backupTabBlurb}
      </p>

      {displayError && (
        <p role="alert" className="text-sm text-destructive">
          {displayError}
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
          description={strings.settings.backupImportConfirm(pending.file.name)}
          actionLabel={strings.settings.backupImportActionLabel(pending.file.name)}
          onConfirm={() => onImport(pending.bundle)}
          destructive
        />
      )}
    </div>
  )
}
