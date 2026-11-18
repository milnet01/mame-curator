/**
 * mame-curator-1233 (CR-08-7): forgetting old choices refreshes what shows
 * them even when a later delete fails, since the earlier ones took effect.
 */
import { describe, expect, it } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { http, HttpResponse, server } from "@/test/handlers";
import { renderWithClient } from "@/test/renderWithClient";
import { useForgetChoices } from "../useAlternatives";

describe("useForgetChoices", () => {
  it("refreshes the games after a press that failed partway", async () => {
    server.use(
      http.delete("/api/overrides/:parent", ({ params }) =>
        params.parent === "first"
          ? HttpResponse.json({ entries: {}, warnings: [], unusable: [] })
          : HttpResponse.json(
              { code: "internal", detail: "boom", fields: [] },
              { status: 500 },
            ),
      ),
    );
    const { qc, wrapper } = renderWithClient();
    qc.setQueryData(["games", "anything"], { total: 0 });
    const { result } = renderHook(() => useForgetChoices(), { wrapper });
    result.current.mutate(["first", "second"]);
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(qc.getQueryState(["games", "anything"])?.isInvalidated).toBe(true);
  });
});
