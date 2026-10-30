/**
 * mame-curator-1144 — the guide: one question per screen, from "what do you
 * want?" to a finished copy. See docs/specs/mame-curator-1144-guided-library.md.
 * It never reads or writes the cart, so a half-built cart survives a run.
 */
import { useEffect, useMemo, useState } from "react";
import { GuideStep } from "@/components/guide/GuideStep";
import { CheckStep } from "@/components/guide/steps/CheckStep";
import {
  ChooseGroupStep,
  ChooseTypeStep,
} from "@/components/guide/steps/ChooseGroupStep";
import { CopyingStep } from "@/components/guide/steps/CopyingStep";
import { SetupWizard } from "@/components/guide/steps/SetupWizard";
import { WhatThatFindsStep } from "@/components/guide/steps/WhatThatFindsStep";
import { WhereStep } from "@/components/guide/steps/WhereStep";
import { WhichGamesStep } from "@/components/guide/steps/WhichGamesStep";
import { useCopySession } from "@/hooks/useCopySession";
import { useSetupCheck } from "@/hooks/useSetupCheck";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import type { GuideSelection } from "@/lib/fetchGameNames";
import { markGuideSeen } from "@/lib/guideState";
import { strings } from "@/strings";
import type { CopyJobRequest } from "@/api/types";

type Step = "which" | "group" | "type" | "finds" | "where" | "check";

/** "Every game" skips the group step, which moves every later step up one. */
function stepNumbers(selection: GuideSelection | null) {
  const skipped = selection?.kind === "everything" ? 1 : 0;
  return {
    stepCount: 6 - skipped,
    group: 2,
    finds: 3 - skipped,
    where: 4 - skipped,
    check: 5 - skipped,
    copying: 6 - skipped,
  };
}

function GuideSteps() {
  const copySession = useCopySession();
  const [step, setStep] = useState<Step>("which");
  const [selection, setSelection] = useState<GuideSelection | null>(null);
  const [names, setNames] = useState<string[]>([]);

  // Memoised so CheckStep's dry run runs once per list, not once per render.
  const request = useMemo<CopyJobRequest>(
    () => ({
      selected_names: names,
      conflict_strategy: "APPEND",
      append_decisions: {},
    }),
    [names],
  );

  const numbers = stepNumbers(selection);
  const backFromFinds = () => {
    if (selection?.kind === "tile") setStep("group");
    else if (selection?.kind === "genre") setStep("type");
    else {
      // Back past "every game" unchooses it, so the step total is right again.
      setSelection(null);
      setStep("which");
    }
  };
  const startOver = () => {
    copySession.reset();
    setSelection(null);
    setNames([]);
    setStep("which");
  };
  const choose = (next: GuideSelection) => {
    setSelection(next);
    setStep("finds");
  };

  if (copySession.state) {
    return (
      <CopyingStep
        state={copySession.state}
        stepNumber={numbers.copying}
        stepCount={numbers.stepCount}
        onPause={() => copySession.pause()}
        onResume={() => copySession.resume()}
        onAbort={(req) => copySession.abort(req)}
        onCopyMore={startOver}
      />
    );
  }

  switch (step) {
    case "which":
      return (
        <WhichGamesStep
          onEverything={() => choose({ kind: "everything" })}
          onGroup={() => setStep("group")}
          onType={() => setStep("type")}
        />
      );
    case "group":
      return (
        <ChooseGroupStep
          stepNumber={numbers.group}
          stepCount={numbers.stepCount}
          onBack={() => setStep("which")}
          onChoose={(id) => choose({ kind: "tile", id })}
        />
      );
    case "type":
      return (
        <ChooseTypeStep
          stepNumber={numbers.group}
          stepCount={numbers.stepCount}
          onBack={() => setStep("which")}
          onChoose={(genre) => choose({ kind: "genre", genre })}
        />
      );
    case "finds":
      return (
        <WhatThatFindsStep
          selection={selection ?? { kind: "everything" }}
          stepNumber={numbers.finds}
          stepCount={numbers.stepCount}
          onBack={backFromFinds}
          onNames={(found) => {
            setNames(found);
            setStep("where");
          }}
        />
      );
    case "where":
      return (
        <WhereStep
          stepNumber={numbers.where}
          stepCount={numbers.stepCount}
          onBack={() => setStep("finds")}
          onConfirm={() => setStep("check")}
        />
      );
    case "check":
      return (
        <CheckStep
          request={request}
          stepNumber={numbers.check}
          stepCount={numbers.stepCount}
          onBack={() => setStep("where")}
          onCopyMore={startOver}
          onStart={(onError) => copySession.start(request, { onError })}
          starting={copySession.isStarting}
        />
      );
  }
}

export function GuidePage() {
  const setupCheck = useSetupCheck();
  const setupRequired = setupCheck.data?.setup_required;

  // Only once games can load, so the guide opens by itself after setup too.
  useEffect(() => {
    if (setupRequired === false) markGuideSeen();
  }, [setupRequired]);

  if (setupRequired === true) return <SetupWizard />;
  if (setupRequired === false) return <GuideSteps />;
  return (
    <GuideStep
      heading={
        setupCheck.isError ? strings.guide.loadFailed : strings.guide.loading
      }
      exitLabel={strings.guide.exit}
    >
      {setupCheck.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(setupCheck.error)}
        </p>
      )}
    </GuideStep>
  );
}
