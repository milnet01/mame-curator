// mame-curator-1138: a link that opens a new tab says so (WCAG technique G201).
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ExternalLink } from "../ExternalLink";
import { strings } from "@/strings";

// Every screen file, as text, to find a new-tab link made some other way.
const sources = import.meta.glob<string>(["../../**/*.tsx"], {
  query: "?raw",
  import: "default",
  eager: true,
});

describe("ExternalLink (mame-curator-1138)", () => {
  it("opens a new tab safely and says so in its name", () => {
    render(<ExternalLink href="https://example.org/">Read more</ExternalLink>);
    const link = screen.getByRole("link", {
      name: `Read more ${strings.common.opensInNewTab}`,
    });
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    expect(link).toHaveAttribute("href", "https://example.org/");
  });

  it("is the only way a screen opens a new tab", () => {
    const offenders = Object.entries(sources)
      .filter(([path]) => !path.includes("__tests__"))
      .filter(([path]) => !path.endsWith("/ExternalLink.tsx"))
      .filter(([, text]) => /\starget=["{]/.test(text))
      .map(([path]) => path);
    expect(offenders).toEqual([]);
  });
});
