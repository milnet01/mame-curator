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
  // quiet: this step says the outcome itself, so no toast repeats it.
  const patch = useConfigPatch({ quiet: true });
  const queryClient = useQueryClient();
  const [browseOpen, setBrowseOpen] = useState(false);
  const [focusKey, setFocusKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const paths = config.data?.paths;

  // Through PATCH /api/config, as Settings saves it, so the server applies
  // the same path validation (INV-13). As in the wizard, a choice moves focus
  // to the heading, and Cancel leaves it to the picker (mame-curator-1206).
  const saveFolder = (dest_roms: string) => {
    setFocusKey((key) => key + 1);
    if (!paths) return;
    // mame-curator-1145 INV-11: the server also refuses it, by resolved path.
    if (dest_roms === paths.source_roms) {
      setError(strings.guide.setup.sameFolder);
      return;
    }
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
      focusKey={focusKey}
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
          <GuideAction primary onClick={onConfirm} busy={patch.isPending}>
            {strings.guide.where.yes}
          </GuideAction>
          <GuideAction onClick={() => setBrowseOpen(true)}>
            {strings.guide.where.choose}
          </GuideAction>
          {browseOpen && (
            <FsBrowser
              open
              large
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
