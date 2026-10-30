import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { strings } from "@/strings";

interface WhichGamesStepProps {
  onEverything: () => void;
  onGroup: () => void;
  onType: () => void;
}

export function WhichGamesStep({
  onEverything,
  onGroup,
  onType,
}: WhichGamesStepProps) {
  return (
    <GuideStep
      heading={strings.guide.which.heading}
      stepNumber={1}
      exitLabel={strings.guide.exit}
    >
      <GuideAction onClick={onEverything}>
        {strings.guide.which.everything}
      </GuideAction>
      <GuideAction onClick={onGroup}>{strings.guide.which.group}</GuideAction>
      <GuideAction onClick={onType}>{strings.guide.which.type}</GuideAction>
    </GuideStep>
  );
}
