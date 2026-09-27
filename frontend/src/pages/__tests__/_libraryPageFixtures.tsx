/**
 * Shared fixtures for LibraryPage integration tests (mame-curator-1100 /
 * -1102 loading-state regressions).
 *
 * Leading-underscore filename = not a test file; Vitest discovery skips
 * this module. `LibraryPage_loading_state.test.tsx` imports the `render`
 * wrapper + fixed-shape API payloads from here.
 *
 * `LibraryPage` fans out to five queries on mount (config, sessions,
 * facets, setup-check, review-state) that every render needs satisfied —
 * `msw`'s `onUnhandledRequest: 'error'` (src/test/setup.ts) throws on
 * anything left unmocked, which would abort the render before either
 * regression's assertion. This file supplies minimal-but-schema-valid
 * responses for all five so a test file only has to `server.use(...)`
 * the one endpoint its scenario cares about (`/api/games` or
 * `/api/games/:name/alternatives`).
 */
import type { ReactElement } from "react";
import { render as rtlRender } from "@testing-library/react";
import type { RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import { http, HttpResponse } from "@/test/handlers";
import type { UseCartResult } from "@/hooks/useCart";
import { config as appConfig } from "./_settingsPageFixtures";

/** A cart with nothing in it and every mutator a stable no-op. */
export function makeFakeCart(): UseCartResult {
  return {
    items: [],
    has: () => false,
    add: () => {},
    remove: () => {},
    addAll: () => ({ added: 0, truncated: 0 }),
    setVariant: () => {},
    clear: () => {},
    totalBytes: 0,
    isStorageBroken: false,
  };
}

/** Schema-valid `GET /api/setup/check` body — RetroArch left unconfigured;
 *  irrelevant to both regressions, just needs to parse. */
export const setupCheckFixture = {
  config_present: true,
  paths: {
    source_roms: {
      path: "/mnt/roms",
      exists: true,
      readable: true,
      writable: true,
      dat_parses: null,
    },
    source_dat: {
      path: "/mnt/dat.xml",
      exists: true,
      readable: true,
      writable: false,
      dat_parses: true,
    },
    dest_roms: {
      path: "/mnt/dest",
      exists: true,
      readable: true,
      writable: true,
      dat_parses: null,
    },
  },
  reference_files: {
    catver: { path: "", exists: false },
    languages: { path: "", exists: false },
    bestgames: { path: "", exists: false },
    mature: { path: "", exists: false },
    series: { path: "", exists: false },
    listxml: { path: "", exists: false },
  },
  cloneof_map_size: 0,
  retroarch_configured: false,
};

/**
 * Register the five always-needed handlers `LibraryPage` fires on
 * mount (everything except `/api/games` and the per-game alternatives
 * endpoint, which each test scenario owns). Call once per test via
 * `server.use(...libraryPageBaseHandlers())`.
 */
export function libraryPageBaseHandlers() {
  return [
    http.get("/api/config", () => HttpResponse.json(appConfig)),
    http.get("/api/sessions", () =>
      HttpResponse.json({ active: null, sessions: {} }),
    ),
    http.get("/api/library/facets", () =>
      HttpResponse.json({
        genres: [],
        publishers: [],
        developers: [],
        letters: [],
      }),
    ),
    http.get("/api/setup/check", () => HttpResponse.json(setupCheckFixture)),
    http.get("/api/state", () => HttpResponse.json({ entries: {} })),
  ];
}

/** A `GamesPage` envelope wrapping the given items. */
export function makeGamesPage(items: ReturnType<typeof makeGameCard>[]) {
  return {
    items,
    page: 1,
    page_size: 200,
    total: items.length,
    total_bytes: 0,
  };
}

export function makeGameCard(overrides: {
  short_name: string;
  description: string;
}) {
  return {
    year: 1980,
    manufacturer: "Namco",
    publisher: "Midway",
    developer: "Namco",
    badges: [],
    ...overrides,
  };
}

/** A handler whose promise never settles — the query stays `isPending`
 *  for the lifetime of the test, same as a slow backend the user is
 *  still waiting on. */
export function hangingGet(url: string) {
  return http.get(url, () => new Promise(() => {}));
}

export function renderLibraryPageTree(
  ui: ReactElement,
  options?: RenderOptions & { initialPath?: string },
) {
  const { initialPath = "/", ...rtlOptions } = options ?? {};
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return rtlRender(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
    rtlOptions,
  );
}
