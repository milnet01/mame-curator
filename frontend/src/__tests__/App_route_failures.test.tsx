/**
 * mame-curator-1144 — Settings, Help and Sessions say when something fails,
 * with a way forward, and the words stay on the page after a toast has gone.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent, { type UserEvent } from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";

import { ShellWithPalette } from "@/App";
import { GUIDE_SEEN_KEY } from "@/lib/guideState";
import { libraryPageBaseHandlers } from "@/pages/__tests__/_libraryPageFixtures";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";

const boom = () =>
  HttpResponse.json(
    { code: "boom", detail: "it broke", fields: [] },
    { status: 500 },
  );

const session = {
  include_genres: [],
  include_publishers: [],
  include_developers: [],
  include_year_range: null,
};
const LISTING = {
  active: "shooters",
  sessions: { fighters: session, shooters: session },
};

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <ShellWithPalette />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const retry = (user: UserEvent) =>
  user.click(screen.getByRole("button", { name: strings.common.retry }));

beforeEach(() => {
  // jsdom has no matchMedia, and the shell's Toaster reads it.
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  localStorage.clear();
  localStorage.setItem(GUIDE_SEEN_KEY, "true");
  server.use(
    ...libraryPageBaseHandlers(),
    http.get("/api/help/index", () =>
      HttpResponse.json({
        topics: [{ slug: "start", title: "Getting started" }],
      }),
    ),
    http.get("/api/updates/check", () => HttpResponse.json({})),
  );
});

describe("a page that cannot load", () => {
  it("Settings says so instead of loading forever, and can try again", async () => {
    server.use(http.get("/api/config", boom));
    const user = userEvent.setup();
    renderAt("/settings");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(strings.settings.loadError);
    expect(alert).toHaveTextContent(strings.common.loadFailedHint);
    expect(screen.queryByText(strings.loading.settings)).toBeNull();

    server.use(
      ...libraryPageBaseHandlers(),
      http.get("/api/config/snapshots", () => HttpResponse.json({ items: [] })),
    );
    await retry(user);

    await waitFor(() =>
      expect(screen.queryByText(strings.settings.loadError)).toBeNull(),
    );
  });

  it.each([
    ["Sessions", "/sessions", "/api/sessions", strings.sessions.loadError],
    ["Help", "/help", "/api/help/index", strings.help.loadError],
  ])(
    "%s says so in an alert, and can try again",
    async (_name, path, url, words) => {
      server.use(http.get(url, boom));
      const user = userEvent.setup();
      renderAt(path);

      const alert = await screen.findByRole("alert");
      expect(alert).toHaveTextContent(words);
      expect(alert).toHaveTextContent(strings.common.loadFailedHint);

      server.use(
        http.get("/api/sessions", () => HttpResponse.json(LISTING)),
        http.get("/api/help/index", () =>
          HttpResponse.json({
            topics: [{ slug: "start", title: "Getting started" }],
          }),
        ),
      );
      await retry(user);

      await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    },
  );
});

describe("a retry", () => {
  it("says it is retrying, and a second press does not ask again", async () => {
    let requests = 0;
    let finish = () => {};
    const held = new Promise<void>((resolve) => {
      finish = resolve;
    });
    server.use(
      http.get("/api/sessions", async () => {
        requests += 1;
        if (requests > 1) await held;
        return boom();
      }),
    );
    const user = userEvent.setup();
    renderAt("/sessions");
    await screen.findByRole("alert");
    await retry(user);

    const retrying = await screen.findByRole("button", {
      name: strings.common.retrying,
    });
    await user.click(retrying);
    finish();

    await screen.findByRole("button", { name: strings.common.retry });
    expect(requests).toBe(2);
  });
});

describe("a help topic that cannot load", () => {
  it("says so instead of leaving an empty pane, and can try again", async () => {
    server.use(http.get("/api/help/start", boom));
    const user = userEvent.setup();
    renderAt("/help?topic=start");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(strings.help.topicLoadError);
    expect(
      within(screen.getByRole("article")).getByRole("alert"),
    ).toBeVisible();

    server.use(
      http.get("/api/help/start", () =>
        HttpResponse.json({
          slug: "start",
          title: "Getting started",
          html: "<p>Welcome</p>",
        }),
      ),
    );
    await retry(user);

    expect(await screen.findByText("Welcome")).toBeVisible();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("a session action that fails", () => {
  beforeEach(() => {
    server.use(http.get("/api/sessions", () => HttpResponse.json(LISTING)));
  });

  it("says Activate failed, and why, and the next try clears it", async () => {
    server.use(http.post("/api/sessions/fighters/activate", boom));
    const user = userEvent.setup();
    renderAt("/sessions");
    const activate = strings.sessions.actions.activateAriaLabel("fighters");

    await user.click(await screen.findByRole("button", { name: activate }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      strings.sessions.activateFailed("fighters"),
    );
    expect(alert).toHaveTextContent("it broke");
    expect(alert).toHaveTextContent(strings.common.tryAgain);

    let finish = () => {};
    const held = new Promise<void>((resolve) => {
      finish = resolve;
    });
    server.use(
      http.post("/api/sessions/fighters/activate", async () => {
        await held;
        return HttpResponse.json(LISTING);
      }),
    );
    await user.click(screen.getByRole("button", { name: activate }));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    finish();
  });

  it("says Deactivate failed", async () => {
    server.use(http.post("/api/sessions/_deactivate", boom));
    const user = userEvent.setup();
    renderAt("/sessions");

    await user.click(
      await screen.findByRole("button", {
        name: strings.sessions.actions.deactivate,
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      strings.sessions.deactivateFailed,
    );
  });

  it("says Delete failed, once the dialog has closed", async () => {
    server.use(http.delete("/api/sessions/fighters", boom));
    const user = userEvent.setup();
    renderAt("/sessions");

    await user.click(
      await screen.findByRole("button", {
        name: strings.sessions.actions.deleteAriaLabel("fighters"),
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: strings.destructive.deleteSession("fighters"),
      }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      strings.sessions.deleteFailed("fighters"),
    );
    expect(screen.getByText("fighters")).toBeVisible();
  });
});
