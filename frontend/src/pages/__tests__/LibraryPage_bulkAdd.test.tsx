/**
 * mame-curator-1151 — Add all adds the games on screen, so it asks for the
 * same list the page shows, review filter included.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
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

const card = (name: string) =>
  makeGameCard({ short_name: name, description: name });

beforeEach(() => {
  localStorage.setItem(LIBRARY_VIEW_KEY, "full");
});

describe("Add all with a review filter on", () => {
  it("adds only the games the filter shows", async () => {
    const asked: URLSearchParams[] = [];
    server.use(
      ...libraryPageBaseHandlers(),
      http.get("/api/games", ({ request }) => {
        const params = new URL(request.url).searchParams;
        asked.push(params);
        return HttpResponse.json(
          makeGamesPage(
            params.get("review_state") === "reviewed"
              ? [card("seen")]
              : [card("other1"), card("other2")],
          ),
        );
      }),
    );
    const addAll = vi.fn(() => ({ added: 1, truncated: 0 }));
    const user = userEvent.setup();
    renderLibraryPageTree(
      <LibraryPage
        cart={{ ...makeFakeCart(), addAll }}
        cartExpanded={false}
        onCartExpandedChange={() => {}}
      />,
    );

    const tile = strings.library.featured.tiles[0];
    await user.click(await screen.findByRole("button", { name: tile.title }));
    await user.click(
      screen.getByRole("radio", {
        name: strings.library.reviewState.optionReviewed,
      }),
    );
    await user.click(
      await screen.findByRole("button", {
        name: strings.library.cart.bulkAdd(1),
      }),
    );

    await waitFor(() => expect(addAll).toHaveBeenCalledOnce());
    expect(addAll).toHaveBeenCalledWith(["seen"]);
    const bulk = asked.find((p) => p.get("page_size") === "500");
    expect(bulk?.get("publisher")).toBe(tile.query.publisher);
  });
});
