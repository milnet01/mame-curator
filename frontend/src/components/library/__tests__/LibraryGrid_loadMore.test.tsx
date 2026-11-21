/**
 * mame-curator-1234 (CR-09-5) — the grid asks for more games as the user
 * nears the end of those loaded, and the walkthrough looks in the next page
 * before it says "All caught up" (P14 open design call 12).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { toast } from "sonner";

import { LibraryGrid } from "../LibraryGrid";
import type { GameCard, ReviewStateValue, StateView } from "@/api/types";
import { strings } from "@/strings";

// The virtualizer draws no rows in a box of zero size, and jsdom has only those.
beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1200);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1200);
});
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

const makeCards = (n: number): GameCard[] =>
  Array.from({ length: n }, (_, i) => ({
    short_name: `g${i}`,
    description: `Game ${i}`,
    year: 1990,
    manufacturer: "Mfr",
    publisher: "Pub",
    developer: "Dev",
    badges: [],
    picture: null,
  }));

function grid(
  cards: GameCard[],
  props: {
    hasMore: boolean;
    onLoadMore: () => void;
    reviewState?: StateView;
    onSetReviewState?: (shortName: string, state: ReviewStateValue) => void;
  },
) {
  return (
    <LibraryGrid
      cards={cards}
      layout="covers"
      isInCart={() => false}
      onOpen={() => {}}
      onToggleCart={() => {}}
      onClearReviewState={() => {}}
      {...props}
    />
  );
}

const card = (i: number) => screen.getByRole("button", { name: `Game ${i}` });

describe("LibraryGrid: loads more games near the end", () => {
  it("asks for more when the last loaded row is drawn", () => {
    const onLoadMore = vi.fn();
    render(grid(makeCards(12), { hasMore: true, onLoadMore }));
    expect(onLoadMore).toHaveBeenCalled();
  });

  it("asks for none once every game is loaded", () => {
    const onLoadMore = vi.fn();
    render(grid(makeCards(12), { hasMore: false, onLoadMore }));
    expect(onLoadMore).not.toHaveBeenCalled();
  });

  it("asks for none while the end is far off, and asks when End reaches it", async () => {
    const onLoadMore = vi.fn();
    render(grid(makeCards(300), { hasMore: true, onLoadMore }));
    expect(onLoadMore).not.toHaveBeenCalled();
    card(0).focus();
    await userEvent.setup().keyboard("{End}");
    expect(onLoadMore).toHaveBeenCalled();
  });
});

describe("LibraryGrid: the walkthrough looks in the next page", () => {
  const reviewState: StateView = {
    entries: { g1: "reviewed", g2: "skipped" },
  };

  it("loads the next page instead of saying all caught up, then moves on", async () => {
    const success = vi.spyOn(toast, "success");
    const onLoadMore = vi.fn();
    const props = {
      hasMore: true,
      onLoadMore,
      reviewState,
      onSetReviewState: vi.fn(),
    };
    const { rerender } = render(grid(makeCards(3), props));
    onLoadMore.mockClear();
    card(0).focus();
    await userEvent.setup().keyboard("r");

    expect(onLoadMore).toHaveBeenCalled();
    expect(success).not.toHaveBeenCalledWith(
      strings.library.walkthroughCaughtUp,
    );

    rerender(grid(makeCards(5), { ...props, hasMore: false }));
    expect(await screen.findByRole("button", { name: "Game 3" })).toHaveFocus();
    expect(success).not.toHaveBeenCalled();
  });

  it("says all caught up when no page is left", async () => {
    const success = vi.spyOn(toast, "success");
    render(
      grid(makeCards(3), {
        hasMore: false,
        onLoadMore: vi.fn(),
        reviewState,
        onSetReviewState: vi.fn(),
      }),
    );
    card(0).focus();
    await userEvent.setup().keyboard("r");
    expect(success).toHaveBeenCalledWith(strings.library.walkthroughCaughtUp);
  });
});
