import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { FsBrowser } from "@/components/settings/FsBrowser";
import { useConfig, useConfigPatch } from "@/hooks/useConfig";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";

interface WhereStepProps {
  stepNumber: number;
  stepCount: number;
  onBack: () => void;
  onConfirm: () => void;
}

export function WhereStep({
  stepNumber,
  stepCount,
  onBack,
  onConfirm,
}: WhereStepProps) {
  const config = useConfig();
  const patch = useConfigPatch();
  const queryClient = useQueryClient();
  const [browseOpen, setBrowseOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const paths = config.data?.paths;

  // Through PATCH /api/config, as Settings saves it, so the server applies
  // the same path validation (INV-13).
  const saveFolder = (dest_roms: string) => {
    if (!paths) return;
    setError(null);
    patch.mutate(
      { paths: { ...paths, dest_roms } },
      {
        onSuccess: () => {
          void queryClient.invalidateQueries({ queryKey: ["setup", "check"] });
          void queryClient.invalidateQueries({ queryKey: ["config"] });
        },
        onError: (err) => setError(apiErrorMessage(err)),
      },
    );
  };

  return (
    <GuideStep
      heading={strings.guide.where.heading}
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
      {paths && (
        <>
          <p role="status" className="break-words text-2xl font-medium">
            {paths.dest_roms}
          </p>
          {error && (
            <p role="alert" className="text-xl text-destructive">
              {error}
            </p>
          )}
          <GuideAction primary onClick={onConfirm} disabled={patch.isPending}>
            {strings.guide.where.yes}
          </GuideAction>
          <GuideAction onClick={() => setBrowseOpen(true)}>
            {strings.guide.where.choose}
          </GuideAction>
          {browseOpen && (
            <FsBrowser
              open
              onOpenChange={setBrowseOpen}
              onPick={saveFolder}
              initialPath={paths.dest_roms}
            />
          )}
        </>
      )}
    </GuideStep>
  );
}
