/**
 * mame-curator-1145 INV-6, 7, 8, 9, 10, 11, 12 — the setup wizard. Real focus,
 * real picker and a real server are frontend/e2e/setup-wizard.spec.ts.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import { GUIDE_SEEN_KEY } from "@/lib/guideState";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import { GuidePage } from "../GuidePage";
import {
  libraryPageBaseHandlers,
  setupCheckFixture,
} from "./_libraryPageFixtures";
import { config as appConfig } from "./_settingsPageFixtures";

const g = strings.guide;
const s = strings.guide.setup;
const HOME = "/home/me";
const entry = (name: string, is_dir: boolean) => ({
  name,
  path: `${HOME}/${name}`,
  is_dir,
  size: null,
  mtime: "2026-05-01T00:00:00Z",
});

interface Seen {
  patches: { paths: Record<string, string> }[];
  gamesFetched: number;
}

type PatchReply = (body: { paths: Record<string, string> }) => Response;

/** A server in setup mode, until a PATCH reply says the games loaded. */
function useSetupServer(reply?: PatchReply): Seen {
  const seen: Seen = { patches: [], gamesFetched: 0 };
  let setupRequired = true;
  server.use(
    http.get("/api/setup/check", () =>
      HttpResponse.json({
        ...setupCheckFixture,
        setup_required: setupRequired,
      }),
    ),
    http.get("/api/config", () => HttpResponse.json(appConfig)),
    http.patch("/api/config", async ({ request }) => {
      const body = (await request.json()) as {
        paths: Record<string, string>;
      };
      seen.patches.push(body);
      if (reply) return reply(body);
      setupRequired = false;
      return HttpResponse.json({ ...appConfig, restart_required: false });
    }),
    http.get("/api/fs/home", () => HttpResponse.json({ path: HOME })),
    http.get("/api/fs/roots", () => HttpResponse.json({ roots: [] })),
    http.get("/api/fs/allowed-roots", () => HttpResponse.json({ roots: [] })),
    http.get("/api/fs/list", ({ request }) => {
      const path = new URL(request.url).searchParams.get("path");
      return HttpResponse.json({
        path,
        parent: null,
        entries:
          path === HOME
            ? [
                entry("roms", true),
                entry("copied", true),
                entry("mame.xml", false),
              ]
            : [],
      });
    }),
    http.get("/api/library/facets", () =>
      HttpResponse.json({
        genres: [],
        publishers: [],
        developers: [],
        letters: [],
      }),
    ),
    ...libraryPageBaseHandlers(),
  );
  return seen;
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

const heading = (name: string) => screen.findByRole("heading", { name });
const press = async (user: UserEvent, name: string | RegExp) =>
  user.click(await screen.findByRole("button", { name }));

async function pickFolder(user: UserEvent, chooseLabel: string, name: string) {
  await press(user, chooseLabel);
  const dialog = await screen.findByRole("dialog");
  await user.click(
    await within(dialog).findByRole("button", {
      name: new RegExp(`^${name}`),
    }),
  );
  await user.click(
    within(dialog).getByRole("button", {
      name: strings.settings.fsBrowserUseDirectory,
    }),
  );
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
}

async function pickFile(user: UserEvent, chooseLabel: string, name: string) {
  await press(user, chooseLabel);
  const dialog = await screen.findByRole("dialog");
  await user.click(
    await within(dialog).findByRole("button", {
      name: new RegExp(`^${name}`),
    }),
  );
  await waitFor(() =>
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
  );
}

async function walkToLastStep(user: UserEvent) {
  await heading(s.games.heading);
  await pickFolder(user, s.games.choose, "roms");
  await press(user, s.games.yes);
  await heading(s.list.heading);
  await pickFile(user, s.list.choose, "mame.xml");
  await press(user, s.list.yes);
  await heading(s.dest.heading);
}

beforeEach(() => {
  localStorage.clear();
});

describe("the setup wizard", () => {
  it("INV-6: asks three questions in order, and nothing of the guide", async () => {
    useSetupServer();
    const user = userEvent.setup();
    renderGuide();

    await heading(s.games.heading);
    expect(screen.getByText(s.games.help)).toBeInTheDocument();
    expect(screen.getByText(g.stepOf(1, 3))).toBeInTheDocument();
    await pickFolder(user, s.games.choose, "roms");
    await heading(s.games.chosenHeading);
    expect(screen.getByText(`${HOME}/roms`)).toHaveAttribute("role", "status");

    await press(user, s.games.yes);
    await heading(s.list.heading);
    expect(screen.getByText(s.list.help)).toBeInTheDocument();
    expect(screen.getByText(g.stepOf(2, 3))).toBeInTheDocument();
    await pickFile(user, s.list.choose, "mame.xml");
    await heading(s.list.chosenHeading);

    await press(user, s.list.yes);
    await heading(s.dest.heading);
    expect(screen.getByText(s.dest.help)).toBeInTheDocument();
    expect(screen.getByText(g.stepOf(3, 3))).toBeInTheDocument();
    await pickFolder(user, s.dest.choose, "copied");
    await heading(s.dest.chosenHeading);

    expect(
      screen.queryByRole("button", { name: g.which.everything }),
    ).not.toBeInTheDocument();
    expect(localStorage.getItem(GUIDE_SEEN_KEY)).toBeNull();
  });

  it("INV-7: one save, sent last, holds all four answers", async () => {
    const seen = useSetupServer();
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await pickFolder(user, s.dest.choose, "copied");
    expect(seen.patches).toHaveLength(0);

    await press(user, s.dest.yes);
    await waitFor(() => expect(seen.patches).toHaveLength(1));
    expect(seen.patches[0]?.paths).toMatchObject({
      source_roms: `${HOME}/roms`,
      source_dat: `${HOME}/mame.xml`,
      dest_roms: `${HOME}/copied`,
      retroarch_playlist: `${HOME}/copied/mame.lpl`,
    });
    await heading(g.which.heading);
    expect(seen.patches).toHaveLength(1);
  });

  it("INV-7: leaving early saves nothing", async () => {
    const seen = useSetupServer();
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await user.click(screen.getByRole("link", { name: g.exit }));
    expect(seen.patches).toHaveLength(0);
  });

  it("INV-7: keeps a placed playlist when the destination has not changed", async () => {
    const seen = useSetupServer();
    server.use(
      http.get("/api/config", () =>
        HttpResponse.json({
          ...appConfig,
          paths: {
            ...appConfig.paths,
            dest_roms: `${HOME}/copied`,
            retroarch_playlist: "/placed/by/me.lpl",
          },
        }),
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await pickFolder(user, s.dest.choose, "copied");
    await press(user, s.dest.yes);
    await waitFor(() => expect(seen.patches).toHaveLength(1));
    expect(seen.patches[0]?.paths.retroarch_playlist).toBe("/placed/by/me.lpl");
  });

  it("INV-8: a good save leads to the guide's first question, without a page load", async () => {
    useSetupServer();
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await pickFolder(user, s.dest.choose, "copied");
    await press(user, s.dest.yes);
    await heading(g.which.heading);
    await waitFor(() =>
      expect(localStorage.getItem(GUIDE_SEEN_KEY)).not.toBeNull(),
    );
  });

  it("INV-9: an unreadable game list returns to its step and keeps the others", async () => {
    let bad = true;
    const seen = useSetupServer(() => {
      const restart_required = bad;
      bad = false;
      return HttpResponse.json({ ...appConfig, restart_required });
    });
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await pickFolder(user, s.dest.choose, "copied");
    await press(user, s.dest.yes);

    await heading(s.list.heading);
    expect(await screen.findByRole("alert")).toHaveTextContent(s.notAGameList);
    expect(screen.getByText(g.stepOf(2, 3))).toBeInTheDocument();

    await pickFile(user, s.list.choose, "mame.xml");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    await press(user, s.list.yes);
    await heading(s.dest.chosenHeading);
    await press(user, s.dest.yes);
    await waitFor(() => expect(seen.patches).toHaveLength(2));
    expect(seen.patches[1]?.paths).toMatchObject({
      source_roms: `${HOME}/roms`,
      dest_roms: `${HOME}/copied`,
    });
  });

  it("INV-9: a refused save stays on the last step and says why", async () => {
    useSetupServer(() =>
      HttpResponse.json(
        {
          code: "config_invalid",
          detail: "config validation failed",
          fields: [
            {
              loc: "paths.source_roms",
              msg: "path does not exist",
              type: "path_not_found",
            },
          ],
        },
        { status: 422 },
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await pickFolder(user, s.dest.choose, "copied");
    await press(user, s.dest.yes);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      strings.errors.rejectedPath["paths.source_roms"],
    );
    await heading(s.dest.chosenHeading);
    expect(screen.getByRole("button", { name: g.back })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: g.exit })).toBeInTheDocument();
  });

  it("INV-9: a failed save says so", async () => {
    useSetupServer(() =>
      HttpResponse.json(
        { code: "something_else", detail: "it broke", fields: [] },
        { status: 500 },
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await pickFolder(user, s.dest.choose, "copied");
    await press(user, s.dest.yes);
    expect(await screen.findByRole("alert")).toHaveTextContent("it broke");
    expect(screen.getByRole("button", { name: s.dest.yes })).toBeEnabled();
  });

  it("INV-10: every step has the exit, later steps have Back, and neither shows during the save", async () => {
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    let saves = 0;
    useSetupServer();
    server.use(
      http.patch("/api/config", async () => {
        saves += 1;
        await held;
        return HttpResponse.json({ ...appConfig, restart_required: true });
      }),
    );
    const user = userEvent.setup();
    renderGuide();

    await heading(s.games.heading);
    expect(screen.getByRole("link", { name: g.exit })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: g.back }),
    ).not.toBeInTheDocument();

    await pickFolder(user, s.games.choose, "roms");
    await press(user, s.games.yes);
    await heading(s.list.heading);
    expect(screen.getByRole("button", { name: g.back })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: g.exit })).toBeInTheDocument();

    await press(user, g.back);
    await heading(s.games.chosenHeading);
    await press(user, s.games.yes);
    await pickFile(user, s.list.choose, "mame.xml");
    await press(user, s.list.yes);
    await heading(s.dest.heading);
    expect(screen.getByRole("button", { name: g.back })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: g.exit })).toBeInTheDocument();

    await pickFolder(user, s.dest.choose, "copied");
    await press(user, s.dest.yes);
    await screen.findByText(s.reading);
    expect(
      screen.queryByRole("button", { name: g.back }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: g.exit }),
    ).not.toBeInTheDocument();
    // Pressing again during the save sends no second one.
    await press(user, s.dest.yes);
    expect(saves).toBe(1);
    release();
    await heading(s.list.heading);
  });

  it("INV-11: the games folder cannot also be the destination", async () => {
    const seen = useSetupServer();
    const user = userEvent.setup();
    renderGuide();
    await walkToLastStep(user);
    await pickFolder(user, s.dest.choose, "roms");
    await press(user, s.dest.yes);
    expect(await screen.findByRole("alert")).toHaveTextContent(s.sameFolder);
    expect(seen.patches).toHaveLength(0);
    await heading(s.dest.chosenHeading);
  });

  it("INV-12: the picker asks before looking somewhere new, and is large", async () => {
    useSetupServer();
    server.use(
      http.get("/api/fs/list", () =>
        HttpResponse.json(
          { code: "fs_sandboxed", detail: "outside", fields: [] },
          { status: 403 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await heading(s.games.heading);
    await press(user, s.games.choose);
    const allow = await screen.findByRole("button", {
      name: strings.settings.fsGrantActionLabel(HOME),
    });
    expect(allow).toHaveClass("text-xl");
    expect(screen.getByText(strings.settings.fsGrantTitle)).toBeInTheDocument();
  });

  it("INV-12: the list step shows files, and the picker is large", async () => {
    useSetupServer();
    const user = userEvent.setup();
    renderGuide();
    await heading(s.games.heading);
    await pickFolder(user, s.games.choose, "roms");
    await press(user, s.games.yes);
    await heading(s.list.heading);
    await press(user, s.list.choose);
    const dialog = await screen.findByRole("dialog", {
      name: strings.settings.fsBrowserTitleFile,
    });
    expect(
      await within(dialog).findByRole("button", { name: /^mame\.xml/ }),
    ).toHaveClass("text-xl");
  });

  it("INV-12: the picker is the simple one", async () => {
    useSetupServer();
    server.use(
      http.get("/api/fs/allowed-roots", () =>
        HttpResponse.json({
          roots: [{ id: "a", path: "/data/app-folder", source: "config" }],
        }),
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await heading(s.games.heading);
    await press(user, s.games.choose);
    await screen.findByRole("button", { name: /^roms/ });
    expect(
      screen.queryByRole("button", { name: "/data/app-folder" }),
    ).not.toBeInTheDocument();
  });
});
