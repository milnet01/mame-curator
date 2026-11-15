/**
 * mame-curator-1146 INV-11 — a card's image address names its stored picture
 * choice, so a new choice is a new address the browser fetches.
 */
import { describe, expect, it } from "vitest";

import { pictureSrc } from "../pictureSrc";

describe("pictureSrc", () => {
  it("is the plain boxart address with no choice", () => {
    expect(pictureSrc({ short_name: "pacman", picture: null })).toBe(
      "/media/pacman/boxart",
    );
  });

  it("names the choice with v=<source>.<kind>", () => {
    expect(
      pictureSrc({
        short_name: "pacman",
        picture: { source: "esde", kind: "title" },
      }),
    ).toBe("/media/pacman/boxart?v=esde.title");
  });

  it("mame-curator-1143: a fresh look is a new address, after the choice", () => {
    expect(pictureSrc({ short_name: "pacman", picture: null }, 2)).toBe(
      "/media/pacman/boxart?r=2",
    );
    expect(
      pictureSrc(
        { short_name: "pacman", picture: { source: "esde", kind: "title" } },
        1,
      ),
    ).toBe("/media/pacman/boxart?v=esde.title&r=1");
  });

  it("escapes the game's name", () => {
    expect(pictureSrc({ short_name: "a b", picture: null })).toBe(
      "/media/a%20b/boxart",
    );
  });
});
