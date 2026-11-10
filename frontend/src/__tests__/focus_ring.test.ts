/**
 * mame-curator-1205 — one strong focus ring on every control.
 *
 * The green buttons drew their ring in their own fill colour, other buttons a
 * faint half-opacity ring, and the guide's focused heading none at all. A user
 * with a magnifier could not see where focus was. jsdom cannot draw focus, so
 * these read the stylesheet: one rule, outside every cascade layer so no
 * component's `outline-none` or `ring-*` can undo it.
 */
import { describe, expect, it } from "vitest";
import css from "../index.css?raw";

/** Each top-level rule (not inside @layer, @theme or a media query). */
function topLevelRules(source: string): { selector: string; body: string }[] {
  const rules: { selector: string; body: string }[] = [];
  const text = source.replace(/\/\*[\s\S]*?\*\//g, "");
  let depth = 0;
  let start = 0;
  let selectorEnd = 0;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === "{") {
      if (depth === 0) selectorEnd = i;
      depth++;
    } else if (c === "}") {
      depth--;
      if (depth === 0) {
        rules.push({
          selector: text.slice(start, selectorEnd).trim(),
          body: text.slice(selectorEnd + 1, i),
        });
        start = i + 1;
      }
    } else if (c === ";" && depth === 0) {
      start = i + 1; // an @import or @source statement
    }
  }
  return rules;
}

function focusRule() {
  const rule = topLevelRules(css).find((r) =>
    r.selector.split(",").some((s) => s.trim() === ":focus-visible"),
  );
  expect(rule, "an unlayered :focus-visible rule").toBeDefined();
  return rule!;
}

describe("the shared focus ring (mame-curator-1205)", () => {
  it("is at least 3px in the text colour, set off from the control by a gap", () => {
    const { body } = focusRule();
    const outline =
      /(?:^|[;\s])outline:\s*(\d+)px\s+solid\s+var\(--foreground\)/.exec(body);
    expect(outline, "outline: <n>px solid var(--foreground)").not.toBeNull();
    expect(Number(outline![1])).toBeGreaterThanOrEqual(3);
    const offset = /outline-offset:\s*(\d+)px/.exec(body);
    expect(offset, "outline-offset").not.toBeNull();
    expect(Number(offset![1])).toBeGreaterThanOrEqual(2);
  });

  it("clears the controls' own rings, which filled the gap in the button's colour", () => {
    const { body } = focusRule();
    expect(body).toMatch(/--tw-ring-shadow:\s*0 0 #0000/);
    expect(body).toMatch(/--tw-ring-offset-shadow:\s*0 0 #0000/);
  });

  it("also marks a heading the guide moved focus to, however it got there", () => {
    const { selector } = focusRule();
    expect(selector.split(",").map((s) => s.trim())).toContain(
      'h1[tabindex="-1"]:focus',
    );
  });
});
