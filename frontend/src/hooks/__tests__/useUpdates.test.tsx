/**
 * mame-curator-1233 (CR-08-10): applying an INI update refreshes what the
 * page holds, but not the session's one update check (refreshEverything).
 */
import { describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { http, HttpResponse, server } from "@/test/handlers";
import { renderWithClient } from "@/test/renderWithClient";
import { useIniApply } from "../useUpdates";

describe("useIniApply", () => {
  it("refreshes the games and leaves the startup update check alone", async () => {
    server.use(
      http.post("/api/updates/ini/apply", () =>
        HttpResponse.json({
          changed_files: [],
          failed: [],
          winners_added: [],
          winners_removed: [],
        }),
      ),
    );
    const { qc, wrapper } = renderWithClient();
    qc.setQueryData(["games", "anything"], { total: 0 });
    qc.setQueryData(["updates", "startup"], { latest_version: null });
    const { result } = renderHook(() => useIniApply(), { wrapper });
    result.current.mutate();
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(qc.getQueryState(["games", "anything"])?.isInvalidated).toBe(true);
    expect(qc.getQueryState(["updates", "startup"])?.isInvalidated).toBe(false);
  });
});
