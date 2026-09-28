import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import {
  IniPreviewSchema,
  UpdateApplyResultSchema,
  UpdatesCheckSchema,
  type UpdatesCheck,
} from "@/api/types";
import { toastApiError } from "@/lib/apiErrorToast";
import { useApiQuery } from "./useApi";

const CHECK_KEY = ["updates", "check"] as const;

/**
 * GET /api/updates/check (mame-curator-1010 §4.2). The server caches the
 * GitHub answer for an hour, so this stays cheap however often it runs.
 */
export function useUpdatesCheck(enabled = true) {
  return useApiQuery<UpdatesCheck>(
    CHECK_KEY,
    "/api/updates/check",
    UpdatesCheckSchema,
    { enabled, staleTime: 5 * 60_000 },
  );
}

/** "Check now": bypasses the server's hour-long cache. */
export function useUpdatesRefresh() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiRequest("/api/updates/check?refresh=true", UpdatesCheckSchema),
    onSuccess: (next) => qc.setQueryData(CHECK_KEY, next),
    onError: toastApiError,
  });
}

function useUpdatePost(path: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiRequest(path, UpdateApplyResultSchema, { method: "POST" }),
    onSettled: () => qc.invalidateQueries({ queryKey: CHECK_KEY }),
    onError: toastApiError,
  });
}

/** POST /api/updates/apply — update a clone, or download a bundle. */
export function useUpdateApply() {
  return useUpdatePost("/api/updates/apply");
}

/** POST /api/updates/rollback — a clone returns to its previous commit. */
export function useUpdateRollback() {
  return useUpdatePost("/api/updates/rollback");
}

/** POST /api/updates/ini/preview — stage fresh INIs; nothing changes yet. */
export function useIniPreview() {
  return useMutation({
    mutationFn: () =>
      apiRequest("/api/updates/ini/preview", IniPreviewSchema, {
        method: "POST",
      }),
    onError: toastApiError,
  });
}

/** POST /api/updates/ini/apply — apply exactly what was previewed. */
export function useIniApply() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiRequest("/api/updates/ini/apply", IniPreviewSchema, {
        method: "POST",
      }),
    // The library's winners changed: every games / stats view is stale.
    onSuccess: () => qc.invalidateQueries(),
    onError: toastApiError,
  });
}
