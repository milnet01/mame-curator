import { useEffect, useState } from "react";
import { GuideAction } from "../GuideAction";
import { GuideStep } from "../GuideStep";
import { useDryRun } from "@/hooks/useDryRun";
import { apiErrorMessage } from "@/lib/apiErrorToast";
import { strings } from "@/strings";
import type { CopyJobRequest, DryRunReport } from "@/api/types";

interface CheckStepProps {
  request: CopyJobRequest;
  stepNumber: number;
  stepCount: number;
  onBack: () => void;
  onCopyMore: () => void;
  onStart: (onError: (err: unknown) => void) => void;
}

/** The report in plain words, and whether a copy could work at all (INV-8). */
function readReport({ counts, summary }: DryRunReport) {
  const newGames = counts.new ?? 0;
  const missing = counts.missing_source ?? 0;
  const gap = Number(summary.free_space_gap_bytes ?? 0);
  const notWritable = summary.dest_writable === false;
  const lines = [
    newGames > 0 && strings.guide.check.newGames(newGames),
    newGames === 0 && missing === 0 && strings.guide.check.allCopied,
    (counts.already_copied ?? 0) > 0 &&
      strings.guide.check.alreadyCopied(counts.already_copied),
    missing > 0 && strings.guide.check.missingSource(missing),
    (counts.bios ?? 0) > 0 && strings.guide.check.bios(counts.bios),
    Boolean(summary.existing_playlist) && strings.guide.check.existingPlaylist,
    notWritable && strings.guide.check.notWritable,
    gap < 0 &&
      strings.guide.check.needsSpace(strings.guide.size(Math.abs(gap))),
  ].filter((line): line is string => typeof line === "string");
  return {
    lines,
    canStart: !notWritable && gap >= 0 && newGames > 0,
    nothingNew: newGames === 0,
  };
}

export function CheckStep({
  request,
  stepNumber,
  stepCount,
  onBack,
  onCopyMore,
  onStart,
}: CheckStepProps) {
  const dryRun = useDryRun();
  const { mutate } = dryRun;
  const [startError, setStartError] = useState<string | null>(null);

  useEffect(() => {
    mutate(request);
  }, [mutate, request]);

  const report = dryRun.data ? readReport(dryRun.data) : null;

  return (
    <GuideStep
      heading={
        dryRun.isPending
          ? strings.guide.check.loadingHeading
          : strings.guide.check.heading
      }
      stepNumber={stepNumber}
      stepCount={stepCount}
      onBack={onBack}
      exitLabel={strings.guide.exit}
    >
      {dryRun.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(dryRun.error)}
        </p>
      )}
      {report?.lines.map((line) => (
        <p key={line} className="text-xl">
          {line}
        </p>
      ))}
      {startError && (
        <p role="alert" className="text-xl text-destructive">
          {startError}
        </p>
      )}
      {report?.canStart && (
        <GuideAction
          primary
          onClick={() => {
            setStartError(null);
            onStart((err) => setStartError(apiErrorMessage(err)));
          }}
        >
          {strings.guide.check.start}
        </GuideAction>
      )}
      {report?.nothingNew && (
        <GuideAction onClick={onCopyMore}>
          {strings.guide.copying.copyMore}
        </GuideAction>
      )}
    </GuideStep>
  );
}
