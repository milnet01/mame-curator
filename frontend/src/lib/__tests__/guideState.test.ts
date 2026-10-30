/** mame-curator-1144 — the guide's "seen" flag when storage writes fail. */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

beforeEach(() => {
  localStorage.clear();
  vi.resetModules();
});
afterEach(() => vi.restoreAllMocks());

describe("guideState", () => {
  it("remembers for this page when storage reads but cannot write", async () => {
    const { isGuideSeen, markGuideSeen } = await import("../guideState");
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    expect(isGuideSeen()).toBe(false);
    markGuideSeen();
    expect(isGuideSeen()).toBe(true);
  });
});
