/**
 * mame-curator-1233 (CR-09-2): a card's cart button is announced as
 * "Remove … from cart" once the game is held, so pressing it must remove it.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { http, HttpResponse, server } from "@/test/handlers";
import { LibraryPage } from "../LibraryPage";
import {
  libraryPageBaseHandlers,
  makeFakeCart,
  makeGameCard,
  makeGamesPage,
  renderLibraryPageTree,
} from "./_libraryPageFixtures";

// The virtualizer draws no rows in a box of zero size, and jsdom has only those.
beforeEach(() => {
  localStorage.clear();
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1200);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1200);
  server.use(
    http.get("/api/games", () =>
      HttpResponse.json(
        makeGamesPage([
          makeGameCard({ short_name: "pacman", description: "Pac-Man" }),
        ]),
      ),
    ),
    ...libraryPageBaseHandlers(),
  );
});
afterEach(() => vi.restoreAllMocks());

describe("LibraryPage: the card's cart button", () => {
  it("removes a game already in the cart", async () => {
    const user = userEvent.setup();
    const toggle = vi.fn();
    const add = vi.fn();
    renderLibraryPageTree(
      <LibraryPage
        cart={{ ...makeFakeCart(), has: () => true, toggle, add }}
        cartExpanded={false}
        onCartExpandedChange={() => {}}
      />,
    );
    await user.click(
      await screen.findByRole("button", { name: "Remove Pac-Man from cart" }),
    );
    expect(toggle).toHaveBeenCalledWith("pacman");
    expect(add).not.toHaveBeenCalled();
  });
});
