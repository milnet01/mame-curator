import {
  useMutation,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { apiRequest } from "@/api/client";
import {
  AppConfigResponseSchema,
  ConfigExportBundleSchema,
  SnapshotsListingSchema,
  type AppConfigResponse,
  type ConfigExportBundle,
  type SnapshotsListing,
} from "@/api/types";
import { toast } from "sonner";
import { toastApiError } from "@/lib/apiErrorToast";
import { strings } from "@/strings";
import { useApiQuery } from "./useApi";

const KEY = ["config"] as const;
const SNAPSHOTS_KEY = ["config", "snapshots"] as const;

/** How long a save stays busy waiting for the page to catch up. */
export const REFRESH_LIMIT_MS = 30_000;

/**
 * mame-curator-1145 §4.3: every answer the page holds, except the one update
 * check a session makes, which can wait on the network. Queries on screen are
 * refetched now and the others when next viewed. Settles when they are fresh or
 * at the limit, so one hung request cannot hold a caller for ever.
 */
export async function refreshEverything(qc: QueryClient): Promise<void> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const limit = new Promise<void>((resolve) => {
    timer = setTimeout(resolve, REFRESH_LIMIT_MS);
  });
  try {
    await Promise.race([
      qc.invalidateQueries({
        predicate: ({ queryKey: [area, name] }) =>
          !(area === "updates" && name === "startup"),
      }),
      limit,
    ]);
  } finally {
    clearTimeout(timer);
  }
}

/** Cancels first, or an older answer still on its way overwrites this one. */
async function storeReply(qc: QueryClient, next: AppConfigResponse) {
  await qc.cancelQueries({ queryKey: KEY, exact: true });
  qc.setQueryData(KEY, next);
}

export function useConfig() {
  return useApiQuery<AppConfigResponse>(
    KEY,
    "/api/config",
    AppConfigResponseSchema,
  );
}

/** `quiet`: the caller says the outcome itself, so no toast repeats it. */
export function useConfigPatch({ quiet = false }: { quiet?: boolean } = {}) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (patch: Partial<AppConfigResponse>) =>
      apiRequest<AppConfigResponse>("/api/config", AppConfigResponseSchema, {
        method: "PATCH",
        body: patch,
      }),
    onSuccess: async (next) => {
      await storeReply(qc, next);
      // Each PATCH writes a fresh snapshot server-side (R15 contract);
      // invalidate so the Snapshots tab reflects the new entry on next read.
      qc.invalidateQueries({ queryKey: SNAPSHOTS_KEY });
      // mame-curator-1038: settings save as you edit, so say it happened.
      // One fixed id, so a burst of edits updates a single toast.
      if (!quiet) {
        toast.success(strings.settings.saved, {
          id: "config-saved",
          duration: 1500,
        });
      }
      // mame-curator-1145 §4.3: a save that ended setup mode changed every
      // answer the page holds. Waiting keeps the mutation pending until they
      // are fresh. The reply says so, because a cached answer can be out of date.
      if (next.setup_ended) await refreshEverything(qc);
    },
    onError: (err) => {
      if (!quiet) toastApiError(err);
    },
  });
}

export function useSnapshots() {
  return useApiQuery<SnapshotsListing>(
    SNAPSHOTS_KEY,
    "/api/config/snapshots",
    SnapshotsListingSchema,
  );
}

export function useSnapshotRestore() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiRequest<AppConfigResponse>(
        `/api/config/snapshots/${encodeURIComponent(id)}/restore`,
        AppConfigResponseSchema,
        { method: "POST" },
      ),
    // mame-curator-1145 INV-15: a restore replaces most of what the page holds.
    onSuccess: async (next) => {
      await storeReply(qc, next);
      await refreshEverything(qc);
    },
    onError: toastApiError,
  });
}

// FP12 § J — R18 export + R19 import. Backend takes / returns the full
// `ConfigExportBundle` JSON (config.py:170 + 186); the multipart hint in
// the roadmap entry is stale.
export function useConfigExport() {
  return useMutation({
    mutationFn: () =>
      apiRequest<ConfigExportBundle>(
        "/api/config/export",
        ConfigExportBundleSchema,
        { method: "POST" },
      ),
  });
}

export function useConfigImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (bundle: ConfigExportBundle) =>
      apiRequest<AppConfigResponse>(
        "/api/config/import",
        AppConfigResponseSchema,
        { method: "POST", body: bundle },
      ),
    // mame-curator-1145 INV-15: an import replaces most of what the page holds.
    onSuccess: async (next) => {
      await storeReply(qc, next);
      await refreshEverything(qc);
    },
  });
}
