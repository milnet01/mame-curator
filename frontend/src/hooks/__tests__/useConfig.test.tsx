import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import {
  QueryClient,
  QueryClientProvider,
  QueryObserver,
} from "@tanstack/react-query";

import { server, http, HttpResponse } from "@/test/handlers";
import { makeClientWrapper } from "@/test/renderWithClient";
import { apiRequest } from "@/api/client";
import { AppConfigResponseSchema } from "@/api/types";
import { _resetApiErrorToastDedupForTests } from "@/lib/apiErrorToast";
import {
  REFRESH_LIMIT_MS,
  refreshEverything,
  useConfigImport,
  useConfigPatch,
  useSnapshotRestore,
} from "../useConfig";
import { strings } from "@/strings";
import { config } from "@/pages/__tests__/_settingsPageFixtures";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { toast } from "sonner";
import { ERROR_TOAST } from "@/lib/apiErrorToast";

// DS04 T3.1: vitest `globals: true` auto-cleanup handles RTL teardown;
// only the mock-clear is load-bearing here.
afterEach(() => {
  vi.mocked(toast.error).mockClear();
  vi.mocked(toast.success).mockClear();
});

const renderWithClient = makeClientWrapper;
const STARTUP_CHECK = ["updates", "startup"] as const;

describe("useConfigPatch onError → toast (FP13 § A1)", () => {
  it("toasts byCode-friendly copy when PATCH /api/config returns 422", async () => {
    server.use(
      http.patch("/api/config", () =>
        HttpResponse.json(
          { code: "fs_path_invalid", detail: "bad path", fields: [] },
          { status: 422 },
        ),
      ),
    );
    const { result } = renderHook(() => useConfigPatch(), {
      wrapper: renderWithClient(),
    });
    result.current.mutate({ paths: { source_roms: "x" } } as never);
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining("not a valid directory"),
      ERROR_TOAST,
    );
  });
});

describe("useConfigPatch onSuccess → saved indicator (mame-curator-1038)", () => {
  it("says the settings were saved, reusing one toast so rapid edits do not stack", async () => {
    server.use(http.patch("/api/config", () => HttpResponse.json(config)));
    const { result } = renderHook(() => useConfigPatch(), {
      wrapper: renderWithClient(),
    });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith(
      strings.settings.saved,
      expect.objectContaining({ id: "config-saved" }),
    );
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled();
  });
});

// mame-curator-1145 INV-8: a save that ended setup mode changed every answer.
describe("useConfigPatch after a save in setup mode", () => {
  function setupClient(setupRequired?: boolean) {
    const client = new QueryClient();
    if (setupRequired !== undefined) {
      client.setQueryData(["setup", "check"], {
        setup_required: setupRequired,
      });
    }
    client.setQueryData(["games", "anything"], { total: 0 });
    client.setQueryData(STARTUP_CHECK, { latest_version: null });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    return { client, wrapper };
  }
  const stale = (client: QueryClient) =>
    client.getQueryState(["games", "anything"])?.isInvalidated;

  it.each([
    ["says setup mode is on", true],
    ["has already flipped", false],
    ["is missing", undefined],
  ])(
    "refreshes everything on setup_ended when the cached check %s",
    async (_name, cached) => {
      server.use(
        http.patch("/api/config", () =>
          HttpResponse.json({ ...config, setup_ended: true }),
        ),
      );
      const { client, wrapper } = setupClient(cached);
      const { result } = renderHook(() => useConfigPatch(), { wrapper });
      result.current.mutate({} as never);
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(stale(client)).toBe(true);
    },
  );

  it("refreshes when one save ended setup mode and changed the server too", async () => {
    server.use(
      http.patch("/api/config", () =>
        HttpResponse.json({
          ...config,
          setup_ended: true,
          restart_required: true,
        }),
      ),
    );
    const { client, wrapper } = setupClient(true);
    const { result } = renderHook(() => useConfigPatch(), { wrapper });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(stale(client)).toBe(true);
  });

  it("leaves the once-a-session update check alone", async () => {
    server.use(
      http.patch("/api/config", () =>
        HttpResponse.json({ ...config, setup_ended: true }),
      ),
    );
    const { client, wrapper } = setupClient(true);
    const { result } = renderHook(() => useConfigPatch(), { wrapper });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(client.getQueryState(STARTUP_CHECK)?.isInvalidated).toBe(false);
  });

  it("refreshes nothing extra when the reply does not say setup ended, whatever is cached", async () => {
    server.use(http.patch("/api/config", () => HttpResponse.json(config)));
    const { client, wrapper } = setupClient(true);
    const { result } = renderHook(() => useConfigPatch(), { wrapper });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(stale(client)).toBe(false);
  });

  it("keeps the restart prompt when the save did not end setup mode", async () => {
    server.use(
      http.patch("/api/config", () =>
        HttpResponse.json({ ...config, restart_required: true }),
      ),
    );
    const { client, wrapper } = setupClient(true);
    const { result } = renderHook(() => useConfigPatch(), { wrapper });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(stale(client)).toBe(false);
    expect(client.getQueryData(["config"])).toMatchObject({
      restart_required: true,
    });
  });

  it("an older answer still on its way cannot overwrite the reply", async () => {
    let answerOld = () => {};
    const held = new Promise<void>((resolve) => {
      answerOld = resolve;
    });
    server.use(
      http.get("/api/config", async () => {
        await held;
        return HttpResponse.json({ ...config, restart_required: false });
      }),
      http.patch("/api/config", () =>
        HttpResponse.json({ ...config, restart_required: true }),
      ),
    );
    const { client, wrapper } = setupClient(false);
    const inFlight = client
      .fetchQuery({
        queryKey: ["config"],
        queryFn: () => apiRequest("/api/config", AppConfigResponseSchema),
      })
      .catch(() => undefined);
    const { result } = renderHook(() => useConfigPatch(), { wrapper });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    answerOld();
    await inFlight;
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(client.getQueryData(["config"])).toMatchObject({
      restart_required: true,
    });
  });

  it("stays quiet when its caller says the outcome itself", async () => {
    server.use(http.patch("/api/config", () => HttpResponse.json(config)));
    const { wrapper } = setupClient(true);
    const { result } = renderHook(() => useConfigPatch({ quiet: true }), {
      wrapper,
    });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(vi.mocked(toast.success)).not.toHaveBeenCalled();
  });

  it("does not repeat a failure its caller shows itself", async () => {
    _resetApiErrorToastDedupForTests();
    server.use(
      http.patch("/api/config", () =>
        HttpResponse.json(
          { code: "fs_path_invalid", detail: "bad path", fields: [] },
          { status: 422 },
        ),
      ),
    );
    const { wrapper } = setupClient(true);
    const { result } = renderHook(() => useConfigPatch({ quiet: true }), {
      wrapper,
    });
    result.current.mutate({} as never);
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(vi.mocked(toast.error)).not.toHaveBeenCalled();
  });
});

