/** mame-curator-1144 review — saving a session when settings did not load. */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";

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

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

beforeEach(() => {
  localStorage.setItem(LIBRARY_VIEW_KEY, "full");
  vi.mocked(toast.error).mockClear();
});

describe("LibraryPage: saving a session", () => {
  it("says so when settings have not loaded, instead of closing silently", async () => {
    const user = userEvent.setup();
    server.use(
      // First match wins, so this outranks the base handlers' good config.
      http.get("/api/config", () =>
        HttpResponse.json({ detail: "no" }, { status: 500 }),
      ),
      http.get("/api/games", () =>
        HttpResponse.json(
          makeGamesPage([
            makeGameCard({ short_name: "pacman", description: "Pac-Man" }),
          ]),
        ),
      ),
      ...libraryPageBaseHandlers(),
    );
    renderLibraryPageTree(
      <LibraryPage
        cart={makeFakeCart()}
        cartExpanded={false}
        onCartExpandedChange={() => {}}
      />,
    );
    await screen.findByTestId("library-grid");
    await user.click(
      screen.getByRole("button", { name: /save (as )?session/i }),
    );
    await user.type(
      screen.getByLabelText(strings.library.filters.sessionNameLabel),
      "mine",
    );
    await user.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(strings.library.sessionNotSaved),
    );
  });
});
