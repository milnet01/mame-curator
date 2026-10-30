/**
 * mame-curator-1144 INV-3, 4, 5, 6, 7, 8, 13 — walking the guide's steps.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, useLocation } from "react-router";

import { CART_STORAGE_KEY } from "@/hooks/useCart";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import { GuidePage } from "../GuidePage";
import {
  libraryPageBaseHandlers,
  makeGameCard,
  setupCheckFixture,
} from "./_libraryPageFixtures";
import { config as appConfig } from "./_settingsPageFixtures";

const g = strings.guide;

class MockEventSource {
  static instances: MockEventSource[] = [];
  static CLOSED = 2;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  readyState = 1;
  constructor() {
    MockEventSource.instances.push(this);
  }
  emit(event: string, payload: Record<string, unknown> = {}) {
    this.onmessage?.(
      new MessageEvent("message", {
        data: JSON.stringify({ event, payload, ts: new Date().toISOString() }),
      }),
    );
  }
  close() {
    this.readyState = MockEventSource.CLOSED;
  }
}

const REPORT = {
  counts: {
    selected: 2,
    bios: 1,
    missing_source: 0,
    already_copied: 0,
    new: 2,
  },
  summary: {
    dest_writable: true,
    free_space_gap_bytes: 1000,
    existing_playlist: false,
  },
};

interface Recorded {
  games: URL[];
  dryRuns: unknown[];
  starts: unknown[];
  patches: unknown[];
}

function useHandlers(report: typeof REPORT = REPORT): Recorded {
  const seen: Recorded = { games: [], dryRuns: [], starts: [], patches: [] };
  server.use(
    http.get("/api/setup/check", () => HttpResponse.json(setupCheckFixture)),
    http.get("/api/library/facets", () =>
      HttpResponse.json({
        genres: ["Maze"],
        publishers: [],
        developers: [],
        letters: [],
      }),
    ),
    http.get("/api/games", ({ request }) => {
      seen.games.push(new URL(request.url));
      return HttpResponse.json({
        items: [
          makeGameCard({ short_name: "pacman", description: "Pac-Man" }),
          makeGameCard({ short_name: "galaga", description: "Galaga" }),
        ],
        page: 1,
        page_size: 500,
        total: 2,
        total_bytes: 3 * 1024 ** 3,
      });
    }),
    http.post("/api/copy/dry-run", async ({ request }) => {
      seen.dryRuns.push(await request.json());
      return HttpResponse.json(report);
    }),
    http.post("/api/copy/start", async ({ request }) => {
      seen.starts.push(await request.json());
      return HttpResponse.json({ job_id: "job-1" });
    }),
    http.post("/api/copy/abort", () =>
      HttpResponse.json({
        job_id: "job-1",
        state: "terminating",
        started_at: new Date().toISOString(),
        files_done: 0,
        files_total: 2,
        bytes_done: 0,
        bytes_total: 2,
      }),
    ),
    http.patch("/api/config", async ({ request }) => {
      seen.patches.push(await request.json());
      return HttpResponse.json(appConfig);
    }),
    // Last: MSW uses the first match, so the overrides above win.
    ...libraryPageBaseHandlers(),
  );
  return seen;
}

function Where() {
  const location = useLocation();
  return (
    <div data-testid="where" data-state={JSON.stringify(location.state)}>
      {location.pathname}
    </div>
  );
}

function renderGuide() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/start"]}>
        <GuidePage />
        <Where />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const heading = (name: string | RegExp) =>
  screen.findByRole("heading", { name });
const press = async (user: UserEvent, name: string | RegExp) =>
  user.click(await screen.findByRole("button", { name }));

async function walkToCheck(user: UserEvent) {
  await press(user, g.which.everything);
  await press(user, g.finds.copyThese);
  await press(user, g.where.yes);
  await heading(g.check.heading);
}

const expectExit = () =>
  expect(screen.getByRole("link", { name: g.exit })).toHaveAttribute(
    "href",
    "/",
  );
const expectBack = () =>
  expect(screen.getByRole("button", { name: g.back })).toBeInTheDocument();

beforeEach(() => {
  localStorage.clear();
  MockEventSource.instances = [];
  vi.stubGlobal("EventSource", MockEventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("GuidePage steps", () => {
  it("INV-3: every step has an exit, and every step but the first and Copying has Back", async () => {
    useHandlers();
    const user = userEvent.setup();
    renderGuide();

    await heading(g.which.heading);
    expectExit();
    expect(screen.queryByRole("button", { name: g.back })).toBeNull();

    await press(user, g.which.group);
    await heading(g.chooseGroup.heading);
    expectExit();
    expectBack();

    await press(user, g.back);
    await press(user, g.which.type);
    await heading(g.chooseType.heading);
    expectExit();
    expectBack();

    await press(user, "Maze");
    await heading(/This finds 2 games/);
    expectExit();
    expectBack();

    await press(user, g.finds.copyThese);
    await heading(g.where.heading);
    expectExit();
    expectBack();

    await press(user, g.where.yes);
    await heading(g.check.heading);
    expectExit();
    expectBack();

    await press(user, g.check.start);
    await heading(g.copying.heading);
    expectExit();
    expect(screen.queryByRole("button", { name: g.back })).toBeNull();
  });

  it("numbers the steps out of 5 for every game and out of 6 for a group", async () => {
    useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await heading(g.which.heading);
    expect(screen.getByText("Step 1")).toBeInTheDocument();

    await press(user, g.which.everything);
    await heading(/This finds/);
    expect(screen.getByText("Step 2 of 5")).toBeInTheDocument();

    await press(user, g.back);
    await press(user, g.which.group);
    await heading(g.chooseGroup.heading);
    expect(screen.getByText("Step 2 of 6")).toBeInTheDocument();
  });

  it("states the number of games and their size", async () => {
    useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await press(user, g.which.everything);
    expect(await heading("This finds 2 games, about 3.0 GB.")).toBeVisible();
  });

  it("INV-4: a full run leaves the cart exactly as it was", async () => {
    const cart = JSON.stringify([{ shortName: "dkong" }]);
    localStorage.setItem(CART_STORAGE_KEY, cart);
    useHandlers();
    const user = userEvent.setup();
    renderGuide();

    await walkToCheck(user);
    await press(user, g.check.start);
    await heading(g.copying.heading);
    act(() =>
      MockEventSource.instances[0].emit("job_finished", { status: "OK" }),
    );
    await heading(g.copying.finishedHeading);

    expect(localStorage.getItem(CART_STORAGE_KEY)).toBe(cart);
  });

  it("INV-5: every game sends no year filter, and the names reach the start", async () => {
    const seen = useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await press(user, g.check.start);
    await heading(g.copying.heading);

    expect(seen.games.length).toBeGreaterThan(0);
    for (const url of seen.games) {
      expect(url.searchParams.has("year_min")).toBe(false);
      expect(url.searchParams.has("year_max")).toBe(false);
    }
    expect(seen.starts).toEqual([
      {
        selected_names: ["pacman", "galaga"],
        conflict_strategy: "APPEND",
        append_decisions: {},
      },
    ]);
  });

  it("INV-5: a tile sends its own year bounds and no others", async () => {
    const seen = useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await press(user, g.which.group);
    await press(user, /Best of 1992/);
    await press(user, g.finds.copyThese);
    await heading(g.where.heading);

    expect(seen.games.length).toBeGreaterThan(0);
    for (const url of seen.games) {
      expect(url.searchParams.get("year_min")).toBe("1992");
      expect(url.searchParams.get("year_max")).toBe("1992");
    }
  });

  it("INV-6: the dry run and the start both send APPEND", async () => {
    const seen = useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await press(user, g.check.start);
    await heading(g.copying.heading);

    expect(seen.dryRuns).toHaveLength(1);
    expect(seen.dryRuns[0]).toMatchObject({ conflict_strategy: "APPEND" });
    expect(seen.starts[0]).toMatchObject({ conflict_strategy: "APPEND" });
  });

  it("offers a look through the games, carrying the selection to the Library", async () => {
    useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await press(user, g.which.type);
    await press(user, "Maze");
    await press(user, g.finds.lookThrough);
    const where = await screen.findByTestId("where");
    expect(where.textContent).toBe("/");
    expect(JSON.parse(where.dataset.state ?? "null")).toEqual({
      guideSelection: { kind: "genre", genre: "Maze" },
    });
  });

  it("a group with no games says so and offers only Back", async () => {
    useHandlers();
    server.use(
      http.get("/api/games", () =>
        HttpResponse.json({
          items: [],
          page: 1,
          page_size: 1,
          total: 0,
          total_bytes: 0,
        }),
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await press(user, g.which.type);
    await press(user, "Maze");
    await heading(g.finds.heading(0, ""));
    expect(
      screen.queryByRole("button", { name: g.finds.copyThese }),
    ).toBeNull();
    expect(
      screen.queryByRole("button", { name: g.finds.lookThrough }),
    ).toBeNull();
    expectBack();
  });

  describe("INV-7: a failure shows its reason on the step, and Back works", () => {
    it.each([
      [409, "job_already_running", strings.errors.byCode.job_already_running],
      [409, "playlist_unreadable", strings.errors.byCode.playlist_unreadable],
      [500, "boom", "it broke"],
    ])("a %i %s on the start", async (status, code, reason) => {
      useHandlers();
      server.use(
        http.post("/api/copy/start", () =>
          HttpResponse.json(
            { code, detail: "it broke", fields: [] },
            { status },
          ),
        ),
      );
      const user = userEvent.setup();
      renderGuide();
      await walkToCheck(user);
      await press(user, g.check.start);

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(reason);
      expect(
        screen.getByRole("heading", { name: g.check.heading }),
      ).toBeVisible();
      await press(user, g.back);
      await heading(g.where.heading);
    });

    it.each([
      [409, "job_already_running", strings.errors.byCode.job_already_running],
      [500, "boom", "it broke"],
    ])("a %i %s on the dry run", async (status, code, reason) => {
      useHandlers();
      server.use(
        http.post("/api/copy/dry-run", () =>
          HttpResponse.json(
            { code, detail: "it broke", fields: [] },
            { status },
          ),
        ),
      );
      const user = userEvent.setup();
      renderGuide();
      await press(user, g.which.everything);
      await press(user, g.finds.copyThese);
      await press(user, g.where.yes);

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(reason);
      expect(screen.queryByRole("button", { name: g.check.start })).toBeNull();
      await press(user, g.back);
      await heading(g.where.heading);
    });

    it.each([
      [409, "job_already_running", strings.errors.byCode.job_already_running],
      [500, "boom", "it broke"],
    ])("a %i %s while fetching the names", async (status, code, reason) => {
      useHandlers();
      const user = userEvent.setup();
      renderGuide();
      await press(user, g.which.everything);
      await heading(/This finds 2 games/);
      server.use(
        http.get("/api/games", () =>
          HttpResponse.json(
            { code, detail: "it broke", fields: [] },
            { status },
          ),
        ),
      );
      await press(user, g.finds.copyThese);

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(reason);
      await press(user, g.back);
      await heading(g.which.heading);
    });

    it.each([
      [409, "job_already_running", strings.errors.byCode.job_already_running],
      [500, "boom", "it broke"],
    ])("a %i %s on the folder save", async (status, code, reason) => {
      useHandlers();
      server.use(
        http.get("/api/fs/home", () => HttpResponse.json({ path: "/home" })),
        http.get("/api/fs/drive-roots", () => HttpResponse.json({ roots: [] })),
        http.get("/api/fs/allowed-roots", () =>
          HttpResponse.json({ roots: [] }),
        ),
        http.get("/api/fs/list", () =>
          HttpResponse.json({ path: "/mnt/dest", parent: null, entries: [] }),
        ),
        http.patch("/api/config", () =>
          HttpResponse.json(
            { code, detail: "it broke", fields: [] },
            { status },
          ),
        ),
      );
      const user = userEvent.setup();
      renderGuide();
      await press(user, g.which.everything);
      await press(user, g.finds.copyThese);
      await press(user, g.where.choose);
      await press(user, strings.settings.fsBrowserUseDirectory);

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(reason);
      expect(
        screen.getByRole("heading", { name: g.where.heading }),
      ).toBeVisible();
      await press(user, g.back);
      await heading(/This finds/);
    });

    it("a copy finishing with PARTIAL_FAILURE never shows as complete", async () => {
      useHandlers();
      const user = userEvent.setup();
      renderGuide();
      await walkToCheck(user);
      await press(user, g.check.start);
      await heading(g.copying.heading);
      act(() =>
        MockEventSource.instances[0].emit("job_finished", {
          status: "PARTIAL_FAILURE",
        }),
      );

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(g.copying.partial);
      expect(within(alert).getByRole("link")).toHaveAttribute(
        "href",
        "/activity",
      );
      expect(
        screen.queryByRole("heading", { name: g.copying.finishedHeading }),
      ).toBeNull();
    });
  });

  describe("INV-8: Start is not offered when the copy cannot work", () => {
    const report = (
      counts: Partial<typeof REPORT.counts>,
      summary: Partial<typeof REPORT.summary>,
    ) => ({
      counts: { ...REPORT.counts, ...counts },
      summary: { ...REPORT.summary, ...summary },
    });

    it.each([
      [
        "an unwritable folder",
        report({}, { dest_writable: false }),
        g.check.notWritable,
      ],
      [
        "too little free space",
        report({}, { free_space_gap_bytes: -(2 * 1024 ** 3) }),
        g.check.needsSpace("2.0 GB"),
      ],
      [
        "nothing new",
        report({ new: 0, already_copied: 2 }, {}),
        g.check.allCopied,
      ],
    ])("%s", async (_name, fixture, message) => {
      useHandlers(fixture);
      const user = userEvent.setup();
      renderGuide();
      await press(user, g.which.everything);
      await press(user, g.finds.copyThese);
      await press(user, g.where.yes);

      expect(await screen.findByText(message)).toBeVisible();
      expect(screen.queryByRole("button", { name: g.check.start })).toBeNull();
      expectBack();
    });

    it("offers Start when all is well, and says what will happen", async () => {
      useHandlers({
        ...REPORT,
        counts: { ...REPORT.counts, already_copied: 1, missing_source: 1 },
        summary: { ...REPORT.summary, existing_playlist: true },
      });
      const user = userEvent.setup();
      renderGuide();
      await walkToCheck(user);

      expect(screen.getByText(g.check.newGames(2))).toBeVisible();
      expect(screen.getByText(g.check.alreadyCopied(1))).toBeVisible();
      expect(screen.getByText(g.check.missingSource(1))).toBeVisible();
      expect(screen.getByText(g.check.bios(1))).toBeVisible();
      expect(screen.getByText(g.check.existingPlaylist)).toBeVisible();
      expect(screen.getByRole("button", { name: g.check.start })).toBeVisible();
    });
  });

  it("INV-13: a chosen folder saves through PATCH /api/config, and a sandboxed folder asks first", async () => {
    const seen = useHandlers();
    server.use(
      http.get("/api/fs/home", () => HttpResponse.json({ path: "/home/me" })),
      http.get("/api/fs/drive-roots", () => HttpResponse.json({ roots: [] })),
      http.get("/api/fs/allowed-roots", () => HttpResponse.json({ roots: [] })),
      http.get("/api/fs/list", ({ request }) => {
        const path = new URL(request.url).searchParams.get("path");
        if (path === "/mnt/dest") {
          return HttpResponse.json(
            { code: "fs_sandboxed", detail: "outside", fields: [] },
            { status: 403 },
          );
        }
        return HttpResponse.json({ path, parent: null, entries: [] });
      }),
    );
    const user = userEvent.setup();
    renderGuide();
    await press(user, g.which.everything);
    await press(user, g.finds.copyThese);
    await press(user, g.where.choose);

    // The folder is outside the allowlist, so FsBrowser's own grant shows.
    expect(
      await screen.findByText(strings.settings.fsGrantTitle),
    ).toBeVisible();
    await user.click(
      screen.getByRole("button", { name: strings.common.cancel }),
    );

    // Past the grant, a save goes through the same route as Settings.
    server.use(
      http.get("/api/fs/list", () =>
        HttpResponse.json({ path: "/mnt/dest", parent: null, entries: [] }),
      ),
    );
    await press(user, g.where.choose);
    await press(user, strings.settings.fsBrowserUseDirectory);
    await vi.waitFor(() => expect(seen.patches).toHaveLength(1));
    expect(seen.patches[0]).toMatchObject({
      paths: { dest_roms: "/mnt/dest", source_roms: "/mnt/roms" },
    });
  });

  it("Stop asks whether to keep or remove the files, and Pause says how to leave", async () => {
    useHandlers();
    const user = userEvent.setup();
    server.use(
      http.post("/api/copy/pause", () =>
        HttpResponse.json({
          job_id: "job-1",
          state: "paused",
          started_at: new Date().toISOString(),
          files_done: 0,
          files_total: 2,
          bytes_done: 0,
          bytes_total: 2,
        }),
      ),
    );
    renderGuide();
    await walkToCheck(user);
    await press(user, g.check.start);
    await heading(g.copying.heading);
    expect(screen.getByText(g.copying.closeHint)).toBeVisible();

    act(() => MockEventSource.instances[0].emit("paused"));
    expect(await screen.findByText(g.copying.pausedHint)).toBeVisible();
    expect(
      screen.getByRole("button", { name: strings.copy.resume }),
    ).toBeVisible();
    // User ruling, 2026-10-30: only Resume and Stop while paused.
    expect(screen.queryByRole("link", { name: g.exit })).toBeNull();

    act(() =>
      MockEventSource.instances[0].emit("file_finished", { files_done: 1 }),
    );
    await press(user, g.copying.stop);
    expect(
      await screen.findByRole("button", { name: strings.copy.abortKeepFiles }),
    ).toBeVisible();
    expect(
      screen.getByRole("button", { name: strings.copy.abortRecycleFiles }),
    ).toBeVisible();
  });

  it("Copy more games returns to the first step after a finished copy", async () => {
    useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await press(user, g.check.start);
    await heading(g.copying.heading);
    act(() =>
      MockEventSource.instances[0].emit("job_finished", { status: "OK" }),
    );
    await heading(g.copying.finishedHeading);
    expect(
      screen.getByRole("link", { name: g.copying.goToLibrary }),
    ).toHaveAttribute("href", "/");

    await press(user, g.copying.copyMore);
    await heading(g.which.heading);
  });
});
