import { describe, expect, it } from "vitest";
import { folderOf } from "../folderOf";

describe("folderOf", () => {
  it.each([
    ["/mnt/lists/mame.dat", "/mnt/lists"],
    ["/mame.dat", "/"],
    ["C:\\lists\\mame.dat", "C:\\lists"],
    ["C:\\mame.dat", "C:\\"],
    ["\\\\nas\\share\\mame.dat", "\\\\nas\\share"],
    ["relative/mame.dat", "relative"],
    // A backslash is an ordinary character in a Linux name.
    ["/mnt/odd\\name.dat", "/mnt"],
    // Typed by hand on Windows.
    ["C:\\lists/mame.dat", "C:\\lists"],
  ])("%s is in %s", (file, folder) => {
    expect(folderOf(file)).toBe(folder);
  });

  it.each([["mame.dat"], [""]])("%j names no folder", (file) => {
    expect(folderOf(file)).toBeUndefined();
  });
});
