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

const SECTIONS: Array<{ key: string; label: string }> = [
  { key: "new", label: "new" },
  { key: "replace", label: "replace" },
  { key: "skip", label: "skip" },
  { key: "bios_included", label: "BIOS included" },
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
              className="flex items-center justify-between rounded bg-muted/50 px-3 py-2"
            >
              <span className="capitalize">{label}</span>
              <span className="font-mono tabular-nums">
                {(values[key] ?? 0).toLocaleString()} {label}
              </span>
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
            Cancel
          </Button>
          <Button onClick={onConfirm}>{strings.library.actions.copy}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
