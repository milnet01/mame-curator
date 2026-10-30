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
  /** The start has been sent and its answer has not come back. */
  starting: boolean;
}

/** The report in plain words, and whether a copy could work at all (INV-8). */
function readReport({ counts, summary }: DryRunReport) {
  const newGames = counts.new ?? 0;
  const missing = counts.missing_source ?? 0;
  const gap = Number(summary.free_space_gap_bytes ?? 0);
  const notWritable = summary.dest_writable === false;
  const canStart = !notWritable && gap >= 0 && newGames > 0;
  // A missing BIOS is skipped, not failed, so only the rest can be promised.
  const biosMissing = counts.bios_missing_source ?? 0;
  const biosIncluded = (counts.bios ?? 0) - biosMissing;
  const lines = [
    newGames > 0 && strings.guide.check.newGames(newGames),
    newGames === 0 && missing === 0 && strings.guide.check.allCopied,
    (counts.already_copied ?? 0) > 0 &&
      strings.guide.check.alreadyCopied(counts.already_copied),
    missing > 0 && strings.guide.check.missingSource(missing),
    biosIncluded > 0 && strings.guide.check.bios(biosIncluded),
    biosMissing > 0 && strings.guide.check.biosMissing(biosMissing),
    canStart &&
      Boolean(summary.existing_playlist) &&
      strings.guide.check.existingPlaylist,
    notWritable && strings.guide.check.notWritable,
    gap < 0 &&
      strings.guide.check.needsSpace(strings.guide.size(Math.abs(gap))),
  ].filter((line): line is string => typeof line === "string");
  return {
    lines,
    canStart,
    nothingNew: newGames === 0,
  };
}

type Report = ReturnType<typeof readReport>;

/** How the check came out, so "Ready to copy?" never heads a refusal. */
function headingFor(report: Report | null, failed: boolean): string {
  if (report === null) {
    return failed
      ? strings.guide.loadFailed
      : strings.guide.check.loadingHeading;
  }
  if (report.canStart) return strings.guide.check.heading;
  return report.nothingNew
    ? strings.guide.check.nothingNewHeading
    : strings.guide.check.cannotStartHeading;
}

export function CheckStep({
  request,
  stepNumber,
  stepCount,
  onBack,
  onCopyMore,
  onStart,
  starting,
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
      heading={headingFor(report, dryRun.isError)}
      stepNumber={stepNumber}
      stepCount={stepCount}
      // Leaving now would lose the answer, and a failed start with it.
      onBack={starting ? undefined : onBack}
      exitLabel={starting ? undefined : strings.guide.exit}
    >
      {dryRun.isError && (
        <p role="alert" className="text-xl text-destructive">
          {apiErrorMessage(dryRun.error)}
        </p>
      )}
      {/* On the page before the report, or a screen reader would not hear it. */}
      <div role="status" className="flex flex-col gap-3">
        {report?.lines.map((line) => (
          <p key={line} className="text-xl">
            {line}
          </p>
        ))}
        {starting && <p className="text-xl">{strings.guide.check.starting}</p>}
      </div>
      {startError && (
        <p role="alert" className="text-xl text-destructive">
          {startError}
        </p>
      )}
      {report?.canStart && (
        <GuideAction
          primary
          busy={starting}
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
