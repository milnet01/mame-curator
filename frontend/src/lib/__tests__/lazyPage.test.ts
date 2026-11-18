/**
 * mame-curator-1233 (CR-08-3): after an in-app update, an open tab asks for
 * page files the update replaced. React.lazy keeps that failure for good, so
 * the page reloads once to fetch the new ones, and does not loop.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { PAGE_RELOAD_KEY, reloadOnceIfMissing } from "../lazyPage";

const lost = new TypeError("Failed to fetch dynamically imported module");

afterEach(() => {
  sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("reloadOnceIfMissing", () => {
  it("reloads the page when a page file fails to load", async () => {
    const reload = vi.fn();
    const load = reloadOnceIfMissing(() => Promise.reject(lost), reload);
    let settled = false;
    void load().finally(() => {
      settled = true;
    });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(reload).toHaveBeenCalledOnce();
    expect(settled).toBe(false);
  });

  it("gives the failure to the error panel when the reload did not help", async () => {
    const reload = vi.fn();
    const load = reloadOnceIfMissing(() => Promise.reject(lost), reload);
    void load();
    await new Promise((resolve) => setTimeout(resolve, 0));
    await expect(load()).rejects.toBe(lost);
    expect(reload).toHaveBeenCalledOnce();
  });

  it("allows another reload once a page has loaded", async () => {
    sessionStorage.setItem(PAGE_RELOAD_KEY, "1");
    const page = { default: () => null };
    await expect(
      reloadOnceIfMissing(() => Promise.resolve(page))(),
    ).resolves.toBe(page);
    expect(sessionStorage.getItem(PAGE_RELOAD_KEY)).toBeNull();
  });

  it("does not reload when storage is blocked, since nothing would stop a loop", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    const reload = vi.fn();
    await expect(
      reloadOnceIfMissing(() => Promise.reject(lost), reload)(),
    ).rejects.toBe(lost);
    expect(reload).not.toHaveBeenCalled();
  });
});
