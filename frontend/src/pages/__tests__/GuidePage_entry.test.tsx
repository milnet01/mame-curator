/**
 * mame-curator-1144 INV-1, INV-14 — when the guide opens by itself.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, useLocation } from "react-router";

import { ShellWithPalette } from "@/App";
import { GUIDE_SEEN_KEY } from "@/lib/guideState";
import { LIBRARY_VIEW_KEY } from "@/lib/libraryView";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import {
  libraryPageBaseHandlers,
  makeGamesPage,
  setupCheckFixture,
} from "./_libraryPageFixtures";

function Where() {
  return <div data-testid="where">{useLocation().pathname}</div>;
}

function renderApp(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <ShellWithPalette />
        <Where />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const at = () => screen.getByTestId("where").textContent;

afterEach(() => {
  vi.unstubAllGlobals();
});

beforeEach(() => {
  // jsdom has no matchMedia, and the shell's Toaster reads it.
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  localStorage.clear();
  localStorage.setItem(LIBRARY_VIEW_KEY, "full");
  server.use(
    ...libraryPageBaseHandlers(),
    http.get("/api/games", () => HttpResponse.json(makeGamesPage([]))),
    http.get("/api/help/index", () => HttpResponse.json({ topics: [] })),
    http.get("/api/updates/check", () => HttpResponse.json({})),
  );
});

describe("the guide's first opening", () => {
  it("INV-1: opening / with the flag unset lands on /start", async () => {
    renderApp("/");
    await screen.findByRole("heading", { name: strings.guide.which.heading });
    expect(at()).toBe("/start");
  });

  it("INV-1: marks itself seen, so the next load stays on /", async () => {
    renderApp("/");
    await screen.findByRole("heading", { name: strings.guide.which.heading });
    expect(localStorage.getItem(GUIDE_SEEN_KEY)).not.toBeNull();
  });

  it("INV-1: with the flag set, / stays", async () => {
    localStorage.setItem(GUIDE_SEEN_KEY, "true");
    renderApp("/");
    await screen.findByTestId("library-grid");
    expect(at()).toBe("/");
  });

  it("INV-1: no other route redirects", async () => {
    server.use(
      http.get("/api/config/snapshots", () => HttpResponse.json({ items: [] })),
    );
    renderApp("/help");
    await waitFor(() => expect(at()).toBe("/help"));
    expect(
      screen.queryByRole("heading", { name: strings.guide.which.heading }),
    ).not.toBeInTheDocument();
  });

  it("INV-1: leaving the guide for / stays on / on that same load", async () => {
    const user = userEvent.setup();
    renderApp("/");
    await screen.findByRole("heading", { name: strings.guide.which.heading });
    await user.click(screen.getByRole("link", { name: strings.guide.exit }));
    await screen.findByTestId("library-grid");
    expect(at()).toBe("/");
  });

  it("INV-14: in setup mode only the setup step shows, and the flag stays unset", async () => {
    server.use(
      http.get("/api/setup/check", () =>
        HttpResponse.json({ ...setupCheckFixture, setup_required: true }),
      ),
    );
    renderApp("/");
    await screen.findByRole("heading", { name: strings.guide.setup.heading });
    expect(
      screen.getByRole("link", { name: strings.guide.setup.openSettings }),
    ).toHaveAttribute("href", "/settings?tab=paths");
    expect(
      screen.queryByRole("button", { name: strings.guide.which.everything }),
    ).not.toBeInTheDocument();
    expect(localStorage.getItem(GUIDE_SEEN_KEY)).toBeNull();
  });

  it("offers Start here in the top menu and reopens at the first step", async () => {
    localStorage.setItem(GUIDE_SEEN_KEY, "true");
    const user = userEvent.setup();
    renderApp("/");
    await screen.findByTestId("library-grid");
    const start = screen.getAllByRole("link", {
      name: strings.guide.nav.startHere,
    })[0];
    await user.click(start);
    await screen.findByRole("heading", { name: strings.guide.which.heading });
    expect(at()).toBe("/start");
  });
});
