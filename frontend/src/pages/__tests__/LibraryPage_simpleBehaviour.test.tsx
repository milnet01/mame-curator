/**
 * mame-curator-1156 — small simple-view behaviours, as the user decided on
 * 2026-11-10: no walkthrough while its switch is hidden, focus stays on the
 * view button, and a search counts as a filter (spec §4.7).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LIBRARY_VIEW_KEY } from "@/lib/libraryView";
import { strings } from "@/strings";
import { http, HttpResponse, server } from "@/test/handlers";
import { LibraryPage } from "../LibraryPage";
import {
  libraryPageBaseHandlers,
  makeFakeCart,
  makeGameCard,
  makeGamesPage,
  renderLibraryPageTree,
} from "./_libraryPageFixtures";

const s = strings.guide.simpleLibrary;

let marked: string[] = [];

// The virtualizer draws no rows in a box of zero size, and jsdom has only those.
beforeEach(() => {
  localStorage.clear();
  marked = [];
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1200);
  server.use(
    http.get("/api/games", () =>
      HttpResponse.json(
        makeGamesPage([
          makeGameCard({ short_name: "pacman", description: "Pac-Man" }),
          makeGameCard({ short_name: "galaga", description: "Galaga" }),
        ]),
      ),
    ),
    http.post("/api/state", async ({ request }) => {
      const body = (await request.json()) as { short_name: string };
      marked.push(body.short_name);
      return HttpResponse.json({ entries: { [body.short_name]: "reviewed" } });
    }),
    ...libraryPageBaseHandlers(),
  );
});
afterEach(() => vi.restoreAllMocks());

function renderPage(view: "simple" | "full") {
  localStorage.setItem(LIBRARY_VIEW_KEY, view);
  return renderLibraryPageTree(
    <LibraryPage
      cart={makeFakeCart()}
      cartExpanded={false}
      onCartExpandedChange={() => {}}
    />,
  );
}

describe("LibraryPage: simple-view behaviours (mame-curator-1156)", () => {
  it("R in simple view marks the game and leaves focus on it", async () => {
    const user = userEvent.setup();
    renderPage("simple");
    const first = await screen.findByRole("button", { name: "Pac-Man" });
    first.focus();
    await user.keyboard("r");
    await waitFor(() => expect(marked).toEqual(["pacman"]));
    // Give a walkthrough the chance to move focus before checking it did not.
    await new Promise((resolve) => requestAnimationFrame(resolve));
    expect(first).toHaveFocus();
  });

  it("R in full view still moves on to the next game when walkthrough is on", async () => {
    const user = userEvent.setup();
    renderPage("full");
    const first = await screen.findByRole("button", { name: "Pac-Man" });
    first.focus();
    await user.keyboard("r");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Galaga" })).toHaveFocus(),
    );
  });

  it("More options puts focus on Fewer options, and back again", async () => {
    const user = userEvent.setup();
    renderPage("simple");
    await user.click(
      await screen.findByRole("button", { name: s.moreOptions }),
    );
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: s.fewerOptions }),
      ).toHaveFocus(),
    );
    await user.click(screen.getByRole("button", { name: s.fewerOptions }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: s.moreOptions })).toHaveFocus(),
    );
  });

  it("opening the Library does not move focus to a view button", async () => {
    renderPage("simple");
    await screen.findByRole("button", { name: "Pac-Man" });
    await new Promise((resolve) => requestAnimationFrame(resolve));
    expect(
      screen.getByRole("button", { name: s.moreOptions }),
    ).not.toHaveFocus();
  });

  it("a search alone says Some filters are on, as spec §4.7 asks", async () => {
    const user = userEvent.setup();
    renderPage("simple");
    await screen.findByRole("button", { name: "Pac-Man" });
    expect(screen.queryByText(s.filtersOn)).not.toBeInTheDocument();
    await user.type(screen.getByRole("searchbox"), "pac");
    expect(await screen.findByText(s.filtersOn)).toBeVisible();
  });
});
