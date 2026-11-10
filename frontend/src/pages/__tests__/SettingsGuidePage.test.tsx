/**
 * mame-curator-1147 — changing a setting one topic at a time, at
 * /settings/guide. Saves go through PATCH /api/config, as Settings saves.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router";
import { toast } from "sonner";

import type { AppConfigResponse } from "@/api/types";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import { SettingsGuidePage } from "../SettingsGuidePage";
import { config as baseConfig } from "./_settingsPageFixtures";

vi.mock("sonner", async (original) => ({
  ...(await original<typeof import("sonner")>()),
  toast: { success: vi.fn(), warning: vi.fn(), error: vi.fn() },
}));

const t = strings.guide.settings;
const HOME = "/home/me";
const config: AppConfigResponse = {
  ...baseConfig,
  filters: {
    ...baseConfig.filters,
    region_priority: ["World", "USA", "Europe"],
  },
};

const refused = () =>
  HttpResponse.json(
    { code: "internal_error", detail: "The disk is full.", fields: [] },
    { status: 500 },
  );

/** Serves the config; each PATCH answers as `replies` says, in turn. */
function serve(...replies: (() => Response)[]) {
  const patches: Partial<AppConfigResponse>[] = [];
  const entry = (name: string) => ({
    name,
    path: `${HOME}/${name}`,
    is_dir: true,
    hidden: false,
    size: null,
    mtime: "2026-05-01T00:00:00Z",
  });
  server.use(
    http.get("/api/config", () => HttpResponse.json(config)),
    http.patch("/api/config", async ({ request }) => {
      patches.push((await request.json()) as Partial<AppConfigResponse>);
      const reply = replies.shift();
      return reply ? reply() : HttpResponse.json(config);
    }),
    http.get("/api/fs/home", () => HttpResponse.json({ path: HOME })),
    http.get("/api/fs/roots", () => HttpResponse.json({ roots: [] })),
    http.get("/api/fs/allowed-roots", () => HttpResponse.json({ roots: [] })),
    http.get("/api/fs/list", ({ request }) =>
      HttpResponse.json({
        path: new URL(request.url).searchParams.get("path"),
        parent: null,
        entries: [entry("copied"), entry("roms")],
      }),
    ),
  );
  return patches;
}

