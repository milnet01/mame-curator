import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import { toastApiError } from "@/lib/apiErrorToast";
import {
  AlternativesSchema,
  LaunchResponseSchema,
  OverridesViewSchema,
  type Alternatives,
  type LaunchResponse,
  type OverridePostRequest,
  type OverridesView,
} from "@/api/types";
import { useApiQuery } from "./useApi";

const KEY = (shortName: string) => ["alternatives", shortName] as const;

/**
 * Fetch the parent + clones group for ``shortName``. The endpoint returns
 * an empty ``items`` array when the game has no alternative versions —
 * the Drawer renders a single-row state in that case.
 *
 * Keyed by short_name so switching between games invalidates correctly.
 */
export function useAlternatives(shortName: string | null) {
  return useApiQuery<Alternatives>(
    KEY(shortName ?? ""),
    `/api/games/${encodeURIComponent(shortName ?? "")}/alternatives`,
    AlternativesSchema,
    { enabled: shortName !== null },
  );
}

/**
 * POST a manual override (parent → winner). Invalidates the games listing
 * + the family lists so the UI re-renders with the picked winner. A caller
 * reports failure through ``mutate``'s ``onError`` (mame-curator-1195).
 */
export function useOverride() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: OverridePostRequest) =>
      apiRequest<OverridesView>("/api/overrides", OverridesViewSchema, {
        method: "POST",
        body: req,
      }),
    // Returned, so a caller's onSuccess runs once the page shows the choice.
    onSuccess: () =>
      Promise.all([
        qc.invalidateQueries({ queryKey: ["games"] }),
        // Every version's family list: any of them may be the next one opened.
        qc.invalidateQueries({ queryKey: ["alternatives"] }),
      ]),
    // No onError here: each caller says a failure its own way, and the
    // version guide says it on screen (mame-curator-1195).
  });
}

/**
 * FP19: spawn RetroArch with the given game's ROM. Returns the spawned
 * pid + argv on success; the API surfaces 422 if RetroArch isn't
 * configured or 404 if the ROM file doesn't exist on disk. FP21-R:
 * ``toastApiError`` baked into the hook so all call-sites get the
 * friendly byCode-mapped copy out of the box.
 */
export function useLaunchGame() {
  return useMutation({
    mutationFn: (shortName: string) =>
      apiRequest<LaunchResponse>(
        `/api/games/${encodeURIComponent(shortName)}/launch`,
        LaunchResponseSchema,
        { method: "POST" },
      ),
    onError: toastApiError,
  });
}
