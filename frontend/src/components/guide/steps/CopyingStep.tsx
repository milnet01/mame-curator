import { useState } from "react";
import { Link } from "react-router";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { AbortCopyDialog } from "@/components/library/AbortCopyDialog";
import type { CopyModalState } from "@/components/library/CopyModal";
import { Progress } from "@/components/ui/progress";
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

  const finished = state.state === "finished";
  const aborted = state.state === "aborted";
  // Only OK is complete: anything else may have left games uncopied.
  const complete = finished && state.finishedStatus === "OK";
  const heading = complete
    ? strings.guide.copying.finishedHeading
    : finished
      ? strings.guide.copying.partialHeading
      : aborted
        ? strings.guide.copying.stoppedHeading
        : strings.guide.copying.heading;
  const pct =
    state.filesTotal === 0 ? 0 : (state.filesDone / state.filesTotal) * 100;

  return (
    <GuideStep
      heading={heading}
      stepNumber={stepNumber}
      stepCount={stepCount}
      exitLabel={strings.guide.exit}
    >
      <Progress
        value={complete ? 100 : pct}
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

      {finished && !complete && (
        <div role="alert" className="flex flex-col gap-2 text-xl">
          <p>{strings.guide.copying.partial}</p>
          <Link to="/activity" className="underline">
            {strings.guide.copying.seeWhich}
          </Link>
        </div>
      )}

      {state.state === "running" && (
        <>
          <p className="text-xl">{strings.guide.copying.closeHint}</p>
          <GuideAction onClick={onPause}>{strings.copy.pause}</GuideAction>
        </>
      )}
      {state.state === "paused" && (
        <>
          <p className="text-xl">{strings.guide.copying.pausedHint}</p>
          <GuideAction primary onClick={onResume}>
            {strings.copy.resume}
          </GuideAction>
        </>
      )}
      {(state.state === "running" || state.state === "paused") && (
        <GuideAction onClick={() => setAbortOpen(true)}>
          {strings.copy.abort}
        </GuideAction>
      )}
      {state.state === "terminating" && (
        <p role="status" className="text-xl">
          {strings.copy.sessionState.terminating}
        </p>
      )}
      {(finished || aborted) && (
        <>
          <GuideAction onClick={onCopyMore}>
            {strings.guide.copying.copyMore}
          </GuideAction>
          <GuideAction to="/">{strings.guide.copying.goToLibrary}</GuideAction>
        </>
      )}

      <AbortCopyDialog
        open={abortOpen}
        onOpenChange={setAbortOpen}
        filesDone={state.filesDone}
        onAbort={onAbort}
      />
    </GuideStep>
  );
}
