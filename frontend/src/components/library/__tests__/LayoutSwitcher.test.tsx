import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LayoutSwitcher } from "../LayoutSwitcher";
import type { LayoutName } from "@/api/types";

describe("LayoutSwitcher", () => {
  it("shows the current layout label", () => {
    render(<LayoutSwitcher value="masonry" onChange={() => {}} />);
    expect(
      screen.getByRole("button", { name: /masonry/i }),
    ).toBeInTheDocument();
  });

  it("lists every layout option in the menu", async () => {
    const user = userEvent.setup();
    render(<LayoutSwitcher value="masonry" onChange={() => {}} />);
    await user.click(screen.getByRole("button", { name: /masonry/i }));
    for (const layout of ["Masonry", "List", "Covers"]) {
      expect(
        await screen.findByRole("menuitemradio", { name: layout }),
      ).toBeInTheDocument();
    }
  });

  // mame-curator-1155: Grouped drew the same grid as Masonry.
  it("does not offer Grouped", async () => {
    const user = userEvent.setup();
    render(<LayoutSwitcher value="masonry" onChange={() => {}} />);
    await user.click(screen.getByRole("button", { name: /masonry/i }));
    expect(await screen.findAllByRole("menuitemradio")).toHaveLength(3);
    expect(
      screen.queryByRole("menuitemradio", { name: "Grouped" }),
    ).not.toBeInTheDocument();
  });

  it("calls onChange with the picked layout", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn<(name: LayoutName) => void>();
    render(<LayoutSwitcher value="masonry" onChange={onChange} />);
    await user.click(screen.getByRole("button", { name: /masonry/i }));
    await user.click(
      await screen.findByRole("menuitemradio", { name: "List" }),
    );
    expect(onChange).toHaveBeenCalledWith("list");
  });
});
