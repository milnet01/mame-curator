/**
 * mame-curator-1144 — the guide is honest and audible. Backing out sticks,
 * each result is in a live region, and a heading says how a step came out.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

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

const REPORT = {
  counts: {
    selected: 2,
    bios: 0,
    bios_missing_source: 0,
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

type Report = {
  counts?: Partial<typeof REPORT.counts>;
  summary?: Partial<typeof REPORT.summary>;
};

const gamesPage = (names: string[]) => ({
  items: names.map((short_name) =>
    makeGameCard({ short_name, description: short_name }),
  ),
  page: 1,
  page_size: 500,
  total: names.length,
  total_bytes: 1024,
});

function useHandlers(report: Report = {}) {
  const starts: { selected_names: string[] }[] = [];
  server.use(
    http.get("/api/setup/check", () => HttpResponse.json(setupCheckFixture)),
    http.get("/api/games", ({ request }) => {
      const year = new URL(request.url).searchParams.get("year_min");
      return HttpResponse.json(gamesPage(year ? ["galaga"] : ["pacman"]));
    }),
    http.post("/api/copy/dry-run", () =>
      HttpResponse.json({
        counts: { ...REPORT.counts, ...report.counts },
        summary: { ...REPORT.summary, ...report.summary },
      }),
    ),
    http.post("/api/copy/start", async ({ request }) => {
      starts.push((await request.json()) as { selected_names: string[] });
      return HttpResponse.json({ job_id: "job-1" });
    }),
    ...libraryPageBaseHandlers(),
  );
  return starts;
}

function deferred() {
  let release = () => {};
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  return { held, release };
}

function renderGuide() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/start"]}>
        <GuidePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const heading = (name: string | RegExp) =>
  screen.findByRole("heading", { name });
const press = async (user: UserEvent, name: string | RegExp) =>
  user.click(await screen.findByRole("button", { name }));
const button = (name: string) => screen.queryByRole("button", { name });

async function walkToCheck(user: UserEvent) {
  await press(user, g.which.everything);
  await press(user, g.finds.copyThese);
  await press(user, g.where.yes);
}

beforeEach(() => {
  localStorage.clear();
  vi.stubGlobal(
    "EventSource",
    class {
      close() {}
    },
  );
});

describe("INV-5: backing out of the name fetch sticks", () => {
  it("a stale fetch neither moves the guide nor changes the list", async () => {
    const starts = useHandlers();
    const { held, release } = deferred();
    let stale = true;
    server.use(
      http.get("/api/games", async ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get("page_size") === "1") {
          return HttpResponse.json(gamesPage(["pacman"]));
        }
        if (stale) {
          stale = false;
          await held;
          return HttpResponse.json(gamesPage(["pacman"]));
        }
        return HttpResponse.json(gamesPage(["galaga"]));
      }),
    );
    const user = userEvent.setup();
    renderGuide();

    await press(user, g.which.everything);
    await press(user, g.finds.copyThese);
    await press(user, g.back);
    await press(user, g.which.group);
    await press(user, strings.library.featured.tiles[0].title);
    await heading(/This finds 1 game/);

    release();
    // Long enough for the held reply to have reached the page, if it could.
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByRole("heading", { name: g.where.heading })).toBeNull();
    await heading(/This finds 1 game/);

    await press(user, g.finds.copyThese);
    await press(user, g.where.yes);
    await press(user, g.check.start);
    await waitFor(() => expect(starts).toHaveLength(1));
    expect(starts[0].selected_names).toEqual(["galaga"]);
  });
});

describe("a heading says how the step came out", () => {
  it("a failed count does not go on saying it is counting", async () => {
    useHandlers();
    server.use(
      http.get("/api/games", () =>
        HttpResponse.json(
          { code: "boom", detail: "it broke", fields: [] },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await press(user, g.which.everything);
    await heading(g.loadFailed);
    expect(screen.getByRole("alert")).toHaveTextContent("it broke");
  });

  it("a failed dry run is not ready to copy", async () => {
    useHandlers();
    server.use(
      http.post("/api/copy/dry-run", () =>
        HttpResponse.json(
          { code: "boom", detail: "it broke", fields: [] },
          { status: 500 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await heading(g.loadFailed);
    expect(screen.queryByRole("heading", { name: g.check.heading })).toBeNull();
  });

  it.each([
    ["nothing new", { counts: { new: 0 } }, g.check.nothingNewHeading],
    [
      "an unwritable folder",
      { summary: { dest_writable: false } },
      g.check.cannotStartHeading,
    ],
    [
      "too little space",
      { summary: { free_space_gap_bytes: -1 } },
      g.check.cannotStartHeading,
    ],
  ])("%s is not ready to copy", async (_name, report, expected) => {
    useHandlers(report);
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await heading(expected);
    expect(button(g.check.start)).toBeNull();
  });

  it("is ready to copy only when Start is offered", async () => {
    useHandlers();
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await heading(g.check.heading);
    expect(button(g.check.start)).toBeVisible();
  });
});

describe("the Check report", () => {
  it("is in a live region that is there before the report arrives", async () => {
    useHandlers();
    const { held, release } = deferred();
    server.use(
      http.post("/api/copy/dry-run", async () => {
        await held;
        return HttpResponse.json(REPORT);
      }),
    );
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await heading(g.check.loadingHeading);
    const region = screen.getByRole("status");
    expect(region).toHaveTextContent("");

    release();

    await within(region).findByText(g.check.newGames(2));
    expect(region).toBeInTheDocument();
  });

  it.each([
    [3, 1, [g.check.bios(2), g.check.biosMissing(1)]],
    [2, 2, [g.check.biosMissing(2)]],
    [2, 0, [g.check.bios(2)]],
  ])(
    "with %i BIOS files and %i missing, promises only what will happen",
    async (bios, missing, lines) => {
      useHandlers({ counts: { bios, bios_missing_source: missing } });
      const user = userEvent.setup();
      renderGuide();
      await walkToCheck(user);
      await heading(g.check.heading);
      const shown = screen.getByRole("status").textContent;
      for (const line of lines) expect(shown).toContain(line);
      expect(shown?.match(/BIOS/g)).toHaveLength(lines.length);
    },
  );

  it("offers to add to the game list only when it can start", async () => {
    useHandlers({ counts: { new: 0 }, summary: { existing_playlist: true } });
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await heading(g.check.nothingNewHeading);
    expect(screen.queryByText(g.check.existingPlaylist)).toBeNull();
  });

  it("still says it when Start is offered", async () => {
    useHandlers({ summary: { existing_playlist: true } });
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await screen.findByText(g.check.existingPlaylist);
  });
});

describe("Start while it waits for its answer", () => {
  it("cannot be pressed twice, and leaves nowhere to lose its answer", async () => {
    const starts = useHandlers();
    const { held, release } = deferred();
    server.use(
      http.post("/api/copy/start", async () => {
        starts.push({ selected_names: [] });
        await held;
        return HttpResponse.json(
          { code: "boom", detail: "it broke", fields: [] },
          { status: 500 },
        );
      }),
    );
    const user = userEvent.setup();
    renderGuide();
    await walkToCheck(user);
    await press(user, g.check.start);

    await screen.findByText(g.check.starting);
    expect(button(g.check.start)).toHaveAttribute("aria-disabled", "true");
    expect(button(g.back)).toBeNull();
    expect(screen.queryByRole("link", { name: g.exit })).toBeNull();
    await user.click(button(g.check.start)!);
    expect(starts).toHaveLength(1);

    release();

    expect(await screen.findByRole("alert")).toHaveTextContent("it broke");
    expect(button(g.check.start)).not.toHaveAttribute("aria-disabled");
    expect(button(g.back)).toBeVisible();
    expect(screen.getByRole("link", { name: g.exit })).toBeVisible();
    expect(screen.queryByText(g.check.starting)).toBeNull();
  });
});

describe("a chosen folder", () => {
  function folderHandlers() {
    server.use(
      http.get("/api/fs/home", () => HttpResponse.json({ path: "/home/me" })),
      http.get("/api/fs/drive-roots", () => HttpResponse.json({ roots: [] })),
      http.get("/api/fs/allowed-roots", () => HttpResponse.json({ roots: [] })),
      http.get("/api/fs/list", () =>
        HttpResponse.json({ path: "/mnt/new", parent: null, entries: [] }),
      ),
    );
  }

  it("that is refused shows the actual reason on the step", async () => {
    useHandlers();
    folderHandlers();
    server.use(
      http.patch("/api/config", () =>
        HttpResponse.json(
          {
            code: "config_invalid",
            detail: "config validation failed",
            fields: [
              {
                loc: "paths.retroarch_playlist",
                msg: "parent directory does not exist",
                type: "path_not_found",
              },
            ],
          },
          { status: 422 },
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
    expect(alert).toHaveTextContent(
      strings.errors.rejectedPath["paths.retroarch_playlist"],
    );
    expect(alert).not.toHaveTextContent(/below/);
  });

  it("that is saved is heard", async () => {
    useHandlers();
    folderHandlers();
    const saved = {
      ...appConfig,
      paths: { ...appConfig.paths, dest_roms: "/mnt/new" },
    };
    server.use(
      http.patch("/api/config", () => {
        server.use(http.get("/api/config", () => HttpResponse.json(saved)));
        return HttpResponse.json(saved);
      }),
    );
    const user = userEvent.setup();
    renderGuide();
    await press(user, g.which.everything);
    await press(user, g.finds.copyThese);
    await heading(g.where.heading);
    const region = await screen.findByRole("status");
    expect(region).toHaveTextContent(appConfig.paths.dest_roms);

    await press(user, g.where.choose);
    await press(user, strings.settings.fsBrowserUseDirectory);

    await waitFor(() => expect(region).toHaveTextContent("/mnt/new"));
  });
});

describe("words", () => {
  it("the BIOS warning has no jargon", () => {
    expect(strings.copy.biosWarning("sf2", "missing_from_listxml")).not.toMatch(
      /listxml/,
    );
  });

  it("the empty Library names no sidebar, which simple view lacks", () => {
    expect(strings.library.emptyHint).not.toMatch(/sidebar/);
  });
});
