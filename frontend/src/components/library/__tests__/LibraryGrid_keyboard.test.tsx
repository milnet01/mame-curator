/**
 * mame-curator-1144 review, Group 2 — the Library by keyboard alone. jsdom
 * cannot show a ring or a scroll, so the browser half is
 * frontend/e2e/library-keyboard.spec.ts.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createEvent, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LibraryGrid } from "../LibraryGrid";
import type { GameCard, StateView } from "@/api/types";

// The virtualizer draws no rows in a box of zero size, and jsdom has only those.
beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(2000);
  vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(1200);
});
afterEach(() => vi.restoreAllMocks());

const cards: GameCard[] = Array.from({ length: 12 }, (_, i) => ({
  short_name: `g${i}`,
  description: `Game ${i}`,
  year: 1990,
  manufacturer: "Mfr",
  publisher: "Pub",
  developer: "Dev",
  badges: [],
}));

function setup(reviewState?: StateView) {
  const handlers = {
    onOpen: vi.fn(),
    onAdd: vi.fn(),
    onSetReviewState: vi.fn(),
    onClearReviewState: vi.fn(),
  };
  const view = render(
    <>
      <LibraryGrid
        cards={cards}
        layout="covers"
        isInCart={() => false}
        reviewState={reviewState}
        {...handlers}
      />
      <button type="button">after the grid</button>
    </>,
  );
  return { ...handlers, ...view, user: userEvent.setup() };
}

const card = (i: number) => screen.getByRole("button", { name: `Game ${i}` });
const add = (i: number) =>
  screen.getByRole("button", { name: new RegExp(`Add Game ${i}\\b`, "i") });

describe("LibraryGrid: arrow keys move real focus", () => {
  it("moves focus across and down, and Home and End reach the ends", async () => {
    const { user } = setup();
    card(0).focus();
    await user.keyboard("{ArrowRight}");
    expect(card(1)).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(card(4)).toHaveFocus();
    await user.keyboard("{ArrowUp}{ArrowLeft}");
    expect(card(0)).toHaveFocus();
    await user.keyboard("{End}");
    expect(card(11)).toHaveFocus();
    await user.keyboard("{Home}");
    expect(card(0)).toHaveFocus();
  });

  it("an arrow at the edge moves nothing and cannot pull focus back later", async () => {
    const { user, rerender } = setup();
    card(0).focus();
    await user.keyboard("{ArrowLeft}");
    expect(card(0)).toHaveFocus();
    const outside = screen.getByRole("button", { name: "after the grid" });
    outside.focus();
    rerender(
      <>
        <LibraryGrid
          cards={cards}
          layout="covers"
          isInCart={() => false}
          onOpen={() => {}}
          onAdd={() => {}}
        />
        <button type="button">after the grid</button>
      </>,
    );
    expect(
      screen.getByRole("button", { name: "after the grid" }),
    ).toHaveFocus();
  });

  it("Tab stops on one card and its Add, then leaves the grid", async () => {
    const { user } = setup();
    await user.tab();
    expect(card(0)).toHaveFocus();
    await user.tab();
    expect(add(0)).toHaveFocus();
    await user.tab();
    expect(
      screen.getByRole("button", { name: "after the grid" }),
    ).toHaveFocus();
  });

  it("Tab comes back to the card the arrows reached", async () => {
    const { user } = setup();
    card(0).focus();
    await user.keyboard("{ArrowRight}");
    await user.tab();
    expect(add(1)).toHaveFocus();
    await user.tab({ shift: true });
    expect(card(1)).toHaveFocus();
  });
});

describe("LibraryGrid: keys act on the game that has focus", () => {
  it("Enter opens the focused game, once", async () => {
    const { user, onOpen } = setup();
    card(4).focus();
    await user.keyboard("{Enter}");
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen).toHaveBeenCalledWith(cards[4]);
  });

  it("R marks the game focus reached by a click, not the first one", async () => {
    const { user, onSetReviewState } = setup();
    await user.click(card(5));
    await user.keyboard("r");
    expect(onSetReviewState).toHaveBeenCalledWith("g5", "reviewed");
  });

  it("R and O still reach the game whose Add button has focus", async () => {
    const { user, onSetReviewState, onOpen } = setup();
    add(3).focus();
    await user.keyboard("r");
    expect(onSetReviewState).toHaveBeenCalledWith("g3", "reviewed");
    add(4).focus();
    await user.keyboard("o");
    expect(onOpen).toHaveBeenCalledWith(cards[4]);
  });

  it.each(["{Enter}", " "])(
    "%s on Add adds the game and opens nothing",
    async (key) => {
      const { user, onAdd, onOpen } = setup();
      add(2).focus();
      await user.keyboard(key);
      expect(onAdd).toHaveBeenCalledTimes(1);
      expect(onAdd).toHaveBeenCalledWith("g2");
      expect(onOpen).not.toHaveBeenCalled();
    },
  );

  it("walkthrough moves focus to the next pending game after R", async () => {
    const { user } = setup({ entries: { g1: "reviewed" } } as StateView);
    card(0).focus();
    await user.keyboard("r");
    expect(card(2)).toHaveFocus();
  });
});

describe("LibraryGrid: a key with Ctrl, Cmd or Alt is not the grid's", () => {
  it.each([
    ["Ctrl+R", { key: "r", ctrlKey: true }],
    ["Ctrl+S", { key: "s", ctrlKey: true }],
    ["Ctrl+K", { key: "k", ctrlKey: true }],
    ["Ctrl+O", { key: "o", ctrlKey: true }],
    ["Ctrl+J", { key: "j", ctrlKey: true }],
    ["Cmd+R", { key: "r", metaKey: true }],
    ["Alt+ArrowRight", { key: "ArrowRight", altKey: true }],
  ])("%s does nothing and stays the browser's", (_name, init) => {
    const { onOpen, onSetReviewState, onClearReviewState } = setup();
    const start = card(4);
    start.focus();
    const event = createEvent.keyDown(start, init);
    fireEvent(start, event);
    expect(event.defaultPrevented).toBe(false);
    expect(onOpen).not.toHaveBeenCalled();
    expect(onSetReviewState).not.toHaveBeenCalled();
    expect(onClearReviewState).not.toHaveBeenCalled();
    expect(start).toHaveFocus();
  });
});
