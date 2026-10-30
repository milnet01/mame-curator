/**
 * mame-curator-1144 INV-9 — the stored text size is applied before first
 * paint, every size scales rem text, and an unknown value gives the default.
 */
import { afterEach, describe, expect, it } from "vitest";
import mainSource from "@/main.tsx?raw";
import {
  DEFAULT_TEXT_SIZE,
  TEXT_SIZE_KEY,
  TEXT_SIZES,
  applyTextSize,
  readTextSize,
  rootFontScale,
  setTextSize,
} from "../textSize";

afterEach(() => {
  localStorage.clear();
  document.documentElement.style.fontSize = "";
});

describe("textSize", () => {
  it("defaults to large, which is bigger than the browser's own size", () => {
    expect(DEFAULT_TEXT_SIZE).toBe("large");
    applyTextSize();
    expect(document.documentElement.style.fontSize).toBe("125%");
  });

  it.each(Object.entries(TEXT_SIZES))(
    "applies the stored size %s to the root",
    (name, value) => {
      localStorage.setItem(TEXT_SIZE_KEY, name);
      applyTextSize();
      expect(document.documentElement.style.fontSize).toBe(value);
    },
  );

  it("falls back to the default for an unknown stored value", () => {
    localStorage.setItem(TEXT_SIZE_KEY, "toString");
    expect(readTextSize()).toBe(DEFAULT_TEXT_SIZE);
    applyTextSize();
    expect(document.documentElement.style.fontSize).toBe("125%");
  });

  it("remembers a chosen size and applies it at once", () => {
    setTextSize("largest");
    expect(localStorage.getItem(TEXT_SIZE_KEY)).toBe("largest");
    expect(document.documentElement.style.fontSize).toBe("200%");
  });

  it("reads the root size over 16 as the scale", () => {
    document.documentElement.style.fontSize = "32px";
    expect(rootFontScale()).toBe(2);
    document.documentElement.style.fontSize = "";
    expect(rootFontScale()).toBe(1);
  });

  it("main.tsx applies the size before it creates the React root", () => {
    const apply = mainSource.indexOf("applyTextSize()");
    const root = mainSource.indexOf("createRoot(document");
    expect(apply).toBeGreaterThan(-1);
    expect(apply).toBeLessThan(root);
  });
});
