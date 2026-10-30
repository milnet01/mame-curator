/**
 * mame-curator-1144 INV-11, INV-12 — the simple Library and the full one.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useLocation, useNavigate } from "react-router";

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
const card = makeGameCard({ short_name: "pacman", description: "Pac-Man" });

/** Every /api/games request the page's own grid made, tile counts excluded.
 *  A filtered request answers with a long list, so the page's "Showing the
 *  first" line tells which query the grid is on, even when a clear goes back
 *  to an answer already cached and sends no request. */
const FILTERED_TOTAL = 5000;
function serveGames(total?: number): URL[] {
  const seen: URL[] = [];
  server.use(
    http.get("/api/games", ({ request }) => {
      const url = new URL(request.url);
      if (url.searchParams.get("page_size") !== "1") seen.push(url);
      const filtered =
        url.searchParams.has("genre") || url.searchParams.has("q");
      return HttpResponse.json({
        ...makeGamesPage([card]),
        total: filtered ? FILTERED_TOTAL : (total ?? 1),
      });
    }),
    ...libraryPageBaseHandlers(),
  );
  return seen;
}

function renderPage(view: "simple" | "full", extra?: React.ReactNode) {
  localStorage.setItem(LIBRARY_VIEW_KEY, view);
  return renderLibraryPageTree(
    <>
      <LibraryPage
        cart={makeFakeCart()}
        cartExpanded={false}
        onCartExpandedChange={() => {}}
      />
      {extra}
    </>,
  );
}

beforeEach(() => {
  localStorage.clear();
});

const FULL_ONLY_TEST_IDS = [
  "library-progress-chip",
  "library-walkthrough-toggle",
];

describe("LibraryPage views", () => {
  it("INV-11: simple view hides the advanced items and keeps search and the copy bar", async () => {
    serveGames();
    renderPage("simple");
    await screen.findByTestId("library-grid");

    for (const id of FULL_ONLY_TEST_IDS) {
      expect(screen.queryByTestId(id)).not.toBeInTheDocument();
    }
    expect(
      screen.queryByRole("complementary", {
        name: strings.a11y.filtersLandmark,
      }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText(strings.library.featured.tiles[0].title),
    ).not.toBeInTheDocument();
    expect(document.getElementById("filters-search")).toBeInstanceOf(
      HTMLInputElement,
    );
    expect(screen.getByRole("link", { name: s.startHere })).toHaveAttribute(
      "href",
      "/start",
    );
  });

  it("INV-11: simple view shows covers whatever the configured layout is", async () => {
    serveGames();
    renderPage("simple");
    expect(await screen.findByTestId("library-grid")).toHaveAttribute(
      "data-layout",
      "covers",
    );
  });

  it("INV-11: full view renders everything it does today", async () => {
    serveGames();
    renderPage("full");
    await screen.findByTestId("library-grid");

    for (const id of FULL_ONLY_TEST_IDS) {
      expect(screen.getByTestId(id)).toBeInTheDocument();
    }
    expect(
      screen.getByRole("complementary", { name: strings.a11y.filtersLandmark }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(strings.library.featured.tiles[0].title),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: s.startHere }),
    ).not.toBeInTheDocument();
  });

  it("More options and Fewer options switch views, and the choice is remembered", async () => {
    serveGames();
    const user = userEvent.setup();
    renderPage("simple");
    await user.click(
      await screen.findByRole("button", { name: s.moreOptions }),
    );
    expect(
      await screen.findByTestId("library-progress-chip"),
    ).toBeInTheDocument();
    expect(localStorage.getItem(LIBRARY_VIEW_KEY)).toBe("full");

    await user.click(screen.getByRole("button", { name: s.fewerOptions }));
    expect(
      screen.queryByTestId("library-progress-chip"),
    ).not.toBeInTheDocument();
    expect(localStorage.getItem(LIBRARY_VIEW_KEY)).toBe("simple");
  });

  it("INV-12: filters set in full view are stated in simple view and can be cleared", async () => {
    const seen = serveGames();
    const user = userEvent.setup();
    renderPage("full");
    await screen.findByTestId("library-grid");

    await user.click(
      screen.getByRole("button", {
        name: new RegExp(strings.library.featured.tiles[1].title),
      }),
    );
    await waitFor(() =>
      expect(seen.at(-1)?.searchParams.get("genre")).toBe(
        "Platform / Fighter Scrolling",
      ),
    );
    await user.click(screen.getByRole("button", { name: s.fewerOptions }));

    expect(await screen.findByText(s.filtersOn)).toBeVisible();
    await user.click(screen.getByRole("button", { name: s.clearFilters }));

    await waitFor(() =>
      expect(
        screen.queryByText(s.showingFirst(1, FILTERED_TOTAL)),
      ).not.toBeInTheDocument(),
    );
    expect(screen.queryByText(s.filtersOn)).not.toBeInTheDocument();
  });

  it("INV-12: Clear filters also empties the search box", async () => {
    const seen = serveGames();
    const user = userEvent.setup();
    renderPage("simple");
    const search = await screen.findByRole("searchbox");
    await user.type(search, "pac");
    await waitFor(() => expect(seen.at(-1)?.searchParams.get("q")).toBe("pac"));

    await user.click(
      await screen.findByRole("button", { name: s.clearFilters }),
    );
    await waitFor(() => expect(search).toHaveValue(""));
    await waitFor(() =>
      expect(
        screen.queryByText(s.showingFirst(1, FILTERED_TOTAL)),
      ).not.toBeInTheDocument(),
    );
  });

  it("states no filters when none are on", async () => {
    serveGames();
    renderPage("simple");
    await screen.findByTestId("library-grid");
    expect(screen.queryByText(s.filtersOn)).not.toBeInTheDocument();
  });

  it("INV-12: a list cut to one page says so", async () => {
    serveGames(5000);
    renderPage("simple");
    expect(await screen.findByText(s.showingFirst(1, 5000))).toBeVisible();
  });

  it("applies a selection the guide sent once, and clears it from the route", async () => {
    const seen = serveGames();
    localStorage.setItem(LIBRARY_VIEW_KEY, "simple");

    function Launch() {
      const navigate = useNavigate();
      const location = useLocation();
      return (
        <>
          <button
            type="button"
            onClick={() =>
              navigate("/guided", {
                state: { guideSelection: { kind: "genre", genre: "Maze" } },
              })
            }
          >
            launch
          </button>
          <div data-testid="route-state">{JSON.stringify(location.state)}</div>
        </>
      );
    }
    const { RouteTree } = await import("./_libraryPageRouteTree");
    const user = userEvent.setup();
    renderLibraryPageTree(
      <RouteTree launcher={<Launch />} page={<PageForRoute />} />,
    );
    await user.click(await screen.findByRole("button", { name: "launch" }));

    await waitFor(() =>
      expect(seen.at(-1)?.searchParams.get("genre")).toBe("Maze"),
    );
    expect(seen.at(-1)?.searchParams.has("year_min")).toBe(true);
    await waitFor(() =>
      expect(screen.getByTestId("route-state").textContent).toBe("null"),
    );
  });
});

function PageForRoute() {
  return (
    <LibraryPage
      cart={makeFakeCart()}
      cartExpanded={false}
      onCartExpandedChange={() => {}}
    />
  );
}