function renderGuide() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/settings/guide"]}>
        <Routes>
          <Route path="/settings/guide" element={<SettingsGuidePage />} />
          <Route path="/settings" element={<p>the settings page</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const heading = (name: string) => screen.findByRole("heading", { name });
const button = (name: string | RegExp) => screen.findByRole("button", { name });
const press = async (user: UserEvent, name: string | RegExp) =>
  user.click(await button(name));
const starting = (text: string) =>
  new RegExp(`^${text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}`);

async function pickFolder(user: UserEvent, name: string) {
  await press(user, t.folders.choose);
  const dialog = await screen.findByRole("dialog");
  await user.click(
    await within(dialog).findByRole("button", { name: starting(name) }),
  );
  await user.click(
    within(dialog).getByRole("button", {
      name: strings.settings.fsBrowserUseDirectory,
    }),
  );
}

beforeEach(() => vi.clearAllMocks());

describe("the Settings guide", () => {
  it("asks what to change, offering each topic, with a way back to Settings", async () => {
    serve();
    const user = userEvent.setup();
    renderGuide();
    await heading(t.heading);
    for (const topic of Object.values(t.topics)) {
      expect(await button(topic)).toBeInTheDocument();
    }
    await user.click(screen.getByRole("link", { name: t.toSettings }));
    expect(await screen.findByText("the settings page")).toBeInTheDocument();
  });

  it("says when the settings could not be loaded, with a way back", async () => {
    server.use(http.get("/api/config", refused));
    renderGuide();
    await heading(strings.guide.loadFailed);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: t.toSettings })).toHaveAttribute(
      "href",
      "/settings",
    );
  });

  it("leaves a kind of game in, saving only that switch, and says so", async () => {
    const patches = serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.leaveOut);
    await heading(t.leaveOut.heading);
    const adults = t.leaveOut.kinds.drop_mature;
    expect(await button(starting(adults.name))).toHaveTextContent(
      t.leaveOut.leftOutNow,
    );
    await press(user, starting(adults.name));
    await heading(t.leaveOut.question(adults.inSentence));
    expect(screen.getByText(adults.help)).toBeInTheDocument();
    expect(await button(starting(t.leaveOut.yes))).toHaveTextContent(t.inUse);
    expect(await button(t.leaveOut.no)).not.toHaveTextContent(t.inUse);

    await press(user, t.leaveOut.no);
    await heading(t.leaveOut.included(adults.name));
    expect(patches).toEqual([
      { filters: { ...config.filters, drop_mature: false } },
    ]);
    // The screen says it, so no message pops up as well.
    expect(toast.success).not.toHaveBeenCalled();
    await press(user, t.changeMore);
    await heading(t.heading);
  });

  it("leaves out compilations (mame-curator-1216)", async () => {
    const patches = serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.leaveOut);
    const compilations = t.leaveOut.kinds.drop_multigame;
    expect(await button(starting(compilations.name))).toHaveTextContent(
      t.leaveOut.includedNow,
    );
    await press(user, starting(compilations.name));
    await heading(t.leaveOut.question(compilations.inSentence));
    await press(user, starting(t.leaveOut.yes));
    await heading(t.leaveOut.leftOut(compilations.name));
    expect(patches).toEqual([
      { filters: { ...config.filters, drop_multigame: true } },
    ]);
  });

  it("keeps only the languages ticked (mame-curator-1217)", async () => {
    const patches = serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.leaveOut);
    const languages = t.leaveOut.languages;
    expect(await button(starting(languages.name))).toHaveTextContent(
      languages.everyNow,
    );
    await press(user, starting(languages.name));
    await heading(strings.guide.languages.heading);
    await press(user, starting("English"));
    await press(user, strings.guide.languages.done);
    await heading(languages.saved(["English"]));
    expect(patches).toEqual([
      { filters: { ...config.filters, keep_languages: ["English"] } },
    ]);
  });

  it("saves nothing when the choice is the setting in use", async () => {
    const patches = serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.cart);
    await heading(t.cart.heading);
    await press(user, starting(t.cart.options.on_success));
    await heading(t.unchangedHeading);
    expect(screen.getByText(t.nothingChanged)).toBeInTheDocument();
    expect(patches).toEqual([]);
  });

  it("puts the chosen region first and keeps the rest in order", async () => {
    const patches = serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.region);
    await heading(t.region.heading);
    expect(await button(starting("World"))).toHaveTextContent(
      t.region.firstNow,
    );
    await press(user, starting("Europe"));
    await heading(t.region.saved("Europe"));
    expect(screen.getByText(t.region.yoursStay)).toBeInTheDocument();
    expect(patches).toEqual([
      {
        filters: {
          ...config.filters,
          region_priority: ["Europe", "World", "USA"],
        },
      },
    ]);
  });

  it("changes what the cart does after a copy", async () => {
    const patches = serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.cart);
    expect(await button(starting(t.cart.options.on_success))).toHaveTextContent(
      t.inUse,
    );
    await press(user, starting(t.cart.options.never));
    await heading(t.cart.saved.never);
    expect(patches).toEqual([
      { ui: { ...config.ui, cart_clear_on_copy: "never" } },
    ]);
  });

  it("copies games to a newly chosen folder", async () => {
    const patches = serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.folders);
    await heading(t.folders.heading);
    expect(await button(starting(t.folders.dest))).toHaveTextContent(
      config.paths.dest_roms,
    );
    await press(user, starting(t.folders.dest));
    // The setup wizard's words for the same question (mame-curator-1145).
    await heading(strings.guide.setup.dest.heading);
    expect(screen.getByText(config.paths.dest_roms)).toBeInTheDocument();
    await pickFolder(user, "copied");
    await heading(t.folders.destSaved(`${HOME}/copied`));
    expect(patches).toEqual([
      { paths: { ...config.paths, dest_roms: `${HOME}/copied` } },
    ]);
  });

  it("refuses the games folder as the copy folder, before saving", async () => {
    const patches = serve();
    server.use(
      http.get("/api/config", () =>
        HttpResponse.json({
          ...config,
          paths: { ...config.paths, source_roms: `${HOME}/roms` },
        }),
      ),
    );
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.folders);
    await press(user, starting(t.folders.dest));
    await pickFolder(user, "roms");
    expect(await screen.findByRole("alert")).toHaveTextContent(
      t.folders.sameAsGames,
    );
    expect(patches).toEqual([]);
  });

  it("says a failed save changed nothing, and tries the same change again", async () => {
    const patches = serve(refused);
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.cart);
    await press(user, starting(t.cart.options.always));
    await heading(t.failedHeading);
    expect(screen.getByRole("alert")).toHaveTextContent("The disk is full.");
    expect(screen.getByText(t.nothingChanged)).toBeInTheDocument();
    expect(toast.error).not.toHaveBeenCalled();

    await press(user, t.tryAgain);
    await heading(t.cart.saved.always);
    await waitFor(() => expect(patches).toHaveLength(2));
    expect(patches[1]).toEqual(patches[0]);
  });

  it("goes back from a topic to the list of topics", async () => {
    serve();
    const user = userEvent.setup();
    renderGuide();
    await press(user, t.topics.region);
    await heading(t.region.heading);
    await press(user, strings.guide.back);
    await heading(t.heading);
  });
});
