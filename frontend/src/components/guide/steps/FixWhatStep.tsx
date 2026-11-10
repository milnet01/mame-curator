import { GuideAction } from "@/components/guide/GuideAction";
import { GuideStep } from "@/components/guide/GuideStep";
import { strings } from "@/strings";

interface FixWhatStepProps {
  onVersion: () => void;
  onPicture: () => void;
  /** Router state the way out carries: the Library card to focus. */
  back: unknown;
}

/**
 * mame-curator-1146 §4.6 step 1: what to fix, for a game with several
 * versions. A game with one version opens at the picture question instead.
 */
export function FixWhatStep({ onVersion, onPicture, back }: FixWhatStepProps) {
  return (
    <GuideStep
      heading={strings.guide.fix.picture.whatHeading}
      exitLabel={strings.guide.fix.toLibrary}
      exitState={back}
    >
      <GuideAction onClick={onVersion}>
        {strings.guide.fix.picture.whatVersion}
      </GuideAction>
      <GuideAction onClick={onPicture}>
        {strings.guide.fix.picture.whatPicture}
      </GuideAction>
    </GuideStep>
  );
}
