/**
 * mame-curator-1216 — "Hide compilations?" The answer is a filter the server
 * applies, so it is saved to config, as Settings saves it, before the next
 * step counts the games.
 */
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { ChoiceLabel } from "../settings/SettingsStep";
import { useConfig, useConfigPatch } from "@/hooks/useConfig";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

interface CompilationsStepProps {
  stepNumber: number;
  stepCount: number;
  onBack: () => void;
  onNext: () => void;
}

export function CompilationsStep({
  stepNumber,
  stepCount,
  onBack,
  onNext,
}: CompilationsStepProps) {
  const config = useConfig();
  // quiet: the step moves on or says what went wrong, so no toast repeats it.
  const patch = useConfigPatch({ quiet: true });
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const filters = config.data?.filters;

  const choose = (hide: boolean) => {
    if (!filters) return;
    // Already in use: nothing to save, and no new snapshot.
    if (hide === filters.drop_multigame) {
      onNext();
      return;
    }
    setError(null);
    patch.mutate(
      { filters: { ...filters, drop_multigame: hide } },
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
  const inUse = (hide: boolean) =>
    hide === filters?.drop_multigame ? strings.guide.settings.inUse : undefined;

  return (
    <GuideStep
      heading={strings.guide.compilations.heading}
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
        <>
          <p className="text-xl">{strings.guide.compilations.help}</p>
          {error && (
            <p role="alert" className="text-xl text-destructive">
              {error}
            </p>
          )}
          <GuideAction onClick={() => choose(true)} busy={patch.isPending}>
            <ChoiceLabel
              label={strings.guide.compilations.yes}
              mark={inUse(true)}
            />
          </GuideAction>
          <GuideAction onClick={() => choose(false)} busy={patch.isPending}>
            <ChoiceLabel
              label={strings.guide.compilations.no}
              mark={inUse(false)}
            />
          </GuideAction>
        </>
      )}
    </GuideStep>
  );
}
