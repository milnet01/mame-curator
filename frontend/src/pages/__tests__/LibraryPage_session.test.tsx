/** Saving a session from the Library (mame-curator-1144 review, 1156). */
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
import { ERROR_TOAST } from "@/lib/apiErrorToast";

vi.mock("sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

beforeEach(() => {
  localStorage.setItem(LIBRARY_VIEW_KEY, "full");
  vi.mocked(toast.error).mockClear();
});

/** Every session body the page sent to POST /api/sessions. */
function serveSessions(): unknown[] {
  const sent: unknown[] = [];
  server.use(
    http.post("/api/sessions", async ({ request }) => {
      const body = (await request.json()) as { name: string; session: unknown };
      sent.push(body.session);
      return HttpResponse.json({
        active: null,
        sessions: { [body.name]: body.session },
      });
    }),
  );
  return sent;
}

async function saveAs(user: ReturnType<typeof userEvent.setup>, name: string) {
  await user.click(screen.getByRole("button", { name: /save (as )?session/i }));
  await user.type(
    screen.getByLabelText(strings.library.filters.sessionNameLabel),
    name,
  );
  await user.click(screen.getByRole("button", { name: /^save$/i }));
}

function renderPage() {
  return renderLibraryPageTree(
    <LibraryPage
      cart={makeFakeCart()}
      cartExpanded={false}
      onCartExpandedChange={() => {}}
    />,
  );
}

const pacman = makeGameCard({ short_name: "pacman", description: "Pac-Man" });

describe("LibraryPage: saving a session", () => {
  // mame-curator-1156: a session saves what is on screen now. It used to save
  // the preferred genres from Settings, so it also needed them loaded.
  it("saves the publisher and years on screen, not the preferences in Settings", async () => {
    const user = userEvent.setup();
    const sent = serveSessions();
    server.use(
      http.get("/api/games", () => HttpResponse.json(makeGamesPage([pacman]))),
      ...libraryPageBaseHandlers(),
    );
    renderPage();
    await screen.findByTestId("library-grid");
    await user.click(
      screen.getByRole("button", {
        name: new RegExp(strings.library.featured.tiles[0].title),
      }),
    );
    await saveAs(user, "capcom");
    await waitFor(() =>
      expect(sent).toEqual([
        {
          include_year_range: [1975, 2000],
          include_genres: [],
          include_publishers: ["Capcom"],
          include_developers: [],
        },
      ]),
    );
  });

  it("saves even when settings have not loaded", async () => {
    const user = userEvent.setup();
    const sent = serveSessions();
    server.use(
      // First match wins, so this outranks the base handlers' good config.
      http.get("/api/config", () =>
        HttpResponse.json({ detail: "no" }, { status: 500 }),
      ),
      http.get("/api/games", () => HttpResponse.json(makeGamesPage([pacman]))),
      ...libraryPageBaseHandlers(),
    );
    renderPage();
    await screen.findByTestId("library-grid");
    await saveAs(user, "mine");
    await waitFor(() => expect(sent).toHaveLength(1));
    expect(toast.error).not.toHaveBeenCalledWith(
      expect.anything(),
      ERROR_TOAST,
    );
  });
});
