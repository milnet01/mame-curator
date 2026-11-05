/**
 * mame-curator-1149 — choosing a version when the current pick is a clone.
 * The server's own behaviour is in tests/api/test_mame_curator_1149_*; the
 * real path is in e2e/version-choice.spec.ts.
 */
import {
  afterAll,
  beforeAll,
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";
import { renderHook, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";

import { Route, Routes } from "react-router";

import { LibraryPage } from "../LibraryPage";
import { FixVersionRoute } from "../FixVersionPage";
import { useOverride } from "@/hooks/useAlternatives";
import { delay } from "msw";
import { server, http, HttpResponse } from "@/test/handlers";
import { strings } from "@/strings";
import {
  libraryPageBaseHandlers,
  makeFakeCart,
  makeGameCard,
  makeGamesPage,
  renderLibraryPageTree,
} from "./_libraryPageFixtures";
import type { UseCartResult } from "@/hooks/useCart";
import { ERROR_TOAST } from "@/lib/apiErrorToast";

vi.mock("sonner", async (original) => ({
  ...(await original<typeof import("sonner")>()),
  toast: { success: vi.fn(), warning: vi.fn(), error: vi.fn() },
}));

// jsdom has no layout, and the grid draws no card without a sized scroll area
// (LibraryPage_loading_state.test.tsx says which sizes the virtualizer reads).
const SIZES = {
  clientHeight: 600,
  clientWidth: 1200,
  offsetHeight: 600,
  offsetWidth: 1200,
};
const realRect = HTMLElement.prototype.getBoundingClientRect;
const realSizes = Object.keys(SIZES).map(
  (key) =>
    [key, Object.getOwnPropertyDescriptor(HTMLElement.prototype, key)] as const,
);

beforeAll(() => {
  for (const [key, value] of Object.entries(SIZES)) {
    Object.defineProperty(HTMLElement.prototype, key, {
      configurable: true,
      get: () => value,
    });
  }
  HTMLElement.prototype.getBoundingClientRect = () =>
    new DOMRect(0, 0, 1200, 600);
});

afterAll(() => {
  HTMLElement.prototype.getBoundingClientRect = realRect;
  for (const [key, descriptor] of realSizes) {
    if (descriptor) {
      Object.defineProperty(HTMLElement.prototype, key, descriptor);
    } else {
      delete (HTMLElement.prototype as unknown as Record<string, unknown>)[key];
    }
  }
});

const parent = makeGameCard({ short_name: "puck", description: "Puck World" });
const fast = makeGameCard({ short_name: "puckf", description: "Puck Fast" });
const junior = makeGameCard({
  short_name: "puckj",
  description: "Puck Junior",
});

/** Puts the clone `puckf` on show, after any `before`; a POST then answers
 *  as `reply` says. */
function serve(
  reply: () => Response,
  before: ReturnType<typeof makeGameCard>[] = [],
) {
  const posted: unknown[] = [];
  let shown = fast;
  server.use(
    ...libraryPageBaseHandlers(),
    // The reload is not instant, and the page must wait for it.
    http.get("/api/games", async () => {
      if (shown === junior) await delay(50);
      return HttpResponse.json(makeGamesPage([...before, shown]));
    }),
    http.get("/api/games/:name/alternatives", () =>
      HttpResponse.json({
        parent: "puck",
        items: [parent, fast, junior],
        in_use: shown.short_name,
      }),
    ),
    http.post("/api/overrides", async ({ request }) => {
      posted.push(await request.json());
      const response = reply();
      if (response.ok) shown = junior;
      return response;
    }),
  );
  return posted;
}

const accepted = (warnings: string[] = []) =>
  HttpResponse.json({ entries: { puck: "puckj" }, warnings });

async function chooseJunior(cart: UseCartResult = makeFakeCart()) {
  const user = userEvent.setup();
  renderLibraryPageTree(
    <LibraryPage
      cart={cart}
      cartExpanded={false}
      onCartExpandedChange={() => {}}
    />,
  );
  await user.click(await screen.findByText("Puck Fast"));
  await user.click(
    await screen.findByRole("button", { name: "Use Puck Junior" }),
  );
}

describe("choosing a version from a clone", () => {
  beforeEach(() => vi.clearAllMocks());

  it("saves under the family's real parent and names the choice", async () => {
    const posted = serve(() => accepted());
    await chooseJunior();
    await waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith(
        strings.library.overrideApplied("Puck Junior"),
      ),
    );
    expect(posted).toEqual([{ parent: "puck", winner: "puckj" }]);
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("moves focus to the chosen version's card", async () => {
    serve(() => accepted());
    await chooseJunior();
    const card = await screen.findByRole("button", { name: "Puck Junior" });
    await waitFor(() => expect(card).toHaveFocus());
  });

  it("says so, and not success, when the reply carries warnings", async () => {
    serve(() => accepted(["override key 'ghost' is not a known parent"]));
    await chooseJunior();
    await waitFor(() =>
      expect(toast.warning).toHaveBeenCalledWith(
        strings.library.overrideOldChoicesUnusable(1),
        expect.anything(),
      ),
    );
    expect(toast.success).not.toHaveBeenCalled();
  });

  it("says so, and not success, when the server refuses", async () => {
    serve(() =>
      HttpResponse.json(
        { code: "override_rejected", detail: "no", fields: [] },
        { status: 422 },
      ),
    );
    await chooseJunior();
    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        strings.errors.byCode.override_rejected,
        ERROR_TOAST,
      ),
    );
    expect(toast.success).not.toHaveBeenCalled();
  });

  it.each([
    ["under the clone on show", { shortName: "puckf" }],
    ["under the parent", { shortName: "puck" }],
    ["under an older version", { shortName: "puck", chosenVariant: "puckf" }],
  ])("updates a copy-list entry saved %s", async (_where, item) => {
    serve(() => accepted());
    const setVariant = vi.fn();
    const other = { shortName: "solo" };
    await chooseJunior({
      ...makeFakeCart(),
      items: [item, other],
      setVariant,
    });
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
    expect(setVariant).toHaveBeenCalledTimes(1);
    expect(setVariant).toHaveBeenCalledWith(item.shortName, "puckj");
  });
});

describe("coming back from the version guide (mame-curator-1196)", () => {
  beforeEach(() => vi.clearAllMocks());

  /** The guide at /fix/puckf, with the Library one link away. */
  function openGuide() {
    const cart = makeFakeCart();
    renderLibraryPageTree(
      <Routes>
        <Route
          path="/"
          element={
            <LibraryPage
              cart={cart}
              cartExpanded={false}
              onCartExpandedChange={() => {}}
            />
          }
        />
        <Route
          path="/fix/:shortName"
          element={<FixVersionRoute cart={cart} />}
        />
      </Routes>,
      { initialPath: "/fix/puckf" },
    );
    return userEvent.setup();
  }
  // The card is drawn again as the list settles, so look it up each time.
  const cardHasFocus = (name: string) =>
    waitFor(() => expect(screen.getByRole("button", { name })).toHaveFocus());
  const backToLibrary = () =>
    screen.findByRole("link", { name: strings.guide.fix.toLibrary });

  it("puts focus on the chosen version's card", async () => {
    // Another card first, so the grid's own first card is not the answer.
    serve(accepted, [
      makeGameCard({ short_name: "solo", description: "Solo" }),
    ]);
    const user = openGuide();
    await user.click(
      await screen.findByRole("button", { name: /Puck Junior/ }),
    );
    await screen.findByRole("heading", {
      name: strings.library.overrideApplied("Puck Junior"),
    });
    await user.click(await backToLibrary());
    await cardHasFocus("Puck Junior");
  });

  it("puts focus on the game's own card when nothing was chosen", async () => {
    serve(() => accepted());
    const user = openGuide();
    await screen.findByRole("heading", { name: strings.guide.fix.heading });
    await user.click(await backToLibrary());
    await cardHasFocus("Puck Fast");
  });

  it("puts focus on the game's own card when the version in use was chosen", async () => {
    serve(() => accepted());
    const user = openGuide();
    await user.click(await screen.findByRole("button", { name: /Puck Fast/ }));
    await screen.findByRole("heading", {
      name: strings.guide.fix.unchanged("Puck Fast"),
    });
    await user.click(await backToLibrary());
    await cardHasFocus("Puck Fast");
  });
});

it("marks every version's family list out of date after a choice", async () => {
  serve(() => accepted());
  const client = new QueryClient();
  // The version the panel was opened from is neither the parent nor the choice.
  client.setQueryData(["alternatives", "puckf"], {
    parent: "puck",
    items: [],
    in_use: "puckf",
  });
  const { result } = renderHook(() => useOverride(), {
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  });
  await result.current.mutateAsync({ parent: "puck", winner: "puckj" });
  expect(client.getQueryState(["alternatives", "puckf"])?.isInvalidated).toBe(
    true,
  );
});
