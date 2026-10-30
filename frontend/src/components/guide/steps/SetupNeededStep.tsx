import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { strings } from "@/strings";

/** Games cannot load before setup, so this is the only reachable step. */
export function SetupNeededStep() {
  return (
    <GuideStep
      heading={strings.guide.setup.heading}
      exitLabel={strings.guide.exit}
    >
      <GuideAction to="/settings?tab=paths" primary>
        {strings.guide.setup.openSettings}
      </GuideAction>
    </GuideStep>
  );
}
