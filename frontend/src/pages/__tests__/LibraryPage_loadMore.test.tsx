/**
 * mame-curator-1234 (CR-09-5) — the Library shows every game, loading the
 * next page as the user nears the end of those loaded, in both views.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LIBRARY_VIEW_KEY } from "@/lib/libraryView";
import { http, HttpResponse, server } from "@/test/handlers";
import { LibraryPage } from "../LibraryPage";
import {
  libraryPageBaseHandlers,
  makeFakeCart,
  makeGameCard,
  renderLibraryPageTree,
} from "./_libraryPageFixtures";

const TOTAL = 250;
const all = Array.from({ length: TOTAL }, (_, i) =>
  makeGameCard({ short_name: `g${i}`, description: `Game ${i}` }),
);

/** Serves `all` a page at a time, and records the pages the grid asked for. */
function serveGames(): number[] {
  const pages: number[] = [];
  server.use(
    http.get("/api/games", ({ request }) => {
      const url = new URL(request.url);
      const size = Number(url.searchParams.get("page_size"));
      const page = Number(url.searchParams.get("page"));
      if (size !== 1) pages.push(page);
      const start = (page - 1) * size;
      return HttpResponse.json({
        items: all.slice(start, start + size),
        page,
        page_size: size,
        total: TOTAL,
        total_bytes: 0,
      });
    }),
    ...libraryPageBaseHandlers(),
  );
  return pages;
}

// The virtualizer draws no rows in a box of zero size, and jsdom has only those.
beforeEach(() => {
  localStorage.clear();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1200);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1200);
});
afterEach(() => vi.restoreAllMocks());

describe.each(["simple", "full"] as const)(
  "LibraryPage (%s view): loads more games as the user scrolls",
  (view) => {
    it("loads the next page at the end, and stops when every game is in", async () => {
      const pages = serveGames();
      localStorage.setItem(LIBRARY_VIEW_KEY, view);
      renderLibraryPageTree(
        <LibraryPage
          cart={makeFakeCart()}
          cartExpanded={false}
          onCartExpandedChange={() => {}}
        />,
      );
      const first = await screen.findByRole("button", { name: "Game 0" });
      expect(pages).toEqual([1]);

      first.focus();
      const user = userEvent.setup();
      await user.keyboard("{End}");
      await waitFor(() => expect(pages).toEqual([1, 2]));
      // jsdom never scrolls, so a far-off card is not drawn; the grid's row
      // count shows the second page was added.
      const grid = screen.getByTestId("library-grid");
      const columns = Number(grid.dataset.columns);
      await waitFor(() =>
        expect(grid).toHaveAttribute(
          "aria-rowcount",
          String(Math.ceil(TOTAL / columns)),
        ),
      );
      expect(grid).toContainElement(document.activeElement as HTMLElement);
      await user.keyboard("{End}");
      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(pages).toEqual([1, 2]);
    });
  },
);
