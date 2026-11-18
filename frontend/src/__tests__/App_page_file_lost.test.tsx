/**
 * mame-curator-1233 (CR-08-3): a page file the app cannot fetch, as after an
 * in-app update replaced it, reloads the page rather than failing for good.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import { ShellWithPalette } from "@/App";
import { GUIDE_SEEN_KEY } from "@/lib/guideState";
import { PAGE_RELOAD_KEY } from "@/lib/lazyPage";
import { libraryPageBaseHandlers } from "@/pages/__tests__/_libraryPageFixtures";
import { HttpResponse, http, server } from "@/test/handlers";

vi.mock("@/pages/StatsPage", () => {
  throw new TypeError("Failed to fetch dynamically imported module");
});

beforeEach(() => {
  // jsdom has no matchMedia, and the shell's Toaster reads it.
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  localStorage.setItem(GUIDE_SEEN_KEY, "true");
  sessionStorage.clear();
  server.use(
    ...libraryPageBaseHandlers(),
    http.get("/api/updates/check", () => HttpResponse.json({})),
    http.get("/api/stats", () =>
      HttpResponse.json({
        by_genre: {},
        by_decade: {},
        by_publisher: {},
        by_driver_status: {},
        total_bytes: 0,
      }),
    ),
  );
});

describe("a page whose file cannot be fetched", () => {
  it("starts a reload", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/stats"]}>
          <ShellWithPalette />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await waitFor(() =>
      expect(sessionStorage.getItem(PAGE_RELOAD_KEY)).toBe("1"),
    );
  });
});
