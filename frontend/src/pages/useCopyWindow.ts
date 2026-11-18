import { useState } from "react";
import type { CopyModalState } from "@/components/library/CopyModal";
import { copyOutcome } from "@/lib/copyOutcome";

/**
 * mame-curator-1233: whether the Library's copy window shows. The user
 * decided 2026-11-16 that closing it during a copy hides it and the copy goes
 * on; the cart bar's Show copy opens it again. Closing an ended copy clears it.
 */
export function useCopyWindow(state: CopyModalState | null, reset: () => void) {
  const [hiddenJob, setHiddenJob] = useState<string | null>(null);
  const hidden = state !== null && state.jobId === hiddenJob;
  const close = () => {
    if (state && copyOutcome(state) === "active") setHiddenJob(state.jobId);
    else reset();
  };
  const show = () => setHiddenJob(null);
  return { hidden, close, show };
}
