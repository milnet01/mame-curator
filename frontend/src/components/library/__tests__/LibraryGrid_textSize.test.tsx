/**
 * mame-curator-1144 — enlarged text must not clip a fixed-height grid row, so
 * rows grow with the root font size. The browser half is INV-10, in
 * frontend/e2e/guide-flow.spec.ts.
 */
import { afterEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { LibraryGrid } from "../LibraryGrid";

const cards = Array.from({ length: 5 }, (_, i) => ({
  short_name: `game${i}`,
  description: `Game ${i}`,
  year: 1990,
  manufacturer: "Namco",
  publisher: "Namco",
  developer: "Namco",
  badges: [],
}));

function spacerHeight() {
  render(
    <LibraryGrid
      cards={cards}
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
