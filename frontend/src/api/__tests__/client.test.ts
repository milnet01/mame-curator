/**
 * The status an `ApiError` carries: the response's own, or `STATUS_UNSENT`
 * only when no response came back.
 */
import { describe, expect, it } from "vitest";
import { z } from "zod";

import { ApiError, apiRequest, STATUS_UNSENT } from "../client";
import { http, HttpResponse, server } from "@/test/handlers";

const Thing = z.object({ name: z.string() }).strict();

async function failure(run: () => Promise<unknown>): Promise<ApiError> {
  try {
    await run();
  } catch (err) {
    if (err instanceof ApiError) return err;
    throw err;
  }
  throw new Error("expected an ApiError");
}

describe("apiRequest error status", () => {
  it("a 200 whose body fails the schema carries 200", async () => {
    server.use(http.get("/api/thing", () => HttpResponse.json({ name: 1 })));
    const err = await failure(() => apiRequest("/api/thing", Thing));
    expect(err.code).toBe("response_shape_invalid");
    expect(err.status).toBe(200);
  });

  it("a request that never reached the server carries STATUS_UNSENT", async () => {
    server.use(http.get("/api/thing", () => HttpResponse.error()));
    const err = await failure(() => apiRequest("/api/thing", Thing));
    expect(err.code).toBe("network");
    expect(err.status).toBe(STATUS_UNSENT);
  });
});
