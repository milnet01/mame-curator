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
import { strings } from "@/strings";

interface AbortCopyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  filesDone: number;
  onAbort: (req: { recycle_partial: boolean }) => void;
}

/**
 * FP11 § A3: design §9 mandates "Cancel asks whether to keep already-copied
 * files or remove them." A single ConfirmationDialog is single-action and
 * traps the user on whichever path the action label names. Use a dedicated
 * two-action prompt so both `recycle_partial=true` and
 * `recycle_partial=false` are reachable.
 */
export function AbortCopyDialog({
  open,
  onOpenChange,
  filesDone,
  onAbort,
}: AbortCopyDialogProps) {
  const recyclable = filesDone > 0;
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{strings.copy.abortTitle}</AlertDialogTitle>
          <AlertDialogDescription>
            {strings.copy.abortConfirm(recyclable)}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>{strings.copy.keepCopying}</AlertDialogCancel>
          {recyclable ? (
            <>
              <AlertDialogAction
                variant="outline"
                onClick={() => onAbort({ recycle_partial: false })}
              >
                {strings.copy.abortKeepFiles}
              </AlertDialogAction>
              <AlertDialogAction
                variant="destructive"
                onClick={() => onAbort({ recycle_partial: true })}
              >
                {strings.copy.abortRecycleFiles}
              </AlertDialogAction>
            </>
          ) : (
            <AlertDialogAction
              variant="destructive"
              onClick={() => onAbort({ recycle_partial: false })}
            >
              {strings.copy.abortNothingCopied}
            </AlertDialogAction>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
