/**
 * mame-curator-1233 (RR-10-4): a page's load-failure Retry ignores presses
 * while a retry is under way, as the Library's and the drawer's do.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { RouteLoadError } from "../RouteLoadError";
import { strings } from "@/strings";

describe("RouteLoadError", () => {
  it("ignores Retry while retrying, keeping it focusable", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <RouteLoadError message="Could not load." onRetry={onRetry} retrying />,
    );
    const button = screen.getByRole("button", {
      name: strings.common.retrying,
    });
    expect(button).not.toBeDisabled();
    await user.click(button);
    expect(onRetry).not.toHaveBeenCalled();
  });
});
