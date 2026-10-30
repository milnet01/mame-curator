import type { CopyModalState } from "@/components/library/CopyModal";
import { strings } from "@/strings";

/** How a copy stands, as the user must be told it. */
export type CopyOutcome =
  "active" | "complete" | "partial" | "stopped" | "failed" | "lost";

export function copyOutcome(state: CopyModalState): CopyOutcome {
  // Only OK is complete: anything else may have left games uncopied.
  if (state.state === "finished") {
    return state.finishedStatus === "OK" ? "complete" : "partial";
  }
  // Only CANCELLED is the user's own Stop; a crash also ends as job_aborted.
  if (state.state === "aborted") {
    return state.abortReason === "CANCELLED" ? "stopped" : "failed";
  }
  return state.connection === "lost" ? "lost" : "active";
}

/** The words of a role="alert" for this state; empty when nothing is wrong. */
export function copyProblem(state: CopyModalState): string[] {
  // A missing BIOS is skipped, not failed, so even a job that ends OK has it.
  const biosMissing = state.biosMissing
    ? [strings.copy.biosMissing(state.biosMissing)]
    : [];
  switch (copyOutcome(state)) {
    case "complete":
      return biosMissing;
    case "partial":
      return [strings.guide.copying.partial, ...biosMissing];
    case "failed":
      return [
        strings.copy.failed,
        ...(state.abortReason
          ? [strings.copy.failedDetail(state.abortReason)]
          : []),
      ];
    case "lost":
      return [strings.copy.lost];
    case "active":
      return [
        ...(state.connection === "reconnecting"
          ? [strings.copy.reconnecting]
          : []),
        ...(state.controlError ? [state.controlError] : []),
      ];
    default:
      return [];
  }
}

/** Whether Activity can say more about this state's problem. */
export function copyProblemHasActivity(state: CopyModalState): boolean {
  return ["partial", "failed", "lost"].includes(copyOutcome(state));
}
