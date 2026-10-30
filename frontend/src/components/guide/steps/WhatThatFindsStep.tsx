import { useState } from "react";
import { useNavigate } from "react-router";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { useGames } from "@/hooks/useGames";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import {
  fetchGameNames,
  guideQueryFor,
  type GuideSelection,
} from "@/lib/fetchGameNames";
import { strings } from "@/strings";

interface WhatThatFindsStepProps {
  selection: GuideSelection;
  stepNumber: number;
  stepCount: number;
  onBack: () => void;
  onNames: (names: string[]) => void;
}

export function WhatThatFindsStep({
  selection,
  stepNumber,
  stepCount,
  onBack,
  onNames,
}: WhatThatFindsStepProps) {
  const navigate = useNavigate();
  const query = guideQueryFor(selection);
  const count = useGames({ ...query, page: 1, pageSize: 1 });
  const [progress, setProgress] = useState<[number, number] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // The names are fetched here, so they are the ones the user acts on.
  const copyThese = async () => {
    setError(null);
    setProgress([0, count.data?.total ?? 0]);
    try {
      onNames(
        await fetchGameNames(query, (done, total) =>
          setProgress([done, total]),
        ),
      );
    } catch (err) {
      setError(apiErrorMessage(err));
      setProgress(null);
    }
  };

  const total = count.data?.total;
  const heading =
    total === undefined
      ? strings.guide.finds.loadingHeading
      : strings.guide.finds.heading(
          total,
          strings.guide.size(count.data?.total_bytes ?? 0),
        );

  return (
    <GuideStep
      heading={heading}
      stepNumber={stepNumber}
      stepCount={stepCount}
      onBack={onBack}
      exitLabel={strings.guide.exit}
    >
      {count.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(count.error)}
        </p>
      )}
      {error && (
        <p role="alert" className="text-xl text-destructive">
          {error}
        </p>
      )}
      {progress && (
        <p role="status" className="text-xl">
          {strings.guide.finds.gettingList(progress[0], progress[1])}
        </p>
      )}
      {total !== undefined && total > 0 && (
        <>
          <GuideAction
            primary
            onClick={() => void copyThese()}
            disabled={progress !== null}
          >
            {strings.guide.finds.copyThese}
          </GuideAction>
          <GuideAction
            onClick={() =>
              navigate("/", { state: { guideSelection: selection } })
            }
          >
            {strings.guide.finds.lookThrough}
          </GuideAction>
        </>
      )}
    </GuideStep>
  );
}
