import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { strings } from '@/strings'
import type { JobState, AppendDecisionKind } from '@/api/types'

export interface CopyModalConflict {
  short_name: string
  existing: string
}

export interface CopyModalState {
  jobId: string
  state: JobState
  filesDone: number
  filesTotal: number
  bytesDone: number
  bytesTotal: number
  currentFile: string
  warnings: string[]
  conflict: CopyModalConflict | null
}

interface CopyModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  state: CopyModalState
  onPause: () => void
  onResume: () => void
  onAbort: (req: { recycle_partial: boolean }) => void
  onResolveConflict: (req: { kind: AppendDecisionKind; replaces: string }) => void
}

export function CopyModal({
  open,
  onOpenChange,
  state,
  onPause,
  onResume,
  onAbort,
  onResolveConflict,
}: CopyModalProps) {
  const [abortOpen, setAbortOpen] = useState(false)

  const pct = state.filesTotal === 0 ? 0 : (state.filesDone / state.filesTotal) * 100

  const handleResolve = (kind: AppendDecisionKind) => {
    if (!state.conflict) return
    onResolveConflict({ kind, replaces: state.conflict.existing })
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{strings.copy.modalTitle}</DialogTitle>
          </DialogHeader>

          <Progress value={pct} aria-label="Copy progress" />
          <p className="font-mono text-sm" data-testid="progress-line">
            {strings.copy.progressLine(state.filesDone, state.filesTotal, state.currentFile)}
          </p>

          <p className="text-xs text-muted-foreground">
            State: {strings.copy.sessionState[state.state] ?? state.state}
          </p>

          {state.warnings.length > 0 && (
            <ul className="rounded border bg-muted/40 p-2 text-xs">
              {state.warnings.slice(-3).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}

          {state.conflict && (
            <div
              role="region"
              aria-label="Existing playlist conflict"
              className="flex flex-col gap-2 rounded border border-destructive/40 bg-destructive/10 p-3"
            >
              <p className="text-sm font-semibold">
                {strings.copy.conflictTitle}
              </p>
              <p className="text-xs">
                {state.conflict.short_name} would replace {state.conflict.existing}.
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleResolve('KEEP_EXISTING')}
                >
                  {strings.copy.conflictKeepExisting}
                </Button>
                <Button size="sm" onClick={() => handleResolve('REPLACE')}>
                  {strings.copy.conflictReplace}
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleResolve('REPLACE_AND_RECYCLE')}
                >
                  {strings.copy.conflictReplaceAndRecycle}
                </Button>
              </div>
            </div>
          )}

          <div className="flex justify-end gap-2">
            {state.state === 'paused' ? (
              <Button onClick={onResume}>{strings.copy.resume}</Button>
            ) : (
              <Button
                variant="outline"
                onClick={onPause}
                disabled={state.state !== 'running'}
              >
                {strings.copy.pause}
              </Button>
            )}
            <Button variant="destructive" onClick={() => setAbortOpen(true)}>
              {strings.copy.abort}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/*
        FP11 § A3: design §9 mandates "Cancel asks whether to keep
        already-copied files or remove them." A single
        ConfirmationDialog is single-action and traps the user on
        whichever path the action label names. Use a dedicated
        two-action prompt so both `recycle_partial=true` and
        `recycle_partial=false` are reachable.
      */}
      <Dialog open={abortOpen} onOpenChange={setAbortOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{strings.copy.abort}</DialogTitle>
            <DialogDescription>
              {strings.copy.abortConfirm(state.filesDone > 0)}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-col gap-2 sm:flex-row">
            <Button variant="outline" onClick={() => setAbortOpen(false)}>
              {strings.common.cancel}
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                onAbort({ recycle_partial: false })
                setAbortOpen(false)
              }}
            >
              {strings.copy.abortKeepFiles}
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                onAbort({ recycle_partial: true })
                setAbortOpen(false)
              }}
            >
              {strings.copy.abortRecycleFiles}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
