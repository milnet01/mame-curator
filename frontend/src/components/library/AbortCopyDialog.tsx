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
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{strings.copy.abort}</DialogTitle>
          <DialogDescription>
            {strings.copy.abortConfirm(filesDone > 0)}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="flex-col gap-2 sm:flex-row">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {strings.common.cancel}
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              onAbort({ recycle_partial: false });
              onOpenChange(false);
            }}
          >
            {strings.copy.abortKeepFiles}
          </Button>
          <Button
            variant="destructive"
            onClick={() => {
              onAbort({ recycle_partial: true });
              onOpenChange(false);
            }}
          >
            {strings.copy.abortRecycleFiles}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
