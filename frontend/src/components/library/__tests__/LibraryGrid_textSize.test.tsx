/**
 * mame-curator-1144 — enlarged text must not clip a fixed-height grid row, so
 * rows grow with the root font size. The browser half is INV-10, in
 * frontend/e2e/guide-flow.spec.ts.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { LibraryGrid } from "../LibraryGrid";

const cards = Array.from({ length: 100 }, (_, i) => ({
  short_name: `game${i}`,
  description: `Game ${i}`,
  year: 1990,
  manufacturer: "Namco",
  publisher: "Namco",
  developer: "Namco",
  badges: [],
  picture: null,
}));

function spacerHeight() {
  render(
    <LibraryGrid
      cards={cards.slice(0, 5)}
      layout="list"
      onOpen={() => {}}
      isInCart={() => false}
      onAdd={() => {}}
    />,
  );
  const spacer = screen.getByTestId("library-grid").firstElementChild;
  return (spacer as HTMLElement).style.height;
}

afterEach(() => {
  document.documentElement.style.fontSize = "";
  vi.restoreAllMocks();
});

describe("LibraryGrid row height", () => {
  it("keeps the layout's height at the browser's own size", () => {
    expect(spacerHeight()).toBe(`${5 * 96}px`);
  });

  it("doubles the row height when the root size doubles", () => {
    document.documentElement.style.fontSize = "32px";
    expect(spacerHeight()).toBe(`${5 * 96 * 2}px`);
  });
});

// mame-curator-1156: rows grow with the text, so a scroll offset kept in
// pixels would land on a different game.
describe("LibraryGrid scroll position", () => {
  it("keeps the same game at the top when the text size changes", () => {
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(500);
    vi.spyOn(HTMLElement.prototype, "offsetWidth", "get").mockReturnValue(800);
    render(
      <LibraryGrid
        cards={cards}
        layout="list"
        onOpen={() => {}}
        isInCart={() => false}
        onAdd={() => {}}
      />,
    );
    const grid = screen.getByTestId("library-grid");
    grid.scrollTop = 10 * 96; // the eleventh game is at the top
    act(() => {
      document.documentElement.style.fontSize = "32px";
      // What setTextSize sends once the new size is applied.
      window.dispatchEvent(new Event("mame-curator:text-size-change"));
    });
    expect(grid.scrollTop).toBe(10 * 96 * 2);
  });
});
