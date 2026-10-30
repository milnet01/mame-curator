import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { AboutTab } from "../AboutTab";

// mame-curator-1133: a support link, and the house-style disclaimer the
// website session asked for (2026-10-16). No feature is gated on donating.

describe("AboutTab (mame-curator-1133)", () => {
  it("links to the GitHub Sponsors page in a new tab", () => {
    render(<AboutTab />);
    const link = screen.getByRole("link", {
      name: "Support this project on GitHub Sponsors (opens in a new tab)",
    });
    expect(link).toHaveAttribute(
      "href",
      "https://github.com/sponsors/milnet01",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("states that the app ships no ROM files", () => {
    render(<AboutTab />);
    expect(
      screen.getByText(/does not include, distribute or host any ROM files/),
    ).toBeInTheDocument();
  });

  // review-code 2026-10-30 #4: design.md lists About as "version, license, links".
  it("shows the running version and the licence", () => {
    render(<AboutTab version="1.3.0" />);
    expect(screen.getByText("Version 1.3.0")).toBeInTheDocument();
    expect(screen.getByText(/MIT License/)).toBeInTheDocument();
  });

  it("omits the version line until the version is known", () => {
    render(<AboutTab />);
    expect(screen.queryByText(/^Version /)).not.toBeInTheDocument();
  });
});
