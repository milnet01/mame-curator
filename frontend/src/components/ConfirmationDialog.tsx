import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { strings } from "@/strings";

interface ConfirmationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  actionLabel: string;
  onConfirm: () => void;
  destructive?: boolean;
  /** Large words and buttons, for the guide's screens. */
  large?: boolean;
}

/**
 * Action-label values that fail the design § 8 "concrete primary
 * label" rule. Compared case-insensitively + trimmed so `' OK '`
 * sneaks past nothing. The set names every generic affirmation; the
 * caller MUST give a concrete verb-+-target label like "Delete 3
 * files from drive" or "Reset configuration to defaults".
 */
const FORBIDDEN_LABELS_LOWER = new Set([
  "ok",
  "confirm",
  "yes",
  "continue",
  "proceed",
  "submit",
  "done",
  "apply",
  "save",
]);

export function ConfirmationDialog({
  open,
  onOpenChange,
  title,
  description,
  actionLabel,
  onConfirm,
  destructive = true,
  large,
}: ConfirmationDialogProps) {
  // Enforce design §8: destructive-action labels must be concrete (e.g.
  // "Delete 3 files from drive"), never generic. Throw at render time so
  // a regression in any caller fails loudly during dev / tests rather
  // than shipping an "OK" button to users. Case-insensitive + trimmed.
  if (FORBIDDEN_LABELS_LOWER.has(actionLabel.trim().toLowerCase())) {
    throw new Error(
      `ConfirmationDialog: actionLabel must be concrete, not "${actionLabel}". ` +
        'Per design §8, name the verb + target (e.g. "Delete 3 files from drive").',
    );
  }

  const handleConfirm = () => {
    onConfirm();
    onOpenChange(false);
  };

  const largeWords = large ? "text-xl" : undefined;
  const largeButton = large ? "min-h-12 text-xl" : undefined;
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className={largeWords}>{title}</AlertDialogTitle>
          <AlertDialogDescription className={largeWords}>
            {description}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className={largeButton}>
            {strings.common.cancel}
          </AlertDialogCancel>
          <AlertDialogAction
            onClick={handleConfirm}
            className={cn(
              destructive &&
                "bg-destructive text-destructive-foreground hover:bg-destructive/90",
              largeButton,
            )}
          >
            {actionLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