describe("refreshEverything's wait (mame-curator-1145 §4.3)", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("gives up after its time limit, so one hung request cannot hold the wizard", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    const client = new QueryClient();
    const observer = new QueryObserver(client, {
      queryKey: ["hung"],
      queryFn: () => new Promise(() => {}),
    });
    const unsubscribe = observer.subscribe(() => {});
    let settled = false;
    void refreshEverything(client).then(() => {
      settled = true;
    });
    await vi.advanceTimersByTimeAsync(REFRESH_LIMIT_MS - 1);
    expect(settled).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(settled).toBe(true);
    unsubscribe();
  });
});

// mame-curator-1145 INV-15: both replace most of what the page holds.
describe.each<[string, string, () => { ok: boolean; run: () => void }]>([
  [
    "useSnapshotRestore",
    "/api/config/snapshots/a/restore",
    () => {
      const restore = useSnapshotRestore();
      return { ok: restore.isSuccess, run: () => restore.mutate("a") };
    },
  ],
  [
    "useConfigImport",
    "/api/config/import",
    () => {
      const load = useConfigImport();
      return { ok: load.isSuccess, run: () => load.mutate({} as never) };
    },
  ],
])("%s on success", (_name, url, hook) => {
  it("refreshes everything but the once-a-session update check", async () => {
    server.use(http.post(url, () => HttpResponse.json(config)));
    const client = new QueryClient();
    client.setQueryData(["games", "anything"], { total: 0 });
    client.setQueryData(STARTUP_CHECK, { latest_version: null });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const { result } = renderHook(hook, { wrapper });
    result.current.run();
    await waitFor(() => expect(result.current.ok).toBe(true));
    expect(client.getQueryState(["games", "anything"])?.isInvalidated).toBe(
      true,
    );
    expect(client.getQueryState(STARTUP_CHECK)?.isInvalidated).toBe(false);
  });
});

describe("useSnapshotRestore onError → toast (FP13 § A2)", () => {
  it("toasts byCode-friendly copy when restore returns 404 snapshot_not_found", async () => {
    server.use(
      http.post("/api/config/snapshots/missing/restore", () =>
        HttpResponse.json(
          {
            code: "snapshot_not_found",
            detail: "no such snapshot",
            fields: [],
          },
          { status: 404 },
        ),
      ),
    );
    const { result } = renderHook(() => useSnapshotRestore(), {
      wrapper: renderWithClient(),
    });
    result.current.mutate("missing");
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith(
      expect.stringContaining("No configuration snapshot"),
      ERROR_TOAST,
    );
  });
});
