import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { strings } from "@/strings";
import type { DryRunReport } from "@/api/types";

interface DryRunModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  report: DryRunReport;
  onConfirm: () => void;
}

// Keys are the server's (api/routes/copy.py dry_run), except bios_included,
// which readCounts works out (mame-curator-1198).
const SECTIONS: Array<{ key: string; label: string }> = [
  { key: "new", label: strings.copy.dryRunSections.new },
  { key: "already_copied", label: strings.copy.dryRunSections.alreadyCopied },
  { key: "missing_source", label: strings.copy.dryRunSections.missingSource },
  { key: "not_in_playlist", label: strings.copy.dryRunSections.notInPlaylist },
  { key: "bios_included", label: strings.copy.dryRunSections.biosIncluded },
];

/** The report's counts, with the BIOS line worked out from the server's
 *  fields: it sends every BIOS needed and how many are missing (copy.py). */
function readCounts({ counts }: DryRunReport): {
  values: Record<string, number>;
  biosMissing: number;
} {
  const biosMissing = counts.bios_missing_source ?? 0;
  return {
    values: { ...counts, bios_included: (counts.bios ?? 0) - biosMissing },
    biosMissing,
  };
}

export function DryRunModal({
  open,
  onOpenChange,
  report,
  onConfirm,
}: DryRunModalProps) {
  const { values, biosMissing } = readCounts(report);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{strings.copy.dryRunTitle}</DialogTitle>
          <DialogDescription>{strings.copy.dryRunHint}</DialogDescription>
        </DialogHeader>

        <ul className="flex flex-col gap-2 text-sm">
          {SECTIONS.map(({ key, label }) => (
            <li
              key={key}
              className="rounded bg-muted/50 px-3 py-2 tabular-nums"
            >
              {(values[key] ?? 0).toLocaleString()} {label}
            </li>
          ))}
        </ul>
        {biosMissing > 0 && (
          <p className="text-sm text-amber-700 dark:text-amber-400">
            {strings.guide.check.biosMissing(biosMissing)}
          </p>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {strings.common.cancel}
          </Button>
          <Button onClick={onConfirm}>{strings.library.actions.copy}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
