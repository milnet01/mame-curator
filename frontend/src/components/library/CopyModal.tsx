import { useState } from "react";
import { Link } from "react-router";
import { AbortCopyDialog } from "@/components/library/AbortCopyDialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  copyOutcome,
  copyProblem,
  copyProblemHasActivity,
} from "@/lib/copyOutcome";
import { strings } from "@/strings";
import type { JobState } from "@/api/types";

export interface CopyModalState {
  jobId: string;
  state: JobState;
  filesDone: number;
  filesTotal: number;
  bytesDone: number;
  bytesTotal: number;
  currentFile: string;
  warnings: string[];
  /** job_finished's status, `OK` or `PARTIAL_FAILURE`, once it has arrived. */
  finishedStatus?: string;
  /** job_aborted's reason, once it has arrived. Only CANCELLED is the user's. */
  abortReason?: string;
  /** Set only while the status stream is down. */
  connection?: "reconnecting" | "lost";
  /** Why the last pause, resume or abort failed, in the user's words. */
  controlError?: string;
}

interface CopyModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  state: CopyModalState;
  onPause: () => void;
  onResume: () => void;
  onAbort: (req: { recycle_partial: boolean }) => void;
}

export function CopyModal({
  open,
  onOpenChange,
  state,
  onPause,
  onResume,
  onAbort,
}: CopyModalProps) {
  const [abortOpen, setAbortOpen] = useState(false);

  const outcome = copyOutcome(state);
  const live = outcome === "active";
  const paused = live && state.state === "paused";
  const controllable = live && (state.state === "running" || paused);
  const problem = copyProblem(state);
  const pct =
    state.filesTotal === 0 ? 0 : (state.filesDone / state.filesTotal) * 100;

  return (
    <>
      {/* Nothing reattaches to a job, so closing during a copy would lose
          Pause and Cancel for good: no way to dismiss it until it ends. */}
      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!live) onOpenChange(next);
        }}
      >
        <DialogContent className="max-w-lg" showCloseButton={!live}>
          <DialogHeader>
            <DialogTitle>{strings.copy.modalTitle}</DialogTitle>
          </DialogHeader>

          {/* A lost stream knows nothing current, so it shows no progress. */}
          {outcome !== "lost" && (
            <>
              <Progress
                value={pct}
                aria-label={strings.copy.progressAriaLabel}
              />
              <p className="font-mono text-sm" data-testid="progress-line">
                {/* mame-curator-1103: no total until job_started arrives, so
                    "0 / 0" would read as an empty job. */}
                {state.state === "running" && state.filesTotal === 0
                  ? strings.copy.preparing
                  : strings.copy.progressLine(
                      state.filesDone,
                      state.filesTotal,
                      state.currentFile,
                    )}
              </p>
            </>
          )}

          {/* A crash ends as "aborted" and a lost stream may still say
              "running": neither label is true for them. */}
          {outcome !== "failed" && outcome !== "lost" && (
            <p className="text-xs text-muted-foreground">
              {strings.copy.stateLine(
                strings.copy.sessionState[state.state] ?? state.state,
              )}
            </p>
          )}

          {outcome === "complete" && (
            <p role="status" className="text-sm">
              {strings.guide.copying.finishedHeading}
            </p>
          )}
          {problem.length > 0 && (
            <div role="alert" className="flex flex-col gap-1 text-sm">
              {problem.map((line) => (
                <p key={line} className="break-words">
                  {line}
                </p>
              ))}
              {copyProblemHasActivity(state) && (
                <Link to="/activity" className="underline">
                  {strings.guide.copying.seeWhich}
                </Link>
              )}
            </div>
          )}

          {state.warnings.length > 0 && (
            <ul className="rounded border bg-muted/40 p-2 text-xs">
              {/* FP11 § D9: warnings are append-only via SSE; key by
                  the absolute index of the warning rather than the
                  position in the slice. The slice shifts on every
                  new event, so positional keys forced React to
                  re-mount each <li> on each event — replacing with
                  absolute index keeps DOM identity stable. */}
              {state.warnings.slice(-3).map((w, sliceIndex) => {
                const absoluteIndex = state.warnings.length - 3 + sliceIndex;
                return <li key={absoluteIndex}>{w}</li>;
              })}
            </ul>
          )}

          {/* FP11 § D8: state-machine action row. Settled states get a single
              Done button so the user isn't stranded with a stale Cancel.
              `terminating` shows non-interactive status only. */}
          <div className="flex justify-end gap-2">
            {!live && (
              <Button onClick={() => onOpenChange(false)}>
                {strings.copy.done}
              </Button>
            )}
            {live && state.state === "terminating" && (
              <Button variant="outline" disabled>
                {strings.copy.sessionState.terminating}
              </Button>
            )}
            {controllable && (
              <>
                {/* One button, so focus stays on it when Pause becomes Resume. */}
                <Button
                  variant={paused ? "default" : "outline"}
                  onClick={paused ? onResume : onPause}
                >
                  {paused ? strings.copy.resume : strings.copy.pause}
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => setAbortOpen(true)}
                >
                  {strings.copy.abort}
                </Button>
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <AbortCopyDialog
        open={abortOpen && controllable}
        onOpenChange={setAbortOpen}
        filesDone={state.filesDone}
        onAbort={onAbort}
      />
    </>
  );
}
