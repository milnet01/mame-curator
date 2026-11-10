import { GuideAction } from "@/components/guide/GuideAction";
import { GuideStep } from "@/components/guide/GuideStep";
import type { PictureChoice } from "@/api/types";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { pictureSrc } from "@/lib/pictureSrc";
import { strings } from "@/strings";

/** What happened to a picture choice: every screen after "Which picture?". */
export type PictureOutcome =
  | { kind: "saving" }
  | { kind: "done"; choice: PictureChoice | null }
  | { kind: "unchanged" }
  | { kind: "failed"; error: unknown; retry: () => void };

interface PictureDoneStepProps {
  name: string;
  outcome: PictureOutcome;
  onBack: () => void;
  back: unknown;
}

/**
 * mame-curator-1146 §4.6 step 3 and the screens beside it: done, already in
 * use, saving, and the version half's failure screen.
 */
export function PictureDoneStep({
  name,
  outcome,
  onBack,
  back,
}: PictureDoneStepProps) {
  const fix = strings.guide.fix;
  const exit = { exitLabel: fix.toLibrary, exitState: back };
  switch (outcome.kind) {
    case "saving":
      return (
        <GuideStep heading={fix.savingHeading} {...exit}>
          {null}
        </GuideStep>
      );
    case "done":
      return (
        <GuideStep
          heading={
            outcome.choice
              ? strings.guide.fix.picture.savedHeading
              : strings.guide.fix.picture.clearedHeading
          }
          {...exit}
        >
          <img
            src={pictureSrc({ short_name: name, picture: outcome.choice })}
            alt=""
            className="w-full"
          />
        </GuideStep>
      );
    case "unchanged":
      return (
        <GuideStep
          heading={strings.guide.fix.picture.alreadyUsing}
          onBack={onBack}
          {...exit}
        >
          <p className="text-xl">{fix.nothingChanged}</p>
        </GuideStep>
      );
    case "failed":
      return (
        <GuideStep heading={fix.failedHeading} onBack={onBack} {...exit}>
          <p role="alert" className="text-xl text-destructive">
            {apiErrorMessage(outcome.error)}
          </p>
          <p className="text-xl">{fix.nothingChanged}</p>
          <GuideAction primary onClick={outcome.retry}>
            {fix.tryAgain}
          </GuideAction>
        </GuideStep>
      );
  }
}
