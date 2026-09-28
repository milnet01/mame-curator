import { afterEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { server, http, HttpResponse } from "@/test/handlers";
import { makeClientWrapper } from "@/test/renderWithClient";
import { useConfigPatch, useSnapshotRestore } from "../useConfig";
import { strings } from "@/strings";
import { config } from "@/pages/__tests__/_settingsPageFixtures";

vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
}));

import { toast } from "sonner";

// DS04 T3.1: vitest `globals: true` auto-cleanup handles RTL teardown;
// only the mock-clear is load-bearing here.
afterEach(() => {
  vi.mocked(toast.error).mockClear();
  vi.mocked(toast.success).mockClear();
});

const renderWithClient = makeClientWrapper;

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
    );
  });
});
