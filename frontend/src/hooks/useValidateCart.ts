import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import {
  SetupCheckSchema,
  ValidateResponseSchema,
  type SetupCheck,
  type ValidateRequest,
  type ValidateResponse,
} from "@/api/types";

export interface ValidateCartResult extends ValidateResponse {
  /** No game list is loaded, so `missing` says nothing about the cart. */
  setupRequired: boolean;
}

/**
 * P15 § 5.1 — POST /api/games/validate.
 *
 * Splits cart shortnames into {existing, missing} via O(1) lookup
 * against world.machines on the backend. Called pre-Copy: orphaned
 * items are dropped with a single toast and CopyModal opens with
 * the surviving set.
 *
 * mame-curator-1183: before anything counts as orphaned, ask whether a game
 * list is loaded at all. Asked afresh, because the app may have restarted since
 * the page loaded. If that check fails the whole call fails, so nothing is
 * dropped on a guess.
 */
export function useValidateCart() {
  return useMutation({
    mutationFn: async (req: ValidateRequest): Promise<ValidateCartResult> => {
      const reply = await apiRequest<ValidateResponse>(
        "/api/games/validate",
        ValidateResponseSchema,
        {
          method: "POST",
          body: req,
        },
      );
      if (reply.missing.length === 0) {
        return { ...reply, setupRequired: false };
      }
      const check = await apiRequest<SetupCheck>(
        "/api/setup/check",
        SetupCheckSchema,
      );
      return { ...reply, setupRequired: check.setup_required };
    },
  });
}
