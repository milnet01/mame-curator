/** mame-curator-1145 §4.3 — the playlist goes inside the chosen destination. */
import { describe, expect, it } from "vitest";
import { playlistIn } from "../playlistPath";

describe("playlistIn", () => {
  it("joins with the slash the folder uses", () => {
    expect(playlistIn("/mnt/copied")).toBe("/mnt/copied/mame.lpl");
    expect(playlistIn("D:\\Copied")).toBe("D:\\Copied\\mame.lpl");
  });

  it("adds no second slash after a trailing one", () => {
    expect(playlistIn("/")).toBe("/mame.lpl");
    expect(playlistIn("D:\\")).toBe("D:\\mame.lpl");
  });
});
