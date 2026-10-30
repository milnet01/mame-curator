import { useState } from "react";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { AbortCopyDialog } from "@/components/library/AbortCopyDialog";
import type { CopyModalState } from "@/components/library/CopyModal";
import { Progress } from "@/components/ui/progress";
import {
  copyOutcome,
  copyProblem,
  copyProblemHasActivity,
} from "@/lib/copyOutcome";
import { strings } from "@/strings";

interface CopyingStepProps {
  state: CopyModalState;
  stepNumber: number;
  stepCount: number;
  onPause: () => void;
  onResume: () => void;
  onAbort: (req: { recycle_partial: boolean }) => void;
  onCopyMore: () => void;
}

export function CopyingStep({
  state,
  stepNumber,
  stepCount,
  onPause,
  onResume,
  onAbort,
  onCopyMore,
}: CopyingStepProps) {
  const [abortOpen, setAbortOpen] = useState(false);

  const outcome = copyOutcome(state);
  const live = outcome === "active";
  const paused = live && state.state === "paused";
  const controllable = live && (state.state === "running" || paused);
  const problem = copyProblem(state);
  const heading = {
    complete: strings.guide.copying.finishedHeading,
    partial: strings.guide.copying.partialHeading,
    stopped: strings.guide.copying.stoppedHeading,
    failed: strings.guide.copying.failedHeading,
    lost: strings.guide.copying.lostHeading,
    active:
      state.state === "terminating"
        ? strings.guide.copying.stoppingHeading
        : strings.guide.copying.heading,
  }[outcome];
  const pct =
    state.filesTotal === 0 ? 0 : (state.filesDone / state.filesTotal) * 100;

  return (
    <GuideStep
      heading={heading}
      stepNumber={stepNumber}
      stepCount={stepCount}
      // User ruling, 2026-10-30: nothing can come back to a paused copy, so
      // Resume and Stop are the only ways on.
      exitLabel={paused ? undefined : strings.guide.exit}
    >
      {/* A lost stream knows nothing current, so it shows no progress. */}
      {outcome !== "lost" && (
        <>
          <Progress
            value={outcome === "complete" ? 100 : pct}
            aria-label={strings.copy.progressAriaLabel}
            className="h-4"
          />
          <p className="break-words text-xl" data-testid="progress-line">
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

      {problem.length > 0 && (
        <div role="alert" className="flex flex-col gap-2 text-xl">
          {problem.map((line) => (
            <p key={line} className="break-words">
              {line}
            </p>
          ))}
          {copyProblemHasActivity(state) && (
            <GuideAction to="/activity">
              {strings.guide.copying.seeWhich}
            </GuideAction>
          )}
        </div>
      )}

      {controllable && (
        <>
          <p role="status" className="text-xl">
            {paused
              ? strings.guide.copying.pausedHint
              : strings.guide.copying.closeHint}
          </p>
          {/* One button, so focus stays on it when Pause becomes Resume. */}
          <GuideAction primary={paused} onClick={paused ? onResume : onPause}>
            {paused ? strings.copy.resume : strings.copy.pause}
          </GuideAction>
          <GuideAction onClick={() => setAbortOpen(true)}>
            {strings.guide.copying.stop}
          </GuideAction>
        </>
      )}
      {live && state.state === "terminating" && (
        <p role="status" className="text-xl">
          {strings.copy.sessionState.terminating}
        </p>
      )}
      {!live && (
        <>
          <GuideAction onClick={onCopyMore}>
            {strings.guide.copying.copyMore}
          </GuideAction>
          <GuideAction to="/">{strings.guide.copying.goToLibrary}</GuideAction>
        </>
      )}

      {/* Below the actions, so a long list cannot push them off the screen. */}
      {state.warnings.length > 0 && (
        <div className="flex flex-col gap-2 text-xl">
          <p role="status">{strings.guide.copying.warningsLead}</p>
          <ul className="list-disc break-words pl-6">
            {state.warnings.map((warning, index) => (
              <li key={index}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <AbortCopyDialog
        open={abortOpen && controllable}
        onOpenChange={setAbortOpen}
        filesDone={state.filesDone}
        onAbort={onAbort}
      />
    </GuideStep>
  );
}
