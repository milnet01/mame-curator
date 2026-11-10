/**
 * mame-curator-1217 — "Which languages can you read?" Like "Hide
 * compilations?", the answer is a filter the server applies, so it is saved
 * to config before the next step counts the games.
 */
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { GuideStep } from "../GuideStep";
import { LanguagePicker } from "../LanguagePicker";
import { useConfig, useConfigPatch } from "@/hooks/useConfig";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { sameLanguages } from "@/lib/languages";
import { strings } from "@/strings";

interface LanguagesStepProps {
  stepNumber: number;
  stepCount: number;
  onBack: () => void;
  onNext: () => void;
}

export function LanguagesStep({
  stepNumber,
  stepCount,
  onBack,
  onNext,
}: LanguagesStepProps) {
  const config = useConfig();
  // quiet: the step moves on or says what went wrong, so no toast repeats it.
  const patch = useConfigPatch({ quiet: true });
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const filters = config.data?.filters;

  const save = (next: string[]) => {
    if (!filters) return;
    // Already in use: nothing to save, and no new snapshot.
    if (sameLanguages(next, filters.keep_languages)) {
      onNext();
      return;
    }
    setError(null);
    patch.mutate(
      { filters: { ...filters, keep_languages: next } },
      {
        onSuccess: () => {
          // The server filtered again, so a count read before is stale.
          void queryClient.invalidateQueries({ queryKey: ["games"] });
          onNext();
        },
        onError: (err) => setError(apiErrorMessage(err)),
      },
    );
  };

  return (
    <GuideStep
      heading={strings.guide.languages.heading}
      stepNumber={stepNumber}
      stepCount={stepCount}
      onBack={onBack}
      exitLabel={strings.guide.exit}
    >
      {config.isPending && <p className="text-xl">{strings.guide.loading}</p>}
      {config.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(config.error)}
        </p>
      )}
      {filters && (
        <LanguagePicker
          current={filters.keep_languages}
          busy={patch.isPending}
          error={error}
          onSave={save}
        />
      )}
    </GuideStep>
  );
}
