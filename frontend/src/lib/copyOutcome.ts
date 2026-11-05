import type { CopyModalState } from "@/components/library/CopyModal";
import { strings } from "@/strings";

/** How a copy stands, as the user must be told it. */
export type CopyOutcome =
  "active" | "complete" | "partial" | "stopped" | "failed" | "lost";

export function copyOutcome(state: CopyModalState): CopyOutcome {
  // Only OK is complete, and only when nothing was skipped as missing: a
  // missing game or BIOS file is skipped, not failed, so OK alone says nothing.
  if (state.state === "finished") {
    const skipped = Boolean(state.gamesMissing) || Boolean(state.biosMissing);
    return state.finishedStatus === "OK" && !skipped ? "complete" : "partial";
  }
  // Only CANCELLED is the user's own Stop; a crash also ends as job_aborted.
  if (state.state === "aborted") {
    return state.abortReason === "CANCELLED" ? "stopped" : "failed";
  }
  return state.connection === "lost" ? "lost" : "active";
}

/** The words of a role="alert" for this state; empty when nothing is wrong. */
export function copyProblem(state: CopyModalState): string[] {
  switch (copyOutcome(state)) {
    case "partial":
      // A missing game or BIOS is skipped, not failed: OK can carry either.
      return [
        ...(state.finishedStatus !== "OK"
          ? [strings.guide.copying.partial]
          : []),
        ...(state.gamesMissing
          ? [strings.copy.gamesMissing(state.gamesMissing)]
          : []),
        ...(state.biosMissing
          ? [strings.copy.biosMissing(state.biosMissing)]
          : []),
      ];
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
